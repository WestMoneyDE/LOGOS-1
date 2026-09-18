# NEXT SESSION — INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1

**Kind:** governance correction; NO model calls / NO provider calls / NO Claude Code invocations / NO experiment execution
**Amendment verdict:** `INFERENCE_GOVERNANCE_PROVIDER_AMENDED_R1` · **Inference state:** `LIFTED_WITH_CONDITIONS` (unchanged)
**Closed:** 2026-09-18 by `09-SESSIONS/2026-09-18-INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1/`
**Base:** `60e3703` (`INFERENCE_GOVERNANCE_LIFT_APPROVED_R1`)
**Amendment preregistration:** `6ad107d5aa86497d…` · **Run:** `…-run-cd026db3` · artifact `e6639693dadf124f…` `integrity_ok = true` · `model_calls = provider_calls = claude_code_inference_invocations = 0`

## Closure

```text
superseded  G2 OpenAI gpt-5.6-terra Europe API + G4 USD 30 API budget -> SUPERSEDED_BY_FOUNDER_AMENDMENT (preserved in registry; lift artifact 365b2fb6… untouched)
G2 amended  Anthropic · Claude Code · Claude Max subscription · native CLI non-interactive · API key NONE · Console PAYG NOT USED · fallback NONE · API-credit fallback FORBIDDEN
            model = TO_BE_PINNED_FROM_MAX_ACCOUNT_BEFORE_RUN (MODEL_PIN_GATE) · region guarantee NOT ASSUMED · backend_snapshot NOT_EXPOSED
G4 amended  CLAUDE_MAX_SUBSCRIPTION_ONLY · incremental API spend USD 0 · PAYG/credit fallback FORBIDDEN · 3 h · 10 repeats · 200 invocations · 1 session
            usage limit -> STOP (wait for reset only) · accounting: "incremental PAYG/API inference spend = USD 0; execution consumed Claude Max subscription quota"
unchanged   G1 LIFT / LIFTED_WITH_CONDITIONS · G3 SYNTHETIC only · Tier-A B COGNITIVE-PROVENANCE-ABLATION-R1 · construct/privacy/provenance/simulation/drift rules
two-key     provider (approval + Max-auth preflight + dry run) · billing (Max confirmed + PAYG/API-key absence) · privacy · metric — REQUIRED
code        governance.py (amended gates, contamination_check presence-only, billing_activation, model-pin gate, amended order/prereg validators, cli_argv_allowed)
            measurement/claude_code.py (ClaudeCodeMaxProvider CONTRACT: documented argv, forbidden-flag/API-key refusal, preflight, token-gated invoke; never invoked)
records     INFERENCE-GOVERNANCE.json (superseded + amendment + artifact pointer) · ADR amendment section · checklist 7/11 · delta registry · notices on lift records
order       COGNITIVE-PROVENANCE-ABLATION-R1.md regenerated (amended header, MODEL_PIN_GATE, 0b/0c, superseded section) — NOT executed
tests       28 amendment (AMD-P1..P18, pin gate, CLI boundary, zero-inference proof, classification), 15/15 mutants; predecessors 29/25/34 green; full 4190 / 0 / 2
preserved   PRODUCTION_BRIDGE_READY_WITH_CONDITIONS not upgraded; R1-R3 OPEN; Γ, P7, predecessor verdicts unchanged
findings    AMD-F1 INFO (claude on PATH; contamination env vars absent — presence only), AMD-F2 INFO (no backend snapshot id), AMD-F3 LOW (predecessor hard-coded values registered), AMD-F4 INFO (stderr classifier vocabulary unverified)
```

## Credential boundary (in effect for every successor)

The harness must never extract or copy Claude OAuth/session tokens, use custom HTTP clients with subscription credentials, impersonate Claude Code against private endpoints, call the Messages API with subscription credentials, set or use `ANTHROPIC_API_KEY`, reuse Console PAYG, scrape cookies, or reverse-engineer subscription auth. `--dangerously-skip-permissions` is forbidden. Contamination checks record presence/absence and auth class only. Re-authentication is a manual founder step (`claude logout` / `claude login`).

## Successor (exactly one, NOT executed)

`COGNITIVE-PROVENANCE-ABLATION-R1` — `05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md` (amended Claude Max header). First execution step, in this order and nothing before it:

```text
MODEL_PIN_GATE (Claude Code version · auth mode · subscription class = Max · available models · founder-selected identifier -> run prereg + header)
-> zero-inference preflight + dry run (contamination clean, counters 0, dry_run_contract all pass)
-> only then provider activation (ActivationToken minted by governance)
```

Also before its first invocation: register `PlanAdoption` / `MonitorDetection` / `ActionCausalEffect` in the construct registry, freeze a `logos.stochastic-prereg/1` prereg with `cost_cap = 0` and `claude_max_limits` within the amended caps. Not started here.
