"""Proposed state decomposition — typed schemas (Phase 6; status PROPOSED, POST_INFERENCE_SPEC).

Ten state kinds that are kept apart because they are different things, even
where they correlate:

    EvidenceState · BeliefState · PlanState · ExecutionState · ObservedWorldState · PredictedWorldState ·
    CommandedWorldState · MemoryState · TrajectoryUncertaintyState · CausalProvenanceState

    Evidence != Belief != Plan != ExecutionState (RI-P5)
    WorldModelPrediction != WorldEvidence (RI-P6) · CommandIssued != ActionExecuted != IntendedOutcome (RI-P14)
    StepCalibration != TrajectoryCalibration (RI-P1) · Decodable != CausallyUsed (RI-P15) · BeliefState != Authority (RI-P18)

Nothing here is executed against a model. The update contracts are the
preregistrable part: they say which state may be written from which, and which
writes are forbidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field

STATE_KINDS: tuple[str, ...] = ("EvidenceState", "BeliefState", "PlanState", "ExecutionState", "ObservedWorldState", "PredictedWorldState", "CommandedWorldState",
                                "MemoryState", "TrajectoryUncertaintyState", "CausalProvenanceState")
CAUSAL_USE_STATUSES: tuple[str, ...] = ("UNKNOWN", "DECODABLE_ONLY", "CAUSALLY_USED", "NOT_USED")
#: allowed write directions (from -> to). Anything not listed is a forbidden write.
UPDATE_CONTRACT: frozenset[tuple[str, str]] = frozenset({
    ("EvidenceState", "BeliefState"), ("EvidenceState", "MemoryState"), ("MemoryState", "BeliefState"), ("BeliefState", "PlanState"), ("PlanState", "ExecutionState"),
    ("ExecutionState", "CommandedWorldState"), ("ObservedWorldState", "EvidenceState"), ("PredictedWorldState", "PlanState"),
    ("CausalProvenanceState", "BeliefState"), ("CausalProvenanceState", "PlanState"), ("TrajectoryUncertaintyState", "PlanState"),
})
FORBIDDEN_WRITES: tuple[tuple[str, str, str], ...] = (
    ("PlanState", "EvidenceState", "a plan never overwrites persistent evidence"),
    ("BeliefState", "EvidenceState", "belief never rewrites evidence retroactively"),
    ("PredictedWorldState", "ObservedWorldState", "a prediction is not an observation"),
    ("PredictedWorldState", "EvidenceState", "a prediction is not evidence"),
    ("CommandedWorldState", "ObservedWorldState", "a command is not an execution / observation"),
    ("BeliefState", "CausalProvenanceState", "belief cannot rewrite its own ancestry"),
)


def write_allowed(src: str, dst: str) -> bool:
    if src not in STATE_KINDS or dst not in STATE_KINDS:
        raise ValueError("unknown state kind")
    if any(s == src and d == dst for s, d, _ in FORBIDDEN_WRITES):
        return False
    return (src, dst) in UPDATE_CONTRACT


@dataclass(frozen=True)
class BeliefState:
    representation: str                    # opaque handle (e.g. a decoded direction id) — never authority
    evidence_refs: tuple[str, ...]
    update_id: str
    uncertainty: float
    provenance: tuple[str, ...]            # CausalProvenanceState node ids
    causal_use_status: str = "UNKNOWN"     # Decodable != CausallyUsed — set only by an intervention result

    def __post_init__(self) -> None:
        if self.causal_use_status not in CAUSAL_USE_STATUSES:
            raise ValueError("causal_use_status")
        if not (0.0 <= self.uncertainty <= 1.0):
            raise ValueError("uncertainty in [0, 1]")


@dataclass(frozen=True)
class TrajectoryUncertainty:
    """U_local(t), U_state(t), U_trajectory(1:t). The update contract: U_trajectory is never
    computed from U_local alone; it accumulates over the trajectory and is bounded below by
    the largest step uncertainty that fed the current state."""
    u_local: tuple[float, ...]
    u_state: tuple[float, ...]
    u_trajectory: tuple[float, ...]

    def __post_init__(self) -> None:
        n = len(self.u_local)
        if not (len(self.u_state) == len(self.u_trajectory) == n):
            raise ValueError("misaligned uncertainty series")
        for t in range(n):
            if not (0.0 <= self.u_local[t] <= 1.0 and 0.0 <= self.u_state[t] <= 1.0 and 0.0 <= self.u_trajectory[t] <= 1.0):
                raise ValueError("uncertainty in [0, 1]")
            if self.u_trajectory[t] + 1e-12 < max(self.u_local[: t + 1]):
                raise ValueError(f"U_trajectory({t}) below the maximum step uncertainty so far: LocalConfidence != TrajectoryConfidence")
            if t and self.u_trajectory[t] + 1e-12 < self.u_trajectory[t - 1]:
                raise ValueError("U_trajectory is non-decreasing along a trajectory without new evidence")


def accumulate(u_local: list[float], u_state: list[float]) -> TrajectoryUncertainty:
    """Reference update: U_trajectory(t) = 1 - prod(1 - max(U_local(i), U_state(i)))."""
    traj = []; p = 1.0
    for l, s in zip(u_local, u_state):
        p *= 1.0 - max(l, s); traj.append(1.0 - p)
    return TrajectoryUncertainty(tuple(u_local), tuple(u_state), tuple(traj))


@dataclass(frozen=True)
class WorldStateTriple:
    commanded: dict
    executed: dict | None
    observed: dict | None

    @property
    def committed(self) -> bool:
        """No consequential world action is committed because a command was issued."""
        return self.executed is not None and self.observed is not None and self.observed == self.executed

    @property
    def agreement(self) -> dict:
        return {"command_executed": self.executed is not None and self.executed == self.commanded,
                "execution_observed": self.observed is not None and self.observed == self.executed,
                "intended_outcome": self.observed is not None and self.observed == self.commanded}


MEMORY_TAXONOMY: dict[str, dict] = {
    "ExplicitEpisodicMemory": {"maintained_by": "PassivePersistence", "read_class": "READ", "example": "logos_memory records", "authority": "never"},
    "DynamicRecurrentState": {"maintained_by": "ActiveRehearsal (recurrent dynamics)", "read_class": "n/a (state, not store)", "example": "BDH-class hidden state (RD-01, RD-13)", "authority": "never"},
    "ReconsolidatingMemory": {"maintained_by": "SemanticRenewal on retrieval", "read_class": "READ_WITH_RECONSOLIDATION (write-class)", "example": "Phase-4 MemoryGraph system C", "authority": "never"},
    "WorkingMemory": {"maintained_by": "ActiveRehearsal within an execution", "read_class": "READ", "example": "ExecutionState scratch", "authority": "never"},
    "PlanState": {"maintained_by": "PeriodicPlanning", "read_class": "READ", "example": "PlanState (never overwrites evidence)", "authority": "never"},
    "ExternalizedEnvironmentPrior": {"maintained_by": "ExternalRetrieval / EnvironmentStudy", "read_class": "READ", "example": "environment study artifacts (RD-03)", "authority": "never"},
    "DynamicallyMaintainedMemory": {"maintained_by": "HistoryDependentDynamicalState (proposed class)", "read_class": "n/a", "example": "cognitive field networks (RD-13)", "authority": "never"},
}
