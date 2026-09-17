"""LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 — Phase 2: CONSTRUCT-VALIDITY-GATE-R1.

    ReliableMetric != ValidMetric (RI-P4) · SelfReport != SelfGeneratedState (RI-P8) · Decodable != CausallyUsed (RI-P15)
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_research.measurement as ms
from logos_research.measurement import construct as cs

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / "docs/research/LOGOS-METRIC-CONSTRUCT-REGISTRY.json").read_text(encoding="utf-8"))
SEED = ["TaskSuccess", "FinalResponseSafety", "TrajectorySafety", "SelfReportedConfidence", "EmpiricalErrorFrequency", "LocalConfidence", "TrajectoryConfidence",
        "MemoryRetrievalAccuracy", "MemoryFidelity", "SourceAttributionAccuracy", "TaintSurvival", "AuthorityEscalation", "RollbackCoverage", "WorldStateAgreement",
        "BeliefStateDecodability", "CausalSteeringEffect"]
CAUGHT: dict[str, str] = {}


# ==========================================================================
# Registry
# ==========================================================================

def test_registry_complete_and_rendered():
    reg = ms.load_registry()
    names = {m.metric_name for m in reg.values()}
    assert set(SEED) <= names and len(reg) >= 16
    for m in reg.values():
        assert m.status in ms.GATE_STATUSES and all(getattr(m, f) for f in cs.REGISTRY_FIELDS if f != "known_confounders"), m.metric_id
    assert REG["gate_statuses"] == list(ms.GATE_STATUSES)
    r = subprocess.run([sys.executable, str(ROOT / "scripts/render_research_radar.py"), "--check"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout


def test_evidence_rule_only_construct_supported_or_stronger():
    reg = ms.load_registry()
    by_name = {m.metric_name: m for m in reg.values()}
    for name in ("SelfReportedConfidence", "FinalResponseSafety", "BeliefStateDecodability", "MemoryRetrievalAccuracy", "LocalConfidence", "CausalSteeringEffect"):
        m = by_name[name]
        assert not ms.allowed_as_evidence(m)
        with pytest.raises(cs.ConstructClaimError):
            ms.evidence_claim(m, "construct")
        with pytest.raises(cs.ConstructClaimError):
            ms.evidence_claim(m, "causal")
    for name in ("TaintSurvival", "TrajectorySafety", "AuthorityEscalation", "RollbackCoverage"):
        m = by_name[name]
        assert ms.allowed_as_evidence(m) and "fixture" in m.scope and "deterministic" in m.scope
        assert "evidence for" in ms.evidence_claim(m, "construct")
    with pytest.raises(cs.ConstructClaimError):
        ms.evidence_claim(by_name["TransformationDepth"], "causal")                  # CONSTRUCT_SUPPORTED does not license a causal claim
    assert "ranks" in ms.evidence_claim(by_name["GraphCentrality"], "ranking")
    with pytest.raises(cs.ConstructClaimError):
        ms.evidence_claim(by_name["SelfReportedConfidence"], "ranking")            # UNVALIDATED licenses nothing


def test_forbidden_claims_encode_the_radar_separations():
    by_name = {m.metric_name: m for m in ms.load_registry().values()}
    assert "trajectory safety" in by_name["FinalResponseSafety"].forbidden_claim.lower()
    assert "fidelity" in by_name["MemoryRetrievalAccuracy"].forbidden_claim.lower()
    assert "causal use" in by_name["BeliefStateDecodability"].forbidden_claim.lower()
    assert "correctness" in by_name["SelfReportedConfidence"].forbidden_claim.lower()
    assert "truth" in by_name["GraphCentrality"].forbidden_claim.lower()
    assert "command as execution" in by_name["WorldStateAgreement"].forbidden_claim.lower()


# ==========================================================================
# Synthetic construct tests (Section 22)
# ==========================================================================

def _fixture(kind: str, n_items=40, repeats=5, seed=0):
    """Returns (repeated_scores, metric_means, ground_truth)."""
    rng = random.Random(seed)
    truth = [rng.random() for _ in range(n_items)]
    if kind == "reliable-invalid":                 # perfectly repeatable, unrelated to the construct
        base = [rng.random() for _ in range(n_items)]
        rep = [[b] * repeats for b in base]
    elif kind == "reliable-valid":
        rep = [[t] * repeats for t in truth]
    elif kind == "unreliable-valid-mean":          # noisy but centred on truth
        rep = [[t + rng.gauss(0, 0.4) for _ in range(repeats)] for t in truth]
    else:                                          # unreliable-invalid
        rep = [[rng.random() for _ in range(repeats)] for _ in range(n_items)]
    means = [sum(r) / len(r) for r in rep]
    return rep, means, truth


def test_reliability_high_validity_low_is_RELIABLE_ONLY():
    rep, means, truth = _fixture("reliable-invalid")
    r, v = cs.reliability(rep), cs.construct_validity(means, truth)
    assert r >= 0.99 and v < 0.4
    assert cs.gate_status(r, v, None) == "RELIABLE_ONLY"


def test_inverse_control_reliable_and_valid_is_CONSTRUCT_SUPPORTED_and_causal_needs_intervention():
    rep, means, truth = _fixture("reliable-valid")
    r, v = cs.reliability(rep), cs.construct_validity(means, truth)
    assert r >= 0.99 and v >= 0.99
    assert cs.gate_status(r, v, None) == "CONSTRUCT_SUPPORTED"
    assert cs.gate_status(r, v, cs.causal_discrimination(means, [m + 0.5 for m in means], True)) == "CAUSALLY_DISCRIMINATED"
    assert cs.gate_status(r, v, cs.causal_discrimination(means, [m + 0.5 for m in means], False)) == "CONSTRUCT_SUPPORTED"   # moved without a construct change: no causal credit


def test_unreliable_metrics_never_reach_construct_support():
    rep, means, truth = _fixture("unreliable-invalid")
    assert cs.gate_status(cs.reliability(rep), cs.construct_validity(means, truth), None) in ("UNVALIDATED", "REJECTED")
    rep, means, truth = _fixture("unreliable-valid-mean")
    assert cs.gate_status(cs.reliability(rep), cs.construct_validity(means, truth), None) in ("UNVALIDATED", "REJECTED")


@settings(max_examples=100, deadline=None)
@given(seed=st.integers(0, 10_000), kind=st.sampled_from(["reliable-invalid", "reliable-valid", "unreliable-invalid"]))
def test_property_gate_is_monotone_and_never_promotes_reliability_alone(seed, kind):
    rep, means, truth = _fixture(kind, seed=seed)
    r, v = cs.reliability(rep), cs.construct_validity(means, truth)
    s = cs.gate_status(r, v, None)
    if kind == "reliable-invalid":
        assert s == "RELIABLE_ONLY" and s not in ms.construct.EVIDENCE_OK
    if kind == "reliable-valid":
        assert s == "CONSTRUCT_SUPPORTED"
    if kind == "unreliable-invalid":
        assert s in ("UNVALIDATED", "REJECTED")
    assert cs.gate_status(r, None, None) in ("RELIABLE_ONLY", "UNVALIDATED")           # no validity measured -> never supported


# ==========================================================================
# Construct mutants (Section 23)
# ==========================================================================

def _battery():
    by = {m.metric_name: m for m in ms.load_registry().values()}
    rep, means, truth = _fixture("reliable-invalid")
    assert cs.gate_status(cs.reliability(rep), cs.construct_validity(means, truth), None) == "RELIABLE_ONLY", "reliable->valid"
    for name in ("SelfReportedConfidence", "FinalResponseSafety", "MemoryRetrievalAccuracy", "BeliefStateDecodability", "LocalConfidence"):
        assert not ms.allowed_as_evidence(by[name]), name
        try:
            ms.evidence_claim(by[name], "construct"); raise AssertionError(f"{name} licensed a construct claim")
        except cs.ConstructClaimError:
            pass
    rv, mv, tv = _fixture("reliable-valid")
    assert not cs.causal_discrimination(mv, [m + 0.5 for m in mv], False), "moved-without-construct-change credited"
    assert cs.gate_status(cs.reliability(rv), cs.construct_validity(mv, tv), None) != "CAUSALLY_DISCRIMINATED", "validity->causal"
    assert cs.gate_status(0.99, None, True) == "RELIABLE_ONLY", "ranking->construct"
    # world-model prediction / observation: WorldStateAgreement proxy is the OBSERVED world; the registry must not accept predictions
    assert "observed" in by["WorldStateAgreement"].ground_truth_proxy.lower(), "prediction->observation"
    assert "correctness" in by["SelfReportedConfidence"].forbidden_claim.lower(), "confidence->correctness"


def _m(name):
    def reliable_valid(mp):
        real = cs.gate_status
        mp.setattr(cs, "gate_status", lambda r, v, c, **k: "CONSTRUCT_SUPPORTED" if r >= 0.8 else real(r, v, c, **k))
    def self_report(mp):
        mp.setattr(ms, "allowed_as_evidence", lambda m: True); mp.setattr(cs, "allowed_as_evidence", lambda m: True)
        mp.setattr(ms, "evidence_claim", lambda m, k: "licensed"); mp.setattr(cs, "evidence_claim", lambda m, k: "licensed")
    def final_to_trajectory(mp):
        real = ms.load_registry
        def mut(path=None):
            d = real(path); return {k: (m if m.metric_name != "FinalResponseSafety" else cs.MetricRecord(**{**m.__dict__, "status": "CONSTRUCT_SUPPORTED"})) for k, m in d.items()}
        mp.setattr(ms, "load_registry", mut)
    def retrieval_to_fidelity(mp):
        real = ms.load_registry
        def mut(path=None):
            d = real(path); return {k: (m if m.metric_name != "MemoryRetrievalAccuracy" else cs.MetricRecord(**{**m.__dict__, "status": "CONSTRUCT_SUPPORTED", "claimed_construct": "memory fidelity"})) for k, m in d.items()}
        mp.setattr(ms, "load_registry", mut)
    def decodable_causal(mp):
        real = ms.load_registry
        def mut(path=None):
            d = real(path); return {k: (m if m.metric_name != "BeliefStateDecodability" else cs.MetricRecord(**{**m.__dict__, "status": "CAUSALLY_DISCRIMINATED"})) for k, m in d.items()}
        mp.setattr(ms, "load_registry", mut)
    def prediction_observation(mp):
        real = ms.load_registry
        def mut(path=None):
            d = real(path); return {k: (m if m.metric_name != "WorldStateAgreement" else cs.MetricRecord(**{**m.__dict__, "ground_truth_proxy": "world-model prediction"})) for k, m in d.items()}
        mp.setattr(ms, "load_registry", mut)
    def confidence_correctness(mp):
        real = ms.load_registry
        def mut(path=None):
            d = real(path); return {k: (m if m.metric_name != "SelfReportedConfidence" else cs.MetricRecord(**{**m.__dict__, "status": "CONSTRUCT_SUPPORTED", "forbidden_claim": "none"})) for k, m in d.items()}
        mp.setattr(ms, "load_registry", mut)
    def ranking_construct(mp):
        real = cs.gate_status
        mp.setattr(cs, "gate_status", lambda r, v, c, **k: "CONSTRUCT_SUPPORTED" if v is None and r >= 0.8 else real(r, v, c, **k))
    def causal_from_movement(mp):
        mp.setattr(cs, "causal_discrimination", lambda b, i, changed: abs(sum(i) / len(i) - sum(b) / len(b)) > 0.1)
    return {"reliable metric -> valid metric automatically": reliable_valid, "self-report -> ground truth": self_report, "final safety -> trajectory safety": final_to_trajectory,
            "retrieval accuracy -> memory fidelity": retrieval_to_fidelity, "decodability -> causal use": decodable_causal, "world-model prediction -> observation": prediction_observation,
            "confidence -> correctness": confidence_correctness, "ranking validity -> construct validity": ranking_construct, "movement -> causal discrimination": causal_from_movement}[name]


MUTANTS = ["reliable metric -> valid metric automatically", "self-report -> ground truth", "final safety -> trajectory safety", "retrieval accuracy -> memory fidelity",
           "decodability -> causal use", "world-model prediction -> observation", "confidence -> correctness", "ranking validity -> construct validity", "movement -> causal discrimination"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:100]


def test_MUT_zz_all_caught():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 9
    out = os.environ.get("P2_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"mutants": CAUGHT, "registry_size": len(REG["metrics"])}, indent=1), encoding="utf-8")
