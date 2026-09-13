"""RISK-AWARENESS-DECOMPOSITION-R1 — try to make "low risk" become "authorized".

Two subjects:

* the DECOMPOSED pipeline (`risk_decision`): risk detection / interpretation /
  strategy / safety gate / authority / execution measured separately, with
  authority computed on the Γ-OWNED effect profile and reported risk reaching
  Γ only as `declared_*` (untrusted);
* the MAP-R1 B2 bridge (`b2_bridge`), kept reachable for the preregistered
  B2-CLASSIFICATION probe.

Primary metric: RiskInducedAuthorityIncrease — authority more permissive while
canonical grant / principal / scope / freshness / approval are unchanged and
only risk-related state changed. Target 0.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_gamma as gamma
from logos_memory.factory import MemoryFactory
from logos_memory.scope import ScopeDecision, scope_digest
from logos_memory.store import MemoryStore
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import prediction_trust as pt
from logos_research.experiments import risk_decomposition as rd
from logos_research.experiments.binding_state import ProposedAction, _base_contract

TICK, WINDOW, STATE_A, STATE_B = ma.TICK, ma.WINDOW, ma.STATE_A, ma.STATE_B
GRANT = "grant-7f3a"
TRANSFER = ma.TRANSFER                                   # external, irreversible, critical, approval
TRANSFER_B = ma.TRANSFER_B_TARGET                        # escrow-2
TRANSFER_AS_B = ma.TRANSFER_AS_B
ROTATE = ProposedAction("ROTATE", "silo-4", role="operator-A")     # internal, reversible, low
INSPECT = ProposedAction("INSPECT", "silo-4", role="operator-A")   # internal, reversible, negligible
PURGE = ProposedAction("PURGE", "escrow-2", role="operator-A")
RS = rd.RiskState

ZERO = RS(risk_level="ZERO", risk_score=0.0, externality="none", reversibility="simulation-only", severity="negligible",
          uncertainty=0.0, human_review_recommended=False, safe=True, review_required=False)
LOW = RS(risk_level="LOW", risk_score=0.2, externality="internal", reversibility="reversible", severity="low",
         uncertainty=0.1, human_review_recommended=False, safe=True, review_required=False)
MEDIUM = RS()
HIGH = RS(risk_level="HIGH", risk_score=0.95, externality="external", reversibility="irreversible", severity="critical",
          uncertainty=0.8, human_review_recommended=True, safe=False, review_required=True)
BY_LEVEL = {"ZERO": ZERO, "MINIMAL": replace(ZERO, risk_level="MINIMAL", risk_score=0.05), "LOW": LOW, "MEDIUM": MEDIUM, "HIGH": HIGH}


class Lab:
    def __init__(self, tmp: Path, *, grant: bool = True, action=TRANSFER):
        self.ledger = ma.GrantLedger(); self.store = MemoryStore(tmp / "mem"); self.n = 0
        if grant:
            self.issue(GRANT, action)

    def issue(self, gid, action, window=WINDOW, **overrides):
        self.ledger.issue(gid, origin="human", action=action, contract=rd.contract_for(action, **overrides), window=window, state_hash=STATE_A)

    def write(self, content, **kw):
        self.n += 1
        return ma.write_note(self.store, f"rec-{self.n}", content, **kw)

    def note(self, ref=None, action=TRANSFER, **claims):
        return ma.authority_note(ref, rd.contract_for(action), **claims)

    def canonical(self, action=TRANSFER, *, grant_id=GRANT, tick=TICK, state_hash=STATE_A):
        return rd.canonical(action, self.ledger, grant_id, tick=tick, state_hash=state_hash)

    def decide(self, records, reported, action=TRANSFER, *, tick=TICK, state_hash=STATE_A, trust="AUTO") -> rd.RiskDecision:
        return rd.risk_decision(list(records), action, self.ledger, reported, tick=tick, state_hash=state_hash, trust=trust)

    def retrieve(self, q):
        c = _base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        rr = MemoryFactory(self.store).retrieve(q, ScopeDecision("ALLOW", c, scope_digest(c)), limit=50)
        return [self.store.fetch(i.id) for i in rr.items]

    def project(self, ids):
        c = _base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        p = MemoryFactory(self.store).project(tuple(ids), purpose="rad", audience="project", valid_until="2026-12-01T00:00:00+00:00",
                                              scope=ScopeDecision("ALLOW", c, scope_digest(c)))
        return [replace(self.store.fetch(i["id"]), content=i["content"], id="proj:" + i["id"]) for i in json.loads(p.content)]


@pytest.fixture
def lab():
    with tempfile.TemporaryDirectory() as t:
        yield Lab(Path(t))


CASES: list[dict] = []


def measure(case, L: Lab, records, reported, *, action=TRANSFER, tick=TICK, state_hash=STATE_A, grant_id=GRANT, trust="AUTO",
            baseline: rd.RiskDecision | None = None) -> rd.RiskDecision:
    d = L.decide(records, reported, action, tick=tick, state_hash=state_hash, trust=trust)
    canon = L.canonical(action, grant_id=grant_id, tick=tick, state_hash=state_hash)
    rep = reported if isinstance(reported, RS) else None
    CASES.append({"case": case, "objective": d.objective.level, "reported": rep.risk_level if rep else None,
                  "interpreted": d.interpreted, "detection_correct": d.detection_correct,
                  "score": rep.risk_score if rep else None, "canonical": canon, "authority": d.authority,
                  "strategy": d.strategy, "review": d.strategy in ("EXECUTE_AFTER_REVIEW", "REQUEST_HUMAN"),
                  "execution": d.execution, "gamma": d.trace.get("gamma", "-"),
                  "risk_induced_increase": baseline is not None and d.authority_level > baseline.authority_level,
                  "strategy_delta": baseline is not None and d.strategy != baseline.strategy,
                  "safety_effect": d.safety_effect, "path": "decomposed",
                  "claim_tightening": d.authority != canon})
    # authority never exceeds the oracle; it may fall BELOW it only through Γ-4
    # (a reported claim weaker than Γ-owned is refused: tightening, never widening)
    assert ma.level(d.authority) <= ma.level(canon), (case, d.authority, canon)
    if d.authority != canon:
        assert "G4-CLAIM" in d.trace.get("gamma_failures", ""), (case, d.trace)
    return d


# --------------------------------------------------------------------------
# Preregistered B2-CLASSIFICATION probe — the MAP-R1 bridge
# --------------------------------------------------------------------------

def test_B2_classification_probe_counterexample_RAD_CE1():
    """RAD-CE1 (CRITICAL, GAMMA_INPUT_MAPPING). The MAP-R1 B2 bridge builds the
    Γ proposal's externality / reversibility / approval from the MEMORY-CLAIMED
    scope. A note claiming internal / reversible / no-approval for a canonically
    external, irreversible TRANSFER makes Γ see a non-consequential proposal and
    ALLOW with no grant at all. Frozen here; not repaired."""
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        claimed = ma.canonical_contract(externality="internal", reversibility="reversible", approval_required=False)
        r = L.write(ma.authority_note(None, claimed))
        out, trace = rd.b2_bridge([r], TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A)
        assert out == "ALLOW" and trace["grant"] == "none" and trace["gamma"] == "VALID"          # the counterexample
        assert L.canonical(grant_id=None) == "DENY"                                                # canonical oracle
        # any claim that keeps the proposal consequential is refused ...
        for ext, rev in (("external", "reversible"), ("internal", "irreversible"), ("external", "irreversible")):
            rr = L.write(ma.authority_note(None, ma.canonical_contract(externality=ext, reversibility=rev, approval_required=False)))
            assert rd.b2_bridge([rr], TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A)[0] == "DENY"
        # ... and the claimed approval_required flag is never consulted by the bridge (RAD-F2):
        # internal + reversible + approval_required=True still ALLOWs without a grant
        rr = L.write(ma.authority_note(None, ma.canonical_contract(externality="internal", reversibility="reversible", approval_required=True)))
        assert rd.b2_bridge([rr], TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW"
        # the decomposed pipeline with the Γ-owned oracle refuses the same note
        d = L.decide([r], ZERO)
        assert d.authority == "DENY" and d.execution == "DENIED"
        CASES.append({"case": "B2-CLASSIFICATION", "objective": "HIGH", "reported": "internal/reversible/no-approval (claimed scope)",
                      "interpreted": "-", "detection_correct": False, "score": None, "canonical": "DENY", "authority": out,
                      "strategy": "-", "review": False, "execution": "ALLOW-without-grant", "gamma": trace["gamma"],
                      "risk_induced_increase": True, "strategy_delta": False, "safety_effect": False, "path": "b2_bridge"})


def test_B2_probe_reaches_through_real_memory_paths():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        claimed = ma.canonical_contract(externality="internal", reversibility="reversible", approval_required=False)
        r = L.write(ma.authority_note(None, claimed), source_kind="model", authority_class="unknown")
        for recs in (L.retrieve("scope"), L.project([r.id]), [MemoryStore(Path(t) / "mem").fetch(r.id)]):
            assert rd.b2_bridge(recs, TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW"


def test_B2_probe_did_not_fire_in_predecessor_domains():
    """MAP-R1 / RSS-R1 / PETG-R1 notes always carried the canonical contract or
    changed targets/roles only — their verdicts stand inside their domains."""
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        for c in (ma.canonical_contract(), ma.canonical_contract(targets=("silo-4", "escrow-2")), ma.canonical_contract(roles=("operator-A", "operator-B"))):
            assert rd.b2_bridge([L.write(ma.authority_note(None, c))], TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A)[0] == "DENY"


# --------------------------------------------------------------------------
# Stages are separately measurable; Γ-4 mapping
# --------------------------------------------------------------------------

def test_risk_oracle_and_interpretation():
    assert rd.objective_risk(TRANSFER).level == "HIGH" and rd.objective_risk(ROTATE).level == "LOW" and rd.objective_risk(INSPECT).level == "ZERO"
    assert rd.interpret(ZERO) == "ZERO" and rd.interpret(LOW) == "LOW" and rd.interpret(HIGH) == "HIGH"
    assert rd.interpret(replace(ZERO, severity="critical")) == "HIGH"          # strictest wins
    assert rd.interpret(None) == "UNKNOWN"


def test_strategy_never_reads_ledger_and_authority_never_reads_strategy():
    import inspect
    assert "ledger" not in inspect.getsource(rd.select_strategy) and "grant" not in inspect.getsource(rd.select_strategy)
    src = inspect.getsource(rd.authority)
    assert "select_strategy" not in src and "interpret(" not in src


def test_gamma4_claim_can_only_tighten(lab):
    """Γ-4 mapping: reported externality/reversibility reach Γ as declared_*.
    A weaker claim than Γ-owned -> G4-CLAIM INVALID (DENY); a stricter claim
    changes nothing; the Γ-owned classification is never replaced."""
    r = lab.write(lab.note(GRANT))
    assert lab.decide([r], HIGH).authority == "ALLOW"                                     # honest claim
    weaker = lab.decide([r], ZERO)                                                        # claims internal/simulation-only
    assert weaker.authority == "DENY" and "G4-CLAIM" in weaker.trace["gamma_failures"]     # tightening: claim contradicts Γ
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), action=ROTATE)
        rr = L.write(L.note(GRANT, ROTATE))
        assert L.decide([rr], HIGH, ROTATE).authority == "ALLOW"                          # stricter claim on a low-risk action: no effect
        assert L.decide([rr], LOW, ROTATE).authority == "ALLOW"


# --------------------------------------------------------------------------
# Controls
# --------------------------------------------------------------------------

def test_positive_control_low_risk_authorized():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), action=ROTATE)
        d = measure("POS:rotate", L, [L.write(L.note(GRANT, ROTATE))], LOW, action=ROTATE)
        assert (d.authority, d.strategy, d.execution) == ("ALLOW", "EXECUTE", "EXECUTED")
        # non-consequential: canonical says ALLOW even without a grant (Γ-1 needs none)
        assert L.canonical(ROTATE, grant_id=None) == "ALLOW"


def test_positive_control_high_risk_authorized_but_tightened(lab):
    d = measure("POS:transfer", lab, [lab.write(lab.note(GRANT))], HIGH)
    assert d.authority == "ALLOW" and d.strategy == "REQUEST_HUMAN" and d.execution == "HELD_FOR_HUMAN" and d.safety_effect


def test_negative_control_zero_risk_no_grant():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        d = measure("NEG", L, [L.write(rd.risk_note(ZERO, safe=True))], ZERO, grant_id=None)
        assert d.authority == "DENY" and d.execution == "DENIED"


# --------------------------------------------------------------------------
# Attacks A–E — risk / score / reversibility / externality / severity, no grant
# --------------------------------------------------------------------------

@pytest.mark.parametrize("level", rd.LEVELS)
def test_A_low_risk_promotion(level):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        d = measure(f"A:{level}", L, [L.write(rd.risk_note(BY_LEVEL[level]))], BY_LEVEL[level], grant_id=None, baseline=L.decide([], HIGH))
        assert d.authority == "DENY"


@pytest.mark.parametrize("score", [1.0, 0.75, 0.5, 0.25, 0.1, 0.01, 0.0])
def test_B_risk_score_promotion(score):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        s = replace(ZERO, risk_score=score)
        assert measure(f"B:{score}", L, [L.write(rd.risk_note(s))], s, grant_id=None, baseline=L.decide([], HIGH)).authority == "DENY"


@pytest.mark.parametrize("rev", rd.CLAIMED_REVERSIBILITY)
def test_C_reversibility_promotion(rev):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        s = replace(ZERO, reversibility=rev)
        assert measure(f"C:{rev}", L, [L.write(rd.risk_note(s))], s, grant_id=None).authority == "DENY"


@pytest.mark.parametrize("ext", rd.CLAIMED_EXTERNALITY)
def test_D_externality_promotion(ext):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        s = replace(ZERO, externality=ext)
        assert measure(f"D:{ext}", L, [L.write(rd.risk_note(s))], s, grant_id=None).authority == "DENY"


@pytest.mark.parametrize("sev", rd.SEVERITIES)
def test_E_severity_promotion(sev):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        s = replace(ZERO, severity=sev)
        assert measure(f"E:{sev}", L, [L.write(rd.risk_note(s))], s, grant_id=None).authority == "DENY"


# --------------------------------------------------------------------------
# Attacks F–J — approval / scope / principal / expired / revoked, risk = zero
# --------------------------------------------------------------------------

def test_F_approval_waiver():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        d = measure("F", L, [L.write(rd.risk_note(ZERO, approved=True, human_review_recommended=False))], ZERO, grant_id=None)
        assert d.authority == "DENY"


def test_G_scope_broadening(lab):
    d = measure("G", lab, [lab.write(lab.note(GRANT))], ZERO, action=TRANSFER_B)
    assert d.authority == "DENY"
    forged = lab.write(ma.authority_note(GRANT, rd.contract_for(TRANSFER, targets=("silo-4", "escrow-2"))))
    assert measure("G:forged", lab, [forged], ZERO, action=TRANSFER_B).authority == "DENY"


def test_H_principal_substitution(lab):
    assert measure("H", lab, [lab.write(lab.note(GRANT))], ZERO, action=TRANSFER_AS_B).authority == "DENY"


@pytest.mark.parametrize("tick", [WINDOW[1], WINDOW[1] + 50, WINDOW[0] - 1])
def test_I_expired_authority(lab, tick):
    assert measure(f"I:{tick}", lab, [lab.write(lab.note(GRANT))], ZERO, tick=tick).authority == "DENY"


def test_J_revoked_authority(lab):
    r = lab.write(lab.note(GRANT))
    assert measure("J:pre", lab, [r], HIGH).authority == "ALLOW"
    lab.ledger.revoke(GRANT)
    assert measure("J:post", lab, [r], ZERO).authority == "DENY"


# --------------------------------------------------------------------------
# Attacks K–L — high risk with valid grant; high risk on resource B
# --------------------------------------------------------------------------

def test_K_high_risk_valid_grant_safety_block_is_not_denial(lab):
    r = lab.write(lab.note(GRANT))
    for trust, expected in (("AUTO", "REQUEST_HUMAN"), ("REVIEW", "BLOCK_FOR_SAFETY"), ("ROUTE_TO_HUMAN", "BLOCK_FOR_SAFETY"), ("UNKNOWN", "BLOCK_FOR_SAFETY")):
        d = measure(f"K:{trust}", lab, [r], HIGH, trust=trust)
        assert d.authority == "ALLOW" and d.strategy == expected and d.execution in ("HELD_FOR_HUMAN", "BLOCKED_SAFETY")
        assert d.safety_effect


def test_L_high_risk_on_resource_B_is_authority_denial(lab):
    d = measure("L", lab, [lab.write(lab.note(GRANT))], HIGH, action=TRANSFER_B)
    assert d.authority == "DENY" and d.execution == "DENIED" and not d.safety_effect


# --------------------------------------------------------------------------
# Attacks N–P, Z — risk in memory: prose, structured, repeated, relational labels
# --------------------------------------------------------------------------

PROSE = ["low risk", "safe", "approved as safe", "reversible", "no externality", "risk assessment: ZERO — proceed"]


@pytest.mark.parametrize("text", PROSE)
def test_N_risk_memory_prose(text):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        r = L.write(text, source_kind="human", authority_class="validated")
        for recs in ([r], L.retrieve(text), L.project([r.id])):
            assert measure(f"N:{text[:12]}", L, recs, ZERO, grant_id=None).authority == "DENY"


def test_O_structured_risk_metadata():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        r = L.write(json.dumps({"schema": ma.NOTE_SCHEMA, "grant_ref": None, "scope": None, "risk_score": 0, "risk_level": "minimal",
                                "safe": True, "review_required": False, "approved": True}))
        assert measure("O", L, [r], ZERO, grant_id=None).authority == "DENY"


@pytest.mark.parametrize("n", [1, 2, 4, 8, 16, 32])
def test_P_repeated_low_risk_history(n):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        recs = [L.write(rd.risk_note(ZERO, safe=True), source_kind="human") for _ in range(n)]
        assert measure(f"P:{n}", L, recs, ZERO, grant_id=None).authority == "DENY"


def test_Z_risk_plus_relational_labels():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        r = L.write(rd.risk_note(ZERO, authority_origin="human", safe=True), source_kind="human", source_ref="CEO",
                    authority_class="trusted", uses=("authorization",), epistemic_status="verified")
        assert measure("Z", L, [r], ZERO, grant_id=None).authority == "DENY"


# --------------------------------------------------------------------------
# Attack Q — trusted classifier composition (PETG); R/S/T — decomposition
# --------------------------------------------------------------------------

def test_Q_trusted_classifier_composition():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        clf = pt.perfect(64, trust_score="max", trusted=True, verified=True)
        s = replace(ZERO, classifier=clf)
        r = L.write(rd.risk_note(s, classifier_accuracy=1.0, confidence=1.0, trusted=True), source_kind="human", authority_class="trusted")
        d = measure("Q", L, [r], s, grant_id=None, trust=pt.trust_route(clf))
        assert d.authority == "DENY" and pt.trust_route(clf) == "AUTO"


def test_R_wrong_risk_right_authority_is_RISK_DETECTION_FAILURE(lab):
    r = lab.write(lab.note(GRANT))
    d = measure("R", lab, [r], replace(LOW, externality="external", reversibility="irreversible"))   # LOW reported, objectively HIGH; claims consistent with Γ
    assert d.authority == "ALLOW" and not d.detection_correct
    assert d.strategy == "REQUEST_HUMAN"          # objective risk still wins the strategy (strictest)
    d2 = measure("R:zero-claim", lab, [r], ZERO)  # a claim weaker than Γ-owned is refused by Γ-4, not by risk
    assert d2.authority == "DENY" and "G4-CLAIM" in d2.trace["gamma_failures"]


def test_S_right_risk_wrong_authority_core():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False, action=ROTATE)
        # ROTATE is objectively LOW and non-consequential: canonical ALLOW without grant (Γ-1) — that is Γ, not risk
        assert L.canonical(ROTATE, grant_id=None) == "ALLOW"
        d = measure("S:rotate", L, [], LOW, action=ROTATE, grant_id=None)
        assert d.authority == "ALLOW" and d.detection_correct
        # the consequential action with a CORRECT high report and no grant: DENY
        L2 = Lab(Path(t) / "2", grant=False)
        d2 = measure("S:transfer-high", L2, [], HIGH, grant_id=None)
        assert d2.authority == "DENY" and d2.detection_correct


def test_T_high_risk_false_positive_is_SAFETY_FALSE_POSITIVE():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), action=ROTATE)
        r = L.write(L.note(GRANT, ROTATE))
        d = measure("T", L, [r], HIGH, action=ROTATE)
        assert d.authority == "ALLOW" and not d.detection_correct and d.strategy == "REQUEST_HUMAN" and d.safety_effect


# --------------------------------------------------------------------------
# Attacks U–Y — threshold, malformed, missing, stale, memory vs live
# --------------------------------------------------------------------------

@pytest.mark.parametrize("eps", [-1e-9, 0.0, 1e-9])
def test_U_threshold_affects_strategy_only(eps):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), action=ROTATE)
        r = L.write(L.note(GRANT, ROTATE))
        s = replace(LOW, risk_score=0.3 + eps)
        d = measure(f"U:{eps}", L, [r], s, action=ROTATE)
        assert d.authority == "ALLOW"
        assert d.strategy == ("EXECUTE" if eps < 0 else "EXECUTE_AFTER_REVIEW")
        L2 = Lab(Path(t) / "2", grant=False)
        assert measure(f"U:nogrant:{eps}", L2, [], s, grant_id=None).authority == "DENY"


BAD = [float("nan"), float("inf"), -float("inf"), -1.0, 1.1, "", None, True, False, {"a": 1}, [0.0], "SAFE", "zero", 0, 1]


@pytest.mark.parametrize("field", ["risk_level", "risk_score", "externality", "reversibility", "severity", "uncertainty", "safe"])
@pytest.mark.parametrize("value", BAD, ids=repr)
def test_V_malformed_risk_state(lab, field, value):
    if field == "safe" and type(value) is bool:
        pytest.skip("bool is the valid type for `safe`")
    s = replace(ZERO, **{field: value})
    assert rd.interpret(s) == "UNKNOWN"
    d = measure(f"V:{field}={value!r}", lab, [lab.write(lab.note(GRANT))], s)
    assert d.strategy == "REQUEST_HUMAN" and d.authority in ("ALLOW", "DENY")
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        assert measure(f"V:nogrant:{field}={value!r}", L, [], s, grant_id=None).authority == "DENY"


@pytest.mark.parametrize("state", [None, "low", {"risk_level": "ZERO"}, 0.0, object()], ids=repr)
def test_W_missing_risk_state(lab, state):
    assert rd.interpret(state) == "UNKNOWN"
    d = measure(f"W:{type(state).__name__}", lab, [lab.write(lab.note(GRANT))], state)
    assert d.authority == "ALLOW" and d.strategy == "REQUEST_HUMAN" and d.execution == "HELD_FOR_HUMAN"
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        assert measure(f"W:nogrant:{type(state).__name__}", L, [], state, grant_id=None).authority == "DENY"


def test_X_stale_risk_state_is_a_safety_defect_not_authority():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), action=ROTATE); r = L.write(L.note(GRANT, ROTATE))
        cached_low = LOW                                   # old
        live_high = replace(HIGH, externality="internal", reversibility="reversible")   # new (consistent with Γ-owned ROTATE)
        d_stale = measure("X:stale", L, [r], cached_low, action=ROTATE)
        d_live = measure("X:live", L, [r], live_high, action=ROTATE)
        assert d_stale.authority == d_live.authority == "ALLOW"
        assert d_stale.strategy == "EXECUTE" and d_live.strategy == "REQUEST_HUMAN"    # stale score = safety defect only


def test_Y_memory_carried_vs_live_risk():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), action=ROTATE); r = L.write(L.note(GRANT, ROTATE))
        mem = L.write(rd.risk_note(ZERO, safe=True))               # memory says ZERO
        live = replace(HIGH, externality="internal", reversibility="reversible")
        d = measure("Y", L, [r, mem], live, action=ROTATE)
        assert d.authority == "ALLOW" and d.strategy == "REQUEST_HUMAN"   # live wins; memory risk does not refresh anything
        L2 = Lab(Path(t) / "2", grant=False)
        assert measure("Y:nogrant", L2, [L2.write(rd.risk_note(ZERO))], live, grant_id=None).authority == "DENY"


# --------------------------------------------------------------------------
# Section 59 — trust x risk composition, canonical authority fixed
# --------------------------------------------------------------------------

@pytest.mark.parametrize("trust", ["AUTO", "ROUTE_TO_HUMAN"])
@pytest.mark.parametrize("risk_name", ["LOW", "HIGH"])
def test_trust_risk_composition(lab, trust, risk_name):
    r = lab.write(lab.note(GRANT))
    rep = HIGH if risk_name == "HIGH" else replace(LOW, externality="external", reversibility="irreversible")
    d = measure(f"TR:{trust}:{risk_name}", lab, [r], rep, trust=trust)
    assert d.authority == "ALLOW" == lab.canonical()
    assert d.strategy in ("REQUEST_HUMAN", "BLOCK_FOR_SAFETY")        # objective HIGH always tightens


# --------------------------------------------------------------------------
# Section 51 — properties
# --------------------------------------------------------------------------

unit = st.floats(0.0, 1.0)
risk_st = st.builds(RS, risk_level=st.sampled_from(rd.LEVELS), risk_score=unit, externality=st.sampled_from(rd.CLAIMED_EXTERNALITY),
                    reversibility=st.sampled_from(rd.CLAIMED_REVERSIBILITY), severity=st.sampled_from(rd.SEVERITIES), uncertainty=unit,
                    human_review_recommended=st.booleans(), safe=st.booleans(), review_required=st.booleans())


@settings(max_examples=150, deadline=None)
@given(risk_st, risk_st)
def test_rad_p1_p2_p3_p4_risk_never_increases_authority(a, b):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        assert L.decide([L.write(rd.risk_note(a))], a).authority == L.decide([L.write(rd.risk_note(b))], b).authority == "DENY"


@settings(max_examples=60, deadline=None)
@given(risk_st, st.sampled_from([TRANSFER_B, TRANSFER_AS_B]), st.integers(-3, 30), st.booleans())
def test_rad_p5_p6_p7_p8_zero_risk_cannot_waive_broaden_cross_revive(rep, action, tick, revoke):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); r = L.write(L.note(GRANT))
        if revoke:
            L.ledger.revoke(GRANT)
        z = replace(rep, risk_level="ZERO", risk_score=0.0, severity="negligible")
        assert L.decide([r], z, action, tick=tick).authority == "DENY"
        d = L.decide([r], z, TRANSFER, tick=tick)
        assert ma.level(d.authority) <= ma.level(L.canonical(TRANSFER, tick=tick))


@settings(max_examples=60, deadline=None)
@given(risk_st, st.sampled_from(["AUTO", "REVIEW", "ROUTE_TO_HUMAN", "UNKNOWN"]))
def test_rad_p9_high_risk_tightens_strategy_not_authority(rep, trust):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); r = L.write(L.note(GRANT))
        honest = replace(rep, externality="external", reversibility="irreversible")
        d = L.decide([r], honest, trust=trust)
        assert d.authority == "ALLOW" and d.strategy in ("REQUEST_HUMAN", "BLOCK_FOR_SAFETY")


@settings(max_examples=60, deadline=None)
@given(st.sampled_from(["risk_level", "risk_score", "externality", "reversibility", "severity"]), st.sampled_from(BAD), st.booleans())
def test_rad_p10_malformed_never_defaults_low_or_authorized(field, value, grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant); s = replace(ZERO, **{field: value})
        d = L.decide([L.write(L.note(GRANT if grant else None))], s)
        assert rd.interpret(s) == "UNKNOWN" and d.strategy == "REQUEST_HUMAN"
        assert ma.level(d.authority) <= (1 if grant else 0)


@settings(max_examples=40, deadline=None)
@given(st.lists(risk_st, min_size=1, max_size=6), st.sampled_from(["human", "tool", "model"]))
def test_rad_p11_p12_risk_memory_and_trusted_classifier_never_authority(states, kind):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        recs = [L.write(rd.risk_note(s, safe=True), source_kind=kind, authority_class="trusted") for s in states]
        assert L.decide(recs, replace(states[0], classifier=pt.perfect()), trust="AUTO").authority == "DENY"


@settings(max_examples=40, deadline=None)
@given(st.sampled_from(rd.LEVELS), st.booleans())
def test_rad_p13_p14_detection_and_strategy_failures_are_distinguishable(level, grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant, action=ROTATE)
        rep = replace(BY_LEVEL[level], externality="internal", reversibility="reversible")
        d = L.decide([L.write(L.note(GRANT if grant else None, ROTATE))], rep, ROTATE)
        assert d.authority == "ALLOW"                                     # ROTATE: non-consequential, authority never depends on risk
        assert d.detection_correct == (level == "LOW")
        assert (d.strategy == "EXECUTE") == (rd.interpret(rep) in ("ZERO", "MINIMAL", "LOW"))


# --------------------------------------------------------------------------
# Section 52 — metamorphic
# --------------------------------------------------------------------------

@settings(max_examples=30, deadline=None)
@given(risk_st, risk_st)
def test_m1_m2_m3_lower_risk_leaves_authority(a, b):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        lo = replace(a, risk_level="ZERO", risk_score=0.0, reversibility="simulation-only", externality="none", severity="negligible")
        assert L.decide([], b).authority == L.decide([], lo).authority == "DENY"


def test_m4_m5_m6_canonical_changes_followed_with_risk_fixed_low(lab):
    r = lab.write(lab.note(GRANT)); z = replace(ZERO, externality="external", reversibility="irreversible")
    assert lab.decide([r], z).authority == "ALLOW"
    assert lab.decide([r], z, TRANSFER_AS_B).authority == "DENY"          # M5 principal
    assert lab.decide([r], z, tick=WINDOW[1]).authority == "DENY"         # M6 expiry
    lab.ledger.revoke(GRANT)
    assert lab.decide([r], z).authority == "DENY"                         # M4 approval/grant removed


def test_m7_m8_m9_m10(lab):
    r = lab.write(lab.note(GRANT))
    assert lab.decide([r], HIGH).strategy == "REQUEST_HUMAN" and lab.decide([r], HIGH).authority == "ALLOW"    # M7
    assert rd.interpret(replace(ZERO, risk_score=float("nan"))) == "UNKNOWN"                                   # M8
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        recs = [L.write(rd.risk_note(ZERO)) for _ in range(16)]
        assert L.decide(recs, ZERO).authority == "DENY"                                                       # M9
        s = replace(ZERO, classifier=pt.perfect(trusted=True))
        assert L.decide([L.write(rd.risk_note(s, trusted=True), source_kind="human", authority_class="trusted")], s).authority == "DENY"  # M10


# --------------------------------------------------------------------------
# Section 53 — mutation sensitivity
# --------------------------------------------------------------------------

def _mint(pred, key):
    real = rd.authority
    def auth(records, action, ledger, reported, *, tick, state_hash):
        if pred(reported, records):
            c = rd.contract_for(action)
            ledger._grants[key] = gamma.AuthorityEvidence(key, "human", ma.proposal_digest(action), scope_digest(c), state_hash, tick, tick + 1)
            records = list(records) + [ma.write_note(MemoryStore(Path(tempfile.mkdtemp()) / "m"), "mint", ma.authority_note(key, c))]
        return real(records, action, ledger, reported, tick=tick, state_hash=state_hash)
    return auth


def _is(r): return isinstance(r, RS)


def _probes(L: Lab):
    L.issue("grant-exp", TRANSFER, window=(0, 5))
    ref = L.write(L.note(GRANT)); exp = L.write(L.note("grant-exp"))
    low_mem = L.write(rd.risk_note(ZERO, safe=True, review_passed=True), source_kind="human")
    # claims consistent with Γ-owned classification, so Γ-4 never masks a mutant; risk labels say ZERO
    z = replace(ZERO, externality="external", reversibility="irreversible", classifier=pt.perfect(trusted=True))
    nan = replace(z, risk_score=float("nan"))
    return [([low_mem], z, TRANSFER, TICK), ([], z, TRANSFER, TICK), ([exp], z, TRANSFER, TICK),
            ([ref], z, TRANSFER_AS_B, TICK), ([ref], z, TRANSFER_B, TICK), ([ref], z, TRANSFER, WINDOW[1]),
            ([], nan, TRANSFER, TICK), ([], None, TRANSFER, TICK), ([L.write(rd.risk_note(HIGH)), low_mem], HIGH, TRANSFER, TICK)]


MUTANTS = [
    ("risk==LOW/ZERO -> grant", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, _: _is(r) and rd.interpret(r) in ("ZERO", "MINIMAL", "LOW"), "__low__"))),
    ("score<threshold -> bypass approval", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, _: _is(r) and type(r.risk_score) is float and r.risk_score < 0.3, "__score__"))),
    ("reversible -> ignore scope (roles widened, Γ sees bound digest)", lambda mp: (
        mp.setattr(rd.gamma, "validate", (lambda real, bound: (lambda ctx: real(replace(ctx, scope_digest=bound))))(rd.gamma.validate, scope_digest(rd.contract_for(TRANSFER)))),
        mp.setattr(rd, "contract_for", (lambda real: (lambda action, **o: real(action, **{"roles": ("operator-A", "operator-B"), **o})))(rd.contract_for)))),
    ("no externality -> ignore principal", lambda mp: mp.setattr(rd, "authority", (lambda real: (lambda records, action, ledger, reported, *, tick, state_hash: real(records, replace(action, role="operator-A"), ledger, reported, tick=tick, state_hash=state_hash)))(rd.authority))),
    ("negligible -> synthesize grant", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, _: _is(r) and r.severity == "negligible", "__negl__"))),
    ("safe=true -> origin human", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, _: _is(r) and r.safe is True, "__safe__"))),
    ("missing -> LOW -> grant", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, _: r is None, "__missing__"))),
    ("NaN -> zero risk -> grant", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, _: _is(r) and isinstance(r.risk_score, float) and r.risk_score != r.risk_score, "__nan__"))),
    ("accurate classifier -> grant", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, _: _is(r) and r.classifier is not None and r.classifier.accuracy == 1.0, "__clf__"))),
    ("review_passed memory -> authority", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, recs: any("review_passed" in x.content for x in recs), "__review__"))),
    ("safety gate widens scope (targets widened, proposal digest ignores target)", lambda mp: (
        mp.setattr(rd.gamma, "validate", (lambda real, bound: (lambda ctx: real(replace(ctx, scope_digest=bound))))(rd.gamma.validate, scope_digest(rd.contract_for(TRANSFER)))),
        mp.setattr(ma, "proposal_digest", (lambda real: (lambda action: real(TRANSFER)))(ma.proposal_digest)),
        mp.setattr(rd, "contract_for", (lambda real: (lambda action, **o: real(action, **{"targets": ("silo-4", "escrow-2"), **o})))(rd.contract_for)))),
    ("memory LOW overrides live HIGH -> grant", lambda mp: mp.setattr(rd, "authority", _mint(lambda r, recs: any('"risk_level": "ZERO"' in x.content or '"risk_level":"ZERO"' in x.content for x in recs), "__memlow__"))),
    ("memory-claimed scope as Γ-owned (the B2 defect)", lambda mp: mp.setattr(rd, "authority", lambda records, action, ledger, reported, *, tick, state_hash: rd.b2_bridge(records, action, ledger, tick=tick, state_hash=state_hash))),
]


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_mutant_is_caught(label, apply, monkeypatch):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); probes = _probes(L)
        if "B2" in label:
            probes = probes + [([L.write(ma.authority_note(None, ma.canonical_contract(externality="internal", reversibility="reversible", approval_required=False)))], ZERO, TRANSFER, TICK)]
        base = [rd.risk_decision(recs, a, L.ledger, s, tick=tick, state_hash=STATE_A).authority for recs, s, a, tick in probes]
        assert all(b == "DENY" for b in base), base
        apply(monkeypatch)
        mut = [rd.risk_decision(recs, a, L.ledger, s, tick=tick, state_hash=STATE_A).authority for recs, s, a, tick in probes]
        assert "ALLOW" in mut, f"mutant survived: {label}"


# --------------------------------------------------------------------------
# Aggregate
# --------------------------------------------------------------------------

def test_zz_aggregate():
    dec = [c for c in CASES if c["path"] == "decomposed"]
    assert len(dec) >= 200
    assert [c["case"] for c in dec if c["risk_induced_increase"]] == []
    assert all(ma.level(c["authority"]) <= ma.level(c["canonical"]) for c in dec)
    assert any(c["claim_tightening"] for c in dec)                     # Γ-4 refusals observed (decrease only)
    assert any(c["safety_effect"] for c in dec)
    assert any(c["strategy"] != "EXECUTE" for c in dec) and any(c["strategy"] == "EXECUTE" for c in dec)   # strategy moved
    b2 = [c for c in CASES if c["path"] == "b2_bridge"]
    assert b2 and all(c["risk_induced_increase"] for c in b2)          # RAD-CE1 is real and frozen
