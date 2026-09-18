# NEXT SESSION — INFERENCE-GOVERNANCE-LIFT-R1

**Kind:** governance-only gate; NO model calls / NO provider calls / NO experiment execution
**Governance verdict:** `INFERENCE_GOVERNANCE_LIFT_APPROVED_R1` · **Inference state:** `LIFTED_WITH_CONDITIONS`
**Closed:** 2026-09-18 by `09-SESSIONS/2026-09-18-INFERENCE-GOVERNANCE-LIFT-R1/`
**Base:** `ea24e76` (`PRE_INFERENCE_SAFETY_READINESS_VALIDATED_R1`)
**Governance preregistration:** `64b7c5bed8f91dc4…` · **Run:** `…-run-a2c23a8b` · artifact `365b2fb6d62fbac7…` `integrity_ok = true` · `model_calls = provider_calls = 0`

## Closure

```text
G1   LIFT -> INFERENCE_PROHIBITION = LIFTED_WITH_CONDITIONS (founder, verbatim in ADR/registry)
G2   APPROVED: OpenAI, gpt-5.6-terra, Europe, API, fallback NONE; per-request capture; change -> MODEL_VERSION_DRIFT -> INVALID_MEASUREMENT;
     EU residency unavailable -> DEFER (never switch region)
G3   APPROVED: SYNTHETIC only; full capture; lab-only retention; Europe-only; deletion by run_id; mismatch -> STOP -> INVALID_MEASUREMENT
G4   APPROVED: USD 30 total, 2,000,000 tokens, 400 requests, 3 h, 10 repeats, USD 3 per run; first cap ends the run; no expansion; no fallback
Tier-A  B — COGNITIVE-PROVENANCE-ABLATION-R1 (ReasoningContent != ReasoningProvenance)
two-key  provider (G2 + dry run) · privacy (SYNTHETIC + run class) · cost (ceiling + run cap) · metric (construct-valid + exact ground truth) — REQUIRED
code     src/logos_research/governance.py (GOVERNANCE_ONLY): gates, resolve_provider -> ForbiddenProvider unless all keys, order/prereg validators
records  ADR-INFERENCE-GOVERNANCE-LIFT-R1.md, INFERENCE-GOVERNANCE.json (artifact pointer set), checklist items 6/7/8/11 decided
tests    29 governance tests (GOV-P1..P15), 15/15 mutants, zero-inference proof (counters + spy + source audit + adapter inventory)
preserved  PRODUCTION_BRIDGE_READY_WITH_CONDITIONS not upgraded; R1-R3 OPEN; Γ, P7, predecessor verdicts unchanged
findings   GOV-F1 LOW (persistent-DB run-id collision in a predecessor infra test), GOV-F2 INFO (no provider adapter yet), GOV-F3 INFO (no snapshot id; policy pin)
```

## Successor (generated, NOT executed)

`COGNITIVE-PROVENANCE-ABLATION-R1` — `05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md`. Before its first model call it must: add and review a
provider adapter (none exists), register PlanAdoption / MonitorDetection / ActionCausalEffect in the construct registry, freeze a
`logos.stochastic-prereg/1` preregistration within the G4 caps, and pass the zero-inference dry run. Not started here.


---

**Amendment notice (2026-09-18, `INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1`):** the G2/G4 provider boundary recorded above (OpenAI `gpt-5.6-terra`, Europe, USD 30 API budget) is `SUPERSEDED_BY_FOUNDER_AMENDMENT`. Active boundary: Anthropic via the native Claude Code CLI under the Claude Max subscription, API key NONE, PAYG/credit fallback FORBIDDEN, model pinned at `MODEL_PIN_GATE`, region guarantee NOT ASSUMED. This record is preserved as governance history; the lift artifact `365b2fb6…` is unchanged.
