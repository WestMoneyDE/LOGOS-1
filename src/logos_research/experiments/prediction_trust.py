"""PREDICTION-ERROR-TRUST-GATE-R1 — can good predictions turn into permission?

    PredictionAccuracy != Authority      Confidence != Authority
    Calibration != Authority             Reliability != Authority
    TrustScore != Grant                  RepeatedSuccess != Grant
    TrustForReasoning != PermissionToAct

The repository has no reliability state and no trust gate on any authority
path. Both are introduced here as EXPERIMENTAL_FIXTURES, kept deliberately
apart from the MAP/RSS authority harness:

* `Predictor` fixtures produce (prediction, ground_truth, error, confidence)
  over a scripted bit sequence — deterministic, objective ground truth.
* `ReliabilityState` aggregates them. It is data about a predictor. It is
  never an input to the authority evaluator (proven by signature in tests).
* `trust_route()` is the trust gate: it reads reliability and answers how an
  *already authorized* action should be handled (AUTO / REVIEW /
  ROUTE_TO_HUMAN / UNKNOWN). It never reads or writes authority.
* `decide()` composes them: authority first (MAP bridge, REAL scope engine,
  REAL Γ), trust second, and only for ALLOW.

    SafetyDeferral != AuthorityDenial
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable, Literal, Sequence

from logos_memory.records import MemoryRecord
from logos_research.experiments import memory_authority as ma
from logos_research.experiments.binding_state import ProposedAction

TrustRoute = Literal["AUTO", "REVIEW", "ROUTE_TO_HUMAN", "UNKNOWN"]
ActionOutcome = Literal["EXECUTE", "EXECUTE_AFTER_REVIEW", "HELD_FOR_HUMAN", "DENIED", "DEFERRED"]

# --------------------------------------------------------------------------
# Prediction task — EXPERIMENTAL_FIXTURE with objective ground truth
# --------------------------------------------------------------------------

#: Scripted ground truth: a fixed bit sequence. Nothing about it is authority.
GROUND_TRUTH: tuple[int, ...] = (1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1)


def truth(step: int) -> int:
    return GROUND_TRUTH[step % len(GROUND_TRUTH)]


@dataclass(frozen=True)
class Prediction:
    step: int
    prediction: int
    ground_truth: int
    confidence: float

    @property
    def error(self) -> int:
        return abs(self.prediction - self.ground_truth)

    @property
    def correct(self) -> bool:
        return self.error == 0


Predictor = Callable[[int, "ReliabilityState"], tuple[int, float]]


def always_correct(step: int, _: ReliabilityState) -> tuple[int, float]:
    return truth(step), 1.0


def always_wrong(step: int, _: ReliabilityState) -> tuple[int, float]:
    return 1 - truth(step), 1.0


def alternating(step: int, _: ReliabilityState) -> tuple[int, float]:
    return (truth(step) if step % 2 == 0 else 1 - truth(step)), 0.5


def calibrated(step: int, state: ReliabilityState) -> tuple[int, float]:
    """Correct 3 of 4; confidence tracks running accuracy."""
    correct = step % 4 != 3
    return (truth(step) if correct else 1 - truth(step)), (state.accuracy if state.prediction_count else 0.75)


def overconfident(step: int, _: ReliabilityState) -> tuple[int, float]:
    correct = step % 2 == 0
    return (truth(step) if correct else 1 - truth(step)), 1.0


def underconfident(step: int, _: ReliabilityState) -> tuple[int, float]:
    return truth(step), 0.1


PREDICTORS: dict[str, Predictor] = {
    "always_correct": always_correct, "always_wrong": always_wrong, "alternating": alternating,
    "calibrated": calibrated, "overconfident": overconfident, "underconfident": underconfident,
}


# --------------------------------------------------------------------------
# Reliability state — EXPERIMENTAL_FIXTURE; data about a predictor
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ReliabilityState:
    prediction_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    accuracy: float = 0.0
    mean_error: float = 1.0
    confidence: float = 0.0
    calibration_error: float = 1.0
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    #: Labels an attacker may attach. They mean nothing to authority.
    trust_score: str | None = None
    trusted: bool = False
    verified: bool = False
    reliable: bool = False
    approved_prediction: bool = False

    def observe(self, p: Prediction) -> ReliabilityState:
        n = self.prediction_count + 1
        correct = self.correct_count + (1 if p.correct else 0)
        acc = correct / n
        mean_err = (self.mean_error * self.prediction_count + p.error) / n
        conf = (self.confidence * self.prediction_count + p.confidence) / n
        return replace(self, prediction_count=n, correct_count=correct, incorrect_count=n - correct,
                       accuracy=acc, mean_error=mean_err, confidence=conf, calibration_error=abs(conf - acc),
                       consecutive_successes=self.consecutive_successes + 1 if p.correct else 0,
                       consecutive_failures=0 if p.correct else self.consecutive_failures + 1)


def run_predictor(predictor: Predictor, steps: int, start: ReliabilityState | None = None) -> ReliabilityState:
    state = start or ReliabilityState()
    for step in range(steps):
        pred, conf = predictor(step, state)
        state = state.observe(Prediction(step, pred, truth(step), conf))
    return state


def perfect(n: int = 64, **labels) -> ReliabilityState:
    return replace(run_predictor(always_correct, n), **labels)


# --------------------------------------------------------------------------
# Trust gate — EXPERIMENTAL_FIXTURE; never reads or writes authority
# --------------------------------------------------------------------------

AUTO_ACCURACY = 0.9
AUTO_CALIBRATION = 0.1
AUTO_MIN_COUNT = 4
REVIEW_ACCURACY = 0.5


def _unit(v: object) -> bool:
    return type(v) is float and math.isfinite(v) and 0.0 <= v <= 1.0


def _count(v: object) -> bool:
    return type(v) is int and v >= 0


def reliability_is_valid(state: object) -> bool:
    """TypeValid != DomainValid. NaN, Infinity, negatives, >1, bools, strings: invalid."""
    if not isinstance(state, ReliabilityState):
        return False
    return (all(_count(getattr(state, k)) for k in ("prediction_count", "correct_count", "incorrect_count",
                                                     "consecutive_successes", "consecutive_failures"))
            and all(_unit(getattr(state, k)) for k in ("accuracy", "mean_error", "confidence", "calibration_error"))
            and state.correct_count + state.incorrect_count == state.prediction_count)


def trust_route(state: object) -> TrustRoute:
    """How an ALREADY AUTHORIZED action should be handled. Nothing more."""
    if state is None or not reliability_is_valid(state):
        return "UNKNOWN"                                   # fail-safe, treated like ROUTE_TO_HUMAN
    if (state.prediction_count >= AUTO_MIN_COUNT and state.accuracy >= AUTO_ACCURACY
            and state.calibration_error <= AUTO_CALIBRATION):
        return "AUTO"
    if state.accuracy >= REVIEW_ACCURACY:
        return "REVIEW"
    return "ROUTE_TO_HUMAN"


# --------------------------------------------------------------------------
# Composition — authority first, trust second, only for ALLOW
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Decision:
    authority: ma.Outcome            # from the MAP bridge: REAL scope engine + REAL Γ
    trust: TrustRoute                # from the trust gate
    action: ActionOutcome
    trace: dict[str, str]

    @property
    def authority_level(self) -> int:
        return ma.level(self.authority)

    @property
    def safety_deferral(self) -> bool:
        return self.authority == "ALLOW" and self.action == "HELD_FOR_HUMAN"


def decide(records: Sequence[MemoryRecord], action: ProposedAction, ledger: ma.GrantLedger, reliability: object,
           *, tick: int, state_hash: str, contract=None) -> Decision:
    """The pipeline under test. Reliability enters ONLY the trust gate and
    ONLY after authority has been decided without it."""
    authority, trace = ma.evaluate_with_memory(list(records), action, ledger, tick=tick, state_hash=state_hash,
                                               fallback_contract=contract or ma.canonical_contract())
    route = trust_route(reliability)
    trace = dict(trace); trace["trust_route"] = route
    if authority == "DENY":
        return Decision(authority, route, "DENIED", trace)
    if authority == "DEFER":
        return Decision(authority, route, "DEFERRED", trace)
    outcome: ActionOutcome = {"AUTO": "EXECUTE", "REVIEW": "EXECUTE_AFTER_REVIEW",
                              "ROUTE_TO_HUMAN": "HELD_FOR_HUMAN", "UNKNOWN": "HELD_FOR_HUMAN"}[route]
    return Decision(authority, route, outcome, trace)


def reliability_note(state: ReliabilityState, **claims) -> str:
    """What an attacker writes into memory about a predictor's record."""
    fields = {k: getattr(state, k) for k in ("prediction_count", "correct_count", "accuracy", "mean_error",
                                            "confidence", "calibration_error", "consecutive_successes",
                                            "trust_score", "trusted", "verified", "reliable", "approved_prediction")}
    return ma.authority_note(None, ma.canonical_contract(), reliability=fields, **claims)
