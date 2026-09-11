"""BINDING-STATE-PRESERVATION-REPAIR-R1 — attacks on the repair.

R1 is untouched and stays FALSIFIED. These tests attack the repaired pipeline:
prose omission, typed/prose conflict, partial writes, unknown schema versions,
legacy records, digest tampering, and mutants of the repair itself.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from logos_research.experiments import binding_repair as br
from logos_research.experiments import binding_state as bs


@pytest.fixture(scope="module")
def tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="repair-tests-"))


# R2 refined the fail-closed taxonomy: INCOMPLETE was split into
# MISSING_REQUIRED_FIELD / INVALID_TYPE / INVALID_VALUE / DIGEST_MISMATCH.
# Operational behaviour (DEFER, not trusted) is unchanged; only the label is.
FAIL_CLOSED = {"INCOMPLETE", "MISSING_REQUIRED_FIELD", "INVALID_TYPE",
               "INVALID_VALUE", "DIGEST_MISMATCH", "UNKNOWN_VERSION", "LEGACY_UNTYPED"}


def by_id(cid: str) -> bs.Fixture:
    return next(f for f in bs.fixtures() if f.constraint.constraint_id == cid)


# --------------------------------------------------------------------------
# R1 immutability: the old path still fails exactly as R1 recorded
# --------------------------------------------------------------------------

def test_r1_counterexample_1_still_reproduces_on_the_unrepaired_path():
    fx = by_id("C-B-requirement")
    degraded = bs.make_lossy_summary_transform(keep_sentences=2, strict=False).apply(fx.constraint)
    v, _ = bs.evaluate_action(degraded, fx.violating, fx.window)
    assert v == "ALLOW", "R1 CE1 must remain reproducible; the repair must not erase it"


def test_r1_counterexample_2_still_reproduces_on_the_unrepaired_path():
    c = bs.BindingConstraint("CE2", "REQUIREMENT", bs._base_contract(approval_required=True),
                             binding=False)
    out = bs.make_summary_transform(strict=True).apply(c)
    assert out.contract.approval_required is False


# --------------------------------------------------------------------------
# CE1 / CE2 on the repaired path
# --------------------------------------------------------------------------

def test_ce1_prevented_typed_preconditions_survive_lossy_prose(tmp):
    fx = by_id("C-B-requirement")
    content = br.encode_envelope(fx.constraint)
    for tf in (br.make_lossy_summary(2), br.make_memory_roundtrip(tmp / "ce1m"),
               br.make_projection(tmp / "ce1p")):
        content = tf.apply(content)
    decoded = br.decode_envelope(content)
    assert decoded.kind == "TYPED_SOURCE"
    assert "verification-Y" not in decoded.prose, "prose is expected to be lossy"
    assert decoded.typed.preconditions == ("verification-Y",)
    assert "preconditions" in decoded.divergence
    v, _ = br.evaluate_from_content(content, fx.violating, fx.window)
    assert v == "DENY"


def test_ce2_prevented_independent_approval_dimension_survives(tmp):
    c = bs.BindingConstraint("CE2", "REQUIREMENT", bs._base_contract(approval_required=True),
                             binding=False)
    content = br.make_lossy_summary(2).apply(br.encode_envelope(c))
    decoded = br.decode_envelope(content)
    assert "approval" not in decoded.prose.lower()
    assert decoded.typed.contract.approval_required is True
    assert decoded.typed.binding is False
    assert bs.measure_retention(c, decoded.typed).binding is True


def test_prose_may_be_lossy_while_binding_is_lossless(tmp):
    """Section 27: the design objective, stated as a test."""
    for fx in bs.fixtures():
        content = br.make_lossy_summary(1).apply(br.encode_envelope(fx.constraint))
        decoded = br.decode_envelope(content)
        assert len(decoded.prose) < len(bs.render_prose(fx.constraint))
        assert bs.measure_retention(fx.constraint, decoded.typed).binding is True


# --------------------------------------------------------------------------
# Real repository paths do not regress
# --------------------------------------------------------------------------

def test_real_paths_preserve_binding_with_zero_false_allow_or_block(tmp):
    res = br.run_matrix([br.make_memory_roundtrip(tmp / "rm"), br.make_projection(tmp / "rp")])
    assert all(x.source_kind == "TYPED_SOURCE" for x in res)
    assert all(x.retention.binding for x in res)
    assert not any(x.false_allow for x in res)
    assert not any(x.false_block for x in res)


def test_full_repaired_matrix_has_no_false_allow_and_no_false_block(tmp):
    res = br.run_matrix([
        br.make_memory_roundtrip(tmp / "m"), br.make_projection(tmp / "p"),
        br.make_lossy_summary(2), br.make_lossy_summary(1),
        br.chain("chain", br.make_lossy_summary(1), br.make_memory_roundtrip(tmp / "c"),
                 br.make_projection(tmp / "cp")),
    ])
    assert len(res) == 35
    assert sum(x.false_allow for x in res) == 0
    assert sum(x.false_block for x in res) == 0


# --------------------------------------------------------------------------
# Fail-closed reading: nothing ambiguous ever becomes ALLOW
# --------------------------------------------------------------------------

def _action():
    fx = by_id("C-B-requirement")
    return fx.violating, fx.permitted, fx.window


@pytest.mark.parametrize("content,kind", [
    ("Actions must target only: resource-A.", "LEGACY_UNTYPED"),
    ("not json at all", "LEGACY_UNTYPED"),
    (json.dumps({"prose": "x"}), "LEGACY_UNTYPED"),
    (json.dumps({"schema": "logos.binding-envelope/99", "typed": {}, "prose": "x"}),
     "UNKNOWN_VERSION"),
    (json.dumps({"schema": br.ENVELOPE_SCHEMA, "prose": "typed block missing"}), "INCOMPLETE"),
    (json.dumps({"schema": br.ENVELOPE_SCHEMA, "typed": {"garbage": 1}, "prose": "x"}),
     "MISSING_REQUIRED_FIELD"),
])
def test_unreadable_binding_defers_and_never_allows(content, kind):
    violating, permitted, window = _action()
    decoded = br.decode_envelope(content)
    assert decoded.kind == kind
    assert br.evaluate_from_content(content, violating, window)[0] == "DEFER"
    # Fail-closed applies to the permitted action too: unreadable binding licenses nothing.
    assert br.evaluate_from_content(content, permitted, window)[0] == "DEFER"


def test_partial_write_prose_without_typed_is_incomplete_not_permissive():
    """Section 36: prose committed, typed missing. Must not become ALLOW or advisory."""
    fx = by_id("C-B-requirement")
    doc = json.loads(br.encode_envelope(fx.constraint))
    del doc["typed"]
    content = json.dumps(doc)
    assert br.decode_envelope(content).kind == "INCOMPLETE"
    assert br.evaluate_from_content(content, fx.violating, fx.window)[0] == "DEFER"


def test_tampered_typed_block_is_rejected_by_its_digest():
    fx = by_id("C-B-requirement")
    doc = json.loads(br.encode_envelope(fx.constraint))
    doc["typed"]["preconditions"] = []          # weaken typed state in place
    content = json.dumps(doc)
    decoded = br.decode_envelope(content)
    assert decoded.kind == "DIGEST_MISMATCH"
    assert "digest" in decoded.reason
    assert br.evaluate_from_content(content, fx.violating, fx.window)[0] == "DEFER"


# --------------------------------------------------------------------------
# Typed/prose conflict: typed wins, drift is visible (Sections 23, 24, 33)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("prose,expect_divergence", [
    ("Actions should target only: resource-A.", "binding"),
    ("Actions must target only: resource-A, resource-B, record_7.", "targets"),
    ("Actions must target only: resource-A. Human approval is recommended.", "approval_required"),
    ("Constraint. Actions must target only: resource-A.", "preconditions"),
])
def test_prose_that_contradicts_typed_state_does_not_change_enforcement(prose, expect_divergence):
    c = replace(by_id("C-B-requirement").constraint,
                contract=replace(by_id("C-B-requirement").constraint.contract,
                                 approval_required=True))
    content = br.encode_envelope(c, prose=prose)
    decoded = br.decode_envelope(content)
    assert decoded.kind == "TYPED_SOURCE"
    assert expect_divergence in decoded.divergence
    assert decoded.typed == c                     # typed untouched by prose
    fx = by_id("C-B-requirement")
    assert br.evaluate_from_content(content, fx.violating, fx.window)[0] == "DENY"


def test_prose_cannot_strengthen_an_advisory_constraint():
    advisory = next(f for f in bs.fixtures() if not f.constraint.binding)
    content = br.encode_envelope(advisory.constraint,
                                 prose="Actions MUST target only: resource-A.")
    decoded = br.decode_envelope(content)
    assert decoded.typed.binding is False
    assert "binding" in decoded.divergence
    v, _ = br.evaluate_from_content(content, advisory.violating, advisory.window)
    assert v == "ALLOW"                            # advisory stays advisory


# --------------------------------------------------------------------------
# Memory does not become authority
# --------------------------------------------------------------------------

def test_envelope_records_carry_no_authority(tmp):
    fx = by_id("C-D-approval")
    record = br._record(br.encode_envelope(fx.constraint), "auth-check")
    assert record.authority.authority_class == "none"
    assert record.authority.admissible_uses == ()


def test_typed_approval_requirement_in_memory_still_needs_a_human_grant(tmp):
    """Storing approval_required=True is not the same as approval being present."""
    fx = by_id("C-D-approval")
    content = br.make_memory_roundtrip(tmp / "auth").apply(br.encode_envelope(fx.constraint))
    v, trace = br.evaluate_from_content(content, fx.violating, fx.window)
    assert v == "DENY"
    assert "G1-ORIGIN" in trace["gamma_failures"]
    p, _ = br.evaluate_from_content(content, fx.permitted, fx.window)
    assert p == "ALLOW"                            # with the grant, allowed


# --------------------------------------------------------------------------
# Property-based (Section 31)
# --------------------------------------------------------------------------

_targets = st.lists(st.sampled_from(["resource-A", "resource-B", "record_7"]),
                    min_size=1, max_size=3, unique=True)
_pre = st.lists(st.sampled_from(["verification-Y", "audit-Z"]), max_size=2, unique=True)


def _constraint(binding, approval, targets, pre):
    return bs.BindingConstraint("P", "REQUIREMENT",
                                bs._base_contract(targets=tuple(targets), approval_required=approval),
                                binding=binding, preconditions=tuple(pre))


@given(binding=st.booleans(), approval=st.booleans(), targets=_targets, pre=_pre,
       keep=st.integers(min_value=0, max_value=4))
@settings(max_examples=150, deadline=None)
def test_p1_p2_p3_typed_dimensions_survive_lossy_prose(binding, approval, targets, pre, keep):
    c = _constraint(binding, approval, targets, pre)
    decoded = br.decode_envelope(br.make_lossy_summary(keep).apply(br.encode_envelope(c)))
    assert decoded.kind == "TYPED_SOURCE"
    assert decoded.typed.binding == binding                              # P1
    assert decoded.typed.contract.approval_required == approval         # P2
    assert set(decoded.typed.contract.targets) == set(targets)          # P3
    assert decoded.typed.preconditions == tuple(pre)


@given(text=st.text(min_size=0, max_size=80))
@settings(max_examples=80, deadline=None)
def test_p4_p5_p6_arbitrary_prose_cannot_change_binding_or_authority(text):
    c = _constraint(True, True, ["resource-A"], ["verification-Y"])
    decoded = br.decode_envelope(br.encode_envelope(c, prose=text))
    assert decoded.typed == c
    assert decoded.typed.authority_origin == "human"


@given(binding=st.booleans(), approval=st.booleans())
@settings(max_examples=40, deadline=None)
def test_p7_independent_dimensions_do_not_collapse(binding, approval):
    c = _constraint(binding, approval, ["resource-A"], [])
    decoded = br.decode_envelope(br.make_lossy_summary(1).apply(br.encode_envelope(c)))
    assert (decoded.typed.binding, decoded.typed.contract.approval_required) == (binding, approval)


@given(text=st.text(min_size=0, max_size=60))
@settings(max_examples=60, deadline=None)
def test_p8_legacy_prose_never_becomes_trusted_typed_binding(text):
    decoded = br.decode_envelope(text)
    assert decoded.kind in ("LEGACY_UNTYPED", "UNKNOWN_VERSION", "INCOMPLETE")
    assert decoded.typed is None
    fx = by_id("C-B-requirement")
    assert br.evaluate_from_content(text, fx.violating, fx.window)[0] == "DEFER"


@given(binding=st.booleans(), approval=st.booleans(), targets=_targets, pre=_pre)
@settings(max_examples=60, deadline=None)
def test_roundtrip_through_memory_and_projection_is_typed_identity(binding, approval, targets, pre):
    tmp = Path(tempfile.mkdtemp(prefix="repair-prop-"))
    c = _constraint(binding, approval, targets, pre)
    content = br.chain("rt", br.make_memory_roundtrip(tmp / "m"),
                       br.make_projection(tmp / "p")).apply(br.encode_envelope(c))
    assert br.decode_envelope(content).typed == c


# --------------------------------------------------------------------------
# Mutation sensitivity of the repair (Section 32)
# --------------------------------------------------------------------------

def test_mutant_missing_typed_treated_as_allow_is_caught(monkeypatch):
    original = br.evaluate_from_content

    def permissive(content, action, window):
        if br.decode_envelope(content).kind != "TYPED_SOURCE":
            return "ALLOW", {"mutant": "missing typed -> ALLOW"}
        return original(content, action, window)

    monkeypatch.setattr(br, "evaluate_from_content", permissive)
    with pytest.raises(AssertionError):
        test_partial_write_prose_without_typed_is_incomplete_not_permissive()


def test_mutant_prose_made_authoritative_is_caught(monkeypatch):
    """If enforcement re-parsed prose instead of reading typed, CE1 returns."""
    original = br.decode_envelope

    def prose_wins(content):
        d = original(content)
        if d.kind == "TYPED_SOURCE":
            reconstructed = bs.parse_prose(d.prose, d.typed, strict=False)
            return replace(d, typed=reconstructed)
        return d

    monkeypatch.setattr(br, "decode_envelope", prose_wins)
    tmp = Path(tempfile.mkdtemp(prefix="mutant-"))
    with pytest.raises(AssertionError):
        test_ce1_prevented_typed_preconditions_survive_lossy_prose(tmp)


def test_mutant_digest_check_removed_is_caught(monkeypatch):
    original = br.decode_envelope

    def no_digest(content):
        try:
            doc = json.loads(content)
            if isinstance(doc, dict) and doc.get("schema") == br.ENVELOPE_SCHEMA and "typed" in doc:
                typed = br._typed_from_dict(doc["typed"])
                return br.Decoded("TYPED_SOURCE", typed, str(doc.get("prose", "")))
        except Exception:
            pass
        return original(content)

    monkeypatch.setattr(br, "decode_envelope", no_digest)
    with pytest.raises(AssertionError):
        test_tampered_typed_block_is_rejected_by_its_digest()


def test_mutant_unknown_schema_accepted_is_caught(monkeypatch):
    monkeypatch.setattr(br, "KNOWN_SCHEMAS", frozenset({br.ENVELOPE_SCHEMA, "logos.binding-envelope/99"}))
    content = json.dumps({"schema": "logos.binding-envelope/99", "typed": {}, "prose": "x"})
    # With the mutant the record is no longer UNKNOWN_VERSION; the parametrized
    # fail-closed test would then fail on its `kind` assertion.
    assert br.decode_envelope(content).kind != "UNKNOWN_VERSION"
