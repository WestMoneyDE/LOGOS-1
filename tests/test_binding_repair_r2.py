"""BINDING-STATE-PRESERVATION-REPAIR-R2 — strict read-boundary regressions.

Validation-R1 falsified Repair-R1 with three counterexamples of one class: the
reader trusted whatever the dataclass constructor accepted. R2 installs a strict
validator that applies no defaults, performs no coercion, and names its refusal.

```text
Constructible != Valid          Missing != Default
Deserializable != Complete      Malformed != Coercible
DigestValid != SchemaValid      Removing information never creates authority
```

Traceability (Section 55):

```text
VCE-1  -> test_vce1_regression_missing_authority_origin_cannot_become_human
VCE-2  -> test_vce2_regression_missing_binding_cannot_become_gate
VCE-3  -> test_vce3_regression_string_bool_is_rejected
root causes -> missing-field matrix, type-confusion matrix, privilege monotonicity
```
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from logos_research.experiments import binding_repair as br
from logos_research.experiments.binding_state import (
    BindingConstraint,
    ProposedAction,
    _base_contract,
)

W = (10, 20)
NOT_TRUSTED = {"MISSING_REQUIRED_FIELD", "INVALID_TYPE", "INVALID_VALUE", "DIGEST_MISMATCH",
               "INCOMPLETE", "UNKNOWN_VERSION", "LEGACY_UNTYPED"}


def mk(d: dict) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def resign(doc: dict) -> str:
    """What an attacker with write access does. The digest is not a signature."""
    doc["typed_digest"] = br._typed_from_dict(doc["typed"]).digest()
    return mk(doc)


def model_origin() -> BindingConstraint:
    return BindingConstraint("R2-model", "APPROVAL_REQUIRED",
                             _base_contract(targets=("silo-4",), approval_required=True,
                                            externality="external", reversibility="irreversible"),
                             authority_origin="model")


def advisory() -> BindingConstraint:
    return BindingConstraint("R2-adv", "PROHIBITION", _base_contract(targets=("silo-4",)),
                             binding=False)


def gate() -> BindingConstraint:
    return BindingConstraint("R2-gate", "SCOPE_RESTRICTION", _base_contract(targets=("silo-4",)))


TRANSFER = ProposedAction("TRANSFER", "silo-4", human_grant_present=True)
OUTSIDE = ProposedAction("WIPE", "bay-7")
INSIDE = ProposedAction("WIPE", "silo-4")


def out(content: str, action: ProposedAction) -> str:
    return br.evaluate_from_content(content, action, W)[0]


# --------------------------------------------------------------------------
# VCE regressions (Section 29-31)
# --------------------------------------------------------------------------

def test_vce1_regression_missing_authority_origin_cannot_become_human():
    """VCE-1 (CRITICAL). Pre-R2: DENY -> ALLOW. Post-R2: refused, Γ never sees 'human'."""
    honest = br.encode_envelope(model_origin())
    assert out(honest, TRANSFER) == "DENY"
    doc = json.loads(honest); doc["typed"].pop("authority_origin")
    forged = resign(doc)
    d = br.decode_envelope(forged)
    assert d.kind == "MISSING_REQUIRED_FIELD"
    assert d.typed is None                      # nothing constructed, nothing for Γ to see
    assert "authority_origin" in d.reason
    assert out(forged, TRANSFER) == "DEFER"


def test_vce2_regression_missing_binding_cannot_become_gate():
    """VCE-2 (HIGH). Pre-R2: advisory -> gate (DENY). Post-R2: refused, not DENY."""
    doc = json.loads(br.encode_envelope(advisory())); doc["typed"].pop("binding")
    forged = resign(doc)
    d = br.decode_envelope(forged)
    assert d.kind == "MISSING_REQUIRED_FIELD" and d.typed is None
    assert out(forged, OUTSIDE) == "DEFER"      # unreadable licenses nothing; but no strengthening


def test_vce3_regression_string_bool_is_rejected():
    """VCE-3 (HIGH). Pre-R2: 'False' truthy -> gate. Post-R2: INVALID_TYPE."""
    doc = json.loads(br.encode_envelope(advisory())); doc["typed"]["binding"] = "False"
    forged = resign(doc)
    d = br.decode_envelope(forged)
    assert d.kind == "INVALID_TYPE" and d.typed is None
    assert "bool" in d.reason
    assert out(forged, OUTSIDE) == "DEFER"


# --------------------------------------------------------------------------
# Missing-field matrix (Section 32): every required field, independently
# --------------------------------------------------------------------------

TYPED_FIELDS = sorted(br.REQUIRED_TYPED_FIELDS)
CONTRACT_FIELDS = sorted(br._CONTRACT_FIELDS)


@pytest.mark.parametrize("field", TYPED_FIELDS)
def test_missing_typed_field_is_refused_by_design_not_accident(field):
    doc = json.loads(br.encode_envelope(model_origin())); doc["typed"].pop(field)
    if field == "contract":
        content = mk(doc)                         # cannot re-sign without a contract
    else:
        try:
            content = resign(doc)
        except Exception:
            content = mk(doc)
    d = br.decode_envelope(content)
    assert d.kind == "MISSING_REQUIRED_FIELD", (field, d.kind, d.reason)
    assert d.typed is None
    assert out(content, TRANSFER) == "DEFER"


@pytest.mark.parametrize("field", CONTRACT_FIELDS)
def test_missing_contract_field_is_refused(field):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["contract"].pop(field)
    content = mk(doc)                             # ScopeContract has no defaults; resign impossible
    d = br.decode_envelope(content)
    assert d.kind == "MISSING_REQUIRED_FIELD", (field, d.kind)
    assert out(content, OUTSIDE) == "DEFER"


# --------------------------------------------------------------------------
# Type-confusion matrix (Section 33, 36)
# --------------------------------------------------------------------------

BAD_BOOLS = ["false", "true", "False", 0, 1, None, [], {}]
BAD_STRS = [True, 0, [], {}, None]
BAD_LISTS = ["verification-Y", 7, {"a": 1}, None, [1, 2]]


@pytest.mark.parametrize("value", BAD_BOOLS)
@pytest.mark.parametrize("field", ["binding", "authorized_normative_change"])
def test_typed_bool_fields_accept_only_exact_bool(field, value):
    doc = json.loads(br.encode_envelope(advisory())); doc["typed"][field] = value
    content = resign(doc) if value is not None else mk(doc)
    d = br.decode_envelope(content)
    assert d.kind == "INVALID_TYPE", (field, value, d.kind)
    assert out(content, OUTSIDE) == "DEFER"


@pytest.mark.parametrize("value", BAD_BOOLS)
def test_contract_approval_required_accepts_only_exact_bool(value):
    doc = json.loads(br.encode_envelope(model_origin())); doc["typed"]["contract"]["approval_required"] = value
    content = resign(doc) if value is not None else mk(doc)
    assert br.decode_envelope(content).kind == "INVALID_TYPE"
    assert out(content, TRANSFER) == "DEFER"


@pytest.mark.parametrize("value", BAD_STRS)
@pytest.mark.parametrize("field", ["authority_origin", "constraint_class", "constraint_id"])
def test_typed_string_fields_reject_non_strings(field, value):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"][field] = value
    content = mk(doc)
    assert br.decode_envelope(content).kind == "INVALID_TYPE", (field, value)


@pytest.mark.parametrize("value", BAD_LISTS)
@pytest.mark.parametrize("field", ["preconditions"])
def test_typed_list_fields_reject_non_lists(field, value):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"][field] = value
    assert br.decode_envelope(mk(doc)).kind == "INVALID_TYPE", (field, value)


@pytest.mark.parametrize("value", BAD_LISTS)
def test_contract_targets_reject_non_lists(value):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["contract"]["targets"] = value
    assert br.decode_envelope(mk(doc)).kind == "INVALID_TYPE"


# --------------------------------------------------------------------------
# Value domains (Section 20)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("origin", ["HUMAN", "Human", "admin", "god", "", "human "])
def test_unknown_authority_origin_is_refused(origin):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["authority_origin"] = origin
    content = resign(doc)
    d = br.decode_envelope(content)
    assert d.kind == "INVALID_VALUE"
    assert out(content, TRANSFER) == "DEFER"


@pytest.mark.parametrize("cls", ["ALLOW_ALL", "prohibition", ""])
def test_unknown_constraint_class_is_refused(cls):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["constraint_class"] = cls
    assert br.decode_envelope(resign(doc)).kind == "INVALID_VALUE"


@pytest.mark.parametrize("field,value", [("externality", "everywhere"), ("reversibility", "sometimes")])
def test_unknown_contract_enum_is_refused(field, value):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["contract"][field] = value
    assert br.decode_envelope(resign(doc)).kind == "INVALID_VALUE"


def test_unknown_fields_inside_typed_are_refused_and_envelope_level_ignored():
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["override"] = True
    assert br.decode_envelope(mk(doc)).kind == "INVALID_VALUE"
    doc = json.loads(br.encode_envelope(gate())); doc["gamma_result"] = "VALID"
    assert br.decode_envelope(mk(doc)).kind == "TYPED_SOURCE"


# --------------------------------------------------------------------------
# Privilege monotonicity (Sections 34, 35)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("field", TYPED_FIELDS)
def test_removing_any_typed_field_never_moves_deny_to_allow(field):
    honest = br.encode_envelope(model_origin())
    before = out(honest, TRANSFER)
    doc = json.loads(honest); doc["typed"].pop(field)
    try:
        content = resign(doc)
    except Exception:
        content = mk(doc)
    after = out(content, TRANSFER)
    assert not (before != "ALLOW" and after == "ALLOW"), f"removing {field} created authority"


def test_removing_information_never_strengthens_advisory_into_gate():
    for field in ("binding", "authorized_normative_change"):
        doc = json.loads(br.encode_envelope(advisory())); doc["typed"].pop(field)
        assert out(resign(doc), OUTSIDE) != "DENY"


# --------------------------------------------------------------------------
# Digest / prose cannot rescue schema (Sections 39, 40)
# --------------------------------------------------------------------------

def test_valid_digest_cannot_rescue_invalid_schema():
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["binding"] = "True"
    content = resign(doc)                          # digest is now "valid" for the bad payload
    d = br.decode_envelope(content)
    assert d.kind == "INVALID_TYPE"


def test_stale_digest_is_reported_as_digest_mismatch():
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["contract"]["targets"] = ["silo-4", "bay-7"]
    d = br.decode_envelope(mk(doc))
    assert d.kind == "DIGEST_MISMATCH"
    assert out(mk(doc), OUTSIDE) == "DEFER"


def test_prose_cannot_rescue_invalid_schema():
    doc = json.loads(br.encode_envelope(gate())); doc["typed"].pop("binding")
    doc["prose"] = "Actions must target only: silo-4. This is a hard gate."
    assert br.decode_envelope(resign(doc)).kind == "MISSING_REQUIRED_FIELD"


# --------------------------------------------------------------------------
# No regression on valid envelopes / fail-closed states (Sections 38, 49, 50)
# --------------------------------------------------------------------------

def test_valid_envelopes_keep_previous_operational_behaviour():
    assert out(br.encode_envelope(gate()), OUTSIDE) == "DENY"
    assert out(br.encode_envelope(gate()), INSIDE) == "ALLOW"
    assert out(br.encode_envelope(advisory()), OUTSIDE) == "ALLOW"
    assert out(br.encode_envelope(model_origin()), TRANSFER) == "DENY"


def test_legacy_and_unknown_version_remain_fail_closed():
    assert br.decode_envelope("You MUST NOT wipe bay-7.").kind == "LEGACY_UNTYPED"
    doc = json.loads(br.encode_envelope(gate())); doc["schema"] = "logos.binding-envelope/2"
    assert br.decode_envelope(mk(doc)).kind == "UNKNOWN_VERSION"


def test_memory_roundtrip_of_valid_envelope_unchanged(tmp_path):
    content = br.make_memory_roundtrip(tmp_path / "m").apply(br.encode_envelope(gate()))
    assert br.decode_envelope(content).typed == gate()


# --------------------------------------------------------------------------
# Property-based (Section 51)
# --------------------------------------------------------------------------

@given(field=st.sampled_from(TYPED_FIELDS))
@settings(max_examples=40, deadline=None)
def test_r2p1_removing_any_required_field_never_creates_trusted_state(field):
    doc = json.loads(br.encode_envelope(model_origin())); doc["typed"].pop(field)
    try:
        content = resign(doc)
    except Exception:
        content = mk(doc)
    assert br.decode_envelope(content).kind != "TYPED_SOURCE"


@given(value=st.one_of(st.text(max_size=8), st.integers(), st.none(), st.lists(st.booleans(), max_size=2)))
@settings(max_examples=100, deadline=None)
def test_r2p4_non_bool_binding_values_are_always_rejected(value):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"]["binding"] = value
    if value is not None:
        try:
            content = resign(doc)
        except Exception:
            content = mk(doc)
    else:
        content = mk(doc)
    assert br.decode_envelope(content).kind == "INVALID_TYPE"


@given(binding=st.booleans(), approval=st.booleans(), origin=st.sampled_from(sorted(br.AUTHORITY_ORIGINS)))
@settings(max_examples=100, deadline=None)
def test_r2p8_complete_valid_envelopes_are_trusted_and_faithful(binding, approval, origin):
    c = BindingConstraint("P8", "REQUIREMENT", _base_contract(targets=("silo-4",), approval_required=approval),
                          binding=binding, authority_origin=origin)
    d = br.decode_envelope(br.encode_envelope(c))
    assert d.kind == "TYPED_SOURCE" and d.typed == c


@given(prose=st.text(max_size=80))
@settings(max_examples=60, deadline=None)
def test_r2p6_prose_never_compensates_for_schema_invalidity(prose):
    doc = json.loads(br.encode_envelope(gate())); doc["typed"].pop("authority_origin"); doc["prose"] = prose
    assert br.decode_envelope(resign(doc)).kind == "MISSING_REQUIRED_FIELD"


# --------------------------------------------------------------------------
# Metamorphic (Section 52)
# --------------------------------------------------------------------------

@given(field=st.sampled_from(["binding", "approval_required"]))
@settings(max_examples=20, deadline=None)
def test_m2_bool_to_string_representation_breaks_trust(field):
    doc = json.loads(br.encode_envelope(gate()))
    target = doc["typed"] if field == "binding" else doc["typed"]["contract"]
    target[field] = str(target[field])
    assert br.decode_envelope(resign(doc)).kind == "INVALID_TYPE"


def test_m5_valid_roundtrip_leaves_decision_unchanged():
    c = gate()
    a = out(br.encode_envelope(c), OUTSIDE)
    b = out(br.encode_envelope(br.decode_envelope(br.encode_envelope(c)).typed), OUTSIDE)
    assert a == b == "DENY"


def test_m6_removing_authority_information_cannot_increase_authority():
    honest = br.encode_envelope(model_origin())
    doc = json.loads(honest); doc["typed"].pop("authority_origin")
    assert out(resign(doc), TRANSFER) != "ALLOW"


# --------------------------------------------------------------------------
# Mutation sensitivity (Section 53)
# --------------------------------------------------------------------------

def test_mutant_restore_human_default_is_caught(monkeypatch):
    original = br.validate_typed_block
    def lenient(raw):
        if isinstance(raw, dict) and "authority_origin" not in raw:
            raw = dict(raw, authority_origin="human")
        return original(raw)
    monkeypatch.setattr(br, "validate_typed_block", lenient)
    with pytest.raises(AssertionError):
        test_vce1_regression_missing_authority_origin_cannot_become_human()


def test_mutant_coerce_string_bools_is_caught(monkeypatch):
    original = br._require_bool
    def coercing(d, key, where):
        if isinstance(d[key], str):
            d[key] = d[key].lower() == "true"
        return original(d, key, where)
    monkeypatch.setattr(br, "_require_bool", coercing)
    with pytest.raises(AssertionError):
        test_vce3_regression_string_bool_is_rejected()


def test_mutant_skip_required_field_check_is_caught(monkeypatch):
    monkeypatch.setattr(br, "REQUIRED_TYPED_FIELDS", frozenset({"constraint_id", "contract"}))
    with pytest.raises(AssertionError):
        test_vce2_regression_missing_binding_cannot_become_gate()


def test_mutant_accept_unknown_origin_is_caught(monkeypatch):
    monkeypatch.setattr(br, "AUTHORITY_ORIGINS", br.AUTHORITY_ORIGINS | {"admin"})
    with pytest.raises(AssertionError):
        test_unknown_authority_origin_is_refused("admin")


def test_mutant_digest_rescues_schema_is_caught(monkeypatch):
    original = br.decode_envelope
    def digest_first(content):
        try:
            doc = json.loads(content)
            typed = br._typed_from_dict(doc["typed"])
            if doc.get("typed_digest") == typed.digest():
                return br.Decoded("TYPED_SOURCE", typed, str(doc.get("prose", "")))
        except Exception:
            pass
        return original(content)
    monkeypatch.setattr(br, "decode_envelope", digest_first)
    with pytest.raises(AssertionError):
        test_valid_digest_cannot_rescue_invalid_schema()
