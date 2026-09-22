"""LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 — Phase 3: CAUSAL-TAINT-PROPAGATION-R1.

H3: under system C taint survival = 1.0, source attribution = 1.0, false consensus = 0, rollback coverage = 1.0
and authority escalation = 0 over lengths 1/10/100/1000 and all six attack fixtures; under A survival -> 0.
Falsified by any C case where ancestry is lost or authority rises.
"""
from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_authority as la
from logos_memory.scope import scope_digest
from logos_research.experiments import causal_provenance as cp
from logos_research.experiments.binding_state import _base_contract

WINDOW, STATE_A = (10, 20), "a" * 64
LENGTHS = (1, 10, 100, 1000)
ROWS: list[dict] = []
CAUGHT: dict[str, str] = {}


def contract():
    return _base_contract(targets=("silo-4",), roles=("operator-A",), capabilities=("execute-action",), approval_required=True, externality="external", reversibility="irreversible")


def store_with_grant(gid="g", *, revoked=False, origin="human", window=(0, 5000)):
    S = la.InMemoryAuthorityStore()
    S.issue(la.GrantRecord(gid, "v1", "operator-A", "TRANSFER", "silo-4", scope_digest(contract()), origin, STATE_A, window[0], window[0], window[1], "test"))
    if revoked:
        S.revoke(gid, at_tick=1)
    return S


def run(mode, length, attack, **kw) -> cp.ChainResult:
    r = cp.run_chain(mode, length, attack, scope_digest=scope_digest(contract()), state=STATE_A, **kw)
    ROWS.append({"system": mode, "length": length, "attack": attack, **{k: v for k, v in r.metrics.items() if k in ("TaintSurvival", "SourceAttributionAccuracy", "FalseConsensus", "RollbackCoverage", "AuthorityEscalation", "ProvenanceLoss", "DetectionLatency", "ContainmentLatency", "authority_status")}})
    return r


# ==========================================================================
# Three-system comparison (Section 29) and H3
# ==========================================================================

@pytest.mark.parametrize("attack", cp.TAINTS)
@pytest.mark.parametrize("length", LENGTHS)
def test_H3_three_systems(length, attack):
    a, b, c = (run(m, length, attack) for m in "ABC")
    m = c.metrics
    assert m["TaintSurvival"] == 1.0 and m["SourceAttributionAccuracy"] == 1.0 and m["ProvenanceLoss"] == 0.0 and m["FalseConsensus"] == 0 and m["RollbackCoverage"] == 1.0
    assert m["AuthorityEscalation"] == 0 and m["authority_status"] == "NO_GRANT" and m["DetectionLatency"] == 1 and m["ContainmentLatency"] == 0
    assert m["TransformationDepth"] == length and m["execution_policy"] != "PROCEED"
    if length > 10:
        assert m["DelayedAction"] == 1 and m["DelayedActionDetected"] == 1 and a.metrics["DelayedActionDetected"] == 0
    assert a.metrics["TaintSurvival"] == 0.0 and a.metrics["SourceAttributionAccuracy"] == 0.0 and a.metrics["RollbackCoverage"] == 0.0 and a.metrics["DetectionLatency"] is None
    assert a.metrics["AuthorityEscalation"] == b.metrics["AuthorityEscalation"] == 0                    # no system mints authority; escalation is not what distinguishes them
    if length >= 10:
        assert 0.0 < b.metrics["TaintSurvival"] < 1.0 and b.metrics["RollbackCoverage"] < 1.0 and a.metrics["FalseConsensus"] >= 1 and b.metrics["FalseConsensus"] >= 1
    assert c.truth_taint_final == {attack} and set(c.truth_sources_final) >= {"src-taint"}


# ==========================================================================
# Authority separation (Section 28): EpistemicTaint != Authority
# ==========================================================================

def test_valid_grant_does_not_sanitize_taint_and_taint_does_not_mint_grant():
    S = store_with_grant()
    c = run("C", 25, "InjectedPlan", store=S, grant_ref="g")
    assert c.metrics["authority_status"] == "RESOLVED" and c.metrics["AuthorityEscalation"] == 0        # the grant is real: authority holds
    assert c.metrics["TaintSurvival"] == 1.0 and c.metrics["execution_policy"] == "HOLD_FOR_REVIEW"     # ... and the taint is untouched by it
    c2 = run("C", 25, "InjectedPlan", store=store_with_grant(revoked=True), grant_ref="g")
    assert c2.metrics["authority_status"] == "REVOKED"                                                   # revoked dominates
    c3 = run("C", 25, "InjectedPlan", store=la.InMemoryAuthorityStore(), grant_ref="g")
    assert c3.metrics["authority_status"] == "NO_GRANT" and c3.metrics["AuthorityEscalation"] == 0
    g = cp.ProvenanceGraph("C"); n = g.add_source("s", "x", agent_id="a", execution_id="e", tick=0, taint=("Misinformation",), authority_relation="REFERENCES_GRANT:g")
    assert n.authority_relation.startswith("REFERENCES_GRANT") and cp.execution_policy(n) == "INFORMATION_REQUEST"
    assert cp.execution_policy(replace(n, taint_labels=frozenset())) == "PROCEED" and cp.execution_policy(replace(n, epistemic_status="ROLLED_BACK")) == "ROLLBACK"
    assert cp.execution_policy(replace(n, confidence_metadata={"confidence": 0.99, "trusted_agent": True, "votes": 9})) == "INFORMATION_REQUEST"   # confidence/trust/votes change nothing


# ==========================================================================
# Record / graph semantics
# ==========================================================================

def test_record_fields_and_transformation_version():
    g = cp.ProvenanceGraph("C"); s = g.add_source("s", "c", agent_id="ext", execution_id="e", tick=0, taint=("Misinformation",))
    n = g.transform("paraphrase", ["s"], "p", agent_id="agent-A", execution_id="e", tick=1)
    for f in ("node_id", "content_hash", "source_ids", "parent_ids", "transformation_ids", "agent_id", "execution_id", "logical_tick", "epistemic_status", "taint_labels", "confidence_metadata", "authority_relation"):
        assert hasattr(n, f)
    assert n.source_ids == ("s",) and n.parent_ids == ("s",) and n.taint_labels == {"Misinformation"} and n.epistemic_status == "DERIVED"
    t = g.transformations[n.transformation_ids[0]]
    assert t.kind == "paraphrase" and t.version == cp.TRANSFORM_VERSION and t.input_ids == ("s",) and t.output_id == n.node_id
    with pytest.raises(cp.ProvenanceError):
        g.add_source("bad", "x", agent_id="ext", execution_id="e", tick=0, taint=("NotATaint",))
    with pytest.raises(cp.ProvenanceError):
        g.transform("teleport", ["s"], "x", agent_id="a", execution_id="e", tick=2)


def test_tenant_boundary_cycle_safety_tombstone_and_audit():
    g = cp.ProvenanceGraph("C")
    a = g.add_source("a", "x", agent_id="ext", execution_id="e", tick=0, taint=("Misinformation",), tenant_id="tenant-a")
    b = g.add_source("b", "y", agent_id="ext", execution_id="e", tick=0, tenant_id="tenant-b")
    with pytest.raises(cp.ProvenanceError):
        g.transform("summary", ["a", "b"], "z", agent_id="agent-A", execution_id="e", tick=1)
    n1 = g.transform("paraphrase", ["a"], "p1", agent_id="agent-A", execution_id="e", tick=1)
    with pytest.raises(cp.ProvenanceError):
        g.transform("paraphrase", [n1.node_id], "dup", agent_id="agent-A", execution_id="e", tick=2, node_id="a")     # cannot re-create / re-parent an existing id
    n2 = g.transform("summary", [n1.node_id, "a"], "p2", agent_id="agent-B", execution_id="e", tick=2)
    assert g.ancestors(n2.node_id) == {"a", n1.node_id} and g.descendants("a") == {n1.node_id, n2.node_id}
    g.tombstone_source("a")
    assert g.nodes["a"].content_hash == "[deleted]" and g.nodes[n2.node_id].source_ids == ("a",) and g.nodes[n2.node_id].taint_labels == {"Misinformation"}
    lineage = g.reconstruct_lineage(n2.node_id)
    assert lineage["sources"] == ["a"] and set(lineage["ancestors"]) == {"a", n1.node_id} and "paraphrase" in lineage["transformations"]


# ==========================================================================
# CTP-P1..P15 (hypothesis)
# ==========================================================================

S_ATTACK = st.sampled_from(cp.TAINTS); S_LEN = st.integers(1, 60); S_KIND = st.sampled_from(cp.TRANSFORMS)


def _graph_with(attack, kinds, seed=0):
    g = cp.ProvenanceGraph("C"); g.add_source("t", f"t{seed}", agent_id="ext", execution_id="e", tick=0, taint=(attack,))
    g.add_source("c0", "c0", agent_id="ext", execution_id="e", tick=0); g.add_source("c1", "c1", agent_id="ext", execution_id="e", tick=0)
    prev = "t"; hist = ["t"]
    for i, k in enumerate(kinds, 1):
        parents = [prev, "c0"] if k == "summary" else (hist[-3:] if k == "majority_vote" and len(hist) >= 3 else [prev])
        n = g.transform(k, parents, f"{k}{i}", agent_id=("agent-A", "agent-B", "agent-C")[i % 3], execution_id="e", tick=i, trusted_agent=(i % 3 == 2))
        prev = n.node_id; hist.append(prev)
    return g, prev


@settings(max_examples=300, deadline=None)
@given(attack=S_ATTACK, kinds=st.lists(S_KIND, min_size=1, max_size=25))
def test_CTP_P1_P3_P4_P5_ancestry_preserved_over_every_transformation(attack, kinds):
    g, last = _graph_with(attack, kinds)
    assert attack in g.taint(last) and "t" in g.sources(last)
    ROWS.append({"system": "C", "length": len(kinds), "attack": attack, "TaintSurvival": 1.0, "prop": "P1"})


@settings(max_examples=150, deadline=None)
@given(attack=S_ATTACK, length=S_LEN, grant=st.sampled_from(["none", "valid", "revoked", "model"]))
def test_CTP_P2_P9_P10_authority_unchanged_by_taint_revoked_dominates_grant_does_not_sanitize(attack, length, grant):
    S = {"none": la.InMemoryAuthorityStore(), "valid": store_with_grant(), "revoked": store_with_grant(revoked=True), "model": store_with_grant(origin="model")}[grant]
    r = run("C", length, attack, store=S, grant_ref="g")
    expect = {"none": "NO_GRANT", "valid": "RESOLVED", "revoked": "REVOKED", "model": "RESOLVED"}[grant]
    assert r.metrics["authority_status"] == expect and r.metrics["AuthorityEscalation"] == 0 and r.metrics["TaintSurvival"] == 1.0


@settings(max_examples=100, deadline=None)
@given(attack=S_ATTACK, votes=st.integers(3, 9))
def test_CTP_P6_majority_repetition_does_not_create_authority_or_clear_taint(attack, votes):
    g = cp.ProvenanceGraph("C"); g.add_source("t", "t", agent_id="ext", execution_id="e", tick=0, taint=(attack,))
    copies = [g.transform("paraphrase", ["t"], f"copy{i}", agent_id=f"agent-{i}", execution_id="e", tick=1).node_id for i in range(votes)]
    v = g.transform("majority_vote", copies, "vote", agent_id="agent-Z", execution_id="e", tick=2, votes=votes)
    assert g.shared_source_consensus(copies) and attack in v.taint_labels and v.source_ids == ("t",)
    res = cp.authority_for_action(v, la.InMemoryAuthorityStore(), principal="operator-A", action="TRANSFER", target="silo-4", scope_digest=scope_digest(contract()), state=STATE_A, tick=3, grant_ref=None)
    assert res.status == "NO_GRANT"
    ROWS.append({"system": "C", "length": 2, "attack": attack, "TaintSurvival": 1.0, "AuthorityEscalation": 0, "prop": "P6"})


@settings(max_examples=200, deadline=None)
@given(attack=S_ATTACK, length=st.integers(11, 80))
def test_CTP_P7_delayed_actions_retain_ancestry(attack, length):
    r = run("C", length, attack)
    assert r.metrics["DelayedAction"] == 1 and r.metrics["DelayedActionDetected"] == 1 and attack in r.truth_taint_final


@settings(max_examples=150, deadline=None)
@given(attack=S_ATTACK, kinds=st.lists(S_KIND, min_size=1, max_size=20))
def test_CTP_P8_P13_rollback_reaches_descendants_and_audit_reconstructs(attack, kinds):
    g, last = _graph_with(attack, kinds)
    desc = g.descendants("t")
    reached = g.rollback("t", tick=99)
    assert reached == desc | {"t"} and all(g.nodes[n].epistemic_status == "ROLLED_BACK" for n in reached)
    lin = g.reconstruct_lineage(last)
    assert "t" in lin["sources"] and set(lin["ancestors"]) == g.ancestors(last)
    ROWS.append({"system": "C", "length": len(kinds), "attack": attack, "TaintSurvival": 1.0, "RollbackCoverage": 1.0, "prop": "P8"})


@settings(max_examples=80, deadline=None)
@given(kinds=st.lists(S_KIND, min_size=1, max_size=15))
def test_CTP_P11_P12_cycle_safe_and_tenant_preserved(kinds):
    g, last = _graph_with("Misinformation", kinds)
    assert last not in g.ancestors(last) and all(n.tenant_id == "tenant-a" for n in g.nodes.values())
    ROWS.append({"system": "C", "length": len(kinds), "attack": "Misinformation", "TaintSurvival": 1.0, "prop": "P11"})
    g.add_source("other", "o", agent_id="ext", execution_id="e", tick=0, tenant_id="tenant-b")
    with pytest.raises(cp.ProvenanceError):
        g.transform("summary", [last, "other"], "x", agent_id="agent-A", execution_id="e", tick=50)


@settings(max_examples=150, deadline=None)
@given(attack=S_ATTACK, kinds=st.lists(S_KIND, min_size=1, max_size=15))
def test_CTP_P14_P15_source_deletion_keeps_derivation_and_versions_captured(attack, kinds):
    g, last = _graph_with(attack, kinds)
    g.tombstone_source("t")
    assert "t" in g.sources(last) and attack in g.taint(last)
    ROWS.append({"system": "C", "length": len(kinds), "attack": attack, "TaintSurvival": 1.0, "prop": "P14"})
    assert all(t.version == cp.TRANSFORM_VERSION for t in g.transformations.values()) and all(e.get("version") == cp.TRANSFORM_VERSION for e in g.log if e["event"] == "transform")


# ==========================================================================
# Taint mutation suite (15)
# ==========================================================================

def _run_nolog(mode, length, attack, **kw):
    return cp.run_chain(mode, length, attack, scope_digest=scope_digest(contract()), state=STATE_A, **kw)


def _battery():
    for attack in ("Misinformation", "InjectedPlan"):
        c = _run_nolog("C", 12, attack)
        assert c.metrics["TaintSurvival"] == 1.0 and c.metrics["SourceAttributionAccuracy"] == 1.0 and c.metrics["FalseConsensus"] == 0, ("chain", attack, c.metrics)
        assert c.metrics["RollbackCoverage"] == 1.0 and c.metrics["AuthorityEscalation"] == 0 and c.metrics["execution_policy"] != "PROCEED", ("chain2", c.metrics)
    g = cp.ProvenanceGraph("C"); g.add_source("t", "t", agent_id="ext", execution_id="e", tick=0, taint=("InjectedPlan",))
    steps = {}
    prev = "t"
    for i, k in enumerate(("paraphrase", "summary", "agent_handoff", "memory_write", "memory_reload", "plan_conversion", "tool_result"), 1):
        parents = [prev, "t"] if k == "summary" else [prev]
        n = g.transform(k, parents, k, agent_id=("agent-A", "agent-C")[i % 2], execution_id="e", tick=i, trusted_agent=(i % 2 == 1), confidence=0.99)
        assert "InjectedPlan" in n.taint_labels and "t" in n.source_ids, ("transform", k)
        steps[k] = n.node_id; prev = n.node_id
    copies = [g.transform("paraphrase", ["t"], f"c{i}", agent_id=f"agent-{i}", execution_id="e", tick=10).node_id for i in range(3)]
    v = g.transform("majority_vote", copies, "v", agent_id="agent-Z", execution_id="e", tick=11, votes=3)
    assert "InjectedPlan" in v.taint_labels and g.shared_source_consensus(copies), "majority"
    # valid grant does not sanitize
    S = store_with_grant(); r = _run_nolog("C", 12, "InjectedPlan", store=S, grant_ref="g")
    assert r.metrics["authority_status"] == "RESOLVED" and r.metrics["TaintSurvival"] == 1.0 and r.metrics["execution_policy"] == "HOLD_FOR_REVIEW", ("grant", r.metrics)
    lin = g.reconstruct_lineage(prev); assert "t" in lin["sources"] and steps["paraphrase"] in lin["ancestors"], "audit"
    reached = g.rollback("t", tick=20); assert reached == g.descendants("t") | {"t"}, "rollback"
    # cross-agent message keeps the source chain
    h = g.nodes[steps["agent_handoff"]]; assert h.source_ids == ("t",) and h.agent_id != g.nodes[steps["summary"]].agent_id, "handoff"


def _clear_on(kind):
    def apply(mp):
        real = cp.ProvenanceGraph.transform

        def mut(self, k, parents, content, **kw):
            n = real(self, k, parents, content, **kw)
            if k == kind:
                self.nodes[n.node_id] = replace(n, taint_labels=frozenset(), source_ids=())
            return n if k != kind else self.nodes[n.node_id]
        mp.setattr(cp.ProvenanceGraph, "transform", mut)
    return apply


def _clear_when(pred):
    def apply(mp):
        real = cp.ProvenanceGraph.transform

        def mut(self, k, parents, content, **kw):
            n = real(self, k, parents, content, **kw)
            if pred(n, kw):
                self.nodes[n.node_id] = replace(n, taint_labels=frozenset(), source_ids=())
                return self.nodes[n.node_id]
            return n
        mp.setattr(cp.ProvenanceGraph, "transform", mut)
    return apply


def _grant_sanitizes(mp):
    real = cp.run_chain

    def mut(mode, length, attack, **kw):
        r = real(mode, length, attack, **kw)
        if r.metrics["authority_status"] == "RESOLVED":
            r.metrics["TaintSurvival"] = 0.0; r.metrics["execution_policy"] = "PROCEED"
        return r
    mp.setattr(cp, "run_chain", mut)


def _audit_drops_parent(mp):
    real = cp.ProvenanceGraph.reconstruct_lineage
    mp.setattr(cp.ProvenanceGraph, "reconstruct_lineage", lambda self, n: {**real(self, n), "ancestors": real(self, n)["ancestors"][1:]})


def _rollback_shallow(mp):
    real = cp.ProvenanceGraph.rollback
    mp.setattr(cp.ProvenanceGraph, "rollback", lambda self, n, *, tick: (lambda r: {n})(real(self, n, tick=tick)))


def _handoff_loses_chain(mp):
    _clear_on("agent_handoff")(mp)


MUTANTS = [("paraphrase clears taint", _clear_on("paraphrase")), ("summary clears taint", _clear_on("summary")), ("agent handoff clears taint", _clear_on("agent_handoff")),
           ("memory write clears taint", _clear_on("memory_write")), ("memory reload clears taint", _clear_on("memory_reload")), ("plan conversion clears taint", _clear_on("plan_conversion")),
           ("tool output clears taint", _clear_on("tool_result")), ("trusted agent clears ancestry", _clear_when(lambda n, kw: kw.get("trusted_agent"))),
           ("majority vote clears ancestry", _clear_on("majority_vote")), ("high confidence clears taint", _clear_when(lambda n, kw: kw.get("confidence", 0) >= 0.9)),
           ("high trust clears taint", _clear_when(lambda n, kw: n.agent_id == "agent-C")), ("valid grant clears epistemic ancestry", _grant_sanitizes),
           ("audit reconstruction drops parent", _audit_drops_parent), ("rollback ignores descendants", _rollback_shallow),
           ("cross-agent message loses source chain", _clear_when(lambda n, kw: n.agent_id != "agent-A" and len(n.parent_ids) == 1 and n.transformation_ids))]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[f"M{i + 1}" for i in range(len(MUTANTS))])
def test_MUT_caught(label, apply, monkeypatch):
    apply(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[label] = str(e.value)[:100]


def test_MUT_zz_all_fifteen_caught():
    assert len(MUTANTS) == 15 and set(CAUGHT) == {m[0] for m in MUTANTS}


def test_zz_aggregate():
    assert len(ROWS) >= 1000, len(ROWS)
    c_rows = [r for r in ROWS if r["system"] == "C"]
    bad = [r for r in c_rows if r.get("TaintSurvival") != 1.0] + [r for r in ROWS if r.get("AuthorityEscalation", 0) != 0]
    assert bad == [], bad[:5]
    out = os.environ.get("P3_RESULTS")
    if out:
        table = {}
        for r in ROWS:
            if "prop" in r:
                continue
            table.setdefault(f"{r['system']}@{r['length']}", []).append(r)
        summary = {k: {m: sum(x[m] for x in v) / len(v) for m in ("TaintSurvival", "SourceAttributionAccuracy", "FalseConsensus", "RollbackCoverage", "AuthorityEscalation")} for k, v in table.items()}
        Path(out).write_text(json.dumps({"rows": len(ROWS), "mutants": CAUGHT, "three_system_table": summary}, indent=1), encoding="utf-8")
