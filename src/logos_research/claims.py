"""Claim/evidence registry, negative-result registry and failure attribution.

Three concerns that share one rule: a record may never be quietly improved.

* A claim's status must be backed by referenced evidence, and a causal status must
  reference an intervention.
* A falsified hypothesis stays discoverable. Deleting or rewriting it is the
  failure mode this registry exists to prevent.
* A failure is attributed *before* anything learns from it. Not every failure is a
  reason to update memory or a skill.

Statuses reuse the repository's existing claim vocabulary from `CAPABILITIES.md`
and the master work order rather than introducing a new taxonomy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Literal, Sequence

ClaimStatus = Literal[
    "SPECULATIVE",
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "REPLICATED",
    "CAUSALLY_SUPPORTED",
    "CHALLENGED",
    "FALSIFIED",
    "INCONCLUSIVE",
]

CLAIM_STATUSES: tuple[ClaimStatus, ...] = (
    "SPECULATIVE",
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "REPLICATED",
    "CAUSALLY_SUPPORTED",
    "CHALLENGED",
    "FALSIFIED",
    "INCONCLUSIVE",
)

#: Statuses that assert positive support and therefore require evidence.
EVIDENCE_BEARING = frozenset(
    {"SUPPORTED", "PARTIALLY_SUPPORTED", "REPLICATED", "CAUSALLY_SUPPORTED"}
)

#: Section 29 failure attribution classes.
FailureSource = Literal[
    "MODEL", "PROMPT", "MEMORY", "STATE", "WORLD_MODEL", "TOOL", "SANDBOX",
    "NETWORK", "AUTHORITY", "ORCHESTRATOR", "DATASET", "MEASUREMENT", "HUMAN",
    "UNKNOWN",
]

FAILURE_SOURCES: tuple[FailureSource, ...] = (
    "MODEL", "PROMPT", "MEMORY", "STATE", "WORLD_MODEL", "TOOL", "SANDBOX",
    "NETWORK", "AUTHORITY", "ORCHESTRATOR", "DATASET", "MEASUREMENT", "HUMAN",
    "UNKNOWN",
)

#: Attributions that must never drive a durable memory or skill update.
#: A tool timeout teaches nothing about the world; a broken evaluator teaches
#: nothing about the hypothesis.
NON_LEARNABLE_SOURCES = frozenset(
    {"SANDBOX", "NETWORK", "TOOL", "ORCHESTRATOR", "MEASUREMENT", "UNKNOWN"}
)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim: str
    status: ClaimStatus
    scope: str = ""
    supporting_evidence: tuple[str, ...] = ()
    counterevidence: tuple[str, ...] = ()
    experiments: tuple[str, ...] = ()
    interventions: tuple[str, ...] = ()
    replications: int = 0
    known_confounders: tuple[str, ...] = ()
    confidence: str = ""
    last_reviewed: str = ""

    def problems(self) -> tuple[str, ...]:
        issues: list[str] = []
        if self.status in EVIDENCE_BEARING and not self.supporting_evidence:
            issues.append(
                f"status {self.status} asserted with no supporting evidence"
            )
        if self.status == "CAUSALLY_SUPPORTED" and not self.interventions:
            issues.append(
                "CAUSALLY_SUPPORTED asserted without an intervention; "
                "observation is not explanation"
            )
        if self.status == "REPLICATED" and self.replications < 2:
            issues.append(
                f"REPLICATED asserted with {self.replications} replication(s)"
            )
        if self.counterevidence and self.status in {"SUPPORTED", "REPLICATED",
                                                    "CAUSALLY_SUPPORTED"}:
            issues.append(
                "counterevidence exists but the status does not reflect it; "
                "consider CHALLENGED or PARTIALLY_SUPPORTED"
            )
        return tuple(issues)

    def to_gamma_payload(self) -> dict:
        return {
            "claim": self.claim,
            "status": self.status,
            "evidence": list(self.supporting_evidence),
            "interventions": list(self.interventions),
        }


@dataclass(frozen=True)
class NegativeResult:
    """A falsified hypothesis. Append-only by contract.

    `retest_justified` is a judgement that must be argued, not a default. A
    negative result is a research artifact, not a failure to be tidied away.
    """

    negative_id: str
    hypothesis: str
    how_tested: str
    what_falsified_it: str
    scope_of_falsification: str
    known_confounders: tuple[str, ...] = ()
    retest_justified: bool = False
    retest_rationale: str = ""
    experiments: tuple[str, ...] = ()
    recorded_at: str = ""

    def problems(self) -> tuple[str, ...]:
        issues = [
            f"missing {name}"
            for name in ("hypothesis", "how_tested", "what_falsified_it",
                         "scope_of_falsification")
            if not getattr(self, name)
        ]
        if self.retest_justified and not self.retest_rationale:
            issues.append("retest_justified requires a rationale")
        return tuple(issues)


@dataclass(frozen=True)
class FailureAttribution:
    """`Failure -> Attribution -> ScopedLearning`, in that order."""

    failure_id: str
    source: FailureSource
    evidence: str
    scope: str = ""
    #: Whether this failure may inform a durable update.
    learning_permitted: bool = False

    def __post_init__(self) -> None:
        if self.learning_permitted and self.source in NON_LEARNABLE_SOURCES:
            raise ValueError(
                f"failure attributed to {self.source} may not drive durable learning: "
                "infrastructure failure is not evidence about the hypothesis"
            )

    def problems(self) -> tuple[str, ...]:
        issues: list[str] = []
        if not self.evidence:
            issues.append("attribution without evidence is a guess")
        if self.source == "UNKNOWN" and self.learning_permitted:
            issues.append("UNKNOWN attribution cannot justify learning")
        return tuple(issues)


class ClaimRegistry:
    """In-memory registry. Persistence is the caller's concern.

    Deliberately not a database: this repository's canonical truth store is
    git-tracked files, and adding a second store would duplicate an existing
    canonical owner.
    """

    def __init__(self, claims: Sequence[Claim] = ()) -> None:
        self._claims: dict[str, Claim] = {}
        for claim in claims:
            self.add(claim)

    def add(self, claim: Claim) -> None:
        if claim.claim_id in self._claims:
            raise ValueError(f"duplicate claim id {claim.claim_id!r}")
        self._claims[claim.claim_id] = claim

    def get(self, claim_id: str) -> Claim:
        return self._claims[claim_id]

    def __len__(self) -> int:
        return len(self._claims)

    def __contains__(self, claim_id: object) -> bool:
        return claim_id in self._claims

    @property
    def claims(self) -> tuple[Claim, ...]:
        return tuple(self._claims[k] for k in sorted(self._claims))

    def audit(self) -> dict[str, tuple[str, ...]]:
        """Every claim whose status outruns its evidence."""
        return {c.claim_id: c.problems() for c in self.claims if c.problems()}

    def unsupported_statuses(self) -> tuple[str, ...]:
        return tuple(sorted(self.audit()))
