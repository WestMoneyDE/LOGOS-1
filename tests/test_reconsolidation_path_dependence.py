"""LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 — Phase 4: RECONSOLIDATION-PATH-DEPENDENCE-R1.

H4: system B amplifies retrieval frequency into belief influence and cannot roll back structure; system C keeps
BeliefInfluence(A) == BeliefInfluence(B) at equal evidence, recovers contradictory evidence and restores content +
graph on rollback; every structure-changing read is an audited write-class operation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_authority as la
from logos_memory.scope import scope_digest
from logos_research.experiments import reconsolidation as rc
from logos_research.experiments.binding_state import _base_contract

STATE_A = "a" * 64
ROWS: list[dict] = []
CAUGHT: dict[str, str] = {}


def contract():
    return _base_contract(targets=("silo-4",), roles=("operator-A",), capabilities=("execute-action",), approval_required=True, externality="external", reversibility="irreversible")


# ==========================================================================
# Section 39 — frequency experiment; Section 40 — poisoning path
# ==========================================================================

@pytest.mark.parametrize("ratio", [10, 3, 30])
def test_H4_frequency_experiment(ratio):
    a, b, c = (rc.run_frequency_experiment(m, ratio=ratio) for m in "ABC")
    for r in (a, b, c):
        ROWS.append({"exp": "freq", "system": r["system"], "ratio": ratio, "belief_A": r["BeliefInfluence"]["A"], "belief_B": r["BeliefInfluence"]["B"], "drift": r["StructuralDrift"], "audited": r["audited_reads"]})
    assert a["BeliefInfluence"]["A"] == a["BeliefInfluence"]["B"] and a["StructuralDrift"] == 0.0 and a["graph_version"] == 0
    assert b["BeliefInfluence"]["A"] > b["BeliefInfluence"]["B"] and b["GraphCentrality"]["A"] > b["GraphCentrality"]["B"] and b["audited_reads"] == 0 and b["graph_version"] == 0   # silent amplification
    assert c["BeliefInfluence"]["A"] == c["BeliefInfluence"]["B"] == 0.5                                       # equal evidence -> equal belief, centrality notwithstanding
    assert c["GraphCentrality"]["A"] > c["GraphCentrality"]["B"] and c["StructuralDrift"] > 0                   # plasticity is real ...
    assert c["audited_reads"] == c["retrievals"] == c["graph_version"] and c["FutureRetrievalProbability"]["A0"] == c["FutureRetrievalProbability"]["B0"]   # ... and fully audited/versioned
    assert c["ContradictoryEvidenceRecovery"] == 1.0


def test_H4_poisoning_path():
    a, b, c = (rc.run_poisoning_experiment(m) for m in "ABC")
    for r in (a, b, c):
        ROWS.append({"exp": "poison", "system": r["system"], "amplified": r["amplified"], "recovery": r["ContradictoryEvidenceRecovery"], "rollback": r["RollbackCompleteness"]})
    assert b["amplified"] and b["ContradictoryEvidenceRecovery"] == 0.0 and b["RollbackCompleteness"] == 0.5 and b["false_fact_present_after_rollback"] and not b["structure_restored"]
    assert not c["amplified"] and c["ContradictoryEvidenceRecovery"] == 1.0 and c["RollbackCompleteness"] == 1.0 and not c["false_fact_present_after_rollback"] and c["structure_restored"]
    assert c["taint_after_retrievals"] == ["Misinformation"]                                             # taint survives reconsolidation
    assert not a["amplified"] and a["RollbackCompleteness"] == 0.5                                        # immutable memory cannot undo the write either


def test_read_write_boundary_and_gate(tmp_path):
    g = rc.build("C")
    content, kind = g.retrieve("A0", tick=1)
    assert kind == "READ_WITH_RECONSOLIDATION" and g.graph_version == 1 and g.gate.audit[-1].kind == "READ_WITH_RECONSOLIDATION" and g.gate.audit[-1].graph_version == 1
    assert g.structural_mutations[-1]["item"] == "A0" and g.structural_mutations[-1]["sources"] == ["src-A0"]
    g2 = rc.build("C"); g2.gate = rc.MemoryWriteGate(audit=None); e0 = dict(g2.edges)
    with pytest.raises(rc.GateRefused):
        g2.retrieve("A0", tick=1)
    assert g2.edges == e0 and g2.graph_version == 0                                                     # refused -> no mutation
    with pytest.raises(rc.GateRefused):
        g2.inject(rc.MemoryItem("Z", "z", "A", 1.0), ["A0"], tick=2)
    assert rc.build("A").retrieve("A0", tick=1)[1] == "READ" and rc.build("B").retrieve("A0", tick=1)[1] == "READ"   # B mislabels its mutation as a read


def test_centrality_and_frequency_never_reach_authority():
    r = rc.run_frequency_experiment("B")
    g = r["graph"]; assert g.centrality("A0") > g.centrality("B2")
    for item in ("A0", "B2"):
        res = rc.authority_from_graph(g, item, la.InMemoryAuthorityStore(), principal="operator-A", action="TRANSFER", target="silo-4", scope_digest=scope_digest(contract()), state=STATE_A, tick=5, grant_ref=None)
        assert res.status == "NO_GRANT"
    S = la.InMemoryAuthorityStore(); S.issue(la.GrantRecord("g", "v1", "operator-A", "TRANSFER", "silo-4", scope_digest(contract()), "human", STATE_A, 0, 0, 100, "t"))
    assert rc.authority_from_graph(g, "B2", S, principal="operator-A", action="TRANSFER", target="silo-4", scope_digest=scope_digest(contract()), state=STATE_A, tick=5, grant_ref="g").status == "RESOLVED"


def test_tenant_edges_refused():
    g = rc.build("C"); g.add(rc.MemoryItem("T", "t", "A", 1.0, tenant_id="tenant-b"))
    with pytest.raises(ValueError):
        g.link("A0", "T")


@settings(max_examples=120, deadline=None)
@given(ratio=st.integers(1, 40), base=st.integers(1, 6), reinforcement=st.floats(0.01, 1.0))
def test_property_equal_evidence_equal_belief_under_any_frequency(ratio, base, reinforcement):
    g = rc.build("C"); g.reinforcement = reinforcement; tick = 0
    for _ in range(base * ratio):
        g.retrieve("A0", tick=tick); tick += 1
    for _ in range(base):
        g.retrieve("B1", tick=tick); tick += 1
    assert g.belief_influence("A") == g.belief_influence("B") and g.graph_version == base * ratio + base == len(g.gate.audit)
    rb = g.rollback(0); assert rb["completeness"] == 1.0 and g.edges == g.snapshots[0][1]
    ROWS.append({"exp": "prop", "system": "C", "ratio": ratio, "belief_A": g.belief_influence("A"), "belief_B": g.belief_influence("B")})


@settings(max_examples=80, deadline=None)
@given(retrievals=st.integers(1, 50), weight=st.floats(0.05, 0.9))
def test_property_poison_never_amplified_and_rollback_complete_in_C(retrievals, weight):
    g = rc.build("C"); tick = 0
    g.inject(rc.MemoryItem("F", "false", "A", weight, taint=frozenset({"Misinformation"})), ["A0"], tick=tick); tick += 1
    before = g.belief_influence("A")
    for _ in range(retrievals):
        g.retrieve("F", tick=tick); tick += 1
    assert g.belief_influence("A") == before and g.items["F"].taint == {"Misinformation"}
    rb = g.rollback(0); assert rb["completeness"] == 1.0 and "F" not in g.items
    ROWS.append({"exp": "prop-poison", "system": "C", "retrievals": retrievals, "amplified": False})


# ==========================================================================
# Mutants (10)
# ==========================================================================

def _battery():
    f = rc.run_frequency_experiment("C"); g = f["graph"]
    assert f["BeliefInfluence"]["A"] == f["BeliefInfluence"]["B"], ("frequency->truth", f["BeliefInfluence"])
    assert f["audited_reads"] == f["retrievals"] and f["graph_version"] == f["retrievals"], ("audit/version", f["audited_reads"], f["graph_version"])
    assert rc.authority_from_graph(g, "A0", la.InMemoryAuthorityStore(), principal="operator-A", action="TRANSFER", target="silo-4", scope_digest=scope_digest(contract()), state=STATE_A, tick=5, grant_ref=None).status == "NO_GRANT", "centrality->authority"
    p = rc.run_poisoning_experiment("C")
    assert not p["amplified"], "false evidence promoted"
    assert p["ContradictoryEvidenceRecovery"] == 1.0, "contradiction suppressed"
    assert p["RollbackCompleteness"] == 1.0 and p["structure_restored"], "rollback structure"
    assert p["taint_after_retrievals"] == ["Misinformation"], "taint lost"
    g2 = rc.build("C"); g2.gate = rc.MemoryWriteGate(audit=None)
    try:
        g2.retrieve("A0", tick=1); raise AssertionError("gate bypassed")
    except rc.GateRefused:
        pass
    g3 = rc.build("C"); g3.add(rc.MemoryItem("T", "t", "A", 1.0, tenant_id="tenant-b"))
    try:
        g3.link("A0", "T"); raise AssertionError("cross-tenant edge")
    except ValueError:
        pass


def _m(name):
    def freq_truth(mp):
        real = rc.MemoryGraph.belief_influence
        mp.setattr(rc.MemoryGraph, "belief_influence", lambda self, c: (lambda t: self.cluster_centrality(c) / t)(sum(self.centrality(i) for i in self.items) or 1.0))
    def centrality_authority(mp):
        real = rc.authority_from_graph
        def mut(g, item_id, store, **kw):
            r = real(g, item_id, store, **kw)
            if r.status == "NO_GRANT" and g.centrality(item_id) > 5:
                return la.AuthorityResolution("RESOLVED", la.GrantRecord("central", "v1", kw["principal"], kw["action"], kw["target"], kw["scope_digest"], "human", kw["state"], 0, 0, 999, "c").evidence(), "central", "v1", "human", kw["principal"], kw["scope_digest"], 0, 0, 999, kw["state"], "active", "0" * 64, None, {})
            return r
        mp.setattr(rc, "authority_from_graph", mut)
    def no_version_bump(mp):
        real = rc.MemoryGraph.retrieve
        def mut(self, item_id, *, tick):
            v = self.graph_version; out = real(self, item_id, tick=tick); self.graph_version = v; return out
        mp.setattr(rc.MemoryGraph, "retrieve", mut)
    def no_audit(mp):
        mp.setattr(rc.MemoryWriteGate, "check", lambda self, kind, item, gv, tick, detail: rc.AuditRecord(kind, item.item_id, gv, tick, detail))   # returns a record but never stores it
    def rollback_content_only(mp):
        real = rc.MemoryGraph.rollback
        def mut(self, version):
            items0, edges0 = self.snapshots[version]
            for i, it in items0.items():
                if i in self.items:
                    self.items[i].content = it.content
            return {"content": True, "structure": self.edges == edges0, "completeness": 1.0}
        mp.setattr(rc.MemoryGraph, "rollback", mut)
    def taint_lost(mp):
        real = rc.MemoryGraph.retrieve
        def mut(self, item_id, *, tick):
            out = real(self, item_id, tick=tick); self.items[item_id].taint = frozenset(); return out
        mp.setattr(rc.MemoryGraph, "retrieve", mut)
    def cross_tenant(mp):
        mp.setattr(rc.MemoryGraph, "link", lambda self, a, b, w=1.0: self.edges.update({(a, b): w, (b, a): w}))
    def false_promoted(mp):
        real = rc.MemoryGraph.retrieve
        def mut(self, item_id, *, tick):
            out = real(self, item_id, tick=tick); self.items[item_id].evidence_weight += 0.05; return out
        mp.setattr(rc.MemoryGraph, "retrieve", mut)
    def contradiction_suppressed(mp):
        mp.setattr(rc.MemoryGraph, "retrievable", lambda self, item_id, k=3: item_id in sorted(self.items, key=lambda i: -self.centrality(i))[:k])
    def gate_bypass(mp):
        real = rc.MemoryGraph.retrieve
        def mut(self, item_id, *, tick):
            try:
                return real(self, item_id, tick=tick)
            except rc.GateRefused:
                item = self.items[item_id]
                for b in [b for (a, b) in self.edges if a == item_id]:
                    self.edges[(item_id, b)] += self.reinforcement; self.edges[(b, item_id)] += self.reinforcement
                return item.content, "READ"
        mp.setattr(rc.MemoryGraph, "retrieve", mut)
    return {"retrieval frequency becomes truth": freq_truth, "centrality becomes authority": centrality_authority, "mutation without version bump": no_version_bump,
            "structure change without audit": no_audit, "rollback restores content but not graph": rollback_content_only, "taint lost during reconsolidation": taint_lost,
            "cross-tenant graph edge": cross_tenant, "frequent false evidence promoted": false_promoted, "contradictory evidence suppressed": contradiction_suppressed,
            "read mutation bypasses MemoryWriteGate": gate_bypass}[name]


MUTANTS = ["retrieval frequency becomes truth", "centrality becomes authority", "mutation without version bump", "structure change without audit", "rollback restores content but not graph",
           "taint lost during reconsolidation", "cross-tenant graph edge", "frequent false evidence promoted", "contradictory evidence suppressed", "read mutation bypasses MemoryWriteGate"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:100]


def test_MUT_zz_all_caught():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 10
    out = os.environ.get("P4_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"rows": len(ROWS), "mutants": CAUGHT, "freq": [r for r in ROWS if r["exp"] == "freq"], "poison": [r for r in ROWS if r["exp"] == "poison"]}, indent=1), encoding="utf-8")
