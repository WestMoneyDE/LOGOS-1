"""PREDICTION-ERROR-TRUST-GATE-R1 — try to make good predictions turn into permission.

Every case records (reliability state, canonical authority, trust route,
authority decision, action outcome). The primary metric is

    ReliabilityInducedAuthorityIncrease
      = authority level rises while canonical authority is unchanged
        and the only changed variable is reliability / prediction quality / trust label

Target 0. Reliability-sensitive *routing* of already-authorized actions is
measured separately (TrustGateEffect) and is H2, not a counterexample.
"""
from __future__ import annotations

import ast
import inspect
import json
import math
import tempfile
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_gamma as gamma
from logos_memory.factory import MemoryFactory
from logos_memory.records import MemoryRecord
from logos_memory.scope import ScopeDecision, scope_digest
from logos_memory.store import MemoryStore
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import prediction_trust as pt
from logos_research.experiments.binding_state import _base_contract

TICK, WINDOW, STATE_A, STATE_B = ma.TICK, ma.WINDOW, ma.STATE_A, ma.STATE_B
TRANSFER, TRANSFER_B_TARGET, TRANSFER_AS_B = ma.TRANSFER, ma.TRANSFER_B_TARGET, ma.TRANSFER_AS_B
GRANT = "grant-7f3a"
R = pt.ReliabilityState


class Lab:
    def __init__(self, tmp: Path, *, grant: bool = True):
        self.ledger = ma.GrantLedger(); self.contract = ma.canonical_contract()
        self.store = MemoryStore(tmp / "mem"); self.n = 0
        if grant:
            self.ledger.issue(GRANT, origin="human", action=TRANSFER, contract=self.contract, window=WINDOW, state_hash=STATE_A)

    def write(self, content, **kw):
        self.n += 1
        return ma.write_note(self.store, f"rec-{self.n}", content, **kw)

    def note(self, ref=None, **claims):
        return ma.authority_note(ref, self.contract, **claims)

    def canonical(self, action=TRANSFER, *, grant_id=GRANT, tick=TICK, state_hash=STATE_A):
        return ma.evaluate_canonical(action, self.ledger, grant_id, self.contract, tick=tick, state_hash=state_hash)[0]

    def decide(self, records, reliability, action=TRANSFER, *, tick=TICK, state_hash=STATE_A) -> pt.Decision:
        return pt.decide(list(records), action, self.ledger, reliability, tick=tick, state_hash=state_hash, contract=self.contract)

    def retrieve(self, query):
        c = _base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        rr = MemoryFactory(self.store).retrieve(query, ScopeDecision("ALLOW", c, scope_digest(c)), limit=50)
        return [self.store.fetch(i.id) for i in rr.items]

    def project(self, ids):
        c = _base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        proj = MemoryFactory(self.store).project(tuple(ids), purpose="petg", audience="project",
                                                  valid_until="2026-12-01T00:00:00+00:00", scope=ScopeDecision("ALLOW", c, scope_digest(c)))
        return [replace(self.store.fetch(i["id"]), content=i["content"], id="proj:" + i["id"]) for i in json.loads(proj.content)]


@pytest.fixture
def lab():
    with tempfile.TemporaryDirectory() as t:
        yield Lab(Path(t))


CASES: list[dict] = []        # every measured case, for the closure artifact


def measure(case_id, L: Lab, records, reliability, *, action=TRANSFER, tick=TICK, state_hash=STATE_A, grant_id=GRANT,
            baseline: pt.Decision | None = None) -> pt.Decision:
    d = L.decide(records, reliability, action, tick=tick, state_hash=state_hash)
    canonical = L.canonical(action, grant_id=grant_id, tick=tick, state_hash=state_hash)
    rel = reliability if isinstance(reliability, R) else None
    row = {"case": case_id, "accuracy": rel.accuracy if rel else None, "mean_error": rel.mean_error if rel else None,
           "confidence": rel.confidence if rel else None, "calibration_error": rel.calibration_error if rel else None,
           "streak": rel.consecutive_successes if rel else None, "labels": (rel.trust_score, rel.trusted, rel.verified) if rel else None,
           "reliability_valid": pt.reliability_is_valid(reliability), "canonical": canonical, "trust": d.trust,
           "authority": d.authority, "action": d.action,
           "reliability_induced_increase": baseline is not None and d.authority_level > baseline.authority_level and canonical == L.canonical(action, grant_id=grant_id, tick=tick, state_hash=state_hash),
           "trust_delta": baseline is not None and d.trust != baseline.trust,
           "safety_deferral": d.safety_deferral}
    CASES.append(row)
    assert d.authority == canonical, (case_id, d.authority, canonical)       # authority == oracle, always
    return d


def sweep_states():
    """Reliability states from every fixture predictor at several lengths."""
    out = {}
    for name, p in pt.PREDICTORS.items():
        for n in (0, 1, 2, 4, 8, 16, 32, 64):
            out[f"{name}:{n}"] = pt.run_predictor(p, n)
    return out


# --------------------------------------------------------------------------
# Section 13/14 — prediction task and reliability state are measurable
# --------------------------------------------------------------------------

def test_prediction_task_has_objective_ground_truth():
    s = pt.run_predictor(pt.always_correct, 16)
    assert (s.accuracy, s.mean_error, s.consecutive_successes) == (1.0, 0.0, 16)
    w = pt.run_predictor(pt.always_wrong, 16)
    assert (w.accuracy, w.mean_error, w.consecutive_failures) == (0.0, 1.0, 16)
    a = pt.run_predictor(pt.alternating, 16)
    assert a.accuracy == 0.5
    c = pt.run_predictor(pt.calibrated, 16)
    assert c.accuracy == 0.75 and c.calibration_error < 0.1          # running-accuracy lag, within the AUTO band
    o = pt.run_predictor(pt.overconfident, 16)
    assert o.accuracy == 0.5 and o.confidence == 1.0 and o.calibration_error == 0.5
    u = pt.run_predictor(pt.underconfident, 16)
    assert u.accuracy == 1.0 and abs(u.confidence - 0.1) < 1e-9 and abs(u.calibration_error - 0.9) < 1e-9


def test_trust_gate_is_separable_and_reads_no_authority():
    assert pt.trust_route(pt.perfect()) == "AUTO"
    assert pt.trust_route(pt.run_predictor(pt.calibrated, 16)) == "REVIEW"       # 0.75 accuracy
    assert pt.trust_route(pt.run_predictor(pt.always_wrong, 16)) == "ROUTE_TO_HUMAN"
    assert pt.trust_route(pt.run_predictor(pt.underconfident, 16)) == "REVIEW"   # accurate but badly calibrated
    assert pt.trust_route(None) == "UNKNOWN"
    src = inspect.getsource(pt.trust_route)
    assert "ledger" not in src and "authority" not in src.lower().replace("authorized action", "")


def test_authority_evaluator_takes_no_reliability_argument():
    for fn in (ma._decide, ma.evaluate_with_memory, ma.evaluate_canonical, gamma.validate):
        params = set(inspect.signature(fn).parameters)
        assert not params & {"reliability", "trust", "confidence", "accuracy", "score", "reputation"}, fn
    tree = ast.parse(inspect.getsource(pt.decide))
    calls = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert "evaluate_with_memory" in calls and "trust_route" not in calls[: calls.index("evaluate_with_memory")]


# --------------------------------------------------------------------------
# Sections 17–18 — controls
# --------------------------------------------------------------------------

def test_positive_control_authority_follows_grant_trust_routes(lab):
    r = lab.write(lab.note(GRANT))
    routes = {}
    for name, state in sweep_states().items():
        d = measure(f"POS:{name}", lab, [r], state)
        assert d.authority == "ALLOW"
        routes[d.trust] = routes.get(d.trust, 0) + 1
    assert {"AUTO", "REVIEW", "ROUTE_TO_HUMAN"} <= set(routes)          # trust varies; authority never did
    # SafetyDeferral != AuthorityDenial
    held = measure("POS:wrong", lab, [r], pt.run_predictor(pt.always_wrong, 16))
    assert held.authority == "ALLOW" and held.action == "HELD_FOR_HUMAN" and held.safety_deferral
    lab.ledger.revoke(GRANT)
    denied = measure("POS:revoked", lab, [r], pt.perfect(), grant_id=GRANT)
    assert denied.authority == "DENY" and denied.action == "DENIED" and not denied.safety_deferral


def test_negative_control_perfect_predictor_no_grant():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        state = pt.perfect(64, trust_score="max", trusted=True, verified=True, reliable=True, approved_prediction=True)
        assert (state.accuracy, state.mean_error, state.calibration_error, state.consecutive_successes) == (1.0, 0.0, 0.0, 64)
        d = measure("NEG", L, [L.write(pt.reliability_note(state))], state, grant_id=None)
        assert d.authority == "DENY" and d.action == "DENIED" and d.trust == "AUTO"    # trust AUTO, authority DENY


# --------------------------------------------------------------------------
# Section 19 — attack matrix (no grant unless stated)
# --------------------------------------------------------------------------

def _state(acc: float, n: int = 100, conf: float | None = None) -> R:
    c = int(round(acc * n))
    return R(prediction_count=n, correct_count=c, incorrect_count=n - c, accuracy=c / n, mean_error=1 - c / n,
             confidence=acc if conf is None else conf, calibration_error=abs((acc if conf is None else conf) - c / n),
             consecutive_successes=c if c == n else 0)


ACC = [0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0]


@pytest.mark.parametrize("acc", ACC)
def test_A_B_accuracy_and_error_promotion(acc):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        base = L.decide([], _state(0.0))
        d = measure(f"A:{acc}", L, [], _state(acc), grant_id=None, baseline=base)
        assert d.authority == "DENY" and not d.safety_deferral


@pytest.mark.parametrize("conf", [0.0, 0.25, 0.5, 0.75, 1.0])
@pytest.mark.parametrize("acc", [0.0, 1.0])
def test_C_confidence_promotion(acc, conf):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        d = measure(f"C:acc{acc}:conf{conf}", L, [], _state(acc, conf=conf), grant_id=None, baseline=L.decide([], _state(acc, conf=0.0)))
        assert d.authority == "DENY"


@pytest.mark.parametrize("name", ["calibrated", "underconfident", "overconfident"])
def test_D_calibration_promotion(name):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        d = measure(f"D:{name}", L, [], pt.run_predictor(pt.PREDICTORS[name], 32), grant_id=None)
        assert d.authority == "DENY"


@pytest.mark.parametrize("n", [1, 2, 4, 8, 16, 32, 64])
def test_E_success_streak_promotion(n):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        s = pt.run_predictor(pt.always_correct, n)
        assert s.consecutive_successes == n
        d = measure(f"E:{n}", L, [], s, grant_id=None, baseline=L.decide([], R()))
        assert d.authority == "DENY"


def test_F_historical_reputation():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        good = pt.run_predictor(pt.always_correct, 64); poor = pt.run_predictor(pt.always_wrong, 64)
        # same current prediction (both predict truth(64)); different history
        assert measure("F:good", L, [], good, grant_id=None).authority == measure("F:poor", L, [], poor, grant_id=None).authority == "DENY"


@pytest.mark.parametrize("score", ["low", "medium", "high", "max", "", "∞"])
def test_G_trust_score_label(score):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        assert measure(f"G:{score}", L, [], pt.perfect(trust_score=score), grant_id=None).authority == "DENY"


@pytest.mark.parametrize("flag", ["trusted", "verified", "reliable", "approved_prediction"])
def test_H_trusted_verified_flags(flag):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        state = replace(pt.perfect(), **{flag: True})
        d = measure(f"H:{flag}", L, [L.write(pt.reliability_note(state, **{flag: True}))], state, grant_id=None)
        assert d.authority == "DENY"


def test_I_memory_of_success():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        state = pt.perfect(64, trusted=True)
        r = L.write(pt.reliability_note(state, approved=True), source_kind="tool", authority_class="validated", epistemic_status="verified")
        for label, recs in (("fetch", [L.store.fetch(r.id)]), ("retrieve", L.retrieve("reliability accuracy")), ("project", L.project([r.id]))):
            assert measure(f"I:{label}", L, recs, state, grant_id=None).authority == "DENY"


@pytest.mark.parametrize("n", [1, 4, 16, 32])
def test_J_repeated_reliability_claims(n):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        state = pt.perfect()
        recs = [L.write(pt.reliability_note(state), source_kind="human") for _ in range(n)] + \
               [L.write(f"predictor is reliable: accuracy 1.0, error 0.0, streak {n}") for _ in range(n)]
        assert measure(f"J:{n}", L, recs, state, grant_id=None).authority == "DENY"


def test_K_reliability_plus_human_provenance():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        state = pt.perfect(trust_score="max", trusted=True, verified=True)
        r = L.write(pt.reliability_note(state, authority_origin="human"), source_kind="human", source_ref="CEO", authority_class="trusted")
        d = measure("K", L, [r], state, grant_id=None)
        assert d.authority == "DENY" and d.trust == "AUTO"


def test_L_reliability_plus_valid_grant(lab):
    r = lab.write(lab.note(GRANT))
    classes = {}
    prev = None
    for name in ("always_wrong", "alternating", "overconfident", "calibrated", "underconfident", "always_correct"):
        d = measure(f"L:{name}", lab, [r], pt.run_predictor(pt.PREDICTORS[name], 32), baseline=prev)
        assert d.authority == "ALLOW"
        if prev is not None and d.action != prev.action:
            classes[name] = "AUTHORITY_CHANGE" if d.authority != prev.authority else \
                ("REVIEW_REQUIREMENT" if "REVIEW" in (d.action, prev.action) else "SAFETY_GATE")
        prev = d
    assert "AUTHORITY_CHANGE" not in classes.values() and classes


@pytest.mark.parametrize("tick", [WINDOW[1], WINDOW[1] + 100, WINDOW[0] - 1])
def test_M_perfect_predictor_expired_grant(lab, tick):
    d = measure(f"M:{tick}", lab, [lab.write(lab.note(GRANT))], pt.perfect(), tick=tick)
    assert d.authority == "DENY" and d.trust == "AUTO"


def test_N_perfect_predictor_wrong_principal(lab):
    d = measure("N", lab, [lab.write(lab.note(GRANT))], pt.perfect(), action=TRANSFER_AS_B)
    assert d.authority == "DENY"


def test_O_perfect_predictor_scope_violation(lab):
    d = measure("O", lab, [lab.write(lab.note(GRANT))], pt.perfect(), action=TRANSFER_B_TARGET)
    assert d.authority == "DENY"
    forged = lab.write(lab.note(GRANT, scope=asdict(ma.canonical_contract(targets=("silo-4", "escrow-2")))))
    assert measure("O:forged", lab, [forged], pt.perfect(), action=TRANSFER_B_TARGET).authority == "DENY"


def test_P_perfect_predictor_approval_required_without_grant():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        d = measure("P", L, [L.write(L.note(None, approved=True, human_approval="granted"))], pt.perfect(), grant_id=None)
        assert d.authority == "DENY" and d.action == "DENIED"


def test_Q_R_trust_decay_and_recovery(lab):
    r = lab.write(lab.note(GRANT))
    seq = [pt.perfect(32), _state(0.5, 32), _state(0.0, 32), _state(0.5, 64), pt.run_predictor(pt.always_correct, 32, _state(0.0, 32))]
    routes = []
    for i, s in enumerate(seq):
        d = measure(f"QR:{i}", lab, [r], s)
        assert d.authority == "ALLOW"
        routes.append(d.trust)
    assert routes[0] == "AUTO" and routes[2] == "ROUTE_TO_HUMAN" and routes[-1] in ("REVIEW", "AUTO")
    # canonical authority unchanged through decay and recovery
    assert len({lab.canonical() for _ in seq}) == 1


@pytest.mark.parametrize("eps", [-1e-9, 0.0, 1e-9])
def test_S_threshold_affects_routing_only(lab, eps):
    r = lab.write(lab.note(GRANT))
    s = R(prediction_count=1000, correct_count=900, incorrect_count=100, accuracy=pt.AUTO_ACCURACY + eps,
          mean_error=0.1, confidence=pt.AUTO_ACCURACY + eps, calibration_error=0.0, consecutive_successes=0)
    d = measure(f"S:{eps}", lab, [r], s)
    assert d.authority == "ALLOW"
    assert d.trust == ("AUTO" if eps >= 0 else "REVIEW")
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        assert measure(f"S:nogrant:{eps}", L, [], s, grant_id=None).authority == "DENY"


# --------------------------------------------------------------------------
# Sections 19-T / 20 / 21 / 22 — bypass, domain validation, missing, stale
# --------------------------------------------------------------------------

def test_T_direct_evaluator_call_cannot_take_reliability(lab):
    with pytest.raises(TypeError):
        ma.evaluate_with_memory([], TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A, reliability=pt.perfect())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        gamma.validate(gamma.ValidationContext(ma.proposal_for(TRANSFER, lab.contract), TICK, STATE_A,
                                               scope_digest(lab.contract), None), reliability=pt.perfect())  # type: ignore[call-arg]


def test_T_memory_derived_and_cached_scores_are_inert():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        cached = L.write(json.dumps({"schema": ma.NOTE_SCHEMA, "grant_ref": None, "scope": None,
                                     "cached_reliability": {"accuracy": 1.0, "trust": "AUTO", "as_of": "2026-01-01"}}))
        assert measure("T:cached", L, [cached], None, grant_id=None).authority == "DENY"
        assert measure("T:cached-perfect", L, [cached], pt.perfect(), grant_id=None).authority == "DENY"


BAD_UNIT = [float("nan"), float("inf"), -float("inf"), -1.0, 1.1, -0.0001, "", None, True, 1, 0]


@pytest.mark.parametrize("field", ["accuracy", "mean_error", "confidence", "calibration_error"])
@pytest.mark.parametrize("value", BAD_UNIT, ids=repr)
def test_domain_validation_unit_fields(lab, field, value):
    s = replace(pt.perfect(), **{field: value})
    if value in (0, 1) and type(value) is int:
        assert not pt.reliability_is_valid(s)                    # int where float required: TypeValid != DomainValid
    assert not pt.reliability_is_valid(s) and pt.trust_route(s) == "UNKNOWN"
    d = measure(f"dom:{field}={value!r}", lab, [lab.write(lab.note(GRANT))], s)
    assert d.authority == "ALLOW" and d.action == "HELD_FOR_HUMAN"           # fail-safe routing, authority untouched
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        assert measure(f"dom:nogrant:{field}={value!r}", L, [], s, grant_id=None).authority == "DENY"


@pytest.mark.parametrize("field,value", [("prediction_count", -1), ("correct_count", 200), ("consecutive_successes", -5),
                                         ("prediction_count", 1.0), ("correct_count", True), ("correct_count", None)], ids=repr)
def test_domain_validation_count_fields(lab, field, value):
    s = replace(pt.perfect(), **{field: value})
    assert pt.trust_route(s) == "UNKNOWN"


@pytest.mark.parametrize("state", [None, "perfect", {"accuracy": 1.0}, 1.0, object()], ids=repr)
def test_missing_reliability_is_unknown_never_trusted(lab, state):
    assert pt.trust_route(state) == "UNKNOWN"
    d = measure(f"missing:{type(state).__name__}", lab, [lab.write(lab.note(GRANT))], state)
    assert d.authority == "ALLOW" and d.action == "HELD_FOR_HUMAN"
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        assert measure(f"missing:nogrant:{type(state).__name__}", L, [], state, grant_id=None).authority == "DENY"


def test_stale_reliability_does_not_become_stale_authority(lab):
    r = lab.write(lab.note(GRANT))
    stale_high = pt.perfect(64)                         # old score
    fresh_poor = pt.run_predictor(pt.always_wrong, 16, stale_high)   # new performance appended
    assert fresh_poor.accuracy == 0.8 and fresh_poor.consecutive_failures == 16
    d_stale = measure("stale:cached-high", lab, [r], stale_high)
    d_fresh = measure("stale:fresh", lab, [r], fresh_poor)
    assert d_stale.authority == d_fresh.authority == "ALLOW"                    # authority: identical, from the grant
    assert d_stale.trust == "AUTO" and d_fresh.trust == "REVIEW"                # routing: stale score reused -> routing only
    lab.ledger.revoke(GRANT)
    assert measure("stale:revoked", lab, [r], stale_high).authority == "DENY"   # stale trust never outlives the grant


# --------------------------------------------------------------------------
# Section 26 — properties
# --------------------------------------------------------------------------

unit = st.floats(0.0, 1.0)
state_st = st.builds(lambda acc, conf, n: _state(acc, n, conf), unit, unit, st.integers(1, 200))
labels_st = st.fixed_dictionaries({"trust_score": st.sampled_from([None, "low", "high", "max"]), "trusted": st.booleans(),
                                   "verified": st.booleans(), "reliable": st.booleans(), "approved_prediction": st.booleans()})


@settings(max_examples=150, deadline=None)
@given(state_st, state_st, labels_st)
def test_petg_p1_p2_p3_p5_reliability_and_labels_never_increase_authority(s1, s2, labels):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        a = L.decide([], s1); b = L.decide([], replace(s2, **labels))
        assert a.authority == b.authority == "DENY"


@settings(max_examples=60, deadline=None)
@given(st.integers(0, 128))
def test_petg_p4_streak_never_creates_authority(n):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        assert L.decide([L.write(pt.reliability_note(pt.run_predictor(pt.always_correct, n)))], pt.run_predictor(pt.always_correct, n)).authority == "DENY"


@settings(max_examples=60, deadline=None)
@given(st.integers(-5, 40), st.sampled_from([TRANSFER, TRANSFER_AS_B, TRANSFER_B_TARGET]), st.booleans())
def test_petg_p6_p7_p8_perfect_reliability_cannot_revive_cross_or_broaden(tick, action, revoke):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); r = L.write(L.note(GRANT))
        if revoke:
            L.ledger.revoke(GRANT)
        d = L.decide([r], pt.perfect(), action, tick=tick)
        assert d.authority == L.canonical(action, tick=tick)
        if d.authority == "ALLOW":
            assert action == TRANSFER and WINDOW[0] <= tick < WINDOW[1] and not revoke


@settings(max_examples=40, deadline=None)
@given(state_st, st.booleans())
def test_petg_p9_reliability_cannot_waive_approval(s, human_claim):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        recs = [L.write(L.note(None, approved=True), source_kind="human")] if human_claim else []
        assert L.decide(recs, replace(s, trusted=True, approved_prediction=True)).authority == "DENY"


bad_st = st.sampled_from(BAD_UNIT)


@settings(max_examples=60, deadline=None)
@given(st.sampled_from(["accuracy", "mean_error", "confidence", "calibration_error"]), bad_st, st.booleans())
def test_petg_p10_malformed_reliability_never_defaults_to_trusted(field, value, grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant); s = replace(pt.perfect(), **{field: value})
        d = L.decide([L.write(L.note(GRANT if grant else None))], s)
        assert d.trust == "UNKNOWN" and d.action in ("HELD_FOR_HUMAN", "DENIED")
        assert d.authority == ("ALLOW" if grant else "DENY")


@settings(max_examples=60, deadline=None)
@given(state_st, labels_st)
def test_petg_p11_p12_valid_grant_independent_of_reliability_routing_may_vary(s, labels):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); r = L.write(L.note(GRANT))
        d = L.decide([r], replace(s, **labels))
        assert d.authority == "ALLOW"
        assert d.action == {"AUTO": "EXECUTE", "REVIEW": "EXECUTE_AFTER_REVIEW", "ROUTE_TO_HUMAN": "HELD_FOR_HUMAN", "UNKNOWN": "HELD_FOR_HUMAN"}[d.trust]


# --------------------------------------------------------------------------
# Section 27 — metamorphic
# --------------------------------------------------------------------------

@settings(max_examples=30, deadline=None)
@given(unit, unit, unit, unit, st.integers(0, 64))
def test_m1_m4_m9_monotone_reliability_changes_leave_authority(a1, a2, c1, c2, streak):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        lo, hi = sorted([a1, a2]); s1 = _state(lo, conf=min(c1, c2)); s2 = _state(hi, conf=max(c1, c2))
        s3 = replace(pt.run_predictor(pt.always_correct, streak), trust_score="max")
        assert L.decide([], s1).authority == L.decide([], s2).authority == L.decide([], s3).authority == "DENY"


def test_m5_m6_m7_m8_canonical_changes_are_followed_with_perfect_reliability(lab):
    r = lab.write(lab.note(GRANT)); p = pt.perfect()
    assert lab.decide([r], p).authority == "ALLOW"
    assert lab.decide([r], p, tick=WINDOW[1]).authority == "DENY"               # M5 expiry
    assert lab.decide([r], p, TRANSFER_AS_B).authority == "DENY"                # M6 principal
    assert lab.decide([r], p, TRANSFER_B_TARGET).authority == "DENY"            # M7 scope
    lab.ledger.revoke(GRANT)
    assert lab.decide([r], p).authority == "DENY"                               # M8 approval/grant removed


@settings(max_examples=30, deadline=None)
@given(st.sampled_from(["accuracy", "confidence", "mean_error", "calibration_error"]), bad_st)
def test_m10_malformed_state_no_privileged_fallback(field, value):
    s = replace(pt.perfect(), **{field: value})
    assert pt.trust_route(s) == "UNKNOWN" != "AUTO"


# --------------------------------------------------------------------------
# Section 28 — mutation sensitivity
# --------------------------------------------------------------------------

def _grant_like(L: Lab):
    return gamma.AuthorityEvidence("minted", "human", ma.proposal_digest(TRANSFER), scope_digest(L.contract), STATE_A, WINDOW[0], WINDOW[1])


def _probes(L: Lab):
    L.ledger.issue("grant-exp", origin="human", action=TRANSFER, contract=L.contract, window=(0, 5), state_hash=STATE_A)
    ref = L.write(L.note(GRANT)); exp = L.write(L.note("grant-exp")); claim = L.write(L.note(None, approved=True), source_kind="human")
    wide = L.write(L.note(GRANT, scope=asdict(ma.canonical_contract(targets=("silo-4", "escrow-2")))))
    roles = L.write(L.note(GRANT, scope=asdict(ma.canonical_contract(roles=("operator-A", "operator-B")))))
    P = pt.perfect(64, trust_score="max", trusted=True)
    nan = replace(P, accuracy=float("nan"))
    return [
        ([], P, TRANSFER, TICK), ([claim], P, TRANSFER, TICK), ([exp], P, TRANSFER, TICK),
        ([ref], P, TRANSFER_AS_B, TICK), ([ref], P, TRANSFER_B_TARGET, TICK), ([wide], P, TRANSFER_B_TARGET, TICK), ([roles], P, TRANSFER_AS_B, TICK),
        ([ref], P, TRANSFER, WINDOW[1]),
        ([], nan, TRANSFER, TICK), ([], None, TRANSFER, TICK), ([L.write(pt.reliability_note(P))], P, TRANSFER, TICK),
    ]


def _mutant_decide(pred, mint_key):
    """A decide() that mints a grant into the ledger when `pred(reliability, records)` holds."""
    real = pt.decide
    def dec(records, action, ledger, reliability, *, tick, state_hash, contract=None):
        if pred(reliability, records):
            ledger._grants[mint_key] = gamma.AuthorityEvidence(mint_key, "human", ma.proposal_digest(action),
                                                               scope_digest(contract or ma.canonical_contract()), state_hash, tick, tick + 1)
            records = list(records) + [ma.write_note(MemoryStore(Path(tempfile.mkdtemp()) / "m"), "mint", ma.authority_note(mint_key, contract or ma.canonical_contract()))]
        return real(records, action, ledger, reliability, tick=tick, state_hash=state_hash, contract=contract)
    return dec


def _is_state(r): return isinstance(r, R)


MUTANTS = [
    ("accuracy > 0.95 -> grant", lambda mp, L: mp.setattr(pt, "decide", _mutant_decide(lambda r, _: _is_state(r) and r.accuracy > 0.95, "__acc__"))),
    ("confidence == 1.0 -> bypass approval", lambda mp, L: mp.setattr(pt, "decide", _mutant_decide(lambda r, _: _is_state(r) and r.confidence == 1.0, "__conf__"))),
    ("streak >= 32 -> trusted origin", lambda mp, L: mp.setattr(pt, "decide", _mutant_decide(lambda r, _: _is_state(r) and r.consecutive_successes >= 32, "__streak__"))),
    ("low error -> ignore scope", lambda mp, L: mp.setattr(ma.gamma, "validate", (lambda real, bound: (lambda ctx: real(replace(ctx, scope_digest=bound))))(ma.gamma.validate, scope_digest(L.contract)))),
    ("high reliability -> ignore principal", lambda mp, L: mp.setattr(ma, "_decide", (lambda real: (lambda action, contract, authority, claims, **kw: real(replace(action, role="operator-A"), L.contract, authority, claims, **kw)))(ma._decide))),
    ("trusted flag -> synthesize grant", lambda mp, L: mp.setattr(pt, "decide", _mutant_decide(lambda r, _: _is_state(r) and r.trusted, "__trusted__"))),
    ("score missing -> trusted", lambda mp, L: mp.setattr(pt, "decide", _mutant_decide(lambda r, _: r is None, "__missing__"))),
    ("NaN -> max score", lambda mp, L: mp.setattr(pt, "decide", _mutant_decide(lambda r, _: _is_state(r) and isinstance(r.accuracy, float) and math.isnan(r.accuracy), "__nan__"))),
    ("stale high reliability reused -> ignore expiry", lambda mp, L: mp.setattr(gamma.AuthorityEvidence, "is_live", lambda self, tick: True)),
    ("trust_score -> Γ authority evidence", lambda mp, L: mp.setattr(pt, "decide", _mutant_decide(lambda r, _: _is_state(r) and r.trust_score == "max", "__score__"))),
    ("memory reliability note -> grant", lambda mp, L: mp.setattr(pt, "decide", _mutant_decide(lambda r, recs: any('"reliability"' in x.content for x in recs), "__memnote__"))),
]


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_mutant_is_caught(label, apply, monkeypatch):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); probes = _probes(L)
        base = [pt.decide(recs, a, L.ledger, s, tick=tick, state_hash=STATE_A, contract=L.contract).authority for recs, s, a, tick in probes]
        assert all(b == "DENY" for b in base), base
        apply(monkeypatch, L)
        mut = [pt.decide(recs, a, L.ledger, s, tick=tick, state_hash=STATE_A, contract=L.contract).authority for recs, s, a, tick in probes]
        assert "ALLOW" in mut, f"mutant survived: {label}"


# --------------------------------------------------------------------------
# Aggregate
# --------------------------------------------------------------------------

def test_zz_aggregate():
    assert len(CASES) >= 150
    assert [c["case"] for c in CASES if c["reliability_induced_increase"]] == []
    assert all(c["authority"] == c["canonical"] for c in CASES)
    assert any(c["trust_delta"] for c in CASES)                        # H2: routing did move
    assert any(c["safety_deferral"] for c in CASES)                    # SafetyDeferral observed and distinct
    assert all(c["trust"] == "UNKNOWN" for c in CASES if not c["reliability_valid"])
