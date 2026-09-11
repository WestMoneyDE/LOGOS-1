"""BINDING-STATE-PRESERVATION-R1 — can a rule survive being represented differently?

The question is narrow and operational:

    Can a binding constraint pass through representation transformations
    without silently losing, gaining, or shifting its operational force?

```text
SemanticRetention != BindingRetention != AuthorityRetention != ActionOutcome
```

Ground truth is **typed**, never textual. A constraint is a repository-native
`ScopeContract` (24 typed dimensions) wrapped with the two things the contract
does not express: whether it is *binding* (a gate) or *advisory* (a preference),
and any *preconditions*. Wording may change freely. The action-level outcome
must not.

Every transformation path is labelled honestly:

```text
REAL_REPO_PATH                  the code the repository actually runs
EXPERIMENTAL_TRANSFORM_FIXTURE  built for this experiment; not production
```

No summariser, handoff bus, planner or executor exists in this repository. The
summary transform is therefore a fixture and is named as one. Memory write,
retrieval and projection are the real `logos_memory` implementation.

The primary experiment is deterministic and needs no model. No consequential
action is ever performed: `DELETE record_7` is a value passed to an evaluator.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Callable, Literal, Sequence

import logos_gamma as gamma
from logos_memory.factory import MemoryFactory
from logos_memory.records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from logos_memory.scope import ScopeContract, ScopeDecision, ScopeRequest, scope_digest
from logos_memory.store import MemoryStore

EXPERIMENT_ID = "BINDING-STATE-PRESERVATION-R1"

ConstraintClass = Literal[
    "PROHIBITION",          # A  MUST NOT act on target X
    "REQUIREMENT",          # B  MUST satisfy precondition Y before X
    "CONDITIONAL",          # C  X ONLY IF within a validity window
    "APPROVAL_REQUIRED",    # D  X requires a human-rooted grant
    "SCOPE_RESTRICTION",    # E  authority applies only to resource R
    "FRESHNESS",            # F  authority expires at T
]

PathKind = Literal["REAL_REPO_PATH", "EXPERIMENTAL_TRANSFORM_FIXTURE"]

#: Canonical decision vocabulary. `ALLOW`/`DENY` are the scope engine's own
#: words; `DEFER` is Γ's word for an ambiguous consequential proposal.
ActionOutcome = Literal["ALLOW", "DENY", "DEFER"]

#: Failure owners, Section 48 of the work order.
FailureOwner = Literal[
    "CONSTRAINT_SCHEMA", "SERIALIZATION", "SUMMARY_TRANSFORM", "MEMORY_WRITE",
    "MEMORY_RETRIEVAL", "HANDOFF", "AUTHORITY_MAPPING", "GAMMA_VALIDATION",
    "ACTION_EVALUATION", "MEASUREMENT", "INFRASTRUCTURE", "UNKNOWN",
]


# --------------------------------------------------------------------------
# Constraint — the typed ground truth
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class BindingConstraint:
    """A constraint whose binding force is typed, not worded.

    `contract` is the repository's own `ScopeContract`; nothing here duplicates
    it. The wrapper adds only what the contract cannot express:

    * `binding` — True is a gate (MUST / MUST NOT), False is advisory
      (SHOULD / SHOULD NOT). This is the single typed modality axis. Weakening
      is True→False; strengthening is False→True. Both are corruption when
      unauthorized.
    * `preconditions` — things that must hold before the action (class B),
      which the scope contract has no field for.
    * `authority_origin` — where the constraint's authority comes from. Only
      `human` is authority-bearing (Γ-1).
    """

    constraint_id: str
    constraint_class: ConstraintClass
    contract: ScopeContract
    binding: bool = True
    preconditions: tuple[str, ...] = ()
    authority_origin: str = "human"
    #: Set only on the negative control, where a normative change is deliberate.
    authorized_normative_change: bool = False

    def digest(self) -> str:
        return sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True)
class ProposedAction:
    """A simulated consequential action. It is a value, never performed."""

    action: str
    target: str
    role: str = "operator"
    tool: str = "execute"
    capability: str = "execute-action"
    path: str = "resources/production"
    tick: int = 12
    satisfied_preconditions: tuple[str, ...] = ()
    human_grant_present: bool = False


# --------------------------------------------------------------------------
# Fixtures — one per constraint class, plus the actions that conflict
# --------------------------------------------------------------------------

def _base_contract(**overrides) -> ScopeContract:
    base = ScopeContract(
        project="logos-1",
        paths=("resources/**",),
        excluded_paths=(),
        roles=("operator",),
        tools=("execute",),
        memory_kinds=("semantic",),
        projection_audiences=("project",),
        capabilities=("execute-action",),
        targets=("resource-A",),
        parameter_bounds=(),
        max_cost_usd=0.0,
        max_tokens=0,
        max_seconds=0,
        max_attempts=1,
        valid_from="2026-01-01T00:00:00+00:00",
        valid_until="2026-12-31T00:00:00+00:00",
        max_occurrences=1,
        externality="internal",
        reversibility="reversible",
        approval_required=False,
        data_classes=("project",),
        retention_classes=("session",),
        source_versions=("binding-r1@1",),
    )
    return replace(base, **overrides)


@dataclass(frozen=True)
class Fixture:
    constraint: BindingConstraint
    #: An action the constraint forbids. Expected DENY (or DEFER) while binding.
    violating: ProposedAction
    #: An action the constraint permits. Expected ALLOW. Guards FalseBlockRate.
    permitted: ProposedAction
    #: Ticks are the clock the scope contract's validity window is judged in.
    window: tuple[int, int] = (10, 20)


def fixtures() -> tuple[Fixture, ...]:
    """The preregistered constraint set. Deterministic; no randomness."""
    return (
        # A — hard prohibition: record_7 is not an allowed target.
        Fixture(
            BindingConstraint(
                "C-A-prohibition", "PROHIBITION",
                _base_contract(targets=("resource-A",)),
            ),
            violating=ProposedAction("DELETE", "record_7"),
            permitted=ProposedAction("DELETE", "resource-A"),
        ),
        # B — hard requirement: verification must precede execution.
        Fixture(
            BindingConstraint(
                "C-B-requirement", "REQUIREMENT",
                _base_contract(targets=("resource-A",)),
                preconditions=("verification-Y",),
            ),
            violating=ProposedAction("EXECUTE", "resource-A", satisfied_preconditions=()),
            permitted=ProposedAction("EXECUTE", "resource-A",
                                     satisfied_preconditions=("verification-Y",)),
        ),
        # C — conditional on a validity window (ticks 10..20 map to the window).
        Fixture(
            BindingConstraint(
                "C-C-conditional", "CONDITIONAL",
                _base_contract(targets=("resource-A",),
                               externality="external", reversibility="irreversible"),
            ),
            violating=ProposedAction("DEPLOY", "resource-A", tick=25, human_grant_present=True),
            permitted=ProposedAction("DEPLOY", "resource-A", tick=12, human_grant_present=True),
        ),
        # D — human approval prerequisite for an external irreversible action.
        Fixture(
            BindingConstraint(
                "C-D-approval", "APPROVAL_REQUIRED",
                _base_contract(targets=("resource-A",), approval_required=True,
                               externality="external", reversibility="irreversible"),
            ),
            violating=ProposedAction("TRANSFER", "resource-A", human_grant_present=False),
            permitted=ProposedAction("TRANSFER", "resource-A", human_grant_present=True),
        ),
        # E — scope restriction: only resource-A, never resource-B.
        Fixture(
            BindingConstraint(
                "C-E-scope", "SCOPE_RESTRICTION",
                _base_contract(targets=("resource-A",)),
            ),
            violating=ProposedAction("SEND", "resource-B"),
            permitted=ProposedAction("SEND", "resource-A"),
        ),
        # G — advisory baseline (SHOULD NOT). Its violating action is ALLOWED by
        # definition; it exists so that unauthorized STRENGTHENING has a subject.
        Fixture(
            BindingConstraint(
                "C-G-advisory", "PROHIBITION",
                _base_contract(targets=("resource-A",)),
                binding=False,
            ),
            violating=ProposedAction("DELETE", "record_7"),
            permitted=ProposedAction("DELETE", "resource-A"),
        ),
        # F — freshness: the grant expires; tick 20 is outside the half-open window.
        Fixture(
            BindingConstraint(
                "C-F-freshness", "FRESHNESS",
                _base_contract(targets=("resource-A",),
                               externality="external", reversibility="irreversible"),
            ),
            violating=ProposedAction("DISCLOSE", "resource-A", tick=20, human_grant_present=True),
            permitted=ProposedAction("DISCLOSE", "resource-A", tick=19, human_grant_present=True),
        ),
    )


# --------------------------------------------------------------------------
# Action evaluation — REAL_REPO_PATH: scope engine + Γ kernel
# --------------------------------------------------------------------------

STATE_HASH = "a" * 64


def _proposal_digest(action: ProposedAction) -> str:
    return sha256(f"{action.action}:{action.target}".encode()).hexdigest()


def evaluate_action(
    constraint: BindingConstraint, action: ProposedAction, window: tuple[int, int]
) -> tuple[ActionOutcome, dict[str, str]]:
    """Decide the action against the constraint using the repository's gates.

    Two real gates, both required for a binding constraint:

    * `ScopeDecision.evaluate()` — role, tool, memory kind, capability, target,
      path. This is the repository's own six-dimension precondition check.
    * `logos_gamma.validate()` — approval, freshness, authority origin.

    An advisory constraint does not gate. That is what "advisory" means, and it
    is precisely why an unauthorized MUST→SHOULD downgrade is dangerous: the
    same violating action stops being refused.
    """
    trace: dict[str, str] = {}
    if not constraint.binding:
        trace["binding"] = "advisory: constraint does not gate"
        return "ALLOW", trace

    contract = constraint.contract
    decision = ScopeDecision("ALLOW", contract, scope_digest(contract)).evaluate(
        ScopeRequest(role=action.role, tool=action.tool, memory_kind="semantic",
                     capability=action.capability, target=action.target, path=action.path)
    )
    trace["scope"] = decision.verdict
    if decision.verdict != "ALLOW":
        return "DENY", trace

    missing = tuple(p for p in constraint.preconditions
                    if p not in action.satisfied_preconditions)
    trace["preconditions_missing"] = ",".join(missing) or "none"
    if missing:
        return "DENY", trace

    proposal = gamma.EffectProposal(
        action=action.action, target=action.target,
        effect_kind="deployment" if contract.externality == "external" else "write-internal",
        externality=contract.externality,
        reversibility=contract.reversibility,
        proposal_digest=_proposal_digest(action),
        provenance=(gamma.ProvenanceClaim("constraint://" + constraint.constraint_id,
                                          constraint.authority_origin, constraint.digest()),),
    )
    authority = None
    if contract.approval_required or proposal.is_consequential():
        if action.human_grant_present:
            authority = gamma.AuthorityEvidence(
                grant_id=f"grant-{constraint.constraint_id}",
                origin=constraint.authority_origin,
                bound_proposal_digest=proposal.proposal_digest,
                bound_scope_digest=scope_digest(contract),
                bound_state_hash=STATE_HASH,
                issued_at_tick=window[0], expires_tick=window[1],
            )
    verdict = gamma.validate(gamma.ValidationContext(
        proposal=proposal, tick=action.tick, state_hash=STATE_HASH,
        scope_digest=scope_digest(contract), authority=authority))
    trace["gamma"] = verdict.result
    trace["gamma_failures"] = ",".join(f.invariant_id for f in verdict.failures) or "none"
    if verdict.result == "INVALID":
        return "DENY", trace
    if verdict.result == "UNCLEAR":
        return "DEFER", trace
    return "ALLOW", trace


# --------------------------------------------------------------------------
# Transformations
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Transform:
    name: str
    kind: PathKind
    apply: Callable[[BindingConstraint], BindingConstraint] = field(repr=False)


def _to_json(c: BindingConstraint) -> str:
    return json.dumps(asdict(c), sort_keys=True, separators=(",", ":"))


def _from_json(text: str) -> BindingConstraint:
    d = json.loads(text)
    contract = d.pop("contract")
    for key in ("paths", "excluded_paths", "roles", "tools", "memory_kinds",
                "projection_audiences", "capabilities", "targets", "data_classes",
                "retention_classes", "source_versions"):
        contract[key] = tuple(contract[key])
    contract["parameter_bounds"] = tuple(tuple(b) for b in contract["parameter_bounds"])
    d["preconditions"] = tuple(d["preconditions"])
    return BindingConstraint(contract=ScopeContract(**contract), **d)


def t_identity(c: BindingConstraint) -> BindingConstraint:
    return c


def t_serialize(c: BindingConstraint) -> BindingConstraint:
    """T1 — REAL: dataclass → JSON → dataclass. Expected lossless."""
    return _from_json(_to_json(c))


def _memory_record(c: BindingConstraint, record_id: str) -> MemoryRecord:
    return MemoryRecord(
        id=record_id, kind="semantic", created_at="2026-09-11T00:00:00+00:00",
        content=_to_json(c),
        source=ProvenanceRef("binding-r1", "experiment", sha256(_to_json(c).encode()).hexdigest()),
        authority=AuthorityProvenance("none", ()),   # memory carries no authority (Γ-12)
        epistemic_status="observed", schema_version=1, derived_from=(),
        supersedes=None, conflicts_with=(), visibility=("project",),
        retention="session", revoked=False,
    )


def make_memory_transform(directory: Path) -> Transform:
    """T2 — REAL: write into `logos_memory.MemoryStore`, fetch back, parse."""
    counter = {"n": 0}

    def apply(c: BindingConstraint) -> BindingConstraint:
        counter["n"] += 1
        store = MemoryStore(directory / f"t2-{counter['n']}")
        stored = store.append(_memory_record(c, f"mem-{counter['n']}"))
        fetched = store.fetch(stored.id)
        assert fetched is not None
        return _from_json(fetched.content)

    return Transform("T2_memory_roundtrip", "REAL_REPO_PATH", apply)


def make_projection_transform(directory: Path) -> Transform:
    """T5 — REAL: `MemoryFactory.project()` produces the handoff representation."""
    counter = {"n": 0}

    def apply(c: BindingConstraint) -> BindingConstraint:
        counter["n"] += 1
        store = MemoryStore(directory / f"t5-{counter['n']}")
        stored = store.append(_memory_record(c, f"proj-{counter['n']}"))
        scope_contract = _base_contract(memory_kinds=("semantic",),
                                        projection_audiences=("project",))
        scope = ScopeDecision("ALLOW", scope_contract, scope_digest(scope_contract))
        projection = MemoryFactory(store).project(
            (stored.id,), purpose="binding-r1 handoff", audience="project",
            valid_until="2026-12-01T00:00:00+00:00", scope=scope,
        )
        payload = json.loads(projection.content)
        sources = payload["sources"] if "sources" in payload else payload
        first = sources[0] if isinstance(sources, list) else next(iter(sources.values()))
        return _from_json(first["content"])

    return Transform("T5_projection_handoff", "REAL_REPO_PATH", apply)


# ---- summary fixture -------------------------------------------------------

def render_prose(c: BindingConstraint) -> str:
    """Deterministic natural-language rendering. A stand-in for a summariser."""
    k = c.contract
    force = "must" if c.binding else "should"
    lines = [f"Constraint {c.constraint_id} ({c.constraint_class.lower()})."]
    lines.append(f"Actions {force} target only: {', '.join(k.targets)}.")
    if k.approval_required:
        lines.append(f"Human approval {'is required' if c.binding else 'is recommended'}.")
    if c.preconditions:
        lines.append(f"Preconditions {force} hold first: {', '.join(c.preconditions)}.")
    lines.append(f"Valid {k.valid_from} to {k.valid_until}.")
    lines.append(f"Effect is {k.externality} and {k.reversibility}.")
    lines.append(f"Authority origin: {c.authority_origin}.")
    return " ".join(lines)


def parse_prose(text: str, template: BindingConstraint, *, strict: bool) -> BindingConstraint:
    """Recover typed fields from prose.

    `strict=True` fails closed: a field the prose does not state is an error.
    `strict=False` is the lenient reader most systems actually have — it fills
    a missing field from a default. That default is where binding goes to die.
    """
    m_targets = re.search(r"target only: ([^.]+)\.", text)
    m_force = re.search(r"Actions (must|should) target", text)
    m_approval = re.search(r"Human approval (is required|is recommended)", text)
    m_pre = re.search(r"Preconditions (?:must|should) hold first: ([^.]+)\.", text)
    m_valid = re.search(r"Valid (\S+) to (\S+)\.", text)
    m_origin = re.search(r"Authority origin: (\S+)\.", text)

    if strict and not (m_targets and m_force and m_valid and m_origin):
        raise ValueError("prose omits a typed field; refusing to guess")

    targets = tuple(t.strip() for t in m_targets.group(1).split(",")) if m_targets \
        else template.contract.targets
    binding = (m_force.group(1) == "must") if m_force else template.binding
    approval_required = (m_approval.group(1) == "is required") if m_approval else False
    preconditions = tuple(p.strip() for p in m_pre.group(1).split(",")) if m_pre else ()
    valid_from, valid_until = (m_valid.group(1), m_valid.group(2)) if m_valid \
        else (template.contract.valid_from, template.contract.valid_until)
    origin = m_origin.group(1) if m_origin else template.authority_origin

    return replace(
        template,
        binding=binding,
        preconditions=preconditions,
        authority_origin=origin,
        contract=replace(template.contract, targets=targets,
                         approval_required=approval_required,
                         valid_from=valid_from, valid_until=valid_until),
    )


def make_summary_transform(*, strict: bool) -> Transform:
    """T3 — FIXTURE: prose rendering and re-parse. No real summariser exists."""

    def apply(c: BindingConstraint) -> BindingConstraint:
        return parse_prose(render_prose(c), c, strict=strict)

    return Transform(f"T3_summary_{'strict' if strict else 'lenient'}",
                     "EXPERIMENTAL_TRANSFORM_FIXTURE", apply)


def make_lossy_summary_transform(*, keep_sentences: int, strict: bool) -> Transform:
    """T3-lossy — FIXTURE: a summariser that COMPRESSES.

    A complete rendering is a copy, not a summary. Real summaries drop things,
    and what they drop first is the qualifying clause: the approval sentence,
    the precondition sentence, the expiry. This transform keeps the first
    `keep_sentences` sentences of the rendering and discards the rest, then
    re-parses. Against a strict reader the loss is refused; against a lenient
    reader the missing field is filled from a default — and the default for
    "does this need approval?" is no.
    """

    def apply(c: BindingConstraint) -> BindingConstraint:
        sentences = [s for s in render_prose(c).split(". ") if s.strip()]
        compressed = ". ".join(sentences[:keep_sentences]).rstrip(".") + "."
        return parse_prose(compressed, c, strict=strict)

    return Transform(
        f"T3_lossy{keep_sentences}_{'strict' if strict else 'lenient'}",
        "EXPERIMENTAL_TRANSFORM_FIXTURE", apply,
    )


def chain(name: str, *steps: Transform) -> Transform:
    kind: PathKind = "REAL_REPO_PATH" if all(
        s.kind == "REAL_REPO_PATH" for s in steps) else "EXPERIMENTAL_TRANSFORM_FIXTURE"

    def apply(c: BindingConstraint) -> BindingConstraint:
        for step in steps:
            c = step.apply(c)
        return c

    return Transform(name, kind, apply)


# ---- adversarial mutations, Section 18 ----------------------------------------

def mutations() -> dict[str, Callable[[BindingConstraint], BindingConstraint]]:
    """Unauthorized normative changes. Every one must be detected."""
    return {
        "MUST_NOT->SHOULD_NOT": lambda c: replace(c, binding=False),
        "REQUIRES_APPROVAL->RECOMMENDED": lambda c: replace(
            c, contract=replace(c.contract, approval_required=False)),
        "ONLY_IF->PREFER_IF": lambda c: replace(c, preconditions=()),
        "ONLY_RESOURCE_A->A_PREFERRED": lambda c: replace(
            c, contract=replace(c.contract, targets=c.contract.targets + ("resource-B", "record_7"))),
        "EXPIRES_AT_T->INDEFINITE": lambda c: replace(
            c, contract=replace(c.contract, valid_until="2999-01-01T00:00:00+00:00")),
        "SHOULD_NOT->MUST_NOT (strengthening)": lambda c: replace(c, binding=True),
        "AUTHORITY_ORIGIN->model": lambda c: replace(c, authority_origin="model"),
    }


# --------------------------------------------------------------------------
# Instruments — typed, deterministic
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Retention:
    semantic: float          # secondary: token overlap of the prose renderings
    binding: bool            # primary: typed modality + gate-relevant fields equal
    authority: bool          # authority_origin equal
    changed_fields: tuple[str, ...]


def _gate_fields(c: BindingConstraint) -> dict[str, object]:
    k = c.contract
    return {
        "binding": c.binding,
        "targets": tuple(sorted(k.targets)),
        "approval_required": k.approval_required,
        "preconditions": tuple(sorted(c.preconditions)),
        "valid_from": k.valid_from,
        "valid_until": k.valid_until,
        "externality": k.externality,
        "reversibility": k.reversibility,
    }


def measure_retention(original: BindingConstraint, transformed: BindingConstraint) -> Retention:
    a, b = _gate_fields(original), _gate_fields(transformed)
    changed = tuple(k for k in a if a[k] != b[k])
    ta = set(re.findall(r"[a-z0-9_-]+", render_prose(original).lower()))
    tb = set(re.findall(r"[a-z0-9_-]+", render_prose(transformed).lower()))
    semantic = len(ta & tb) / len(ta | tb) if ta | tb else 1.0
    return Retention(
        semantic=round(semantic, 4),
        binding=not changed,
        authority=original.authority_origin == transformed.authority_origin,
        changed_fields=changed,
    )


# --------------------------------------------------------------------------
# Experiment
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CaseResult:
    constraint_id: str
    constraint_class: str
    transform: str
    path_kind: PathKind
    mutation: str
    retention: Retention
    violating_expected: ActionOutcome
    violating_observed: ActionOutcome
    permitted_expected: ActionOutcome
    permitted_observed: ActionOutcome
    transform_error: str = ""

    @property
    def false_allow(self) -> bool:
        return self.violating_expected != "ALLOW" and self.violating_observed == "ALLOW"

    @property
    def false_block(self) -> bool:
        return self.permitted_expected == "ALLOW" and self.permitted_observed != "ALLOW"


def run_matrix(transforms: Sequence[Transform], *, with_mutations: bool) -> tuple[CaseResult, ...]:
    """Every constraint × every transform (× every mutation when requested)."""
    results: list[CaseResult] = []
    for fx in fixtures():
        v_exp, _ = evaluate_action(fx.constraint, fx.violating, fx.window)
        p_exp, _ = evaluate_action(fx.constraint, fx.permitted, fx.window)
        muts = {"none": (lambda c: c)}
        if with_mutations:
            muts.update(mutations())
        for tf in transforms:
            for mut_name, mut in muts.items():
                start = mut(fx.constraint)
                if mut_name != "none" and start.digest() == fx.constraint.digest():
                    continue  # mutation is a no-op on this fixture; nothing to detect
                try:
                    out = tf.apply(start)
                    err = ""
                except Exception as exc:  # a strict parser refusing is a result, not a crash
                    out, err = start, f"{type(exc).__name__}: {exc}"
                v_obs, _ = evaluate_action(out, fx.violating, fx.window)
                p_obs, _ = evaluate_action(out, fx.permitted, fx.window)
                results.append(CaseResult(
                    fx.constraint.constraint_id, fx.constraint.constraint_class,
                    tf.name, tf.kind, mut_name,
                    measure_retention(fx.constraint, out),
                    v_exp, v_obs, p_exp, p_obs, err,
                ))
    return tuple(results)


def summarize(results: Sequence[CaseResult]) -> dict[str, object]:
    unmutated = [r for r in results if r.mutation == "none"]
    mutated = [r for r in results if r.mutation != "none"]
    return {
        "cases": len(results),
        "unmutated_cases": len(unmutated),
        "false_allow_unmutated": sum(r.false_allow for r in unmutated),
        "false_block_unmutated": sum(r.false_block for r in unmutated),
        "binding_retained_unmutated": sum(r.retention.binding for r in unmutated),
        "authority_retained_unmutated": sum(r.retention.authority for r in unmutated),
        "transform_errors": sum(bool(r.transform_error) for r in results),
        "mutations_detected": sum(
            (not r.retention.binding) or (not r.retention.authority) for r in mutated),
        "mutations_total": len(mutated),
        "by_transform": {
            tf: {
                "false_allow": sum(r.false_allow for r in unmutated if r.transform == tf),
                "binding_retained": sum(r.retention.binding for r in unmutated if r.transform == tf),
                "n": sum(1 for r in unmutated if r.transform == tf),
            }
            for tf in sorted({r.transform for r in results})
        },
    }
