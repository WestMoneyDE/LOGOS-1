"""Inbox + radar pipeline (spec §9, order §14–16, §40–43).

Inbox: quick capture (idea | observation | paper | quote | experiment_idea | critique) -> UNTRIAGED.
Radar: RAW -> PARSED -> DEDUPLICATED -> SOURCE_CHECKED -> TRACK_MAPPED -> CLAIM_IMPACT_ANALYZED -> EVIDENCE_STRENGTH_ASSIGNED -> ACTION_PROPOSED -> REVIEWED -> ACCEPTED | REJECTED | DEFERRED.
Every step here is deterministic (regex/keyword heuristics over the registries) and produces a PROPOSAL, never a registry change: the founder reviews the delta
(BEFORE / PROPOSED / EVIDENCE / WHY / WHAT WOULD FALSIFY IT) and an accepted delta becomes a DRAFT (work order, research-brief draft, open-question draft, note) — still not a registry edit.
The optional AI_PROPOSAL (Claude job `radar_process`) is enqueued through the queue and waits for a founder Start like every Claude job.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from hashlib import sha256

from psycopg.rows import dict_row

INBOX_KINDS = ("idea", "observation", "paper", "quote", "experiment_idea", "critique")
PIPELINE = ("RAW", "PARSED", "DEDUPLICATED", "SOURCE_CHECKED", "TRACK_MAPPED", "CLAIM_IMPACT_ANALYZED", "EVIDENCE_STRENGTH_ASSIGNED", "ACTION_PROPOSED", "REVIEWED")
TERMINAL = ("ACCEPTED", "REJECTED", "DEFERRED")
DELTA_KINDS = ("work_order", "prior_art", "open_question", "claim_note", "invariant_note", "none")
TRACK_KEYWORDS = {"authority": ("authority", "grant", "delegation", "veto", "approval", "human-rooted", "autorität"), "provenance": ("provenance", "lineage", "binding", "causal", "herkunft"), "cognitive-provenance": ("cognitive", "attribution", "reasoning", "plan adoption", "assimilation"),
                  "measurement": ("measurement", "benchmark", "metric", "evaluation", "statistic", "messung"), "memory": ("memory", "consolidation", "recall", "gedächtnis", "state"), "trajectory": ("trajectory", "compromise", "containment", "drift", "trajektorie")}
URL = re.compile(r"https?://[^\s)>\]]+"); DOI = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+"); CLAIM = re.compile(r"\bLOGOS-[A-Z]+-\d{3}\b"); ARXIV = re.compile(r"\barXiv:\s*\d{4}\.\d{4,5}\b", re.I)
VERSION = "ros-radar/1"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


# -- inbox -------------------------------------------------------------------

def add_inbox(conn, kind: str, text: str, source: str | None, actor: str) -> dict:
    if kind not in INBOX_KINDS:
        raise ValueError(f"kind must be one of {INBOX_KINDS}")
    if not text.strip():
        raise ValueError("empty text")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_inbox_items (kind, text, source) VALUES (%s, %s, %s) RETURNING *", (kind, text.strip(), source)); row = cur.fetchone()
        cur.execute("INSERT INTO ros_radar_items (inbox_item_id, state, payload) VALUES (%s, 'RAW', %s) RETURNING *", (row["item_id"], json.dumps({"kind": kind, "text": text.strip(), "source": source, "history": [{"state": "RAW", "at": datetime.now(timezone.utc).isoformat(), "by": actor}]}))); radar = cur.fetchone()
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'inbox.add', %s, %s)", (actor, str(row["item_id"]), json.dumps({"kind": kind, "radar_id": radar["radar_id"]})))
    conn.commit()
    return {**row, "radar_id": radar["radar_id"]}


def list_inbox(conn, limit: int = 200) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT i.*, r.radar_id, r.state AS radar_state FROM ros_inbox_items i LEFT JOIN ros_radar_items r ON r.inbox_item_id = i.item_id ORDER BY i.item_id DESC LIMIT %s", (limit,)); return cur.fetchall()


# -- radar pipeline ----------------------------------------------------------

def _step(payload: dict, state: str, data: dict, actor: str) -> dict:
    payload = dict(payload); payload.update(data); payload.setdefault("history", []).append({"state": state, "at": datetime.now(timezone.utc).isoformat(), "by": actor}); return payload


def parse(text: str) -> dict:
    return {"urls": URL.findall(text), "dois": DOI.findall(text), "arxiv": ARXIV.findall(text), "claim_ids": sorted(set(CLAIM.findall(text))), "words": len(text.split()), "text_sha256": sha256(_norm(text).encode()).hexdigest()}


def dedup(conn, radar_id: int, parsed: dict, regs: dict) -> dict:
    dups = []
    with conn.cursor() as cur:
        cur.execute("SELECT radar_id FROM ros_radar_items WHERE radar_id <> %s AND payload->'parsed'->>'text_sha256' = %s", (radar_id, parsed["text_sha256"])); dups += [f"radar:{r[0]}" for r in cur.fetchall()]
    known_urls = {c["url"] for c in regs["prior_art"]["citations"] if c.get("url")}
    dups += [f"prior_art:{u}" for u in parsed["urls"] if u in known_urls]
    return {"duplicates": dups, "is_duplicate": bool(dups)}


def source_check(parsed: dict, kind: str) -> dict:
    has = bool(parsed["urls"] or parsed["dois"] or parsed["arxiv"])
    return {"has_source": has, "source_class": "doi" if parsed["dois"] else "arxiv" if parsed["arxiv"] else "url" if parsed["urls"] else "none", "needs_source": kind in ("paper", "quote") and not has}


def track_map(text: str, regs: dict) -> dict:
    n = _norm(text); scores = {t: sum(n.count(k.lower()) for k in kws) for t, kws in TRACK_KEYWORDS.items()}
    best = max(scores.items(), key=lambda kv: kv[1]) if any(scores.values()) else (None, 0)
    return {"track_scores": scores, "track": best[0], "track_confidence": "keyword_heuristic"}


def claim_impact(text: str, parsed: dict, regs: dict, track: str | None) -> dict:
    n = _norm(text); hits = []
    for c in regs["claims"]["claims"]:
        direct = c["claim_id"] in parsed["claim_ids"]; kw = [w for w in _norm(c["title"]).split() if len(w) > 6 and w in n]
        if direct or len(kw) >= 2 or (track and c["track"] == track and len(kw) >= 1):
            hits.append({"claim_id": c["claim_id"], "title": c["title"], "status": c["status"], "strength": c["evidence_strength"], "match": "id" if direct else f"keywords:{','.join(kw[:4])}"})
    return {"impacted_claims": hits[:8]}


def evidence_strength(kind: str, src: dict) -> dict:
    if kind in ("paper", "quote") and src["source_class"] in ("doi", "arxiv"):
        s = "MEDIUM (proposed; external source, not yet read/verified)"
    elif src["has_source"]:
        s = "LOW (proposed; web source)"
    else:
        s = "PRELIMINARY (proposed; no external source)"
    return {"proposed_evidence_strength": s, "rule": "proposal only — registry evidence_strength is never changed by the radar"}


def action(kind: str, parsed: dict, src: dict, tm: dict, ci: dict, dup: dict, text: str) -> dict:
    if dup["is_duplicate"]:
        dk, why = "none", f"duplicate of {dup['duplicates'][0]}"
    elif kind == "paper" or (kind == "quote" and src["has_source"]):
        dk, why = "prior_art", "external source -> research-brief draft for the founder (deep-research skill can deepen it)"
    elif kind == "experiment_idea":
        dk, why = "work_order", "experiment idea -> work-order DRAFT (needs question, scope, hypothesis, falsification criterion, metrics, governance, caps)"
    elif kind in ("critique", "observation") and ci["impacted_claims"]:
        dk, why = "claim_note", "touches recorded claims -> note on the claim(s); status/strength unchanged"
    else:
        dk, why = "open_question", "no direct claim match -> open-question draft"
    impacted = [c["claim_id"] for c in ci["impacted_claims"]]
    return {"delta_kind": dk, "delta": {"BEFORE": {"claims": impacted, "track": tm["track"], "registry_change": "none"}, "PROPOSED": f"{dk}: {text[:240]}", "EVIDENCE": {"sources": parsed["urls"] + parsed["dois"] + parsed["arxiv"], "class": src["source_class"]},
                                       "WHY": why, "WHAT_WOULD_FALSIFY_IT": "a registry record or citation already covering this delta; or the founder judging the source unreliable / out of scope"}}


def process(conn, radar_id: int, regs: dict, actor: str = "system") -> dict:
    """Run every deterministic step RAW -> ACTION_PROPOSED. Idempotent: reprocessing overwrites the analysis, keeps the history."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_radar_items WHERE radar_id = %s FOR UPDATE", (radar_id,)); item = cur.fetchone()
        if item is None:
            raise KeyError(radar_id)
        if item["state"] in TERMINAL:
            raise ValueError(f"radar item is terminal ({item['state']})")
        p = item["payload"]; text = p["text"]; kind = p["kind"]
        parsed = parse(text); p = _step(p, "PARSED", {"parsed": parsed}, actor)
        dup = dedup(conn, radar_id, parsed, regs); p = _step(p, "DEDUPLICATED", {"dedup": dup}, actor)
        src = source_check(parsed, kind); p = _step(p, "SOURCE_CHECKED", {"source": src}, actor)
        tm = track_map(text, regs); p = _step(p, "TRACK_MAPPED", {"track_map": tm}, actor)
        ci = claim_impact(text, parsed, regs, tm["track"]); p = _step(p, "CLAIM_IMPACT_ANALYZED", {"claim_impact": ci}, actor)
        es = evidence_strength(kind, src); p = _step(p, "EVIDENCE_STRENGTH_ASSIGNED", {"evidence": es}, actor)
        ac = action(kind, parsed, src, tm, ci, dup, text); p = _step(p, "ACTION_PROPOSED", {"action": ac, "version": VERSION}, actor)
        cur.execute("UPDATE ros_radar_items SET state = 'ACTION_PROPOSED', payload = %s, updated_at = now() WHERE radar_id = %s RETURNING *", (json.dumps(p, default=str), radar_id)); row = cur.fetchone()
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'radar.process', %s, %s)", (actor, str(radar_id), json.dumps({"delta_kind": ac["delta_kind"], "track": tm["track"]})))
    conn.commit()
    return row


def review(conn, radar_id: int, verdict: str, actor: str, reason: str = "") -> dict:
    """Founder gate: ACTION_PROPOSED -> REVIEWED -> ACCEPTED | REJECTED | DEFERRED. Accepted deltas become DRAFTS (never registry edits)."""
    if actor != "founder":
        from .state_machines import IllegalTransition
        raise IllegalTransition("radar", "ACTION_PROPOSED", verdict.lower(), actor, "founder gate")
    if verdict not in TERMINAL:
        raise ValueError(f"verdict must be one of {TERMINAL}")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_radar_items WHERE radar_id = %s FOR UPDATE", (radar_id,)); item = cur.fetchone()
        if item is None:
            raise KeyError(radar_id)
        if item["state"] not in ("ACTION_PROPOSED", "DEFERRED"):
            raise ValueError(f"cannot review from {item['state']}")
        p = _step(item["payload"], "REVIEWED", {"review": {"verdict": verdict, "reason": reason}}, actor); p = _step(p, verdict, {}, actor)
        drafts = []
        if verdict == "ACCEPTED":
            drafts = materialize_drafts(conn, item["radar_id"], p, actor)
            p["drafts"] = drafts
        cur.execute("UPDATE ros_radar_items SET state = %s, payload = %s, decided_by = %s, decided_at = now(), updated_at = now() WHERE radar_id = %s RETURNING *", (verdict, json.dumps(p, default=str), actor, radar_id)); row = cur.fetchone()
        cur.execute("UPDATE ros_inbox_items SET state = %s WHERE item_id = %s", (verdict, item["inbox_item_id"]))
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'radar.review', %s, %s)", (actor, str(radar_id), json.dumps({"verdict": verdict, "reason": reason, "drafts": drafts})))
    conn.commit()
    return row


def materialize_drafts(conn, radar_id: int, p: dict, actor: str) -> list[dict]:
    """Accepted delta -> DRAFT objects. work_order -> ros_work_orders DRAFT (spec fields pre-filled, mandatory fields the founder must complete are marked);
    prior_art / open_question / claim_note -> draft JSON under docs/research/dashboard/radar-drafts/ (not a registry)."""
    from .. import registries
    ac = p["action"]; dk = ac["delta_kind"]; out = []
    if dk == "none":
        return out
    if dk == "work_order":
        from . import service
        wo_id = f"WO-RADAR-{radar_id}"
        spec = {"question": p["text"][:400], "scope": "TO_BE_DEFINED_BY_FOUNDER", "hypothesis": "TO_BE_DEFINED_BY_FOUNDER", "falsification_criterion": "TO_BE_DEFINED_BY_FOUNDER", "metrics": ["TO_BE_DEFINED"], "governance": {"provider": "claude-max-subscription-only", "cost_cap_usd": 0}, "caps": {"max_claude_code_invocations": 200, "max_concurrent_sessions": 1}, "origin": {"radar_id": radar_id, "version": VERSION}}
        try:
            row = service.create_work_order(conn, wo_id, None, spec, "system"); out.append({"kind": "work_order", "id": row["work_order_id"], "state": row["state"]})
        except Exception as e:
            conn.rollback(); out.append({"kind": "work_order", "id": wo_id, "error": str(e)[:120]})
        return out
    d = registries.DASH / "radar-drafts"; d.mkdir(exist_ok=True)
    path = d / f"radar-{radar_id}-{dk}.json"
    doc = {"schema": f"logos.radar-draft/{dk}/1", "radar_id": radar_id, "kind": dk, "created_at": datetime.now(timezone.utc).isoformat(), "accepted_by": actor, "delta": ac["delta"], "text": p["text"], "source": p.get("source"), "track": p["track_map"]["track"], "impacted_claims": p["claim_impact"]["impacted_claims"],
           "proposed_evidence_strength": p["evidence"]["proposed_evidence_strength"], "registry_change": "NONE — draft for a governed merge (research_intake.merge_brief for prior art; founder edit for questions/notes)"}
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out.append({"kind": dk, "path": str(path.relative_to(registries.DASH.parents[2])).replace("\\", "/")})
    return out


def list_radar(conn, state: str | None = None, limit: int = 200) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if state:
            cur.execute("SELECT * FROM ros_radar_items WHERE state = %s ORDER BY radar_id DESC LIMIT %s", (state, limit))
        else:
            cur.execute("SELECT * FROM ros_radar_items ORDER BY (state = 'ACTION_PROPOSED') DESC, radar_id DESC LIMIT %s", (limit,))
        return cur.fetchall()


def get_radar(conn, radar_id: int) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_radar_items WHERE radar_id = %s", (radar_id,)); return cur.fetchone()


def delete_test_items(conn, prefix: str = "TEST-ROS") -> int:
    """Test hygiene: inbox items whose text starts with the prefix (cascade to radar rows)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM ros_radar_items WHERE inbox_item_id IN (SELECT item_id FROM ros_inbox_items WHERE text LIKE %s)", (prefix + "%",))
        cur.execute("DELETE FROM ros_work_orders WHERE work_order_id LIKE 'WO-RADAR-%%' AND (spec->'origin'->>'radar_id')::int NOT IN (SELECT radar_id FROM ros_radar_items)")
        cur.execute("DELETE FROM ros_inbox_items WHERE text LIKE %s", (prefix + "%",)); n = cur.rowcount
    conn.commit()
    from .. import registries
    for f in (registries.DASH / "radar-drafts").glob("radar-*.json"):
        try:
            if json.loads(f.read_text(encoding="utf-8")).get("text", "").startswith(prefix):
                f.unlink()
        except ValueError:
            pass
    return n


def attention(conn) -> list[dict]:
    """§43 attention queue: everything only the founder can move."""
    items = []
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT decision_id, kind, subject_ref, why FROM ros_decisions WHERE state = 'WAITING' ORDER BY created_at"); items += [{"kind": "decision", "id": r["decision_id"], "text": f"{r['kind']} · {r['subject_ref']}: {r['why']}", "href": "/decisions"} for r in cur.fetchall()]
        cur.execute("SELECT job_id, kind, thesis_id FROM ros_jobs WHERE state = 'waiting_governance' ORDER BY job_id"); items += [{"kind": "job_start", "id": str(r["job_id"]), "text": f"job #{r['job_id']} {r['kind']} · {r['thesis_id'] or '—'} wartet auf Founder-Start", "href": f"/theses/{r['thesis_id']}" if r["thesis_id"] else "/queue"} for r in cur.fetchall()]
        cur.execute("SELECT job_id, kind FROM ros_jobs WHERE state = 'waiting_quota' ORDER BY job_id"); items += [{"kind": "quota", "id": str(r["job_id"]), "text": f"job #{r['job_id']} {r['kind']} wartet auf Quota-Reset", "href": "/system/quotas"} for r in cur.fetchall()]
        cur.execute("SELECT radar_id, payload->>'kind' AS kind, left(payload->>'text', 120) AS text FROM ros_radar_items WHERE state = 'ACTION_PROPOSED' ORDER BY radar_id"); items += [{"kind": "radar", "id": str(r["radar_id"]), "text": f"Radar #{r['radar_id']} ({r['kind']}): {r['text']}", "href": "/radar"} for r in cur.fetchall()]
        cur.execute("SELECT suite_id FROM ros_benchmark_suites WHERE status <> 'APPROVED' ORDER BY suite_id"); items += [{"kind": "benchmark_definition", "id": r["suite_id"], "text": f"Benchmark-Definition {r['suite_id']} wartet auf Freigabe", "href": "/benchmarks"} for r in cur.fetchall()]
    return items
