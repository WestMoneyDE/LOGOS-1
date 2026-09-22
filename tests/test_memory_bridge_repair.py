"""MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1 — self-tests of the repaired B2 bridge.

    CanonicalEffect  := effect oracle (what Γ says the action IS)
    DeclaredEffect   := what memory claims (declared_* only)

RAD-CE1 must stay reproducible on the historical path and be blocked on the
repaired one. This module implements and self-tests; it does not validate.
"""
from __future__ import annotations

import ast
import inspect
import json
import pathlib
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
from logos_research.experiments import effect_oracle as eo
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import prediction_trust as pt
from logos_research.experiments import risk_decomposition as rd
from logos_research.experiments.binding_state import ProposedAction, _base_contract

TICK, WINDOW, STATE_A, STATE_B = ma.TICK, ma.WINDOW, ma.STATE_A, ma.STATE_B
GRANT = "grant-7f3a"
TRANSFER, TRANSFER_B, TRANSFER_AS_B = ma.TRANSFER, ma.TRANSFER_B_TARGET, ma.TRANSFER_AS_B
ROTATE = ProposedAction("ROTATE", "silo-4", role="operator-A")
UNKNOWN_ACTION = ProposedAction("LAUNCH", "silo-4", role="operator-A")     # no canonical effect

EXT = ("internal", "external")
REV = ("reversible", "partially-reversible", "irreversible")


def claim(ext="external", rev="irreversible", appr=True, **o):
    return ma.canonical_contract(externality=ext, reversibility=rev, approval_required=appr, **o)


def ctr(action: ProposedAction, **overrides):
    """A contract for any oracle-known action: the oracle's effect plus canonical targets/roles."""
    e = eo.canonical_effect(action.action, action.target)
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",),
                approval_required=e.approval_required, externality=e.externality, reversibility=e.reversibility)
    base.update(overrides)
    return ma._base_contract(**base)


class Lab:
    def __init__(self, tmp: Path, *, grant: bool = True, action=TRANSFER):
        self.ledger = ma.GrantLedger(); self.store = MemoryStore(tmp / "mem"); self.n = 0; self.tmp = tmp
        self.contract = ma.canonical_contract() if action is TRANSFER else ctr(action)
        if grant:
            self.ledger.issue(GRANT, origin="human", action=action, contract=self.contract, window=WINDOW, state_hash=STATE_A)

    def write(self, content, **kw):
        self.n += 1
        return ma.write_note(self.store, f"rec-{self.n}", content, **kw)

    def bridge(self, records, action=TRANSFER, *, tick=TICK, state_hash=STATE_A, oracle=eo.canonical_effect):
        return ma.evaluate_with_memory(list(records), action, self.ledger, tick=tick, state_hash=state_hash,
                                       fallback_contract=self.contract, effect_oracle=oracle)

    def canonical(self, action=TRANSFER, *, grant_id=GRANT, tick=TICK, state_hash=STATE_A):
        c = self.contract if action.action == "TRANSFER" else ctr(action)
        return ma.evaluate_canonical(action, self.ledger, grant_id, c, tick=tick, state_hash=state_hash)[0]

    def readers(self, r):
        c = _base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        sc = ScopeDecision("ALLOW", c, scope_digest(c))
        rr = MemoryFactory(self.store).retrieve("scope grant_ref", sc, limit=50)
        proj = MemoryFactory(self.store).project((r.id,), purpose="mbg", audience="project", valid_until="2026-12-01T00:00:00+00:00", scope=sc)
        return {"fetch": [self.store.fetch(r.id)], "retrieve": [self.store.fetch(i.id) for i in rr.items],
                "project": [replace(self.store.fetch(i["id"]), content=i["content"], id="proj:" + i["id"]) for i in json.loads(proj.content)],
                "reload": [MemoryStore(self.tmp / "mem").fetch(r.id)]}


@pytest.fixture
def lab():
    with tempfile.TemporaryDirectory() as t:
        yield Lab(Path(t))


# --------------------------------------------------------------------------
# RAD-CE1: historical path still reproduces; repaired path blocks it
# --------------------------------------------------------------------------

def test_rad_ce1_historical_path_still_reproduces():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        r = L.write(ma.authority_note(None, claim("internal", "reversible", False)))
        for name, recs in L.readers(r).items():
            assert ma.evaluate_with_memory_prerepair(recs, TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A,
                                                     fallback_contract=L.contract)[0] == "ALLOW", name
            assert rd.b2_bridge(recs, TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW", name


def test_rad_ce1_blocked_on_repaired_bridge_all_readers():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        r = L.write(ma.authority_note(None, claim("internal", "reversible", False)))
        for name, recs in L.readers(r).items():
            out, trace = L.bridge(recs)
            assert out == "DENY", name
            assert trace["effect"] == "external/irreversible/approval=True" and trace["declared"] == "internal/reversible"
        assert L.canonical(grant_id=None) == "DENY"


@pytest.mark.parametrize("ext", EXT)
@pytest.mark.parametrize("rev", REV)
@pytest.mark.parametrize("appr", [True, False])
def test_no_claim_combination_makes_transfer_non_consequential(ext, rev, appr):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        out, trace = L.bridge([L.write(ma.authority_note(None, claim(ext, rev, appr)))])
        assert out == "DENY" and trace["effect"].startswith("external/irreversible")


# --------------------------------------------------------------------------
# Missing canonical effect -> DEFER, never memory
# --------------------------------------------------------------------------

def test_missing_canonical_effect_fails_closed(lab):
    r = lab.write(ma.authority_note(GRANT, claim("internal", "reversible", False)))
    out, trace = lab.bridge([r], UNKNOWN_ACTION)
    assert out == "DEFER" and trace["effect"] == "none" and trace["scope"] == "not-evaluated"
    out2, _ = lab.bridge([r], TRANSFER, oracle=lambda a, tgt: None)        # oracle that knows nothing
    assert out2 == "DEFER"
    assert eo.canonical_effect("LAUNCH", "silo-4") is None


def test_oracle_inputs_are_action_and_target_only():
    assert set(inspect.signature(eo.canonical_effect).parameters) == {"action", "target"}
    body = inspect.getsource(eo.canonical_effect) + inspect.getsource(eo.EffectClass)
    for forbidden in ("prose", "authority_class", "trust", "risk_score", "MemoryRecord", "content"):
        assert forbidden not in body
    assert "logos_memory" not in inspect.getsource(eo)


# --------------------------------------------------------------------------
# Contradictory / matching / stricter / weaker claims
# --------------------------------------------------------------------------

def test_contradictory_claim_canonical_wins_and_grant_still_required(lab):
    weak = lab.write(ma.authority_note(None, claim("internal", "reversible", False)))
    out, trace = lab.bridge([weak])
    assert out == "DENY" and trace["effect"] == "external/irreversible/approval=True"
    with_ref = lab.write(ma.authority_note(GRANT, claim("internal", "reversible", False)))
    out2, trace2 = lab.bridge([with_ref])
    assert out2 == "DENY" and "G4-CLAIM" in trace2["gamma_failures"]         # Γ-4 refuses the weaker claim


def test_matching_claim_preserves_valid_behaviour(lab):
    r = lab.write(ma.authority_note(GRANT, claim()))
    out, trace = lab.bridge([r])
    assert out == "ALLOW" == lab.canonical() and trace["declared"] == "external/irreversible"
    lab.ledger.revoke(GRANT)
    assert lab.bridge([r])[0] == "DENY"


def test_stricter_claim_never_widens():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False, action=ROTATE)
        honest = L.write(ma.authority_note(None, ctr(ROTATE)))
        stricter = L.write(ma.authority_note(None, ctr(ROTATE, externality="external", reversibility="irreversible")))
        base = L.bridge([honest], ROTATE); strict = L.bridge([stricter], ROTATE)
        assert base[0] == "ALLOW" == L.canonical(ROTATE, grant_id=None)       # non-consequential: Γ-1 needs no grant
        assert strict[1]["effect"] == "internal/reversible/approval=False"    # canonical unchanged
        assert ma.level(strict[0]) <= ma.level(base[0])


def test_weaker_claim_cannot_weaken_canonical(lab):
    for ext, rev in (("internal", "irreversible"), ("external", "reversible"), ("internal", "reversible")):
        out, trace = lab.bridge([lab.write(ma.authority_note(None, claim(ext, rev, False)))])
        assert out == "DENY" and trace["effect"].startswith("external/irreversible")


# --------------------------------------------------------------------------
# Claimed scope, approval, grant / principal / scope / freshness paths
# --------------------------------------------------------------------------

def test_claimed_scope_binds_but_never_classifies(lab):
    wider = lab.write(ma.authority_note(GRANT, claim(targets=("silo-4", "escrow-2"))))
    out, trace = lab.bridge([wider], TRANSFER_B)
    assert out == "DENY" and "G3-BINDING" in trace["gamma_failures"] and trace["effect"].startswith("external")
    narrower = lab.write(ma.authority_note(GRANT, claim(targets=())))
    assert lab.bridge([narrower])[0] == "DENY"                                # RSS-F1 veto preserved
    # a claimed scope that ALSO lies about effect: canonical effect unchanged, binding refused
    both = lab.write(ma.authority_note(GRANT, claim("internal", "reversible", False, targets=("silo-4", "escrow-2"))))
    out2, trace2 = lab.bridge([both], TRANSFER_B)
    assert out2 == "DENY" and trace2["effect"].startswith("external/irreversible")


def test_approval_claim_cannot_waive_canonical_approval(lab):
    r = lab.write(ma.authority_note(None, claim("external", "irreversible", False)))
    out, trace = lab.bridge([r])
    assert out == "DENY" and trace["gamma_failures"] == "APPROVAL-REQUIRED"
    non_human = ma.GrantLedger(); non_human.issue("g-model", origin="model", action=TRANSFER, contract=lab.contract, window=WINDOW, state_hash=STATE_A)
    r2 = lab.write(ma.authority_note("g-model", claim()))
    assert ma.evaluate_with_memory([r2], TRANSFER, non_human, tick=TICK, state_hash=STATE_A)[0] == "DENY"


def test_grant_principal_scope_freshness_paths_unchanged(lab):
    r = lab.write(ma.authority_note(GRANT, claim("internal", "reversible", False)))       # false low-risk claim throughout
    assert lab.bridge([r], TRANSFER_AS_B)[0] == "DENY" == lab.canonical(TRANSFER_AS_B)
    assert lab.bridge([r], TRANSFER_B)[0] == "DENY" == lab.canonical(TRANSFER_B)
    assert lab.bridge([r], tick=WINDOW[1])[0] == "DENY" == lab.canonical(tick=WINDOW[1])
    assert lab.bridge([r], state_hash=STATE_B)[0] == "DENY" == lab.canonical(state_hash=STATE_B)
    lab.ledger.revoke(GRANT)
    assert lab.bridge([r])[0] == "DENY"


def test_valid_grant_with_false_low_risk_claim_is_refused_by_gamma4_not_by_repair(lab):
    """Section 25: authority follows the grant unless Γ semantics require denial.
    Γ-4 DOES require denial of a weaker-than-canonical claim (RAD-F3). Recorded."""
    r = lab.write(ma.authority_note(GRANT, claim("internal", "reversible", True)))
    out, trace = lab.bridge([r])
    assert out == "DENY" and "G4-CLAIM" in trace["gamma_failures"] and trace["effect"].startswith("external/irreversible")


# --------------------------------------------------------------------------
# Proposal construction / declared-claim invariants (Sections 34–35)
# --------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(st.sampled_from(EXT), st.sampled_from(REV), st.booleans(), st.sampled_from(list(eo.CANONICAL_EFFECTS)))
def test_proposal_construction_invariant(ext, rev, appr, key):
    action = ProposedAction(key[0], key[1], role="operator-A")
    effect = eo.canonical_effect(*key)
    prop = ma.canonical_proposal(action, effect, (), (ext, rev))
    assert (prop.externality, prop.reversibility) == (effect.externality, effect.reversibility)
    assert (prop.declared_externality, prop.declared_reversibility) == (ext, rev)
    assert prop.is_consequential() == effect.consequential


def test_bridge_never_calls_proposal_for_with_claimed_contract():
    tree = ast.parse(inspect.getsource(ma.evaluate_with_memory))
    names = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "proposal_for" not in names and "canonical_proposal" not in names       # goes through _decide with effect=
    dec = ast.parse(inspect.getsource(ma._decide))
    calls = [n.func.id for n in ast.walk(dec) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert "canonical_proposal" in calls and "proposal_for" not in calls
    src = inspect.getsource(ma.evaluate_with_memory)
    assert " or " not in src.split("effect = effect_oracle")[1].split("\n")[0]        # no `oracle or memory`


# --------------------------------------------------------------------------
# Cross-reader consistency (Section 40)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("grant", [True, False])
@pytest.mark.parametrize("ext,rev", [("internal", "reversible"), ("external", "irreversible"), ("internal", "irreversible")])
def test_cross_reader_same_canonical_proposal(grant, ext, rev):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        r = L.write(ma.authority_note(GRANT if grant else None, claim(ext, rev, True)))
        results = {name: L.bridge(recs) for name, recs in L.readers(r).items()}
        outs = {o for o, _ in results.values()}; effects = {tr["effect"] for _, tr in results.values()}
        assert len(outs) == 1 and effects == {"external/irreversible/approval=True"}


# --------------------------------------------------------------------------
# Alternate bridge audit (Section 41)
# --------------------------------------------------------------------------

SRC = pathlib.Path(ma.__file__).resolve().parents[2]


def _effect_proposal_sites():
    out = {}
    for py in SRC.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                fn = n.func; name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
                if name == "EffectProposal":
                    enclosing = next((f.name for f in funcs if f.lineno <= n.lineno <= (f.end_lineno or 0)), "<module>")
                    out[(str(py.relative_to(SRC)).replace("\\", "/"), enclosing)] = True
    return set(out)


BRIDGES = {
    ("logos_research/experiments/memory_authority.py", "canonical_proposal"): "REPAIRED_CANONICAL_BRIDGE (effect oracle; claims -> declared_*)",
    ("logos_research/experiments/memory_authority.py", "evaluate_with_memory_prerepair"): "HISTORICAL (RAD-CE1 reproduction only; not for use)",
    ("logos_research/experiments/binding_state.py", "evaluate_action"): "EXPERIMENTAL (R1, immutable): same defect class — Γ fields from the memory-carried typed contract (MBG-F1)",
    ("logos_research/experiments/no_history_promotion.py", "_unauthorized_proposal"): "NON_CONSEQUENTIAL (fixed literal proposal; no memory input)",
    # registered by CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1 (2026-09-17, C2): the PRODUCTION relocation of canonical_proposal
    ("logos_runtime/bridge.py", "build_proposal"): "PRODUCTION_CANONICAL_BRIDGE (logos_effects owner; claims -> declared_*)",
}


def test_every_effect_proposal_construction_is_classified():
    assert _effect_proposal_sites() == set(BRIDGES), _effect_proposal_sites() ^ set(BRIDGES)


def test_all_consequential_bridges_share_the_oracle():
    """rd.authority and rd.risk_decision go through ma.proposal_for with the
    RiskOracle contract (caller-canonical); PETG decide / RSS evaluate_held go
    through evaluate_with_memory / _decide. None reads a claimed contract's
    effect fields into canonical Γ fields."""
    for fn in (rd.authority, pt.decide):
        src = inspect.getsource(fn)
        assert "ev.contract" not in src.replace("ev.contract or", "") or "contract_for(" in src


# --------------------------------------------------------------------------
# Regressions: MAP (authority evidence), RSS (labels), PETG (reliability), RAD
# --------------------------------------------------------------------------

def test_map_regression_memory_still_cannot_mint_authority():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        for content, kw in (("Human approved this action.", dict(source_kind="human", authority_class="human")),
                            (ma.authority_note("grant-7f3b", claim()), {}),
                            (ma.authority_note(None, claim(), approved=True, gamma_result="VALID"), dict(source_kind="tool"))):
            assert L.bridge([L.write(content, **kw)])[0] == "DENY"


@settings(max_examples=40, deadline=None)
@given(st.sampled_from(["human", "model", "tool", "trusted", "CEO"]), st.sampled_from(["human", "validated", "grant", "authorization"]), st.booleans())
def test_rss_regression_labels_inert(kind, cls, grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        r = L.write(ma.authority_note(GRANT if grant else None, claim()), source_kind=kind, source_ref=kind, authority_class=cls)
        assert L.bridge([r])[0] == ("ALLOW" if grant else "DENY")


def test_petg_regression_reliability_cannot_touch_canonical_fields(lab):
    r = lab.write(ma.authority_note(None, claim("internal", "reversible", False)))
    d = pt.decide([r], TRANSFER, lab.ledger, pt.perfect(64, trusted=True), tick=TICK, state_hash=STATE_A, contract=lab.contract)
    assert d.authority == "DENY" and d.trust == "AUTO"


def test_rad_regression_decomposed_pipeline_unchanged():
    with tempfile.TemporaryDirectory() as t:
        L = rd.risk_decision([], TRANSFER, ma.GrantLedger(), rd.RiskState(risk_level="ZERO", risk_score=0.0, externality="none",
                                                                          reversibility="simulation-only", severity="negligible"),
                             tick=TICK, state_hash=STATE_A)
        assert L.authority == "DENY"


# --------------------------------------------------------------------------
# Properties MBG-P1..P12 (Section 37)
# --------------------------------------------------------------------------

ext_st, rev_st, appr_st = st.sampled_from(EXT), st.sampled_from(REV), st.booleans()
targets_st = st.lists(st.sampled_from(["silo-4", "escrow-2", "reactor-7"]), max_size=3, unique=True)
roles_st = st.lists(st.sampled_from(["operator-A", "operator-B"]), min_size=1, max_size=2, unique=True)


@settings(max_examples=150, deadline=None)
@given(ext_st, rev_st, appr_st, st.booleans())
def test_mbg_p1_p2_p3_p4_p5_claims_never_change_canonical_or_waive(ext, rev, appr, grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        out, trace = L.bridge([L.write(ma.authority_note(GRANT if grant else None, claim(ext, rev, appr)))])
        assert trace["effect"] == "external/irreversible/approval=True"
        assert trace["declared"] == f"{ext}/{rev}"
        if not grant:
            assert out == "DENY"
        else:
            assert ma.level(out) <= ma.level(L.canonical())


@settings(max_examples=80, deadline=None)
@given(targets_st, roles_st, st.sampled_from([TRANSFER, TRANSFER_B, TRANSFER_AS_B]))
def test_mbg_p6_p11_claimed_scope_cannot_broaden_principal_freshness_independent(targets, roles, action):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t))
        r = L.write(ma.authority_note(GRANT, claim(targets=tuple(targets), roles=tuple(roles))))
        out = L.bridge([r], action)[0]
        assert ma.level(out) <= ma.level(L.canonical(action))
        if out == "ALLOW":
            assert tuple(targets) == ("silo-4",) and tuple(roles) == ("operator-A",) and action == TRANSFER
        assert L.bridge([r], action, tick=WINDOW[1])[0] == "DENY"


@settings(max_examples=60, deadline=None)
@given(ext_st, rev_st, st.sampled_from(["LAUNCH", "MELT", "TRANSFER"]), st.sampled_from(["silo-4", "moon"]))
def test_mbg_p7_missing_canonical_effect_never_uses_memory(ext, rev, act, tgt):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t))
        a = ProposedAction(act, tgt, role="operator-A")
        out, trace = L.bridge([L.write(ma.authority_note(GRANT, claim(ext, rev, False, targets=(tgt,))))], a)
        if eo.canonical_effect(act, tgt) is None:
            assert out == "DEFER" and trace["effect"] == "none"
        else:
            assert trace["effect"] == "external/irreversible/approval=True"


@settings(max_examples=60, deadline=None)
@given(st.sampled_from(list(eo.CANONICAL_EFFECTS)), ext_st, rev_st)
def test_mbg_p8_p9_p10_matching_stricter_weaker(key, ext, rev):
    with tempfile.TemporaryDirectory() as t:
        action = ProposedAction(key[0], key[1], role="operator-A")
        L = Lab(Path(t), grant=False)
        effect = eo.canonical_effect(*key)
        honest = ctr(action)
        base = L.bridge([L.write(ma.authority_note(None, honest))], action)
        claimed = L.bridge([L.write(ma.authority_note(None, ctr(action, externality=ext, reversibility=rev)))], action)
        assert claimed[1]["effect"] == f"{effect.externality}/{effect.reversibility}/approval={effect.approval_required}"
        assert ma.level(claimed[0]) <= ma.level(base[0])
        if (ext, rev) == (effect.externality, effect.reversibility):
            assert claimed[0] == base[0]


@settings(max_examples=40, deadline=None)
@given(ext_st, rev_st, st.booleans())
def test_mbg_p12_all_readers_same_canonical_source(ext, rev, grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        r = L.write(ma.authority_note(GRANT if grant else None, claim(ext, rev, True)))
        assert len({L.bridge(recs)[0] for recs in L.readers(r).values()}) == 1


# --------------------------------------------------------------------------
# Metamorphic M1..M10 (Section 38)
# --------------------------------------------------------------------------

@settings(max_examples=30, deadline=None)
@given(ext_st, rev_st, ext_st, rev_st, st.booleans())
def test_m1_m2_m3_m4_claim_changes_leave_canonical_and_never_increase(e1, r1, e2, r2, grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        a = L.bridge([L.write(ma.authority_note(GRANT if grant else None, claim(e1, r1)))])
        b = L.bridge([L.write(ma.authority_note(GRANT if grant else None, claim(e2, r2)))])
        assert a[1]["effect"] == b[1]["effect"]
        assert ma.level(b[0]) <= ma.level(L.canonical() if grant else "DENY")


def test_m5_m6_m7_m8_m9_m10(lab):
    honest = lab.write(ma.authority_note(GRANT, claim()))
    no_claim = lab.write(json.dumps({"schema": ma.NOTE_SCHEMA, "grant_ref": GRANT, "scope": None}))
    assert lab.bridge([honest])[1]["effect"] == lab.bridge([no_claim])[1]["effect"]            # M5
    assert lab.bridge([honest], oracle=lambda a, b: None)[0] == "DEFER"                        # M6
    assert len({lab.bridge(recs)[0] for recs in lab.readers(honest).values()}) == 1             # M7
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        r = L.write(ma.authority_note(GRANT, claim()))
        assert L.bridge([r])[0] == "DENY"
        L.ledger.issue(GRANT, origin="human", action=TRANSFER, contract=L.contract, window=WINDOW, state_hash=STATE_A)
        assert L.bridge([r])[0] == "ALLOW"                                                     # M8: only the grant changed
        L.ledger.revoke(GRANT)
        assert L.bridge([L.write(ma.authority_note(GRANT, claim("internal", "reversible", False)))])[0] == "DENY"   # M9
    wide = lab.write(ma.authority_note(GRANT, claim(targets=("silo-4", "escrow-2"))))
    assert lab.bridge([wide], TRANSFER_B)[1]["effect"].startswith("external") and lab.bridge([wide], TRANSFER_B)[0] == "DENY"   # M10


# --------------------------------------------------------------------------
# Mutation sensitivity (Section 39)
# --------------------------------------------------------------------------

NOTIFY = ProposedAction("NOTIFY", "ops-channel", role="operator-A")      # external, reversible, no approval
ARCHIVE = ProposedAction("ARCHIVE", "silo-4", role="operator-A")          # internal, partially-reversible, no approval
EXPORT = ProposedAction("EXPORT", "ledger-3", role="operator-A")          # internal, reversible, approval


def _probes(L: Lab):
    low = claim("internal", "reversible", False)
    return [([L.write(ma.authority_note(None, low))], TRANSFER),                                                   # all three axes lied
            ([L.write(ma.authority_note(None, ctr(NOTIFY, externality="internal")))], NOTIFY),          # externality lied
            ([L.write(ma.authority_note(None, ctr(ARCHIVE, reversibility="reversible")))], ARCHIVE),    # reversibility lied
            ([L.write(ma.authority_note(None, ctr(EXPORT, approval_required=False)))], EXPORT),         # approval lied
            ([L.write(ma.authority_note(None, claim("internal", "reversible", False, targets=("silo-4", "escrow-2"))))], TRANSFER_B),
            ([L.write(ma.authority_note(None, low))], UNKNOWN_ACTION)]


def _canonical_from_claim(mp, *, ext=False, rev=False, appr=False):
    """Mutant family: the canonical effect handed to Γ is (partly) rebuilt from
    the memory claim — the pre-repair defect, one axis at a time."""
    real = ma._decide
    def dec(action, contract, authority, claims, **kw):
        effect = kw.get("effect"); declared = kw.get("declared", (None, None))
        if effect is not None:
            kw["effect"] = eo.EffectClass(
                (declared[0] or effect.externality) if ext else effect.externality,
                (declared[1] or effect.reversibility) if rev else effect.reversibility,
                (contract.approval_required if appr else effect.approval_required))
        return real(action, contract, authority, claims, **kw)
    mp.setattr(ma, "_decide", dec)


MUTANTS = [
    ("restore proposal.externality = claim", lambda mp: _canonical_from_claim(mp, ext=True)),
    ("restore proposal.reversibility = claim", lambda mp: _canonical_from_claim(mp, rev=True)),
    ("fallback canonical effect to memory claim", lambda mp: mp.setattr(ma, "_decide", (lambda real: (lambda action, contract, authority, claims, **kw: real(action, contract, authority, claims, **{**kw, "effect": None, "canonical_contract": True})))(ma._decide))),   # MBGV-F1 guard: the mutant must now LIE explicitly
    ("derive consequentiality from claim", lambda mp: _canonical_from_claim(mp, ext=True, rev=True)),
    ("ignore canonical effect oracle", lambda mp: mp.setattr(ma, "_decide", (lambda real: (lambda action, contract, authority, claims, **kw: real(action, contract, authority, claims, **{**kw, "effect": None, "canonical_contract": True})))(ma._decide))),   # MBGV-F1 guard: the mutant must now LIE explicitly
    ("claimed scope drives classification", lambda mp: _canonical_from_claim(mp, ext=True, rev=True, appr=True)),
    ("claimed approval waives canonical approval", lambda mp: _canonical_from_claim(mp, appr=True)),
    ("skip declared_* mapping and write canonical", lambda mp: (_canonical_from_claim(mp, ext=True, rev=True, appr=True),
        mp.setattr(ma, "declared_effect", lambda c: (None, None)))),
    ("trust internal/reversible claims before Γ", lambda mp: mp.setattr(ma, "_decide", (lambda real: (lambda action, contract, authority, claims, **kw: ("ALLOW", {"mutant": "1"}) if kw.get("declared") == ("internal", "reversible") else real(action, contract, authority, claims, **kw)))(ma._decide))),
    ("reader-specific divergence (projection trusted)", lambda mp: mp.setattr(ma, "_decide", (lambda real: (lambda action, contract, authority, claims, **kw: ("ALLOW", {"mutant": "1"}) if any(c.ref.startswith("memory://proj:") for c in claims) else real(action, contract, authority, claims, **kw)))(ma._decide))),
]


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_mutant_is_caught(label, apply, monkeypatch):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False); probes = _probes(L)
        if "projection" in label:
            r = L.write(ma.authority_note(None, claim("internal", "reversible", False)))
            probes = probes + [(L.readers(r)["project"], TRANSFER)]
        base = [L.bridge(recs, a)[0] for recs, a in probes]
        assert all(b in ("DENY", "DEFER") for b in base), base
        apply(monkeypatch)
        mut = [L.bridge(recs, a)[0] for recs, a in probes]
        assert "ALLOW" in mut, f"mutant survived: {label}"
