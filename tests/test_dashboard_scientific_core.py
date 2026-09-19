"""LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1 — registry validation layer (Section 32), integrity checks (Section 33), API routes (Section 43).

Deterministic; the lab may be unreachable (records-only mode is itself tested). No model call.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from logos_dashboard import registries as rg, readers as rd
from logos_dashboard.api import app

ROOT = Path(__file__).resolve().parents[1]
REGS = rg.load_all()
client = TestClient(app)


def test_registries_present_and_schema_versioned():
    for name in rg.FILES:
        assert name in REGS and "schema" in REGS[name], name
    assert REGS["claims"]["count"] == len(REGS["claims"]["claims"]) and REGS["experiments"]["count"] == len(REGS["experiments"]["experiments"])


def test_integrity_rules_pass():
    assert rg.validate(REGS) == []


def test_every_supported_claim_has_evidence_and_scope():
    for c in REGS["claims"]["claims"]:
        if c["status"] in ("SUPPORTED", "PARTIALLY_SUPPORTED", "VALIDATED_IN_FIXTURE", "OBSERVED", "FALSIFIED"):
            assert c["supporting_artifacts"] and c["scope"], c["claim_id"]
            for a in c["supporting_artifacts"]:
                assert rg.path_exists(a), (c["claim_id"], a)


def test_every_falsified_claim_points_to_a_run():
    for c in REGS["claims"]["claims"]:
        if c["status"] == "FALSIFIED":
            assert c["preregistration"] and re.fullmatch(r"[0-9a-f]{64}", c["preregistration"]), c["claim_id"]
            assert any(e["prereg_hash"] == c["preregistration"] for e in REGS["experiments"]["experiments"]), c["claim_id"]


def test_experiment_records_and_hashes_exist():
    for e in REGS["experiments"]["experiments"]:
        assert (ROOT / e["record"]).exists(), e["experiment_id"]
        for h in (e["prereg_hash"], e["artifact_hash"]):
            assert h == "" or re.fullmatch(r"[0-9a-f]{64}", h), (e["experiment_id"], h)
    # real-model runs carry the frozen run hashes recorded in the closures
    rerun = next(e for e in REGS["experiments"]["experiments"] if e["experiment_id"] == "EXP-CPA-RERUN")
    closure = (ROOT / "05-WORK-ORDERS/NEXT-SESSION-COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1.md").read_text(encoding="utf-8")
    assert rerun["prereg_hash"][:8] in closure and rerun["artifact_hash"][:8] in closure and rerun["verdict"] in closure


def test_no_proven_and_no_scope_inflation():
    text = json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "forbidden_words"} for k, v in REGS.items()}, ensure_ascii=False)
    assert not re.search(r"\bPROVEN\b|\bREVOLUTIONARY\b|\bBREAKTHROUGH\b|game-changing|world-first", text, re.I)
    for c in REGS["claims"]["claims"]:
        if c["kind"] == "EMPIRICAL_SCIENCE":
            assert not re.search(r"\bLLMs (do|are|behave)\b", c["statement"]), c["claim_id"]                 # no global formulation


def test_negative_results_visible():
    neg = [e for e in REGS["experiments"]["experiments"] if e["negative_result"]]
    ids = {e["experiment_id"] for e in neg}
    assert {"EXP-RAD-R1", "EXP-CPA-R1", "EXP-CPA-RERUN", "EXP-BSP-R1", "EXP-BSP-VAL-R1"} <= ids
    ce = {c["ce_id"] for c in REGS["claims"]["counterexamples"]}
    assert {"CE-CE1", "CE-VCE1", "CE-RAD-CE1", "CE-MBGV-F1", "CE-DCC-F1", "CE-CPA-F5", "CE-CPA-FLOOR"} <= ce


def test_cognitive_provenance_track_states_the_floor_and_the_invalid_run():
    t = client.get("/api/tracks/cognitive-provenance").json()
    verdicts = {e["experiment_id"]: e["verdict"] for e in t["experiments"]}
    assert verdicts["EXP-CPA-R1"] == "INVALID_MEASUREMENT" and verdicts["EXP-CPA-RERUN"] == "COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1"
    h1 = next(c for c in t["claims"] if c["claim_id"] == "LOGOS-CP-001")
    assert h1["status"] == "FALSIFIED" and any("floor" in l.lower() for l in h1["known_limitations"]) and h1["next_falsification_test"] == "COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1"
    assert any(c["claim_id"] == "LOGOS-CP-003" and "SourceSeen" in c["title"] for c in t["claims"])


def test_publication_readiness_not_inflated():
    for p in REGS["publications"]["papers"]:
        assert p["manuscript_status"] in ("NOT_READY", "INTERNAL_DRAFT")
        assert set(p["claims"]) <= {c["claim_id"] for c in REGS["claims"]["claims"]}
        assert p["missing_for_preprint"]                                                        # nothing is preprint-ready yet


def test_replication_and_prior_art_honest():
    for r in REGS["replication"]["replications"]:
        assert not r["levels"]["external_researcher"] and r["count"] in ("0/5", "1/5")
    assert REGS["prior_art"]["search_status"].startswith("NO SYSTEMATIC")
    assert all(c["novelty_status"] != "STRONG_NOVELTY_EVIDENCE" for c in REGS["prior_art"]["citations"])


def test_invariant_graph_relations_resolve():
    g = client.get("/api/invariants/graph").json()
    ids = {n["id"] for n in g["nodes"]} | {e["experiment_id"] for e in REGS["experiments"]["experiments"]} | {c["ce_id"] for c in REGS["claims"]["counterexamples"]}
    assert all(e["to"] in ids for e in g["edges"]) and len(g["nodes"]) == REGS["invariants"]["count"]


@pytest.mark.parametrize("route", ["/api/health", "/api/overview", "/api/registries/claims", "/api/registries/experiments", "/api/registries/invariants", "/api/registries/prior_art", "/api/registries/publications",
                                   "/api/registries/replication", "/api/registries/open_questions", "/api/tracks/authority", "/api/tracks/provenance", "/api/tracks/cognitive-provenance", "/api/tracks/measurement",
                                   "/api/tracks/memory", "/api/tracks/trajectory", "/api/claims/LOGOS-AUTH-001", "/api/experiments/EXP-CPA-RERUN", "/api/invariants/graph", "/api/falsification", "/api/negative-results",
                                   "/api/timeline", "/api/reproducibility", "/api/lab", "/api/closures", "/api/sessions/COGNITIVE-PROVENANCE-ABLATION-R1", "/api/prs", "/api/search?q=floor", "/api/export/paper/PAPER-3", "/api/theses/active"])
def test_routes_render(route):
    r = client.get(route)
    assert r.status_code == 200, (route, r.text[:200])
    assert r.json() is not None


def test_track_completeness_for_first_milestone():
    for track in ("authority", "provenance", "cognitive-provenance"):
        t = client.get(f"/api/tracks/{track}").json()["completeness"]
        assert t["claims"] >= 3 and t["experiments"] >= 2 and t["invariants"] >= 3 and t["prior_art"] >= 2 and t["open_questions"] >= 1 and t["paper"], (track, t)


def test_closure_reader_never_guesses():
    for c in rd.closures():
        assert set(c["unparsed"]) <= {"verdict", "closure", "successor", "closed"}
        if c["verdict"]:
            assert c["verdict_class"] in ("falsified", "invalid", "partial", "supported", "validated", "approved", "amended", "other")
    latest = rd.closures()[-1]
    assert latest["id"].startswith("COGNITIVE-PROVENANCE") and latest["successor_id"]


def test_theses_selection_roundtrip(tmp_path, monkeypatch):
    target = tmp_path / "ACTIVE-THESES.json"; target.write_text(json.dumps({"schema": "logos.active-theses/1", "active": []}), encoding="utf-8")
    monkeypatch.setitem(rg.FILES, "active_theses", target.name); monkeypatch.setattr(rg, "DASH", tmp_path)
    for k in list(rg.FILES):
        if k != "active_theses":
            (tmp_path / rg.FILES[k]).write_text((ROOT / "docs/research/dashboard" / rg.FILES[k]).read_text(encoding="utf-8"), encoding="utf-8")
    import logos_dashboard.api as api
    monkeypatch.setattr(api, "DASH", tmp_path); api._cache.clear()
    assert client.post("/api/theses/active", json={"active": ["LOGOS-CP-001", "LOGOS-AUTH-006"]}).status_code == 200
    got = client.get("/api/theses/active").json()["active"]
    assert [g["claim"]["claim_id"] for g in got] == ["LOGOS-CP-001", "LOGOS-AUTH-006"] and all("NOT STARTED" in g["execution"] for g in got)
    assert client.post("/api/theses/active", json={"active": ["NOPE-1"]}).status_code == 400
    api._cache.clear()


def test_records_only_fallback(monkeypatch):
    import logos_dashboard.api as api
    monkeypatch.setattr(rd, "lab_runs", lambda: {"records_only": True, "error": "down", "runs": [], "preregistrations": [], "artifacts": [], "negative_results": []}); api._cache.clear()
    h = client.get("/api/health").json(); assert h["records_only"] is True
    assert client.get("/api/negative-results").status_code == 200 and client.get("/api/reproducibility").json()["records_only"] is True
    api._cache.clear()


def test_tooling_guard_and_no_model_calls():
    from logos_dashboard import PRODUCTION_PACKAGES, assert_tooling_caller, SOURCE_CLASS
    assert SOURCE_CLASS == "TOOLING" and "logos_authority" in PRODUCTION_PACKAGES
    with pytest.raises(ImportError):
        assert_tooling_caller(["logos_runtime.bridge"])
    src = "".join((ROOT / "src/logos_dashboard" / f).read_text(encoding="utf-8") for f in ("api.py", "readers.py", "registries.py"))
    for tok in ("import openai", "import anthropic", "claude -p", "ClaudeCodeMaxProvider", "subprocess.run([\"claude\""):
        assert tok not in src, tok


def test_research_intake_queue_and_brief_validation(tmp_path, monkeypatch):
    from logos_dashboard import research_intake as ri
    q = ri.queue(REGS)
    assert q and all(t["task_id"].startswith("RQ-") for t in q) and any(t["priority"] == "HIGH" for t in q)
    good = {"schema": "logos.research-brief/1", "brief_id": "RB-test", "date": "2026-09-19", "claim_id": "LOGOS-CP-001", "question": "q", "sub_questions": ["a"], "synthesis": "we observe", "limitations": ["WebSearch fallback"], "reviewed_by_founder": True,
            "novelty_assessment": {"status": "POSSIBLE_INCREMENTAL", "differentiation": ""},
            "sources": [{"citation_id": "PA-900", "title": "t", "authors": "a", "year": 2024, "venue": "v", "url": "https://example.org/x", "claim_supported": "s", "claim_not_supported": "n", "notes": "", "research_track": "cognitive-provenance", "novelty_status": "POSSIBLE_INCREMENTAL"}]}
    assert ri.validate_brief(good) == []
    bad = {**good, "reviewed_by_founder": False, "synthesis": "we are the first", "novelty_assessment": {"status": "CLEAR_DIFFERENTIATION"}, "sources": [{**good["sources"][0], "novelty_status": "STRONG_NOVELTY_EVIDENCE", "url": "nope"}]}
    issues = ri.validate_brief(bad)
    assert any("reviewed" in i for i in issues) and any("forbidden" in i for i in issues) and any("STRONG" in i for i in issues) and any("locator" in i for i in issues) and any(">= 3" in i for i in issues)
    with pytest.raises(ValueError):
        ri.merge_brief(bad)
    monkeypatch.setattr(ri, "DASH", tmp_path)
    (tmp_path / "PRIOR-ART-REGISTRY.json").write_text(json.dumps({"schema": "x", "citations": [], "count": 0}), encoding="utf-8")
    out = ri.merge_brief(good)
    assert out["added"] == ["PA-900"] and json.loads((tmp_path / "PRIOR-ART-REGISTRY.json").read_text(encoding="utf-8"))["count"] == 1
    assert client.get("/api/research-queue").status_code == 200 and client.post("/api/research-briefs/validate", json={"brief": bad}).json()["issues"]
    skill = (ROOT / ".claude/skills/logos-prior-art-research/SKILL.md").read_text(encoding="utf-8")
    assert "deep-research" in skill and "STRONG_NOVELTY_EVIDENCE" in skill and "never edits a registry" in skill


def test_dashboard_source_classification_complete():
    import subprocess
    cls = json.loads((ROOT / "docs/research/DASHBOARD-SOURCE-CLASSIFICATION.json").read_text(encoding="utf-8"))
    sites = cls["sites"]
    assert cls["unclassified"] == 0 and all(v["class"] in cls["vocabulary"] and v["class"] != "UNCLASSIFIED" for v in sites.values())
    assert not any(v["class"] == "PRODUCTION" for v in sites.values())
    assert all(v["class"] == "TOOLING" for k, v in sites.items() if k.startswith(("apps/dashboard/", "src/logos_dashboard/")))
    changed = subprocess.run(["git", "diff", "--name-only", "88d4757", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    files = {c for c in changed + untracked if "__pycache__" not in c and not c.endswith(".pyc")}
    assert files - set(sites) == set(), files - set(sites)
    from logos_research import experiments
    assert "logos_dashboard" not in experiments.PRODUCTION_PACKAGES
