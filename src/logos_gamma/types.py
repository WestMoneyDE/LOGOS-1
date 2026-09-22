"""Typed surface Γ evaluates.

Γ evaluates a bounded *proposal*, never the full latent state (`GAMMA.md`,
Γ-Surface). Everything here is frozen: the trusted core holds no mutable state.

These types are deliberately independent of `logos_memory`. Γ must not import the
memory subsystem, because that would make adaptive memory a structural dependency
of the authority gate and contradict Γ-12 (`AssuranceState != AgentMemory`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping

Result = Literal["VALID", "INVALID", "UNCLEAR"]

#: Origins that may carry authority. Γ-1: authority is external and human-rooted.
AUTHORITY_BEARING_ORIGINS = frozenset({"human"})

#: Origins that exist in the system but can never create authority.
NON_AUTHORITY_ORIGINS = frozenset(
    {"memory", "model", "tool", "summary", "derived", "retrieval", "self-report", "unknown"}
)

#: Γ-2 constitutionally forbidden effect classes. Deliberately incomplete as a
#: taxonomy of harm; unknown effect kinds are denied until classified.
CONSTITUTIONALLY_FORBIDDEN = frozenset(
    {
        "physical-harm",
        "coercion",
        "unauthorized-access",
        "credential-exfiltration",
        "safety-removal",
        "authority-self-grant",
        "action-concealment",
        "shutdown-resistance",
        "unbounded-self-replication",
    }
)

#: Γ-23 plasticity ladder, ordered by what a change can destroy. `residual` sits
#: between memory and mechanism: a reversible adapter around a frozen model changes
#: behaviour and can still be versioned, inspected and rolled back.
PLASTICITY_LADDER: tuple[str, ...] = ("none", "state", "memory", "residual", "mechanism", "deployment")

#: Γ-19 registry of agent output contracts Γ will accept a proposal under.
KNOWN_OUTPUT_CONTRACTS = frozenset({"logos-agent-output/1"})

#: Γ0 canonical effect registry. An effect kind outside this set fails closed.
KNOWN_EFFECT_KINDS = frozenset(
    {
        "read-internal",
        "compute",
        "write-internal",
        "write-memory",
        "network-read",
        "network-write",
        "filesystem-write",
        "process-control",
        "audit-write",
        "message-send",
        "financial-transfer",
        "deployment",
    }
    | CONSTITUTIONALLY_FORBIDDEN
)

#: Γ-18 advisory vocabulary. Deliberately without an "ALLOW": a statistical
#: component may refuse, may ask for caution, may say nothing — never permit.
ADVISORY_VOTES = frozenset({"ABSTAIN", "TIGHTEN", "REFUSE"})

Externality = Literal["internal", "external"]
Reversibility = Literal["reversible", "partially-reversible", "irreversible"]


@dataclass(frozen=True)
class ProvenanceClaim:
    """Where a piece of supporting content came from.

    `origin` is Γ-owned classification, not an agent claim.
    """

    ref: str
    origin: str
    content_digest: str
    #: Γ-16: the tick at which this content entered the agent's context, when the
    #: surrounding system records it. `None` means "not recorded", which Γ-16 treats
    #: as unknown rather than as timely.
    ingested_at_tick: int | None = None

    def is_authority_bearing(self) -> bool:
        return self.origin in AUTHORITY_BEARING_ORIGINS


@dataclass(frozen=True)
class AuthorityEvidence:
    """A grant. Γ reads these; Γ never constructs one from anything else.

    Γ-3: an external one-way effect requires an exact, expiring, human-rooted
    approval bound to the canonical proposal digest.
    Γ-10: a grant authorises one defined causal occurrence.
    Γ-15: a grant may bind numeric parameters, not only the action name.
    Γ-16: a grant may state how far in time its approval of evidence reached.
    Γ-17: a grant may record who issued it, so self-approval becomes detectable.
    """

    grant_id: str
    origin: str
    bound_proposal_digest: str
    bound_scope_digest: str
    bound_state_hash: str
    issued_at_tick: int
    expires_tick: int
    max_occurrences: int = 1
    consumed_occurrences: int = 0
    #: Chain of transformations this evidence passed through, oldest first.
    #: Any non-empty transformation chain means the evidence was re-represented.
    transformation_chain: tuple[str, ...] = ()
    #: Γ-15: closed numeric intervals the approval covers, `name -> (low, high)`.
    #: Empty means the grant carries no magnitude, and Γ-15 constrains nothing —
    #: every grant written before this field keeps its exact previous meaning.
    bounds: Mapping[str, tuple[float, float]] = field(default_factory=dict)
    #: Γ-16: the latest evidence ingestion tick this approval was given over.
    #: `None` means the approver stated no cutoff, and Γ-16 constrains nothing.
    evidence_cutoff_tick: int | None = None
    #: Γ-23: the strongest plasticity class this approval covers. `None` means the
    #: approver stated none, which covers `none` only.
    covers_plasticity: str | None = None
    #: Γ-20: how many consequential executions this approval permits in its scope.
    #: `None` states no budget and leaves Γ-20 inactive.
    scope_budget: int | None = None
    #: Γ-17: the principal that issued this approval, when the store records it.
    #: `None` leaves Γ-17 inactive — Γ will not invent an approver.
    issued_by: str | None = None

    def is_human_rooted(self) -> bool:
        return self.origin in AUTHORITY_BEARING_ORIGINS

    def is_live(self, tick: int) -> bool:
        """Half-open validity interval: `issued_at_tick <= tick < expires_tick`."""
        return self.issued_at_tick <= tick < self.expires_tick

    def has_remaining_occurrence(self) -> bool:
        return self.consumed_occurrences < self.max_occurrences


@dataclass(frozen=True)
class EffectProposal:
    """The bounded representation Γ evaluates.

    Agent-declared `declared_*` fields are untrusted. Γ-4: an agent claim may
    tighten the gate but can never weaken Γ's own classification.
    """

    action: str
    target: str
    effect_kind: str
    externality: Externality
    reversibility: Reversibility
    proposal_digest: str
    parameters: Mapping[str, object] = field(default_factory=dict)
    provenance: tuple[ProvenanceClaim, ...] = ()
    #: Untrusted agent self-assessment.
    declared_externality: Externality | None = None
    declared_reversibility: Reversibility | None = None
    #: Set when the agent asserts it may act. Never sufficient (Γ-1).
    self_claimed_authority: bool = False
    #: Γ-17: the principal that raised this proposal, when the caller records it.
    proposed_by: str | None = None
    #: Γ-19: the agent output contract this proposal was parsed under, when it came
    #: from an agent at all. `None` means it did not.
    contract_version: str | None = None
    #: Γ-23: the strongest plasticity class this proposal touches.
    plasticity: str = "none"
    #: Set when the proposal would resist or defer a shutdown request (Γ-5).
    resists_shutdown: bool = False
    #: Set when the proposal is justified by self-continuity (Γ-6).
    self_preservation_motivated: bool = False

    def is_consequential(self) -> bool:
        return self.externality == "external" or self.reversibility != "reversible"


@dataclass(frozen=True)
class ValidationContext:
    """Everything Γ is allowed to read for one decision."""

    proposal: EffectProposal
    tick: int
    state_hash: str
    scope_digest: str
    authority: AuthorityEvidence | None = None
    #: Occurrences of this exact proposal digest already executed.
    prior_executions: int = 0
    #: True when a prior execution's outcome is unresolved (Γ-11).
    outcome_unknown: bool = False
    #: Γ-20: consequential executions already recorded in this scope.
    scope_consumed: int = 0
    #: Γ-21: steps in this scope whose outcome is recorded as unresolved.
    pending_compensations: tuple[str, ...] = ()
    #: Γ-22: reference binding this decision to its audit record.
    receipt_ref: str | None = None
    #: Γ-22: whether this deployment requires receipts. Default `False`, so a
    #: deployment that has not adopted receipting keeps its exact previous verdicts;
    #: turning it on makes an unreceipted consequential admission UNCLEAR.
    receipts_required: bool = False
    #: Γ-18: votes from statistical components, as `(source, vote)` pairs. Their
    #: vocabulary has no "ALLOW"; see `ADVISORY_VOTES`.
    advisories: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class DecisionToken:
    """A verdict bound to the exact situation that produced it.

    Γ answers a question about one `ValidationContext`. Between that answer and the
    execution, the world can move: an argument is rewritten, a dependency changes, the
    resolved target is not the one that was judged. A boolean `approved = True` does
    not survive that; it says an approval happened, not what it was for.

    The token carries the identity of the judged situation and of the rule set that
    judged it. `redeem` recomputes both and refuses on any difference — so an approval
    is a capability for exactly one state-action pair, not a standing right to act.
    """

    proposal_digest: str
    scope_digest: str
    state_hash: str
    tick: int
    context_digest: str
    invariant_set_digest: str
    result: Result


@dataclass(frozen=True)
class Finding:
    invariant_id: str
    clause: str
    result: Result
    reason: str


@dataclass(frozen=True)
class GammaVerdict:
    """Aggregate result. `VALID` alone admits a consequential proposal."""

    result: Result
    findings: tuple[Finding, ...]

    @property
    def failures(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.result == "INVALID")

    @property
    def ambiguities(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.result == "UNCLEAR")

    def admits(self) -> bool:
        """Fail closed: only an unambiguous VALID admits anything."""
        return self.result == "VALID"
