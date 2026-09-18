"""COGNITIVE-PROVENANCE-ABLATION-R1 — first governed real-model LOGOS-1 experiment (EXPERIMENTAL_INFERENCE).

    ReasoningContent != ReasoningProvenance

H1: a model can preserve task-relevant plan content while losing, misattributing or
rationalising the causal source of that plan.

Package layout (nothing here is production architecture; nothing here touches authority):

    dataset.py        synthetic task families (tie design), source conditions, balance + leakage checks
    prompts.py        frozen prompt templates, deterministic transformation pipeline (T1..T4), ancestry
    parse.py          closed structured-response schema; INVALID_OUTPUT on anything else; no LLM judge
    metrics.py        SourceAttributionAccuracy / PlanAdoption / MonitorDetection / ActionCausalEffect + intervals
    metric_gate.py    deterministic fixture that licenses M32/M33/M34 through the construct gate
    harness.py        preregistered run: budget, hard stops, retry policy, counters, artifact package, verdict
    claude_runner.py  the only place a `claude` process is started — reachable only through an ActivationToken

Real inference happens only through `logos_research.measurement.claude_code.ClaudeCodeMaxProvider`
with a governance `ActivationToken`; every gate in `harness.RunGates` must be PASS first.
"""
from __future__ import annotations

from logos_research.experiments import assert_experimental_caller

assert_experimental_caller()

EXPERIMENT_ID = "COGNITIVE-PROVENANCE-ABLATION-R1"
SOURCE_CLASS = "EXPERIMENTAL_INFERENCE"
VERDICTS: tuple[str, ...] = ("COGNITIVE_PROVENANCE_HYPOTHESIS_SUPPORTED_R1", "COGNITIVE_PROVENANCE_HYPOTHESIS_PARTIALLY_SUPPORTED_R1",
                             "COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1", "INVALID_MEASUREMENT", "INCONCLUSIVE")
