# NEXT SESSION — COGNITIVE-PROVENANCE-ABLATION-R1

**Kind:** first governed real-model experiment (Claude Code · Claude Max · `claude-opus-5`)
**Experiment verdict:** `INVALID_MEASUREMENT` (`MODEL_VERSION_DRIFT` on invocation 1 → preregistered STOP; `MISSING_TRACE`) — no scientific result
**Closed:** 2026-09-18 by `09-SESSIONS/2026-09-18-COGNITIVE-PROVENANCE-ABLATION-R1/`
**Base:** `52563dd` · setup prereg `56ca6144…` · run prereg `42ef348a…` (attempt 1 `779ab8e7…` superseded before inference) · run `…-run-1546654c` · artifact `28a263ea…` + raw log `5f887962…` · `integrity_ok = true`
**Counters:** `model_calls = provider_calls = claude_code_inference_invocations = 1` (reconciled)

## Closure

```text
gates       MODEL_PIN_GATE PASS (founder: claude-opus-5) · AUTH_GATE PASS (claude.ai / firstParty / max) · CONTAMINATION clean · METRIC_GATE PASS (M32-M34 fixture-scoped)
            DATASET/LEAKAGE PASS · HARNESS_MUTANTS 15/15 · ZERO_INFERENCE_PREFLIGHT PASS · DRY_RUN PASS (attempt 2) · ActivationToken run-bound
execution   1 of 156 preregistered trials issued; Claude Code 2.1.275; exit 0; result JSON valid; reported model (first modelUsage key) = claude-haiku-4-5 (auxiliary) beside claude-opus-5 (156 output tokens)
            -> MODEL_DRIFT status -> STOP as preregistered; nothing accepted; no retry; no fallback; no pooling
verdict     INVALID_MEASUREMENT — not a null result; H1 untested
findings    CPA-F5 HIGH (drift detector cannot separate primary from auxiliary model in Claude Code modelUsage; CLI JSON does not label the producer of `result`)
            CPA-F6 INFO (list-price cost fields under Max = not spend) · CPA-F7 INFO (inference_geo not_available) · CPA-F8 LOW (~23.8k scaffolding tokens per invocation) · CPA-F9 INFO (session CLAUDE* env stripped)
            CPA-F1..F4 from the gate phase (fallback-model flag refused; no model enumeration; sampling not configurable; auth JSON identifiers redacted)
accounting  incremental PAYG/API inference spend = USD 0; execution consumed Claude Max subscription quota (1 invocation)
preserved   Γ, P7, production bridge, effect owner, authority resolver, memory reader, audit sink, predecessor verdicts — unchanged; authority_state_changed = false
regressions full suite 4229 / 0 / 2 after the run; predecessor suites green; no verdict changed
records     MODEL-PIN-GATE.md · SESSION-REPORT.md (Section 61 A-AT) · COGNITIVE-PROVENANCE-SOURCE-CLASSIFICATION.json (UNCLASSIFIED = 0; experiment code EXPERIMENTAL_INFERENCE, never promoted)
```

## Successor (exactly one, NOT executed)

`COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1` — repair the exact measurement defect and validate it independently, then rerun as a new preregistered run:

```text
1. Establish, from Claude Code's documented non-interactive output contract, which modelUsage entry produced `result`
   (never guess; if undocumented, define the rule as: the entry matching the requested --model with non-zero output tokens,
   and STOP only when NO entry matches the pin or a non-pinned entry produced the final message).
2. Repair the adapter's reported_model derivation (claude_code.py is a frozen predecessor file: change it in the repair order
   with its own prereg, hash record and tests; or wrap it in the harness) — mutants: auxiliary entry accepted as drift-free
   only when the pinned entry is present; pinned entry absent -> drift; alias resolving to another family -> drift.
3. Characterise CPA-F8 (scaffolding context per invocation) from the captured raw JSON; record it in the run manifest.
4. Independent validation on deterministic fixtures built from the captured raw invocation JSON (artifact 5f887962…).
5. New run preregistration (new run id; same founder pin claude-opus-5; same dataset/prompt hashes), gates, preflight,
   dry run, ActivationToken, the 156 trials; verdict from the frozen criteria.
```

Not started here.
