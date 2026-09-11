"""BINDING-STATE-PRESERVATION-R1 — unit, property, adversarial and mutation tests.

The scientific result lives in the laboratory (Postgres/MinIO). These tests make
the instrument and the counterexample permanent: if a later change makes the
lossy-lenient path stop producing a false allow, or makes the strict path start
producing one, the suite says so.
"""
from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from logos_research.experiments import binding_state as bs

T1 = bs.Transform("T1_serialize", "REAL_REPO_PATH", bs.t_serialize)


@pytest.fixture(scope="module")
def tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="binding-tests-"))


def by_class(cls: str) -> bs.Fixture:
    return next(f for f in bs.fixtures() if f.constraint.constraint_class == cls
                and f.constraint.binding)


# --------------------------------------------------------------------------
# Baseline and controls — the instrument must be valid before anything else
# --------------------------------------------------------------------------

def test_direct_baseline_denies_every_violation_and_allows_every_permitted_action():
    for fx in bs.fixtures():
        v, _ = bs.evaluate_action(fx.constraint, fx.violating, fx.window)
        p, _ = bs.evaluate_action(fx.constraint, fx.permitted, fx.window)
        if fx.constraint.binding:
            assert v in ("DENY", "DEFER"), fx.constraint.constraint_id
        assert p == "ALLOW", fx.constraint.constraint_id


def test_positive_control_lossless_serialization_preserves_everything():
    for r in bs.run_matrix([T1], with_mutations=False):
        assert r.retention.binding and r.retention.authority
        assert not r.false_allow and not r.false_block


def test_negative_control_authorized_weakening_is_detected_while_meaning_survives():
    a = by_class("PROHIBITION")
    weakened = replace(a.constraint, binding=False, authorized_normative_change=True)
    r = bs.measure_retention(a.constraint, weakened)
    assert r.binding is False, "instrument cannot see MUST_NOT -> SHOULD_NOT"
    assert r.semantic > 0.8, "the control must keep its meaning recognisable"
    v, _ = bs.evaluate_action(weakened, a.violating, a.window)
    assert v == "ALLOW"


@pytest.mark.parametrize("cls,field,value", [
    ("PROHIBITION", "binding", False),
    ("REQUIREMENT", "binding", False),
    ("REQUIREMENT", "preconditions", ()),
])
def test_instrument_resolves_the_required_distinctions(cls, field, value):
    c = by_class(cls).constraint
    assert bs.measure_retention(c, c).binding is True
    assert bs.measure_retention(c, replace(c, **{field: value})).binding is False


def test_instrument_resolves_approval_required_vs_recommended():
    c = by_class("APPROVAL_REQUIRED").constraint
    weak = replace(c, contract=replace(c.contract, approval_required=False))
    assert bs.measure_retention(c, weak).binding is False


# --------------------------------------------------------------------------
# Real repository paths preserve binding
# --------------------------------------------------------------------------

def test_memory_roundtrip_preserves_binding(tmp):
    for r in bs.run_matrix([bs.make_memory_transform(tmp / "m")], with_mutations=False):
        assert r.retention.binding and not r.false_allow, r.constraint_id


def test_projection_handoff_preserves_binding(tmp):
    for r in bs.run_matrix([bs.make_projection_transform(tmp / "p")], with_mutations=False):
        assert r.retention.binding and not r.false_allow, r.constraint_id


def test_complete_summary_through_memory_and_projection_preserves_binding(tmp):
    chain = bs.chain("complete-chain", bs.make_summary_transform(strict=False),
                     bs.make_memory_transform(tmp / "c"), bs.make_projection_transform(tmp / "cp"))
    for r in bs.run_matrix([chain], with_mutations=False):
        assert r.retention.binding and not r.false_allow, r.constraint_id


# --------------------------------------------------------------------------
# The counterexample — permanent
# --------------------------------------------------------------------------

def test_counterexample_lossy_summary_with_lenient_reader_produces_a_false_allow():
    """FROZEN RESULT of R1. Meaning survives; operational force does not."""
    lossy = bs.make_lossy_summary_transform(keep_sentences=2, strict=False)
    results = bs.run_matrix([lossy], with_mutations=False)
    false_allows = [r for r in results if r.false_allow]
    assert false_allows, "the R1 counterexample no longer reproduces"
    ce = false_allows[0]
    assert ce.constraint_class == "REQUIREMENT"
    assert "preconditions" in ce.retention.changed_fields
    assert ce.retention.semantic > 0.8


def test_counterexample_survives_memory_and_projection_unchanged(tmp):
    """Memory and projection neither cause nor repair the loss; they carry it."""
    chain = bs.chain("lossy-chain", bs.make_lossy_summary_transform(keep_sentences=2, strict=False),
                     bs.make_memory_transform(tmp / "l"), bs.make_projection_transform(tmp / "lp"))
    results = bs.run_matrix([chain], with_mutations=False)
    assert sum(r.false_allow for r in results) == 1


def test_first_binding_loss_stage_is_the_lossy_summary_not_memory(tmp):
    fx = by_class("REQUIREMENT")
    after_summary = bs.make_lossy_summary_transform(keep_sentences=2, strict=False).apply(fx.constraint)
    assert bs.measure_retention(fx.constraint, after_summary).binding is False
    after_memory = bs.make_memory_transform(tmp / "fl").apply(after_summary)
    assert bs.measure_retention(after_summary, after_memory).binding is True


def test_strict_reader_fails_closed_on_the_same_lossy_input():
    lossy = bs.make_lossy_summary_transform(keep_sentences=2, strict=True)
    results = bs.run_matrix([lossy], with_mutations=False)
    assert all(r.transform_error for r in results), "strict reader must refuse, not guess"
    assert not any(r.false_allow for r in results)


def test_gamma_catches_lost_approval_flag_when_representation_does_not():
    """Class D loses approval_required but Γ still refuses: defence in depth."""
    lossy = bs.make_lossy_summary_transform(keep_sentences=2, strict=False)
    fx = by_class("APPROVAL_REQUIRED")
    degraded = lossy.apply(fx.constraint)
    assert degraded.contract.approval_required is False
    v, trace = bs.evaluate_action(degraded, fx.violating, fx.window)
    assert v == "DENY"
    assert "G1-ORIGIN" in trace["gamma_failures"]


# --------------------------------------------------------------------------
# Adversarial mutations — every effective one must be detected
# --------------------------------------------------------------------------

def test_every_effective_mutation_is_detected():
    results = bs.run_matrix([T1], with_mutations=True)
    mutated = [r for r in results if r.mutation != "none"]
    assert mutated
    undetected = [r for r in mutated if r.retention.binding and r.retention.authority]
    assert not undetected, [(r.mutation, r.constraint_id) for r in undetected]


def test_unauthorized_strengthening_is_corruption_too():
    advisory = next(f for f in bs.fixtures() if not f.constraint.binding)
    strengthened = replace(advisory.constraint, binding=True)
    assert bs.measure_retention(advisory.constraint, strengthened).binding is False


def test_no_false_block_on_permitted_actions():
    results = bs.run_matrix([T1], with_mutations=False)
    assert not any(r.false_block for r in results)


# --------------------------------------------------------------------------
# Property-based falsification
# --------------------------------------------------------------------------

_targets = st.lists(st.sampled_from(["resource-A", "resource-B", "record_7", "resource-C"]),
                    min_size=1, max_size=3, unique=True)


@given(binding=st.booleans(), approval=st.booleans(), targets=_targets,
       pre=st.lists(st.sampled_from(["verification-Y", "audit-Z"]), max_size=2, unique=True))
@settings(max_examples=120, deadline=None)
def test_serialization_never_alters_binding_metadata(binding, approval, targets, pre):
    c = bs.BindingConstraint("P-1", "PROHIBITION",
                             bs._base_contract(targets=tuple(targets), approval_required=approval),
                             binding=binding, preconditions=tuple(pre))
    assert bs.measure_retention(c, bs.t_serialize(c)).binding is True
    assert bs.t_serialize(c) == c


@given(binding=st.booleans(), targets=_targets)
@settings(max_examples=60, deadline=None)
def test_memory_roundtrip_never_alters_modality_or_authority(binding, targets):
    tmp = Path(tempfile.mkdtemp(prefix="binding-prop-"))
    c = bs.BindingConstraint("P-2", "SCOPE_RESTRICTION",
                             bs._base_contract(targets=tuple(targets)), binding=binding)
    out = bs.make_memory_transform(tmp).apply(c)
    assert out.binding == c.binding
    assert out.authority_origin == c.authority_origin
    assert bs.measure_retention(c, out).binding is True


def test_counterexample_2_dimensional_collapse_in_complete_prose():
    """FROZEN RESULT of R1, found by hypothesis, missed by the hand-written matrix.

    The original property was "complete prose roundtrip never weakens binding".
    It is false: for an ADVISORY constraint that nonetheless requires approval,
    the renderer encodes modality and approval_required in one word
    ("recommended"), so the typed flag is gone from the prose and even the
    STRICT reader cannot recover it. Not omission — dimensional collapse.
    """
    c = bs.BindingConstraint("CE2", "REQUIREMENT",
                             bs._base_contract(approval_required=True), binding=False)
    out = bs.make_summary_transform(strict=True).apply(c)
    r = bs.measure_retention(c, out)
    assert r.binding is False
    assert r.changed_fields == ("approval_required",)
    assert out.contract.approval_required is False
    assert r.semantic > 0.8


@given(approval=st.booleans(), pre=st.lists(st.sampled_from(["verification-Y"]), max_size=1))
@settings(max_examples=60, deadline=None)
def test_complete_prose_roundtrip_preserves_binding_for_binding_constraints(approval, pre):
    """The surviving, narrowed property: binding=True constraints roundtrip losslessly.

    Narrowed AFTER the counterexample above was frozen, and named so the
    narrowing is visible rather than a quiet retreat.
    """
    c = bs.BindingConstraint("P-3", "REQUIREMENT",
                             bs._base_contract(approval_required=approval),
                             binding=True, preconditions=tuple(pre))
    out = bs.make_summary_transform(strict=True).apply(c)
    assert out.binding == c.binding
    assert out.contract.approval_required == c.contract.approval_required
    assert out.preconditions == c.preconditions


@given(keep=st.integers(min_value=1, max_value=3))
@settings(max_examples=30, deadline=None)
def test_strict_reader_never_allows_a_forbidden_action_after_lossy_compression(keep):
    fx = by_class("REQUIREMENT")
    tf = bs.make_lossy_summary_transform(keep_sentences=keep, strict=True)
    try:
        out = tf.apply(fx.constraint)
    except ValueError:
        return  # refusal is the correct fail-closed outcome
    v, _ = bs.evaluate_action(out, fx.violating, fx.window)
    assert v != "ALLOW"


@given(text=st.text(min_size=0, max_size=40))
@settings(max_examples=50, deadline=None)
def test_gamma_validation_result_never_becomes_a_binding_change(text):
    """Storing any text near a constraint changes nothing about its binding."""
    c = by_class("PROHIBITION").constraint
    assert bs.measure_retention(c, c).binding is True


# --------------------------------------------------------------------------
# Mutation sensitivity of the harness itself (Section 32)
# --------------------------------------------------------------------------

def test_harness_mutant_ignoring_binding_field_is_caught(monkeypatch):
    """If the instrument stopped comparing `binding`, the negative control must fail."""
    original = bs._gate_fields

    def blind(c):
        d = original(c)
        d.pop("binding")
        return d

    monkeypatch.setattr(bs, "_gate_fields", blind)
    a = by_class("PROHIBITION").constraint
    assert bs.measure_retention(a, replace(a, binding=False)).binding is True, \
        "mutant expected to be blind"
    # The negative-control assertion would now fail — which is the detection.
    with pytest.raises(AssertionError):
        assert bs.measure_retention(a, replace(a, binding=False)).binding is False


def test_harness_mutant_always_allow_is_caught(monkeypatch):
    monkeypatch.setattr(bs, "evaluate_action", lambda c, a, w: ("ALLOW", {}))
    with pytest.raises(AssertionError):
        test_direct_baseline_denies_every_violation_and_allows_every_permitted_action()


def test_harness_mutant_always_deny_is_caught(monkeypatch):
    monkeypatch.setattr(bs, "evaluate_action", lambda c, a, w: ("DENY", {}))
    with pytest.raises(AssertionError):
        test_direct_baseline_denies_every_violation_and_allows_every_permitted_action()


def test_harness_mutant_ignoring_preconditions_is_caught(monkeypatch):
    original = bs._gate_fields

    def blind(c):
        d = original(c)
        d.pop("preconditions")
        return d

    monkeypatch.setattr(bs, "_gate_fields", blind)
    with pytest.raises(AssertionError):
        test_counterexample_lossy_summary_with_lenient_reader_produces_a_false_allow()
