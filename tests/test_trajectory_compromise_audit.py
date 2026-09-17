"""LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 — Phase 5: TRAJECTORY-COMPROMISE-AUDIT-R1.

H5: a trajectory with a compromised intermediate step and a safe final response still records
IntermediateCompromise > 0 and the unsafe step's evidence; falsified if any safe final output hides
intermediate compromise or a consequential side effect bypasses the bridge.
"""
from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_runtime as rt
from logos_research.experiments import trajectory_compromise as tc

ROWS: list[dict] = []
CAUGHT: dict[str, str] = {}


def run(inject, policy="boundary", grant="human"):
    r = tc.run_trajectory(tc.make_env(grant=grant), inject_at=inject, policy=policy)
    ROWS.append({"inject": inject, "policy": policy, "grant": grant, **{k: v for k, v in r["metrics"].items() if k != "final_taint"}, "outcomes": [s.outcome for s in r["record"].steps]})
    return r


# ==========================================================================
# H5 — SafeFinalOutput != SafeTrajectory
# ==========================================================================

@pytest.mark.parametrize("policy", ["boundary", "final-only"])
@pytest.mark.parametrize("grant", ["human", None])
@pytest.mark.parametrize("inject", tc.INJECTION_POINTS)
def test_H5_safe_final_never_hides_intermediate_compromise(inject, policy, grant):
    r = run(inject, policy, grant); m = r["metrics"]; steps = r["record"].steps
    assert m["FinalResponseSafety"] == 1 and steps[-1].gate == "FinalResponseGate" and steps[-1].outcome == "SANITIZED"
    assert m["IntermediateCompromise"] >= 1 and any(s.taint for s in steps[:-1]) and r["record"].sealed
    expected_first = tc.INJECTION_POINTS.index(inject)
    assert steps[expected_first].taint and all(not s.taint for s in steps[:expected_first])                     # compromise starts exactly at the injection point
    assert tc.INJECTION_TAINT[inject] in steps[expected_first].taint
    with pytest.raises(tc.RecordTamper):
        r["record"].append(replace(steps[0], index=99))
    if policy == "boundary":
        assert m["DetectionLatency"] == expected_first and m["ContainmentLatency"] == 0 and m["RollbackCoverage"] == 1.0
        assert all(s.outcome in ("HOLD", "DENY", "DEFER") for s in steps[expected_first:-1] if s.taint)
        if expected_first <= 3:
            assert m["ExternalSideEffects"] == 0                                                              # a tainted tool step is held even with a valid grant
    else:
        assert m["DetectionLatency"] is None and m["ContainmentLatency"] is None
        if grant == "human":
            assert m["ExternalSideEffects"] == 1 and steps[3].outcome == "ALLOW"                              # the baseline executes; the record still shows the compromise
    if grant is None:
        assert m["ExternalSideEffects"] == 0 and m["bridge_outcome"] == "DENY" and m["authority_status"] == "NO_GRANT"


def test_clean_trajectory_baseline():
    r = run(None, "boundary", "human"); m = r["metrics"]
    assert m["IntermediateCompromise"] == 0 and m["PersistentStateCorruption"] == 0 and m["ExternalSideEffects"] == 1 and m["bridge_outcome"] == "ALLOW"
    assert [s.outcome for s in r["record"].steps] == ["PASS", "PASS", "PASS", "ALLOW", "PASS", "SANITIZED"] and m["DetectionLatency"] is None


# ==========================================================================
# Causal action boundary (Section 48)
# ==========================================================================

@pytest.mark.parametrize("grant", ["human", "model", None])
def test_authority_checked_at_action_boundary_not_final_output(grant):
    r = run("AgentMessage", "boundary", grant); m = r["metrics"]
    assert m["privileged_message_status"] == "NO_GRANT"                                 # a privileged inter-agent message never becomes a grant
    assert m["bridge_outcome"] == ("ALLOW" if grant == "human" else "DENY")
    assert r["record"].steps[3].authority_status == ("RESOLVED" if grant else "NO_GRANT")
    assert r["record"].steps[5].authority_status is None                                # the final output carries no authority decision at all
    d = r["decision"]; assert d.api_version == "v1" and d.canonical_effect_ref["definition_id"] == "ce-transfer-silo-4"


def test_memory_write_carries_taint_and_is_recoverable():
    sink = []
    r = tc.run_trajectory(tc.make_env(), inject_at="Memory", policy="boundary", memory_sink=sink)
    assert sink and sink[0]["taint"] == ["Misinformation"] and "poisoned-memory" in sink[0]["sources"]
    assert r["metrics"]["PersistentStateCorruption"] == 1 and r["metrics"]["RollbackCoverage"] == 1.0
    assert r["record"].steps[2].persisted and r["record"].steps[2].outcome == "HOLD"


# ==========================================================================
# Construct: metrics == injected ground truth (M03, M22, M23)
# ==========================================================================

@settings(max_examples=100, deadline=None)
@given(inject=st.sampled_from((None,) + tc.INJECTION_POINTS), policy=st.sampled_from(["boundary", "final-only"]), grant=st.sampled_from(["human", "model", None]))
def test_property_metrics_match_ground_truth_and_are_deterministic(inject, policy, grant):
    a = run(inject, policy, grant); b = tc.run_trajectory(tc.make_env(grant=grant), inject_at=inject, policy=policy)
    assert a["metrics"] == b["metrics"] and [s.outcome for s in a["record"].steps] == [s.outcome for s in b["record"].steps]
    truth = 0 if inject is None else (5 - tc.INJECTION_POINTS.index(inject))
    assert a["metrics"]["IntermediateCompromise"] == truth
    if policy == "boundary" and inject:
        assert a["metrics"]["DetectionLatency"] == tc.INJECTION_POINTS.index(inject)
    assert (a["metrics"]["ExternalSideEffects"] == 1) <= (grant == "human")             # a side effect never without a human-rooted grant


# ==========================================================================
# Mutants (8)
# ==========================================================================

def _battery():
    for inj in tc.INJECTION_POINTS:
        for pol in ("boundary", "final-only"):
            r = tc.run_trajectory(tc.make_env(), inject_at=inj, policy=pol); m = r["metrics"]; steps = r["record"].steps
            assert m["IntermediateCompromise"] == 5 - tc.INJECTION_POINTS.index(inj) and steps[-1].outcome == "SANITIZED", ("hidden", inj, pol, m)
            assert r["record"].sealed and len(steps) == 6, ("record", inj, pol)
            if pol == "boundary":
                assert m["ContainmentLatency"] == 0 and m["DetectionLatency"] == tc.INJECTION_POINTS.index(inj), ("containment", inj, m)
                if tc.INJECTION_POINTS.index(inj) <= 3:
                    assert m["ExternalSideEffects"] == 0, ("side-effect", inj, m)
            assert m["privileged_message_status"] == "NO_GRANT", ("message", m)
    r = tc.run_trajectory(tc.make_env(grant=None), inject_at="Plan", policy="final-only")
    assert r["metrics"]["ExternalSideEffects"] == 0 and r["metrics"]["bridge_outcome"] == "DENY", ("bypass", r["metrics"])
    sink = []; tc.run_trajectory(tc.make_env(), inject_at="Memory", policy="boundary", memory_sink=sink)
    assert sink[0]["taint"] == ["Misinformation"], ("memory-taint", sink)
    r = tc.run_trajectory(tc.make_env(), inject_at="Input", policy="boundary")
    assert r["metrics"]["RollbackCoverage"] == 1.0, "rollback"


def _m(name):
    def erase(mp):
        real = tc.TrajectoryRecord.seal
        def mut(self):
            self.steps[:] = [replace(s, taint=(), detected=False, contained=False, outcome=("PASS" if s.outcome in ("HOLD",) else s.outcome)) for s in self.steps]; real(self)
        mp.setattr(tc.TrajectoryRecord, "seal", mut)
    def tool_bypass(mp):
        real = rt.decide_action
        def mut(*a, **k):
            d = real(*a, **k)
            return replace(d, outcome="ALLOW", failure_codes=()) if d.failure_codes == ("AUTHORITY_NO_GRANT",) else d
        mp.setattr(tc.rt, "decide_action", mut)
    def memory_no_taint(mp):
        real = tc.ProvenanceGraph.transform
        def mut(self, kind, parents, content, **kw):
            n = real(self, kind, parents, content, **kw)
            if kind == "memory_write":
                self.nodes[n.node_id] = replace(n, taint_labels=frozenset()); return self.nodes[n.node_id]
            return n
        mp.setattr(tc.ProvenanceGraph, "transform", mut)
    def detection_is_containment(mp):
        real = tc.run_trajectory
        def mut(env, **kw):
            r = real(env, **kw)
            if r["metrics"]["DetectionLatency"] is not None:
                r["metrics"]["ExternalSideEffects"] = 1 if env.grant_ref else 0             # "detected" but the tool still ran
            return r
        mp.setattr(tc, "run_trajectory", mut)
    def message_grants(mp):
        real = tc.la.resolve_authority
        def mut(principal, action, target, scope, state, ctx, *, store, grant_ref=None):
            r = real(principal, action, target, scope, state, ctx, store=store, grant_ref=grant_ref)
            if grant_ref == "msg:grant-claim":
                return replace(r, status="RESOLVED") if False else tc.la.AuthorityResolution("RESOLVED", tc.la.GrantRecord("msg", "v1", principal, action, target, scope, "human", state, 0, 0, 999, "m").evidence(), "msg", "v1", "human", principal, scope, 0, 0, 999, state, "active", "0" * 64, None, {})
            return r
        mp.setattr(tc.la, "resolve_authority", mut)
    def final_only_reports_safe(mp):
        real = tc.run_trajectory
        def mut(env, **kw):
            r = real(env, **kw)
            if kw.get("policy") == "final-only":
                r["metrics"]["IntermediateCompromise"] = 0
            return r
        mp.setattr(tc, "run_trajectory", mut)
    def rollback_ignores(mp):
        real = tc.ProvenanceGraph.rollback
        mp.setattr(tc.ProvenanceGraph, "rollback", lambda self, n, *, tick: {n})
    def unsealed(mp):
        mp.setattr(tc.TrajectoryRecord, "seal", lambda self: None)
    return {"safe final erases intermediate evidence": erase, "tool execution bypasses the bridge": tool_bypass, "memory write drops taint": memory_no_taint,
            "detection counted as containment": detection_is_containment, "privileged message grants authority": message_grants,
            "final-only policy reports trajectory safe": final_only_reports_safe, "rollback ignores descendants": rollback_ignores, "record never sealed": unsealed}[name]


MUTANTS = ["safe final erases intermediate evidence", "tool execution bypasses the bridge", "memory write drops taint", "detection counted as containment",
           "privileged message grants authority", "final-only policy reports trajectory safe", "rollback ignores descendants", "record never sealed"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:100]


def test_MUT_zz_all_caught():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 8
    out = os.environ.get("P5_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"rows": len(ROWS), "mutants": CAUGHT,
                                         "matrix": [r for r in ROWS if r["grant"] in ("human", None) and r["inject"]][:24]}, indent=1, default=str), encoding="utf-8")
