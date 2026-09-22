"""BINDING-STATE-PRESERVATION-REPAIR-R1 — operational binding independent of prose.

R1 found two ways a rule stops being the same rule after being written down
differently: a lossy summary drops a clause and a lenient reader fills the gap
with a default (CE1); a renderer folds two typed dimensions into one word and
nothing can unfold it (CE2). Both share one cause: **prose was the carrier of
operational binding across a representation boundary.**

The repair is one rule, stated once:

```text
TypedBindingState must not depend on NaturalLanguageReconstruction.

OperationalConstraint = TypedBindingMetadata + HumanReadableProjection
    typed   -> enforcement source, lossless
    prose   -> explanation, may be lossy, never parsed back for enforcement
```

Realized as a **binding envelope** carried in `MemoryRecord.content`. No field
is added to `MemoryRecord`; the envelope is a schema-marked JSON document, so
the memory layer stays exactly what it is and the R1 finding that it
"faithfully preserves whatever it receives" is used rather than fought.

Reading is fail-closed in every ambiguous case:

```text
envelope, current schema, typed valid   -> TYPED_SOURCE     enforce from typed
envelope, unknown schema version        -> UNKNOWN_VERSION  DEFER, never ALLOW
envelope, typed missing/invalid         -> INCOMPLETE       DEFER, never ALLOW
no envelope (plain prose)               -> LEGACY_UNTYPED   DEFER, never ALLOW
typed present, prose diverges           -> TYPED_SOURCE + divergence flagged
```

Memory does not gain authority from any of this. The envelope stores *evidence
of a constraint*; `AuthorityProvenance` on the record stays `("none", ())`, and
the only authority Γ ever sees is the human grant on the action, exactly as in
R1. Γ is not modified and not consulted for any new purpose.

The R1 module is untouched. R1 stays FALSIFIED.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Callable, Literal

from logos_memory.factory import MemoryFactory
from logos_memory.records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from logos_memory.scope import ScopeDecision, scope_digest
from logos_memory.store import MemoryStore

from . import binding_state as bs

ENVELOPE_SCHEMA = "logos.binding-envelope/1"
KNOWN_SCHEMAS = frozenset({ENVELOPE_SCHEMA})

SourceKind = Literal[
    "TYPED_SOURCE", "LEGACY_UNTYPED", "INCOMPLETE", "UNKNOWN_VERSION",
    # R2: the actual cause is preserved instead of being collapsed into INCOMPLETE.
    "MISSING_REQUIRED_FIELD", "INVALID_TYPE", "INVALID_VALUE", "DIGEST_MISMATCH",
]


# --------------------------------------------------------------------------
# R2 - strict typed-block validation at the read boundary
#
# Validation-R1 (VCE-1..3) showed that "the constructor did not raise" was
# being treated as "the typed payload is valid". It is not:
#
#     Constructible != Valid        Missing != Default
#     Deserializable != Complete    Malformed != Coercible
#
# BindingConstraint keeps its constructor defaults for in-process ergonomics.
# The storage/wire boundary is this validator, which applies NO defaults,
# performs NO coercion, and names exactly why it refused.
# --------------------------------------------------------------------------

#: Every BindingConstraint field is required on the wire - including the four
#: that have constructor defaults. authority_origin defaulting to "human" was
#: VCE-1; binding defaulting to True was VCE-2.
REQUIRED_TYPED_FIELDS = frozenset({
    "constraint_id", "constraint_class", "contract", "binding", "preconditions",
    "authority_origin", "authorized_normative_change",
})

CONSTRAINT_CLASSES = frozenset({
    "PROHIBITION", "REQUIREMENT", "CONDITIONAL", "APPROVAL_REQUIRED",
    "SCOPE_RESTRICTION", "FRESHNESS",
})

#: Canonical authority origins, mirroring logos_gamma.types. Only "human" bears
#: authority; the rest exist so a stored origin can be stated honestly.
AUTHORITY_ORIGINS = frozenset({
    "human", "memory", "model", "tool", "summary", "derived", "retrieval",
    "self-report", "unknown",
})

_CONTRACT_STR_TUPLES = (
    "paths", "excluded_paths", "roles", "tools", "memory_kinds", "projection_audiences",
    "capabilities", "targets", "data_classes", "retention_classes", "source_versions",
)
_CONTRACT_FIELDS = frozenset(_CONTRACT_STR_TUPLES) | {
    "project", "parameter_bounds", "max_cost_usd", "max_tokens", "max_seconds",
    "max_attempts", "valid_from", "valid_until", "max_occurrences", "externality",
    "reversibility", "approval_required",
}


class TypedBlockInvalid(ValueError):
    def __init__(self, kind: SourceKind, reason: str) -> None:
        super().__init__(reason)
        self.kind = kind
        self.reason = reason


def _require_bool(d: dict, key: str, where: str) -> None:
    if type(d[key]) is not bool:  # exact: no truthiness, no 0/1/"False"
        raise TypedBlockInvalid(
            "INVALID_TYPE", f"{where}.{key} must be bool, got {type(d[key]).__name__}")


def _require_str(d: dict, key: str, where: str) -> None:
    if type(d[key]) is not str:
        raise TypedBlockInvalid(
            "INVALID_TYPE", f"{where}.{key} must be str, got {type(d[key]).__name__}")


def _require_str_list(d: dict, key: str, where: str) -> None:
    v = d[key]
    if type(v) is not list or any(type(x) is not str for x in v):
        raise TypedBlockInvalid("INVALID_TYPE", f"{where}.{key} must be a list of str")


def _is_number(v: object) -> bool:
    return type(v) in (int, float)


def validate_typed_block(raw: object) -> None:
    """Refuse anything that is not exactly a complete, well-typed constraint.

    Raises TypedBlockInvalid with the precise cause. Applies no defaults.
    """
    if type(raw) is not dict:
        raise TypedBlockInvalid("INVALID_TYPE", "typed block must be an object")
    missing = REQUIRED_TYPED_FIELDS - raw.keys()
    if missing:
        raise TypedBlockInvalid(
            "MISSING_REQUIRED_FIELD",
            f"typed block missing {sorted(missing)}; no default is applied")
    unknown = raw.keys() - REQUIRED_TYPED_FIELDS
    if unknown:
        raise TypedBlockInvalid("INVALID_VALUE", f"typed block has unknown fields {sorted(unknown)}")

    _require_str(raw, "constraint_id", "typed")
    _require_str(raw, "constraint_class", "typed")
    if raw["constraint_class"] not in CONSTRAINT_CLASSES:
        raise TypedBlockInvalid("INVALID_VALUE", f"unknown constraint_class {raw['constraint_class']!r}")
    _require_bool(raw, "binding", "typed")
    _require_bool(raw, "authorized_normative_change", "typed")
    _require_str_list(raw, "preconditions", "typed")
    _require_str(raw, "authority_origin", "typed")
    if raw["authority_origin"] not in AUTHORITY_ORIGINS:
        raise TypedBlockInvalid("INVALID_VALUE", f"unknown authority_origin {raw['authority_origin']!r}")

    contract = raw["contract"]
    if type(contract) is not dict:
        raise TypedBlockInvalid("INVALID_TYPE", "typed.contract must be an object")
    c_missing = _CONTRACT_FIELDS - contract.keys()
    if c_missing:
        raise TypedBlockInvalid("MISSING_REQUIRED_FIELD", f"contract missing {sorted(c_missing)}")
    c_unknown = contract.keys() - _CONTRACT_FIELDS
    if c_unknown:
        raise TypedBlockInvalid("INVALID_VALUE", f"contract has unknown fields {sorted(c_unknown)}")
    for key in _CONTRACT_STR_TUPLES:
        _require_str_list(contract, key, "contract")
    for key in ("project", "valid_from", "valid_until", "externality", "reversibility"):
        _require_str(contract, key, "contract")
    _require_bool(contract, "approval_required", "contract")
    for key in ("max_tokens", "max_seconds", "max_attempts", "max_occurrences"):
        if type(contract[key]) is not int:
            raise TypedBlockInvalid("INVALID_TYPE", f"contract.{key} must be int")
    if not _is_number(contract["max_cost_usd"]):
        raise TypedBlockInvalid("INVALID_TYPE", "contract.max_cost_usd must be a number")
    if contract["externality"] not in ("internal", "external"):
        raise TypedBlockInvalid("INVALID_VALUE", f"unknown externality {contract['externality']!r}")
    if contract["reversibility"] not in ("reversible", "partially-reversible", "irreversible"):
        raise TypedBlockInvalid("INVALID_VALUE", f"unknown reversibility {contract['reversibility']!r}")
    pb = contract["parameter_bounds"]
    if type(pb) is not list or any(
        type(b) is not list or len(b) != 3 or type(b[0]) is not str
        or not _is_number(b[1]) or not _is_number(b[2]) for b in pb
    ):
        raise TypedBlockInvalid("INVALID_TYPE", "contract.parameter_bounds must be [[str, number, number], ...]")


# --------------------------------------------------------------------------
# Envelope
# --------------------------------------------------------------------------

def encode_envelope(c: bs.BindingConstraint, prose: str | None = None) -> str:
    """Serialize typed state as data, with prose alongside as a projection."""
    return json.dumps(
        {
            "schema": ENVELOPE_SCHEMA,
            "typed": asdict(c),
            "typed_digest": c.digest(),
            "prose": prose if prose is not None else bs.render_prose(c),
        },
        sort_keys=True, separators=(",", ":"),
    )


@dataclass(frozen=True)
class Decoded:
    kind: SourceKind
    typed: bs.BindingConstraint | None
    prose: str
    #: Fields on which the prose projection disagrees with the typed source.
    #: Informational only; enforcement never consults prose.
    divergence: tuple[str, ...] = ()
    reason: str = ""


def _typed_from_dict(d: dict) -> bs.BindingConstraint:
    """PRIVATE construction helper. NOT a trusted reader.

    Applies constructor defaults and no validation. The only trusted path is
    `decode_envelope`, which calls `validate_typed_block` first. Kept so that
    tests can compute the digest an attacker would compute.
    """
    return bs._from_json(json.dumps(d))


def decode_envelope(content: str) -> Decoded:
    """Read a memory record's content. Fail closed on anything but a valid envelope."""
    try:
        doc = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return Decoded("LEGACY_UNTYPED", None, content, reason="content is not JSON")
    if not isinstance(doc, dict) or "schema" not in doc:
        return Decoded("LEGACY_UNTYPED", None, content,
                       reason="no envelope schema marker")
    if doc["schema"] not in KNOWN_SCHEMAS:
        return Decoded("UNKNOWN_VERSION", None, str(doc.get("prose", "")),
                       reason=f"unknown envelope schema {doc['schema']!r}")
    if "typed" not in doc:
        return Decoded("INCOMPLETE", None, str(doc.get("prose", "")),
                       reason="envelope present but typed block missing")
    # R2: strict schema validation FIRST. A valid digest cannot rescue an invalid
    # schema, and the constructor is never asked to fill a gap.
    try:
        validate_typed_block(doc["typed"])
    except TypedBlockInvalid as exc:
        return Decoded(exc.kind, None, str(doc.get("prose", "")), reason=exc.reason)
    typed = _typed_from_dict(doc["typed"])
    if doc.get("typed_digest") != typed.digest():
        return Decoded("DIGEST_MISMATCH", None, str(doc.get("prose", "")),
                       reason="typed block does not match its recorded digest")
    prose = str(doc.get("prose", ""))
    return Decoded("TYPED_SOURCE", typed, prose, divergence=_divergence(typed, prose))


def _divergence(typed: bs.BindingConstraint, prose: str) -> tuple[str, ...]:
    """What the prose fails to say, or says differently, versus the typed source.

    Uses the R1 lenient reader deliberately: it is the reader that *would* have
    been fooled. Its disagreement with the typed source is the drift signal.
    """
    # The R1 reader is case-sensitive; "MUST" in capitals fell straight through
    # it and the strengthening went unflagged. Enforcement was never affected
    # (typed wins regardless), but a drift detector with a case blind spot is a
    # drift detector that lies by omission. Normalize before reading.
    normalized = prose
    for loud, quiet in (("MUST", "must"), ("SHOULD", "should"),
                        ("Must", "must"), ("Should", "should")):
        normalized = normalized.replace(loud, quiet)
    try:
        reconstructed = bs.parse_prose(normalized, typed, strict=False)
    except Exception:
        return ("unparseable-prose",)
    return bs.measure_retention(typed, reconstructed).changed_fields


# --------------------------------------------------------------------------
# Enforcement — reads typed only
# --------------------------------------------------------------------------

def evaluate_from_content(
    content: str, action: bs.ProposedAction, window: tuple[int, int]
) -> tuple[bs.ActionOutcome, dict[str, str]]:
    """The repaired operational path: content -> typed -> R1's real gates.

    A record whose binding cannot be read as typed data cannot license anything.
    DEFER is Γ's word for "consequential and ambiguous"; it is never ALLOW.
    """
    decoded = decode_envelope(content)
    if decoded.kind != "TYPED_SOURCE":
        return "DEFER", {"source": decoded.kind, "reason": decoded.reason}
    assert decoded.typed is not None
    outcome, trace = bs.evaluate_action(decoded.typed, action, window)
    trace["source"] = "TYPED_SOURCE"
    if decoded.divergence:
        trace["prose_divergence"] = ",".join(decoded.divergence)
    return outcome, trace


# --------------------------------------------------------------------------
# Repaired transforms — the same pipeline shapes as R1, carrier changed
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class EnvelopeTransform:
    """A transform over envelope *content*, so prose and typed travel together."""

    name: str
    kind: bs.PathKind
    apply: Callable[[str], str]


def _record(content: str, record_id: str) -> MemoryRecord:
    return MemoryRecord(
        id=record_id, kind="semantic", created_at="2026-09-11T00:00:00+00:00",
        content=content,
        source=ProvenanceRef("binding-repair-r1", "experiment",
                             sha256(content.encode()).hexdigest()),
        authority=AuthorityProvenance("none", ()),   # memory carries no authority
        epistemic_status="observed", schema_version=1, derived_from=(),
        supersedes=None, conflicts_with=(), visibility=("project",),
        retention="session", revoked=False,
    )


def lossy_prose(content: str, keep_sentences: int) -> str:
    """The summariser, repaired: it may shorten the PROSE. It never touches typed."""
    decoded = decode_envelope(content)
    doc = json.loads(content)
    sentences = [s for s in decoded.prose.split(". ") if s.strip()]
    doc["prose"] = ". ".join(sentences[:keep_sentences]).rstrip(".") + "."
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))


def make_lossy_summary(keep_sentences: int) -> EnvelopeTransform:
    return EnvelopeTransform(f"R_T3_lossy{keep_sentences}", "EXPERIMENTAL_TRANSFORM_FIXTURE",
                             lambda content: lossy_prose(content, keep_sentences))


def make_memory_roundtrip(directory: Path) -> EnvelopeTransform:
    counter = {"n": 0}

    def apply(content: str) -> str:
        counter["n"] += 1
        store = MemoryStore(directory / f"r-t2-{counter['n']}")
        stored = store.append(_record(content, f"env-{counter['n']}"))
        fetched = store.fetch(stored.id)
        assert fetched is not None
        return fetched.content

    return EnvelopeTransform("R_T2_memory_roundtrip", "REAL_REPO_PATH", apply)


def make_projection(directory: Path) -> EnvelopeTransform:
    counter = {"n": 0}

    def apply(content: str) -> str:
        counter["n"] += 1
        store = MemoryStore(directory / f"r-t5-{counter['n']}")
        stored = store.append(_record(content, f"envp-{counter['n']}"))
        contract = bs._base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        scope = ScopeDecision("ALLOW", contract, scope_digest(contract))
        projection = MemoryFactory(store).project(
            (stored.id,), purpose="binding-repair handoff", audience="project",
            valid_until="2026-12-01T00:00:00+00:00", scope=scope)
        payload = json.loads(projection.content)
        sources = payload["sources"] if "sources" in payload else payload
        first = sources[0] if isinstance(sources, list) else next(iter(sources.values()))
        return first["content"]

    return EnvelopeTransform("R_T5_projection_handoff", "REAL_REPO_PATH", apply)


def chain(name: str, *steps: EnvelopeTransform) -> EnvelopeTransform:
    kind: bs.PathKind = "REAL_REPO_PATH" if all(
        s.kind == "REAL_REPO_PATH" for s in steps) else "EXPERIMENTAL_TRANSFORM_FIXTURE"

    def apply(content: str) -> str:
        for step in steps:
            content = step.apply(content)
        return content

    return EnvelopeTransform(name, kind, apply)


# --------------------------------------------------------------------------
# Matrix over the repaired pipeline
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RepairCase:
    constraint_id: str
    constraint_class: str
    transform: str
    path_kind: bs.PathKind
    source_kind: SourceKind
    retention: bs.Retention | None
    divergence: tuple[str, ...]
    violating_expected: bs.ActionOutcome
    violating_observed: bs.ActionOutcome
    permitted_expected: bs.ActionOutcome
    permitted_observed: bs.ActionOutcome

    @property
    def false_allow(self) -> bool:
        return self.violating_expected != "ALLOW" and self.violating_observed == "ALLOW"

    @property
    def false_block(self) -> bool:
        return self.permitted_expected == "ALLOW" and self.permitted_observed != "ALLOW"


def run_matrix(transforms: list[EnvelopeTransform]) -> tuple[RepairCase, ...]:
    out: list[RepairCase] = []
    for fx in bs.fixtures():
        v_exp, _ = bs.evaluate_action(fx.constraint, fx.violating, fx.window)
        p_exp, _ = bs.evaluate_action(fx.constraint, fx.permitted, fx.window)
        for tf in transforms:
            content = tf.apply(encode_envelope(fx.constraint))
            decoded = decode_envelope(content)
            retention = (bs.measure_retention(fx.constraint, decoded.typed)
                         if decoded.typed is not None else None)
            v_obs, _ = evaluate_from_content(content, fx.violating, fx.window)
            p_obs, _ = evaluate_from_content(content, fx.permitted, fx.window)
            out.append(RepairCase(
                fx.constraint.constraint_id, fx.constraint.constraint_class,
                tf.name, tf.kind, decoded.kind, retention, decoded.divergence,
                v_exp, v_obs, p_exp, p_obs))
    return tuple(out)
