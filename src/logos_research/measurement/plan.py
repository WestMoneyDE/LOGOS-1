"""Stochastic measurement plan and the executable INVALID_MEASUREMENT rules (Sections 14, 15).

    MeasurementOutcome.status ∈ {VALID, INVALID_MEASUREMENT, FALLBACK}

`FALLBACK` is the preregistered response to the cost cap: the run stops and
reports what it has, it never overruns. `INVALID_MEASUREMENT` carries one or
more closed reasons and is a measurement failure, not a scientific verdict.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Sequence

from logos_research.instrument import InstrumentCharacterization, assess_instrument

from .manifest import DRIFT_FIELDS, StochasticRunManifest

PLAN_FIELDS: tuple[str, ...] = ("repeats", "sample_size", "resolution", "dispersion", "confidence_interval", "effect_size", "baseline", "control",
                                "invalid_measurement_criteria", "early_stop_criteria", "cost_cap", "fallback")
INVALID_REASONS: tuple[str, ...] = ("MODEL_VERSION_DRIFT", "PROMPT_DRIFT", "PROVIDER_DRIFT", "REGION_DRIFT", "DATASET_DRIFT", "INSUFFICIENT_REPEATS", "SEED_UNCONTROLLED",
                                    "EXCESSIVE_VARIANCE", "MISSING_TRACE", "MISSING_GROUND_TRUTH", "CONSTRUCT_INVALID", "COST_CAP_REACHED", "INSTRUMENT_FAILURE")
OUTCOMES: tuple[str, ...] = ("VALID", "INVALID_MEASUREMENT", "FALLBACK")


@dataclass(frozen=True)
class MeasurementPlan:
    repeats: int                       # identical-condition repeats per item
    sample_size: int                   # items
    resolution: float                  # smallest score difference the instrument resolves
    dispersion: float                  # maximum tolerated sd across repeats
    confidence_interval: float         # e.g. 0.95
    effect_size: float                 # minimum effect the experiment claims to detect
    baseline: str                      # named baseline condition
    control: str                       # named control condition
    invalid_measurement_criteria: tuple[str, ...]   # subset of INVALID_REASONS that are active
    early_stop_criteria: str
    cost_cap: float                    # currency-agnostic units
    fallback: str                      # what happens at the cap: must be "STOP_AND_REPORT"
    seed_required_when_stochastic: bool = True
    required_ratio: float = 3.0

    def issues(self) -> list[str]:
        out = []
        if type(self.repeats) is not int or self.repeats < 2:
            out.append("repeats >= 2")
        if type(self.sample_size) is not int or self.sample_size < 1:
            out.append("sample_size >= 1")
        for f in ("resolution", "dispersion", "effect_size", "cost_cap"):
            v = getattr(self, f)
            if type(v) not in (int, float) or isinstance(v, bool) or v <= 0:
                out.append(f"{f} > 0")
        if not (0.5 <= self.confidence_interval < 1.0):
            out.append("confidence_interval in [0.5, 1)")
        if not self.baseline or not self.control or self.baseline == self.control:
            out.append("baseline and control must be named and distinct")
        bad = set(self.invalid_measurement_criteria) - set(INVALID_REASONS)
        if bad or not self.invalid_measurement_criteria:
            out.append(f"invalid_measurement_criteria: closed vocabulary, non-empty; bad={sorted(bad)}")
        if self.fallback != "STOP_AND_REPORT":
            out.append("fallback must be STOP_AND_REPORT (never continue past the cap)")
        if not self.early_stop_criteria:
            out.append("early_stop_criteria required")
        return out


@dataclass(frozen=True)
class MeasurementOutcome:
    status: str
    reasons: tuple[str, ...] = ()
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in OUTCOMES:
            raise ValueError(f"status {self.status!r}")
        bad = set(self.reasons) - set(INVALID_REASONS)
        if bad:
            raise ValueError(f"unknown reasons {sorted(bad)}")
        if self.status == "INVALID_MEASUREMENT" and not self.reasons:
            raise ValueError("INVALID_MEASUREMENT needs at least one reason")
        if self.status == "VALID" and self.reasons:
            raise ValueError("VALID cannot carry reasons")


def invalidate(template: StochasticRunManifest, plan: MeasurementPlan, samples: Sequence, *, instrument: InstrumentCharacterization | None,
               construct_ok: bool, cost_spent: float, ground_truth_present: bool) -> MeasurementOutcome:
    """Executes every preregistered invalidation rule against observed samples.
    A `Sample` has: manifest, score (float|None), trace (dict|None), cost (float)."""
    reasons: list[str] = []; detail: dict = {}
    active = set(plan.invalid_measurement_criteria)

    def flag(r: str, why: str) -> None:
        if r in active and r not in reasons:
            reasons.append(r); detail[r] = why

    if cost_spent > plan.cost_cap:
        flag("COST_CAP_REACHED", f"spent {cost_spent} > cap {plan.cost_cap}")
        return MeasurementOutcome("FALLBACK", tuple(reasons), {**detail, "fallback": plan.fallback})
    for s in samples:
        for f, r in DRIFT_FIELDS.items():
            if getattr(s.manifest, f) != getattr(template, f):
                flag(r, f"{f}: {getattr(s.manifest, f)!r} != {getattr(template, f)!r}")
        if s.manifest.temperature > 0 and plan.seed_required_when_stochastic and s.manifest.seed_if_supported is None:
            flag("SEED_UNCONTROLLED", "temperature > 0 without a seed")
        if s.trace is None or not s.trace.get("reconstructable"):
            flag("MISSING_TRACE", f"sample {getattr(s, 'sample_id', '?')} has no reconstructable trace")
    if len(samples) < plan.repeats:
        flag("INSUFFICIENT_REPEATS", f"{len(samples)} < {plan.repeats}")
    by_item: dict[str, list[float]] = {}
    for s in samples:
        if s.score is not None:
            by_item.setdefault(getattr(s, "item_key", ""), []).append(s.score)
    sds = [statistics.pstdev(v) for v in by_item.values() if len(v) >= 2]          # dispersion = within identical-condition repeats
    if sds:
        detail["observed_sd"] = max(sds)
        if max(sds) > plan.dispersion:
            flag("EXCESSIVE_VARIANCE", f"within-item sd {max(sds):.4f} > dispersion {plan.dispersion}")
    if not ground_truth_present:
        flag("MISSING_GROUND_TRUTH", "no ground-truth proxy attached")
    if not construct_ok:
        flag("CONSTRUCT_INVALID", "metric not CONSTRUCT_SUPPORTED in the construct registry")
    if instrument is None:
        flag("INSTRUMENT_FAILURE", "instrument not characterized")
    else:
        v = assess_instrument(instrument, plan.effect_size, required_ratio=plan.required_ratio)
        detail["instrument"] = v.result
        if not v.admits():
            flag("INSTRUMENT_FAILURE", v.reason)
    if reasons:
        return MeasurementOutcome("INVALID_MEASUREMENT", tuple(reasons), detail)
    return MeasurementOutcome("VALID", (), detail)
