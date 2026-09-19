"""Phase 7: evidence debt, paper readiness and the monthly report — deterministic derivations from registries, closures and the ros_* tables.

Every item points at a record; nothing here upgrades a status, declares readiness or writes a registry. The monthly report is Markdown + JSON;
the founder freezes it (file under docs/research/dashboard/reports/ + sha recorded in ros_monthly_snapshots payload).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256

from . import stats

VERSION = "ros-reports/1"
STRENGTH_ORDER = ("PRELIMINARY", "LOW", "LOW_TO_MEDIUM", "MEDIUM", "MEDIUM_TO_HIGH", "HIGH", "INDEPENDENTLY_REPLICATED")


def evidence_debt(regs: dict, closures: list[dict]) -> dict:
    """Debt = a claim/invariant/paper carrying a status its evidence does not yet earn, or a missing next step. Severity HIGH/MEDIUM/LOW; each item cites the record."""
    items = []
    claims = regs["claims"]["claims"]; exps = regs["experiments"]["experiments"]; reps = regs["replication"]["replications"]; inv = regs["invariants"]["invariants"]
    exp_by_claim: dict[str, list[str]] = {}
    for e in exps:
        for cid in (e.get("claims") or []) + ([e["claim_id"]] if e.get("claim_id") else []):
            exp_by_claim.setdefault(cid, []).append(e["experiment_id"])
    rep_by_claim = {r["claim_id"]: r for r in reps}
    for c in claims:
        rec = f"docs/research/dashboard/CLAIM-REGISTRY.json#{c['claim_id']}"; st = c["status"]; strength = c["evidence_strength"]; si = STRENGTH_ORDER.index(strength) if strength in STRENGTH_ORDER else -1
        if st == "SUPPORTED" and si < STRENGTH_ORDER.index("MEDIUM"):
            items.append({"severity": "HIGH", "kind": "status_exceeds_evidence", "subject": c["claim_id"], "record": rec, "text": f"status {st} with evidence strength {strength}"})
        if st in ("SUPPORTED", "PARTIALLY_SUPPORTED", "VALIDATED_IN_FIXTURE") and not c.get("next_falsification_test"):
            items.append({"severity": "MEDIUM", "kind": "no_next_falsification_test", "subject": c["claim_id"], "record": rec, "text": "no next falsification test named"})
        if st in ("SUPPORTED", "PARTIALLY_SUPPORTED") and (c.get("external_replication") or "none").lower().startswith("none"):
            items.append({"severity": "MEDIUM", "kind": "no_external_replication", "subject": c["claim_id"], "record": rec, "text": "no external replication"})
        if st in ("SUPPORTED", "PARTIALLY_SUPPORTED", "FALSIFIED", "INVALID_MEASUREMENT") and not c.get("supporting_artifacts"):
            items.append({"severity": "HIGH", "kind": "no_artifact", "subject": c["claim_id"], "record": rec, "text": "no supporting artifact hash"})
        if c.get("counterevidence") and st == "SUPPORTED":
            items.append({"severity": "MEDIUM", "kind": "unaddressed_counterevidence", "subject": c["claim_id"], "record": rec, "text": f"{len(c['counterevidence'])} counter-evidence entries while SUPPORTED"})
        r = rep_by_claim.get(c["claim_id"])
        if r and r.get("count") == "0/5" and st in ("SUPPORTED", "PARTIALLY_SUPPORTED"):
            items.append({"severity": "LOW", "kind": "replication_0_of_5", "subject": c["claim_id"], "record": "docs/research/dashboard/REPLICATION-REGISTRY.json", "text": "replication ladder 0/5"})
        if st in ("READY_FOR_INFERENCE_TEST", "READY_FOR_DETERMINISTIC_TEST", "PROPOSED") and not exp_by_claim.get(c["claim_id"]):
            items.append({"severity": "LOW", "kind": "no_experiment_registered", "subject": c["claim_id"], "record": rec, "text": f"status {st} without a registered experiment"})
    for i in inv:
        if i.get("status") in ("SUPPORTED", "VALIDATED", "HOLDS") and not i.get("experiments") and not i.get("evidence"):
            items.append({"severity": "MEDIUM", "kind": "invariant_without_evidence", "subject": i["invariant_id"], "record": f"docs/research/dashboard/INVARIANT-REGISTRY.json#{i['invariant_id']}", "text": f"invariant {i['status']} without experiments/evidence"})
    open_gov = sum(len(c.get("open_decisions") or []) for c in closures)
    if open_gov:
        items.append({"severity": "LOW", "kind": "open_governance_questions", "subject": "closures", "record": "05-WORK-ORDERS/NEXT-SESSION-*.md", "text": f"{open_gov} open governance question(s) in closures"})
    by_sev = {s: sum(1 for x in items if x["severity"] == s) for s in ("HIGH", "MEDIUM", "LOW")}
    return {"items": items, "n": len(items), "by_severity": by_sev, "version": VERSION, "rule": "debt is derived from records; paying it needs a governed order, never an edit here"}


def paper_readiness(regs: dict) -> list[dict]:
    claims = {c["claim_id"]: c for c in regs["claims"]["claims"]}; reps = {r["claim_id"]: r for r in regs["replication"]["replications"]}
    pa = regs["prior_art"]["citations"]; out = []
    for p in regs["publications"]["papers"]:
        cl = [claims[c] for c in p["claims"] if c in claims]
        checks = {
            "all_claims_registered": len(cl) == len(p["claims"]),
            "negative_results_labelled": (not any(c["status"] in ("FALSIFIED", "INVALID_MEASUREMENT") for c in cl)) or any(w in json.dumps(p.get("draft_outline", "")).lower() + p.get("core_contribution", "").lower() for w in ("negative", "counterexample", "falsif")),
            "every_claim_has_artifact": all(bool(c.get("supporting_artifacts")) for c in cl),
            "every_claim_min_medium_strength": all(STRENGTH_ORDER.index(c["evidence_strength"]) >= STRENGTH_ORDER.index("MEDIUM") for c in cl if c["evidence_strength"] in STRENGTH_ORDER),
            "related_work_per_track_ge_3": all(sum(1 for x in pa if x["research_track"] == t) >= 3 for t in p["tracks"]),
            "replication_started_for_claims": all(reps.get(c["claim_id"], {}).get("count", "0/5") != "0/5" for c in cl),
            "no_open_blockers": not p.get("open_blockers"),
            "registry_criteria_met": bool(p.get("criteria_met")),
        }
        k = sum(checks.values()); n = len(checks)
        out.append({"paper_id": p["paper_id"], "title": p["title"], "manuscript_status": p["manuscript_status"], "checks": checks, "met": k, "of": n, "open_blockers": p.get("open_blockers", []), "missing_for_preprint": p.get("missing_for_preprint", []),
                    "verdict": "criteria counted, readiness is a founder decision (status vocabulary: " + ", ".join(regs["publications"]["status_vocabulary"]) + ")", "claims": [{"claim_id": c["claim_id"], "status": c["status"], "strength": c["evidence_strength"]} for c in cl]})
    return out


def monthly_report(conn, regs: dict, closures: list[dict], progress: dict, month: str) -> dict:
    from psycopg.rows import dict_row
    cl = [c for c in closures if (c.get("closed") or "").startswith(month)]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT thesis_id, title, state FROM ros_theses WHERE to_char(created_at, 'YYYY-MM') = %s ORDER BY created_at", (month,)); theses = cur.fetchall()
        cur.execute("SELECT run_id, kind, state, thesis_id, stop_reason FROM ros_runs WHERE to_char(created_at, 'YYYY-MM') = %s ORDER BY created_at", (month,)); runs_ = cur.fetchall()
        cur.execute("SELECT decision_id, kind, state, decided_by FROM ros_decisions WHERE to_char(COALESCE(decided_at, created_at), 'YYYY-MM') = %s ORDER BY created_at", (month,)); decisions = cur.fetchall()
        cur.execute("SELECT snapshot_id, suite_id, mode, sha256, payload->'gates'->>'verdict' AS gates FROM ros_benchmark_snapshots WHERE month = %s ORDER BY created_at", (month,)); snaps = cur.fetchall()
        cur.execute("SELECT radar_id, state, payload->>'kind' AS kind, payload->'action'->>'delta_kind' AS delta FROM ros_radar_items WHERE to_char(updated_at, 'YYYY-MM') = %s ORDER BY radar_id", (month,)); radar = cur.fetchall()
        cur.execute("SELECT at, detail FROM ros_audit WHERE action = 'settings.set' AND subject = 'quota_state' AND detail->'value'->>'state' = 'USAGE_LIMIT_REACHED' AND to_char(at, 'YYYY-MM') = %s ORDER BY at", (month,)); quota = cur.fetchall()   # note: the test suite also writes such rows (fake usage-limit tests); counts are audit counts, not subscription facts
    debt = evidence_debt(regs, closures); papers = paper_readiness(regs)
    doc = {"month": month, "generated_at": datetime.now(timezone.utc).isoformat(), "version": VERSION, "closures": [{"id": c["id"], "verdict": c.get("verdict"), "verdict_class": c.get("verdict_class"), "closed": c.get("closed"), "successor": c.get("successor_id")} for c in cl],
           "negative_results": [c["id"] for c in cl if c.get("verdict_class") in ("falsified", "invalid")], "progress": progress, "theses": theses, "runs": runs_, "decisions": decisions, "benchmark_snapshots": snaps, "radar": radar, "quota_events": quota,
           "evidence_debt": {"n": debt["n"], "by_severity": debt["by_severity"], "top": debt["items"][:10]}, "paper_readiness": [{"paper_id": p["paper_id"], "met": p["met"], "of": p["of"], "manuscript_status": p["manuscript_status"]} for p in papers],
           "does_not_claim": ["no readiness verdict", "no status or strength change", "no MoM percentage without a frozen comparable month", "nothing about phenomenal consciousness (P7)"]}
    doc["sha256"] = sha256(json.dumps({k: v for k, v in doc.items() if k not in ("sha256", "generated_at")}, sort_keys=True, default=str).encode()).hexdigest()
    return doc


def render_markdown(doc: dict) -> str:
    p = doc["progress"]; fr = p["falsification_rate"]
    def rate(r): return "NOT_DEFINED" if r["value"] == "NOT_DEFINED" else f"{r['value']*100:.1f} % [{r['ci95'][0]*100:.1f}, {r['ci95'][1]*100:.1f}] (n={r['n']}, Wilson)"
    L = [f"# LOGOS-1 Monthly Report — {doc['month']}", "", f"Generated {doc['generated_at']} · {doc['version']} · sha256 `{doc['sha256']}` · counts from repository records + ros_* tables; no verdict, no status change.", "",
         "## Closures", f"{len(doc['closures'])} closures · negative results: {len(doc['negative_results'])} ({', '.join(doc['negative_results']) or '—'})", ""]
    L += [f"- `{c['id']}` — {c['verdict'] or 'not extracted'} ({c['verdict_class']}) · closed {c['closed']} · successor `{c['successor'] or 'not extracted'}`" for c in doc["closures"]] or ["- —"]
    L += ["", "## Rates (Wilson 95 %)", f"- falsification rate: {rate(fr)}", f"- invalid-measurement rate: {rate(p['invalid_measurement_rate'])}", f"- replication coverage: {rate(p['replication_coverage'])}", f"- agent-run success: {rate(p['agent_run_success'])} · runs {p['agent_runs']}", "",
          "## Research OS activity", f"- theses created: {len(doc['theses'])} · runs: {len(doc['runs'])} · decisions: {len(doc['decisions'])} · radar items touched: {len(doc['radar'])} · benchmark snapshots: {len(doc['benchmark_snapshots'])} · quota events: {len(doc['quota_events'])}", "",
          "## Evidence debt", f"{doc['evidence_debt']['n']} items (HIGH {doc['evidence_debt']['by_severity']['HIGH']} · MEDIUM {doc['evidence_debt']['by_severity']['MEDIUM']} · LOW {doc['evidence_debt']['by_severity']['LOW']})"]
    L += [f"- [{d['severity']}] {d['subject']}: {d['text']} (`{d['record']}`)" for d in doc["evidence_debt"]["top"]]
    L += ["", "## Paper readiness (criteria counted; readiness is a founder decision)"] + [f"- {x['paper_id']}: {x['met']}/{x['of']} criteria · {x['manuscript_status']}" for x in doc["paper_readiness"]]
    L += ["", "## Does not claim"] + [f"- {x}" for x in doc["does_not_claim"]] + [""]
    return "\n".join(L)
