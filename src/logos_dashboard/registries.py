"""Structured registries (docs/research/dashboard/*.json) + scientific integrity validation (Sections 32-33 of the order).

`validate()` returns a list of violations; the dashboard shows them and the test suite asserts the list is empty.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "docs/research/dashboard"
FILES = {"claims": "CLAIM-REGISTRY.json", "experiments": "EXPERIMENT-REGISTRY.json", "invariants": "INVARIANT-REGISTRY.json", "prior_art": "PRIOR-ART-REGISTRY.json",
         "publications": "PUBLICATION-REGISTRY.json", "replication": "REPLICATION-REGISTRY.json", "open_questions": "OPEN-QUESTIONS.json", "active_theses": "ACTIVE-THESES.json"}
FORBIDDEN_WORDS = ("PROVEN", "CONFIRMED FOREVER", "SOLVED", "REVOLUTIONARY", "BREAKTHROUGH", "GAME-CHANGING", "WORLD-FIRST", "AGI SOLVED", "ULTIMATE ARCHITECTURE")
EMPIRICAL_STATUSES = ("OBSERVED", "SUPPORTED", "PARTIALLY_SUPPORTED", "FALSIFIED", "INVALID_MEASUREMENT", "INCONCLUSIVE", "VALIDATED_IN_FIXTURE", "EXTERNALLY_REPLICATED")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _load(name: str) -> dict:
    return json.loads((DASH / FILES[name]).read_text(encoding="utf-8"))


def load_all() -> dict[str, dict]:
    return {k: _load(k) for k in FILES}


def path_exists(rel: str) -> bool:
    rel = rel.split(" (")[0].strip()
    return (ROOT / rel).exists()


def validate(data: dict[str, dict] | None = None) -> list[dict]:
    """Scientific integrity rules. Each violation: {rule, entity, detail}."""
    d = data or load_all()
    out: list[dict] = []
    def v(rule, entity, detail): out.append({"rule": rule, "entity": entity, "detail": detail})
    claims = d["claims"]; exps = d["experiments"]; invs = d["invariants"]; pa = d["prior_art"]; pubs = d["publications"]; rep = d["replication"]
    claim_ids = {c["claim_id"] for c in claims["claims"]}; exp_ids = {e["experiment_id"] for e in exps["experiments"]}; inv_ids = {i["invariant_id"] for i in invs["invariants"]}
    ce_ids = {c["ce_id"] for c in claims["counterexamples"]}; cit_ids = {c["citation_id"] for c in pa["citations"]}
    status_vocab = set(claims["status_vocabulary"]); strength_vocab = set(claims["strength_vocabulary"])
    all_text = json.dumps({k: ({kk: vv for kk, vv in val.items() if kk != "forbidden_words"} if isinstance(val, dict) else val) for k, val in d.items()}, ensure_ascii=False).upper()
    for w in FORBIDDEN_WORDS:
        if re.search(r"\b" + re.escape(w) + r"\b", all_text):
            v("no_forbidden_word", "registries", f"'{w}' appears (only allowed inside a verbatim external quote)")
    for c in claims["claims"]:
        cid = c["claim_id"]
        if c["status"] not in status_vocab: v("status_vocabulary", cid, c["status"])
        if c["evidence_strength"] not in strength_vocab: v("strength_vocabulary", cid, c["evidence_strength"])
        if c["status"] in ("SUPPORTED", "PARTIALLY_SUPPORTED", "VALIDATED_IN_FIXTURE", "OBSERVED", "FALSIFIED", "INVALID_MEASUREMENT") and not c["supporting_artifacts"]:
            v("claim_without_evidence", cid, "status requires supporting_artifacts")
        for a in c["supporting_artifacts"]:
            if not path_exists(a): v("broken_artifact_reference", cid, a)
        if c["status"] == "FALSIFIED" and not any(x.startswith("EXP-") or "run" in x.lower() for x in c["counterevidence"]):
            v("falsified_without_run", cid, "FALSIFIED needs a run/artifact reference in counterevidence")
        if c["status"] in EMPIRICAL_STATUSES and not c.get("scope"): v("missing_scope", cid, "empirical claim without scope")
        if c["external_replication"] != "NONE" and not c.get("external_artifact"): v("external_replication_without_artifact", cid, c["external_replication"])
        if c["evidence_strength"] == "INDEPENDENTLY_REPLICATED" and c["external_replication"] == "NONE": v("strength_inflation", cid, "INDEPENDENTLY_REPLICATED without external replication")
        if c["status"] == "INVALID_MEASUREMENT" and c["claim_type"] in ("hypothesis", "invariant") and "not a scientific" not in c["falsification_test"].lower():
            v("invalid_measurement_as_result", cid, "INVALID_MEASUREMENT must not be presented as a scientific result")
        if "fixture" in c["scope"].lower() and "production" in c["statement"].lower() and "proof" in c["statement"].lower():
            v("fixture_as_production_proof", cid, c["statement"][:80])
        if c["publication_target"]:
            targets = re.findall(r"PAPER-\d", c["publication_target"])
            if not targets and "all papers" not in c["publication_target"]: v("publication_target_unknown", cid, c["publication_target"])
        if c["kind"] not in claims["kind_vocabulary"]: v("kind_vocabulary", cid, c["kind"])
    for e in exps["experiments"]:
        eid = e["experiment_id"]
        if not path_exists(e["record"]): v("broken_record_reference", eid, e["record"])
        if e["kind"] == "EMPIRICAL_SCIENCE" and not e["prereg_hash"] and "deterministic" not in (e.get("model_provider") or "") and "Phase" not in e["order_id"]:
            v("experiment_without_prereg", eid, "empirical experiment needs prereg hash or an explicit historical exception")
        if e["prereg_hash"] and not HEX64.match(e["prereg_hash"]): v("bad_hash", eid, "prereg_hash")
        if e["artifact_hash"] and not HEX64.match(e["artifact_hash"]): v("bad_hash", eid, "artifact_hash")
        if e["verdict"] in ("FALSIFIED", "COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1", "INVALID_MEASUREMENT") and not e["negative_result"]:
            v("negative_result_omitted", eid, "negative verdict must be flagged negative_result")
        for i in e["invariants"]:
            if i not in inv_ids: v("unknown_invariant", eid, i)
    for i in invs["invariants"]:
        for r in i["relations"]:
            if r["type"] not in invs["relation_vocabulary"]: v("relation_vocabulary", i["invariant_id"], r["type"])
            t = r["target"]
            if not (t in inv_ids or t in exp_ids or t in ce_ids): v("dangling_relation", i["invariant_id"], t)
        for s in i["evidence"]:
            if not path_exists(s): v("broken_evidence_reference", i["invariant_id"], s)
        if i["status"] not in status_vocab: v("status_vocabulary", i["invariant_id"], i["status"])
    for c in claims["counterexamples"]:
        if c["experiment"] not in exp_ids: v("counterexample_without_experiment", c["ce_id"], c["experiment"])
    for p in pubs["papers"]:
        for c in p["claims"]:
            if c not in claim_ids: v("paper_claim_not_in_registry", p["paper_id"], c)
        for r in p["required_related_work"]:
            if r.startswith("PA-") and r not in cit_ids: v("citation_missing", p["paper_id"], r)
        met = set(p["criteria_met"]); pre = set(p["criteria_preprint"])
        if p["manuscript_status"] in ("PREPRINT_READY", "WORKSHOP_READY", "SUBMISSION_READY") and not pre <= met: v("readiness_inflation", p["paper_id"], sorted(pre - met))
    for r in rep["replications"]:
        if r["claim_id"] not in claim_ids: v("replication_unknown_claim", r["finding"], r["claim_id"])
        if r["levels"]["external_researcher"]: v("external_replication_claimed", r["finding"], "no external artifact recorded in this repository")
    for c in pa["citations"]:
        if not c.get("url"): v("citation_without_locator", c["citation_id"], "")
        if c["novelty_status"] == "STRONG_NOVELTY_EVIDENCE": v("unsupported_novelty", c["citation_id"], "no systematic search recorded")
    return out


def counts(d: dict[str, dict] | None = None) -> dict:
    d = d or load_all()
    by = lambda items, key: {k: sum(1 for x in items if x[key] == k) for k in sorted({x[key] for x in items})}
    return {"claims_by_status": by(d["claims"]["claims"], "status"), "claims_by_track": by(d["claims"]["claims"], "track"), "claims_by_strength": by(d["claims"]["claims"], "evidence_strength"),
            "experiments_by_verdict": by(d["experiments"]["experiments"], "verdict"), "negative_results": sum(1 for e in d["experiments"]["experiments"] if e["negative_result"]),
            "invariants": len(d["invariants"]["invariants"]), "invariants_by_status": by(d["invariants"]["invariants"], "status"), "counterexamples": len(d["claims"]["counterexamples"]),
            "prior_art": len(d["prior_art"]["citations"]), "papers_by_status": by(d["publications"]["papers"], "manuscript_status"), "open_questions": len(d["open_questions"]["questions"])}
