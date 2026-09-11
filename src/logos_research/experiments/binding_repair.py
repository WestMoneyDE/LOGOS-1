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

SourceKind = Literal["TYPED_SOURCE", "LEGACY_UNTYPED", "INCOMPLETE", "UNKNOWN_VERSION"]


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
    typed_doc = doc.get("typed")
    if not isinstance(typed_doc, dict):
        return Decoded("INCOMPLETE", None, str(doc.get("prose", "")),
                       reason="envelope present but typed block missing")
    try:
        typed = _typed_from_dict(typed_doc)
    except Exception as exc:  # malformed typed block is INCOMPLETE, never permissive
        return Decoded("INCOMPLETE", None, str(doc.get("prose", "")),
                       reason=f"typed block malformed: {type(exc).__name__}")
    if doc.get("typed_digest") != typed.digest():
        return Decoded("INCOMPLETE", None, str(doc.get("prose", "")),
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
