"""Instrument-first dry run (Section 16). Before the first model call the
pipeline must demonstrate, on the synthetic provider:

    all_metadata_captured · all_output_slots_typed · all_traces_reconstructable ·
    all_costs_accounted · all_invalidation_rules_executable
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from logos_research.instrument import InstrumentCharacterization

from .gateway import CALLS, DryRunProvider, Sample
from .manifest import MANIFEST_FIELDS, StochasticRunManifest
from .plan import MeasurementPlan, invalidate

DRY_RUN_GATES: tuple[str, ...] = ("all_metadata_captured", "all_output_slots_typed", "all_traces_reconstructable", "all_costs_accounted", "all_invalidation_rules_executable")
_OPTIONAL = ("seed_if_supported", "reasoning_effort_if_supported")


@dataclass(frozen=True)
class DryRunReport:
    gates: dict
    samples: int
    cost: float
    outcome_status: str
    rules_exercised: tuple[str, ...]
    detail: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(self.gates.values())


def dry_run(template: StochasticRunManifest, plan: MeasurementPlan, items: list[dict], *, instrument: InstrumentCharacterization | None,
            provider: DryRunProvider | None = None, construct_ok: bool = True) -> DryRunReport:
    provider = provider or DryRunProvider()
    before = dict(CALLS)
    samples: list[Sample] = []
    for i, item in enumerate(items):
        for r in range(plan.repeats):
            m = StochasticRunManifest.from_dict({**template.to_dict(), "run_id": f"{template.run_id}-dry-{i}-{r}"})
            samples.append(provider.complete(m, item))
    gates: dict = {}
    gates["all_metadata_captured"] = bool(samples) and all(not s.manifest.issues() and all(getattr(s.manifest, f) is not None or f in _OPTIONAL for f in MANIFEST_FIELDS) for s in samples)
    gates["all_output_slots_typed"] = bool(samples) and all(set(s.output_slots) == set(provider.slot_types) and all(isinstance(s.output_slots[k], t) for k, t in provider.slot_types.items()) for s in samples)
    gates["all_traces_reconstructable"] = bool(samples) and all(s.trace is not None and s.trace.get("reconstructable") is True and s.trace.get("manifest_condition") == s.manifest.condition_hash for s in samples)
    cost = sum(s.cost for s in samples)
    gates["all_costs_accounted"] = abs(cost - len(samples) * provider.unit_cost) < 1e-9 and cost <= plan.cost_cap
    honest = invalidate(template, plan, samples, instrument=instrument, construct_ok=construct_ok, cost_spent=cost, ground_truth_present=True)
    exercised: list[str] = []
    for reason in plan.invalid_measurement_criteria:                     # every rule must fire on a deliberately broken copy
        b = _break(reason, plan, samples, instrument, cost)
        out = invalidate(template, plan, b["samples"], instrument=b["instrument"], construct_ok=b["construct_ok"], cost_spent=b["cost"], ground_truth_present=b["gt"])
        if reason in out.reasons:
            exercised.append(reason)
    gates["all_invalidation_rules_executable"] = set(exercised) == set(plan.invalid_measurement_criteria)
    after = dict(CALLS)
    assert after["model_calls"] == before["model_calls"] and after["provider_calls"] == before["provider_calls"], "dry run must not touch a real provider"
    return DryRunReport(gates, len(samples), cost, honest.status, tuple(exercised), {"honest": honest.detail, "honest_reasons": honest.reasons})


def _break(reason: str, plan: MeasurementPlan, samples: list[Sample], instrument, cost: float) -> dict:
    d = {"samples": list(samples), "instrument": instrument, "construct_ok": True, "cost": cost, "gt": True}
    if not samples:
        return d
    s0 = samples[0]
    if reason == "MODEL_VERSION_DRIFT":
        d["samples"][0] = replace(s0, manifest=replace(s0.manifest, model_version=s0.manifest.model_version + "-drift"))
    elif reason == "PROMPT_DRIFT":
        d["samples"][0] = replace(s0, manifest=replace(s0.manifest, prompt_version=s0.manifest.prompt_version + "-drift"))
    elif reason == "PROVIDER_DRIFT":
        d["samples"][0] = replace(s0, manifest=replace(s0.manifest, provider=s0.manifest.provider + "-other"))
    elif reason == "REGION_DRIFT":
        d["samples"][0] = replace(s0, manifest=replace(s0.manifest, provider_region=s0.manifest.provider_region + "-2"))
    elif reason == "DATASET_DRIFT":
        d["samples"][0] = replace(s0, manifest=replace(s0.manifest, dataset_version=s0.manifest.dataset_version + "-drift"))
    elif reason == "INSUFFICIENT_REPEATS":
        d["samples"] = d["samples"][: max(0, plan.repeats - 1)]
    elif reason == "SEED_UNCONTROLLED":
        d["samples"][0] = replace(s0, manifest=replace(s0.manifest, seed_if_supported=None, temperature=0.7))
    elif reason == "EXCESSIVE_VARIANCE":
        d["samples"] = [replace(s, score=(0.0 if i % 2 else 1.0)) for i, s in enumerate(d["samples"])]
    elif reason == "MISSING_TRACE":
        d["samples"][0] = replace(s0, trace=None)
    elif reason == "MISSING_GROUND_TRUTH":
        d["gt"] = False
    elif reason == "CONSTRUCT_INVALID":
        d["construct_ok"] = False
    elif reason == "COST_CAP_REACHED":
        d["cost"] = plan.cost_cap + 1.0
    elif reason == "INSTRUMENT_FAILURE":
        d["instrument"] = None
    return d
