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

    def is_authority_bearing(self) -> bool:
        return self.origin in AUTHORITY_BEARING_ORIGINS


@dataclass(frozen=True)
class AuthorityEvidence:
    """A grant. Γ reads these; Γ never constructs one from anything else.

    Γ-3: an external one-way effect requires an exact, expiring, human-rooted
    approval bound to the canonical proposal digest.
    Γ-10: a grant authorises one defined causal occurrence.
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
