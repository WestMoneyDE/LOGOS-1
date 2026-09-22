"""logos_research.measurement — real-model measurement readiness (EXPERIMENTAL_DETERMINISTIC).

LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1, Phase 1 (subsumes
REAL-MODEL-MEASUREMENT-READINESS-R1). Everything a future stochastic run must
carry and check BEFORE the first model call:

    StochasticRunManifest   (Section 13)  every pin a run must capture
    MeasurementPlan         (Section 14)  repeats, resolution, dispersion, CI, effect size, baseline, control, ...
    INVALID_REASONS         (Section 15)  closed vocabulary; `invalidate()` makes every rule executable
    dry_run()               (Section 16)  instrument-first gate: metadata / typed slots / traces / costs / rules
    ProviderGateway         no real provider exists here; `DryRunProvider` returns typed synthetic samples and
                            counts calls; `RealProviderForbidden` raises. model_calls == provider_calls == 0.

No inference. No network. This package never touches authority.
"""
from __future__ import annotations

from .construct import GATE_STATUSES, MetricRecord, allowed_as_evidence, evidence_claim, load_registry
from .gateway import CALLS, DryRunProvider, ProviderGateway, RealProviderForbidden, Sample, reset_counters
from .manifest import MANIFEST_FIELDS, StochasticRunManifest, stochastic_preregistration, validate_stochastic_preregistration
from .plan import INVALID_REASONS, PLAN_FIELDS, MeasurementOutcome, MeasurementPlan, invalidate
from .dryrun import DRY_RUN_GATES, DryRunReport, dry_run

__all__ = ["CALLS", "DRY_RUN_GATES", "GATE_STATUSES", "INVALID_REASONS", "MANIFEST_FIELDS", "PLAN_FIELDS", "DryRunProvider", "DryRunReport", "MeasurementOutcome",
           "MeasurementPlan", "MetricRecord", "ProviderGateway", "RealProviderForbidden", "Sample", "StochasticRunManifest", "allowed_as_evidence", "dry_run",
           "evidence_claim", "invalidate", "load_registry", "reset_counters", "stochastic_preregistration", "validate_stochastic_preregistration"]
