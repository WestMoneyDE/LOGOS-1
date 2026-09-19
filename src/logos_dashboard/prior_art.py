"""Prior-Art-Matrix: was je Track belegt ist, was fehlt, und der geführte Weg von einem Deep-Research-Brief ins Register.

Alles hier ist Zählung und Prüfung über Records. Der Merge bleibt eine Founder-Aktion (wie jede Registeränderung): ein Brief wird geprüft,
als Diff gezeigt und erst auf Bestätigung angehängt. Novelty steigt nie über `CLEAR_DIFFERENTIATION`, und eine Aussage über Neuheit ohne
Quellen bleibt `UNKNOWN` — nichts wird ergänzt, was nicht im Brief steht.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from logos_research.governance import GovernanceError

from . import registries, research_intake

NOVELTY = ("UNKNOWN", "POSSIBLE_INCREMENTAL", "CLEAR_DIFFERENTIATION")
MIN_PER_TRACK = 3                       # unter drei Zitaten je Track ist keine Neuheitsaussage belastbar (Regel aus research_intake.queue)
VERSION = "ros-prior-art/1"
BRIEFS = research_intake.BRIEFS


def matrix(regs: dict | None = None) -> dict:
    """Track × (Zitate, Novelty-Verteilung, offene Aufgaben, letzte Recherche, Ampel)."""
    regs = regs or registries.load_all()
    pa = regs["prior_art"]["citations"]; tracks = regs["claims"]["tracks"]
    tasks = research_intake.queue(regs)
    briefs = research_intake.briefs()
    rows = []
    for tid, t in tracks.items():
        cits = [c for c in pa if c["research_track"] == tid]
        nov = {n: sum(1 for c in cits if c.get("novelty_status") == n) for n in NOVELTY}
        open_tasks = [x for x in tasks if x.get("track") == tid]
        last = max([b.get("date", "") for b in briefs if any(s.get("research_track") == tid for s in b.get("sources", []))] or [""])
        status = "rot" if len(cits) < MIN_PER_TRACK else ("gelb" if nov["UNKNOWN"] > 0 or nov["CLEAR_DIFFERENTIATION"] == 0 else "gruen")
        rows.append({"track": tid, "title": t.get("title"), "citations": len(cits), "novelty": nov, "open_tasks": len(open_tasks), "last_brief": last or None, "status": status,
                     "missing": _missing(len(cits), nov), "claims": [c["claim_id"] for c in regs["claims"]["claims"] if c["track"] == tid]})
    claims = []
    for c in regs["claims"]["claims"]:
        related = [x for x in pa if x["research_track"] == c["track"]]
        closest = [{"citation_id": x["citation_id"], "title": x["title"], "year": x.get("year"), "novelty_status": x.get("novelty_status"), "url": x.get("url")} for x in related[:3]]
        claims.append({"claim_id": c["claim_id"], "title": c["title"], "track": c["track"], "closest_prior_art": closest, "n_related": len(related),
                       "novelty_statement": _claim_novelty(c, related)})
    return {"tracks": rows, "claims": claims, "n_citations": len(pa), "n_open_tasks": len(tasks), "n_briefs": len(briefs), "search_status": regs["prior_art"].get("search_status"),
            "rule": regs["prior_art"].get("rule"), "min_per_track": MIN_PER_TRACK, "version": VERSION}


def _missing(n: int, nov: dict) -> list[str]:
    out = []
    if n < MIN_PER_TRACK:
        out.append(f"{MIN_PER_TRACK - n} weitere Quelle(n) für eine belastbare Aussage")
    if nov["UNKNOWN"]:
        out.append(f"{nov['UNKNOWN']} Quelle(n) ohne Neuheitsbewertung")
    if not nov["CLEAR_DIFFERENTIATION"]:
        out.append("keine Quelle mit klarer Abgrenzung — Neuheit unbelegt")
    return out


def _claim_novelty(c: dict, related: list[dict]) -> str:
    if not related:
        return "nicht erfasst — für diesen Track liegt keine Quelle vor"
    diff = [x for x in related if x.get("novelty_status") == "CLEAR_DIFFERENTIATION"]
    if diff:
        return f"abgegrenzt gegenüber {diff[0]['citation_id']} ({diff[0]['title'][:60]})"
    unknown = sum(1 for x in related if x.get("novelty_status") == "UNKNOWN")
    return f"offen — {len(related)} Quelle(n) im Track, davon {unknown} ohne Bewertung; Neuheit ist damit nicht belegt"


def task_payload(task_id: str, regs: dict | None = None) -> dict:
    """Payload für einen `prior_art`-Agentenjob: genau eine Aufgabe aus der Warteschlange, mit Zieldatei und Schema."""
    regs = regs or registries.load_all()
    task = next((t for t in research_intake.queue(regs) if t["task_id"] == task_id), None)
    if task is None:
        raise KeyError(task_id)
    return {"brief_task": {"task_id": task_id, "claim_id": task.get("claim_id"), "track": task.get("track"), "question": task["question"], "why": task["why"], "deliverable": task["deliverable"],
                           "schema": research_intake.BRIEF_SCHEMA, "novelty_cap": "CLEAR_DIFFERENTIATION", "min_sources": MIN_PER_TRACK}}


def brief_diff(brief_id: str) -> dict:
    """Was ein Brief am Register ändern würde — als Diff, ohne zu schreiben."""
    b = next((x for x in research_intake.briefs() if x.get("brief_id") == brief_id), None)
    if b is None:
        raise KeyError(brief_id)
    # der Founder-Review ist der Klick im Dashboard; für die Prüfung wird er hier angenommen und beim Merge in die Brief-Datei geschrieben
    issues = [i for i in research_intake.validate_brief({**b, "reviewed_by_founder": True}) if "reviewed_by_founder" not in i]
    regs = registries.load_all(); have = {c["citation_id"] for c in regs["prior_art"]["citations"]}
    new = [s for s in b.get("sources", []) if s.get("citation_id") not in have]
    dup = [s["citation_id"] for s in b.get("sources", []) if s.get("citation_id") in have]
    capped = [s["citation_id"] for s in new if s.get("novelty_status") == "CLEAR_DIFFERENTIATION" and len(b.get("sources", [])) < MIN_PER_TRACK]
    return {"brief_id": brief_id, "brief": b, "issues": issues, "new_citations": [{k: s.get(k) for k in ("citation_id", "title", "year", "venue", "url", "research_track", "novelty_status")} for s in new],
            "duplicates": dup, "novelty_capped": capped, "before_count": len(have), "after_count": len(have) + len(new), "reviewed_by_founder": bool(b.get("reviewed_by_founder")),
            "founder_review_pending": not b.get("reviewed_by_founder"),
            "ok": not issues and bool(new), "version": VERSION}


def merge(conn, brief_id: str, actor: str) -> dict:
    """🔒 Founder-Aktion: Zitate eines geprüften Briefs anhängen. Kein Status, keine Evidenzstärke, keine Novelty-Erhöhung über die Regel hinaus."""
    if actor != "founder":
        raise GovernanceError("Prior-Art-Merges sind Founder-Sache; ein Agent darf das Register nie ändern")
    d = brief_diff(brief_id)
    if d["issues"]:
        raise ValueError(f"Brief ist nicht gültig: {d['issues']}")
    if not d["new_citations"]:
        raise ValueError("keine neuen Zitate (alle bereits im Register)")
    if d["novelty_capped"]:
        raise ValueError(f"Neuheitsstufe CLEAR_DIFFERENTIATION verlangt mindestens {MIN_PER_TRACK} Quellen im Brief: {d['novelty_capped']}")
    # Founder-Review festhalten: der Klick ist die Prüfung, und sie steht danach in der Brief-Datei
    bp = BRIEFS / f"{brief_id}.json"
    if bp.exists() and not d["brief"].get("reviewed_by_founder"):
        reviewed = {**d["brief"], "reviewed_by_founder": True, "reviewed_by": actor, "reviewed_at": datetime.now(timezone.utc).isoformat()}
        reviewed.pop("_path", None)
        bp.write_text(json.dumps(reviewed, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
        d = brief_diff(brief_id)
    p = registries.DASH / registries.FILES["prior_art"]
    raw_before = p.read_text(encoding="utf-8")
    from hashlib import sha256
    before_hash = sha256(raw_before.encode()).hexdigest()
    res = research_intake.merge_brief(d["brief"], write=True)
    after_hash = sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
    rec = {"at": datetime.now(timezone.utc).isoformat(), "actor": actor, "registry": "prior_art", "entity_id": brief_id, "field": "citations", "before": d["before_count"], "after": res["count"],
           "reason": f"Merge des Briefs {brief_id} ({len(res['added'])} neue Zitate)", "origin": {"kind": "prior_art_brief", "brief_id": brief_id}, "file": registries.FILES["prior_art"],
           "file_sha256_before": before_hash, "file_sha256_after": after_hash, "version": VERSION}
    from .control import registry_edit
    with registry_edit.CHANGELOG.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if conn is not None:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'prior_art.merge', %s, %s)", (actor, brief_id, json.dumps(rec, ensure_ascii=False)))
        conn.commit()
    return {"merged": True, "added": res["added"], "count": res["count"], **rec}
