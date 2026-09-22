"""LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 — Phases 0, 6 and 7: research-radar registry consistency,
state/uncertainty/belief/world schemas, source classification, the cross-layer mutation campaign, the no-real-model
rule and the P7 / Γ / production-bridge boundary checks.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_research.measurement as ms
from logos_research.measurement import construct as cs
from logos_research.measurement import state_schema as ss
from logos_research.experiments import causal_provenance as cp
from logos_research.experiments import reconsolidation as rc
from logos_research.experiments import trajectory_compromise as tc
import logos_authority as la

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
RADAR = json.loads((ROOT / "docs/research/RESEARCH-RADAR.json").read_text(encoding="utf-8"))
CLASSIFICATION = json.loads((ROOT / "docs/research/PRE-INFERENCE-SOURCE-CLASSIFICATION.json").read_text(encoding="utf-8"))
CAUGHT: dict[str, str] = {}


# ==========================================================================
# Phase 0 — radar registry
# ==========================================================================

def test_RD01_RD14_registered_with_required_fields():
    ds = RADAR["deltas"]
    assert [d["id"] for d in ds] == [f"RD-{i:02d}" for i in range(1, 15)]
    for d in ds:
        for f in ("source", "date", "evidence_strength", "replication_status", "logos_relevance", "claim_scope", "limitations", "proposed_invariants", "required_experiment", "dependency", "status"):
            assert d.get(f), (d["id"], f)
        assert d["evidence_strength"] in RADAR["evidence_vocabulary"] and d["status"] in RADAR["status_vocabulary"]
        assert "not replicated" in d["replication_status"] and d["evidence_strength"] != "INDEPENDENTLY_REPLICATED"
    assert next(d for d in ds if d["id"] == "RD-01")["evidence_strength"] == "PRELIMINARY" and "BDH" in next(d for d in ds if d["id"] == "RD-01")["title"]
    assert next(d for d in ds if d["id"] == "RD-01")["status"] == "BLOCKED_BY_INFERENCE"


def test_RI_P1_P19_proposed_never_proven_and_rendered_docs_current():
    ris = RADAR["research_invariants"]
    assert [r["id"] for r in ris] == [f"RI-P{i}" for i in range(1, 20)] and all(r["status"] == "PROPOSED" for r in ris)
    txt = "\n".join((ROOT / p).read_text(encoding="utf-8") for p in ("docs/research/RESEARCH-RADAR-DELTA-REGISTRY.md", "docs/research/LOGOS1-POST-DETERMINISTIC-RESEARCH-MAP.md",
                                                                        "docs/research/RESEARCH-EVIDENCE-STRENGTH.md", "docs/research/POST-INFERENCE-EXPERIMENT-QUEUE.md"))
    import re
    assert not re.search(r"\b(PROVEN|AXIOM|FORMALLY_VERIFIED|PRODUCTION_GUARANTEE)\b", txt)
    r = subprocess.run([sys.executable, str(ROOT / "scripts/render_research_radar.py"), "--check"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout
    tiers = RADAR["post_inference_queue"]
    ids = [q["id"] for t in tiers for q in t["items"]]
    assert set(ids) == {"BELIEF_STATE_GEOMETRY", "COGNITIVE_PROVENANCE_ABLATION", "WORLD_MODEL_TRUST_BOUNDARY", "TRAJECTORY_UNCERTAINTY_ACCUMULATION", "MEMORY_RATE_DISTORTION_SURFACE",
                       "BDH_LONG_HORIZON_DECOMPOSITION", "MEMORY_PLAN_STATE_DECOMPOSITION", "PERSISTENCE_DYNAMICS", "PRETASK_WORLD_STUDY", "INTENT_ACTION_WORLD_DIVERGENCE"}
    assert all("INFERENCE-PROHIBITION (ACTIVE)" in q["blocked_by"] for t in tiers for q in t["items"])


# ==========================================================================
# Phase 6 — schemas
# ==========================================================================

def test_state_kinds_update_contract_and_forbidden_writes():
    assert ss.STATE_KINDS == ("EvidenceState", "BeliefState", "PlanState", "ExecutionState", "ObservedWorldState", "PredictedWorldState", "CommandedWorldState", "MemoryState",
                              "TrajectoryUncertaintyState", "CausalProvenanceState")
    assert not ss.write_allowed("PlanState", "EvidenceState") and not ss.write_allowed("BeliefState", "EvidenceState") and not ss.write_allowed("PredictedWorldState", "ObservedWorldState")
    assert not ss.write_allowed("PredictedWorldState", "EvidenceState") and not ss.write_allowed("CommandedWorldState", "ObservedWorldState") and not ss.write_allowed("BeliefState", "CausalProvenanceState")
    assert ss.write_allowed("EvidenceState", "BeliefState") and ss.write_allowed("BeliefState", "PlanState") and ss.write_allowed("ObservedWorldState", "EvidenceState")
    with pytest.raises(ValueError):
        ss.write_allowed("Authority", "PlanState")
    assert set(ss.MEMORY_TAXONOMY) == {"ExplicitEpisodicMemory", "DynamicRecurrentState", "ReconsolidatingMemory", "WorkingMemory", "PlanState", "ExternalizedEnvironmentPrior", "DynamicallyMaintainedMemory"}
    assert all(v["authority"] == "never" for v in ss.MEMORY_TAXONOMY.values()) and ss.MEMORY_TAXONOMY["ReconsolidatingMemory"]["read_class"].startswith("READ_WITH_RECONSOLIDATION")


def test_belief_state_and_world_triple():
    b = ss.BeliefState("dir-7", ("e1",), "u1", 0.3, ("n1",))
    assert b.causal_use_status == "UNKNOWN" and replace(b, causal_use_status="DECODABLE_ONLY").causal_use_status != "CAUSALLY_USED"
    with pytest.raises(ValueError):
        ss.BeliefState("d", (), "u", 0.1, (), causal_use_status="AUTHORITATIVE")
    w = ss.WorldStateTriple({"valve": "open"}, None, None)
    assert not w.committed and w.agreement == {"command_executed": False, "execution_observed": False, "intended_outcome": False}
    w2 = ss.WorldStateTriple({"valve": "open"}, {"valve": "open"}, {"valve": "half"})
    assert not w2.committed and w2.agreement["command_executed"] and not w2.agreement["intended_outcome"]
    assert ss.WorldStateTriple({"v": 1}, {"v": 1}, {"v": 1}).committed


@settings(max_examples=150, deadline=None)
@given(u=st.lists(st.tuples(st.floats(0, 1, allow_nan=False), st.floats(0, 1, allow_nan=False)), min_size=1, max_size=30))
def test_property_trajectory_uncertainty_contract(u):
    loc = [a for a, _ in u]; sta = [b for _, b in u]
    t = ss.accumulate(loc, sta)
    for i in range(len(loc)):
        assert t.u_trajectory[i] + 1e-12 >= max(loc[: i + 1]) and (i == 0 or t.u_trajectory[i] + 1e-12 >= t.u_trajectory[i - 1])
    if len(loc) > 1 and max(loc) > 0.05:
        with pytest.raises(ValueError):
            ss.TrajectoryUncertainty(tuple(loc), tuple(sta), tuple(min(x, 0.0) for x in loc))       # "trajectory confidence = local confidence" is refused


# ==========================================================================
# Phase 7 — closure checks
# ==========================================================================

def test_source_classification_complete():
    sites = CLASSIFICATION["sites"]
    assert CLASSIFICATION["unclassified"] == 0 and all(v["class"] in CLASSIFICATION["vocabulary"] and v["class"] != "UNCLASSIFIED" for v in sites.values())
    assert not any(v["class"] == "PRODUCTION" for v in sites.values())
    changed = subprocess.run(["git", "diff", "--name-only", "eb1f642", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    files = {c for c in changed + untracked if "__pycache__" not in c and not c.endswith(".pyc")}
    missing = files - set(sites)
    assert missing <= {"docs/research/PRE-INFERENCE-SOURCE-CLASSIFICATION.json"} or missing <= {f for f in files if f.startswith(("09-SESSIONS/", "05-WORK-ORDERS/", "docs/"))}, missing


def test_no_real_model_calls_and_no_network_in_new_code():
    assert ms.CALLS["model_calls"] == 0 and ms.CALLS["provider_calls"] == 0
    for p in ("src/logos_research/measurement", "src/logos_research/experiments/causal_provenance.py", "src/logos_research/experiments/reconsolidation.py", "src/logos_research/experiments/trajectory_compromise.py"):
        for py in ([ROOT / p] if p.endswith(".py") else (ROOT / p).glob("*.py")):
            txt = py.read_text(encoding="utf-8")
            for tok in ("import requests", "import httpx", "import urllib", "import socket", "import openai", "import anthropic", "from openai", "from anthropic", "subprocess"):
                assert tok not in txt, (py.name, tok)


def test_production_bridge_gamma_p7_unchanged():
    frozen = {"src/logos_authority/resolver.py": None, "src/logos_runtime/bridge.py": None, "src/logos_audit/__init__.py": None, "src/logos_memory/reader.py": None, "src/logos_effects/registry.py": None}
    diff = subprocess.run(["git", "diff", "--stat", "eb1f642", "HEAD", "--", "GAMMA.md", "src/logos_gamma", "src/logos_authority", "src/logos_runtime", "src/logos_audit", "src/logos_effects",
                           "src/logos_memory", "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md", "src/logos_research/experiments/binding_state.py",
                           "src/logos_research/experiments/memory_authority.py", "src/logos_research/experiments/effect_oracle.py"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    assert diff == "", diff
    p7 = (ROOT / "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md").read_bytes()
    assert b"## Consciousness / P7 boundary" in p7
    from logos_research import experiments
    assert experiments.B1_STATUS == "NON_PRODUCTION_FROZEN_RISK_GUARDED"
    for frame in ("logos_runtime.bridge", "logos_authority.resolver", "logos_effects.registry"):
        with pytest.raises(ImportError):
            experiments.assert_experimental_caller([frame])


# ==========================================================================
# Cross-layer mutation campaign (Section 69, 15)
# ==========================================================================

def _battery():
    reg = ms.load_registry(); by = {m.metric_name: m for m in reg.values()}
    rep = [[0.3] * 4, [0.9] * 4, [0.5] * 4, [0.1] * 4]; means = [0.3, 0.9, 0.5, 0.1]; truth = [0.2, 0.2, 0.8, 0.8]
    assert cs.gate_status(cs.reliability(rep), cs.construct_validity(means, truth), None) == "RELIABLE_ONLY", "reliable->valid"
    assert not ms.allowed_as_evidence(by["SelfReportedConfidence"]), "self-report"
    assert not ms.allowed_as_evidence(by["BeliefStateDecodability"]) and by["BeliefStateDecodability"].status != "CAUSALLY_DISCRIMINATED", "decodable"
    assert not ms.allowed_as_evidence(by["FinalResponseSafety"]), "final->trajectory"
    g = cp.ProvenanceGraph("C"); g.add_source("t", "t", agent_id="ext", execution_id="e", tick=0, taint=("Misinformation",))
    p = g.transform("paraphrase", ["t"], "p", agent_id="agent-A", execution_id="e", tick=1); assert "t" in p.source_ids and p.taint_labels, "paraphrase"
    copies = [g.transform("paraphrase", ["t"], f"c{i}", agent_id=f"a{i}", execution_id="e", tick=2).node_id for i in range(3)]
    v = g.transform("majority_vote", copies, "v", agent_id="z", execution_id="e", tick=3, votes=3); assert v.taint_labels, "majority"
    f = rc.run_frequency_experiment("C"); assert f["BeliefInfluence"]["A"] == f["BeliefInfluence"]["B"], "frequency->authority"
    assert rc.authority_from_graph(f["graph"], "A0", rc.InMemoryAuthorityStore(), principal="operator-A", action="TRANSFER", target="silo-4", scope_digest="0" * 64, state="a" * 64, tick=1, grant_ref=None).status == "NO_GRANT", "centrality->truth"
    assert not ss.write_allowed("PlanState", "EvidenceState"), "plan->evidence"
    assert not ss.write_allowed("PredictedWorldState", "ObservedWorldState"), "prediction->observation"
    w = ss.WorldStateTriple({"v": 1}, None, None); assert not w.committed and not w.agreement["command_executed"], "command->execution"
    w2 = ss.WorldStateTriple({"v": 1}, {"v": 1}, {"v": 2}); assert not w2.agreement["intended_outcome"], "execution->outcome"
    r = tc.run_trajectory(tc.make_env(), inject_at="Plan", policy="boundary")
    assert r["metrics"]["IntermediateCompromise"] > 0 and r["record"].steps[3].authority_status == "RESOLVED" and r["record"].steps[3].taint, "grant->sanitized"
    n = g.transform("agent_handoff", ["t"], "h", agent_id="agent-C", execution_id="e", tick=4, trusted_agent=True, confidence=0.99); assert n.source_ids == ("t",), "trust->ancestry"
    n2 = g.transform("summary", ["t"], "s", agent_id="agent-A", execution_id="e", tick=5, confidence=1.0); assert n2.taint_labels, "voi->ancestry"


def _m(name):
    def reliable_valid(mp):
        real = cs.gate_status; mp.setattr(cs, "gate_status", lambda r, v, c, **k: "CONSTRUCT_SUPPORTED" if r >= 0.8 else real(r, v, c, **k))
    def self_report(mp):
        mp.setattr(ms, "allowed_as_evidence", lambda m: True)
    def decodable(mp):
        real = ms.load_registry
        mp.setattr(ms, "load_registry", lambda path=None: {k: (cs.MetricRecord(**{**m.__dict__, "status": "CAUSALLY_DISCRIMINATED"}) if m.metric_name == "BeliefStateDecodability" else m) for k, m in real(path).items()})
    def final_traj(mp):
        real = ms.load_registry
        mp.setattr(ms, "load_registry", lambda path=None: {k: (cs.MetricRecord(**{**m.__dict__, "status": "CONSTRUCT_SUPPORTED"}) if m.metric_name == "FinalResponseSafety" else m) for k, m in real(path).items()})
    def clear_kind(kind):
        def apply(mp):
            real = cp.ProvenanceGraph.transform
            def mut(self, k, parents, content, **kw):
                n = real(self, k, parents, content, **kw)
                if k == kind:
                    self.nodes[n.node_id] = replace(n, taint_labels=frozenset(), source_ids=()); return self.nodes[n.node_id]
                return n
            mp.setattr(cp.ProvenanceGraph, "transform", mut)
        return apply
    def freq_auth(mp):
        mp.setattr(rc.MemoryGraph, "belief_influence", lambda self, c: (lambda t: self.cluster_centrality(c) / t)(sum(self.centrality(i) for i in self.items) or 1.0))
    def centrality_truth(mp):
        real = rc.authority_from_graph
        def mut(g, item_id, store, **kw):
            r = real(g, item_id, store, **kw)
            return la.AuthorityResolution("RESOLVED", la.GrantRecord("c", "v1", kw["principal"], kw["action"], kw["target"], kw["scope_digest"], "human", kw["state"], 0, 0, 999, "c").evidence(), "c", "v1", "human", kw["principal"], kw["scope_digest"], 0, 0, 999, kw["state"], "active", "0" * 64, None, {}) if g.centrality(item_id) > 5 else r
        mp.setattr(rc, "authority_from_graph", mut)
    def plan_evidence(mp):
        mp.setattr(ss, "FORBIDDEN_WRITES", tuple(x for x in ss.FORBIDDEN_WRITES if x[:2] != ("PlanState", "EvidenceState"))); mp.setattr(ss, "UPDATE_CONTRACT", ss.UPDATE_CONTRACT | {("PlanState", "EvidenceState")})
    def pred_obs(mp):
        mp.setattr(ss, "FORBIDDEN_WRITES", tuple(x for x in ss.FORBIDDEN_WRITES if x[:2] != ("PredictedWorldState", "ObservedWorldState"))); mp.setattr(ss, "UPDATE_CONTRACT", ss.UPDATE_CONTRACT | {("PredictedWorldState", "ObservedWorldState")})
    def command_exec(mp):
        mp.setattr(ss.WorldStateTriple, "committed", property(lambda self: True))
        mp.setattr(ss.WorldStateTriple, "agreement", property(lambda self: {"command_executed": True, "execution_observed": True, "intended_outcome": True}))
    def exec_outcome(mp):
        mp.setattr(ss.WorldStateTriple, "agreement", property(lambda self: {"command_executed": self.executed is not None, "execution_observed": self.observed is not None, "intended_outcome": self.executed is not None}))
    def grant_sanitizes(mp):
        real = tc.run_trajectory
        def mut(env, **kw):
            r = real(env, **kw)
            if r["record"].steps[3].authority_status == "RESOLVED":
                r["record"].steps[:] = [replace(s, taint=()) if s.gate == "ToolExecutionGate" else s for s in r["record"].steps]
            return r
        mp.setattr(tc, "run_trajectory", mut)
    def trust_clears(mp):
        real = cp.ProvenanceGraph.transform
        def mut(self, k, parents, content, **kw):
            n = real(self, k, parents, content, **kw)
            if kw.get("trusted_agent"):
                self.nodes[n.node_id] = replace(n, source_ids=(), taint_labels=frozenset()); return self.nodes[n.node_id]
            return n
        mp.setattr(cp.ProvenanceGraph, "transform", mut)
    def voi_clears(mp):
        real = cp.ProvenanceGraph.transform
        def mut(self, k, parents, content, **kw):
            n = real(self, k, parents, content, **kw)
            if kw.get("confidence", 0) >= 1.0:
                self.nodes[n.node_id] = replace(n, taint_labels=frozenset()); return self.nodes[n.node_id]
            return n
        mp.setattr(cp.ProvenanceGraph, "transform", mut)
    return {"reliable metric -> construct valid automatically": reliable_valid, "self-report -> ground truth": self_report, "decodable -> causally used": decodable,
            "safe final -> safe trajectory": final_traj, "paraphrase -> provenance reset": clear_kind("paraphrase"), "majority vote -> taint cleared": clear_kind("majority_vote"),
            "retrieval frequency -> authority": freq_auth, "graph centrality -> truth": centrality_truth, "plan -> evidence overwrite": plan_evidence,
            "world prediction -> observation": pred_obs, "command -> execution": command_exec, "execution -> intended outcome": exec_outcome,
            "valid grant -> epistemic taint sanitized": grant_sanitizes, "high trust -> source ancestry cleared": trust_clears, "high VOI -> source ancestry cleared": voi_clears}[name]


MUTANTS = ["reliable metric -> construct valid automatically", "self-report -> ground truth", "decodable -> causally used", "safe final -> safe trajectory", "paraphrase -> provenance reset",
           "majority vote -> taint cleared", "retrieval frequency -> authority", "graph centrality -> truth", "plan -> evidence overwrite", "world prediction -> observation",
           "command -> execution", "execution -> intended outcome", "valid grant -> epistemic taint sanitized", "high trust -> source ancestry cleared", "high VOI -> source ancestry cleared"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:100]


def test_MUT_zz_all_fifteen_caught():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 15
    out = os.environ.get("P7_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"mutants": CAUGHT, "calls": ms.CALLS}, indent=1), encoding="utf-8")
