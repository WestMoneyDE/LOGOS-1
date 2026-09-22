# SESSION REPORT — INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1

**Kind:** governance correction — NO MODEL CALLS / NO PROVIDER CALLS / NO CLAUDE CODE INVOCATIONS / NO EXPERIMENT EXECUTION
**Amendment verdict:** `INFERENCE_GOVERNANCE_PROVIDER_AMENDED_R1` · **Inference state:** `LIFTED_WITH_CONDITIONS` (unchanged)
**Base:** `60e3703` (`INFERENCE_GOVERNANCE_LIFT_APPROVED_R1`) · **Branch:** `research/inference-governance-provider-amendment-r1`
**Amendment preregistration:** `6ad107d5aa86497d8300e3f039fae3d0d2897ee48d1cdf8f36bf2ae012951395` (frozen at the clean base tree, before any file change)
**Lab run:** `INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1-run-cd026db3` · artifact `e6639693dadf124f116a14d25f0880b6` (`sha256 e6639693…fbfbb238`) · `integrity_ok = true`
**Counters at closure:** `model_calls = 0`, `provider_calls = 0`, `claude_code_inference_invocations = 0`, `external_inference_calls = 0`

---

## A. Branch / commit / base / PR
`research/inference-governance-provider-amendment-r1` on `60e3703`, stacked on PR #30 (`research/inference-governance-lift-r1`) → #29 → … → #14. Commits: `30ecd5d` (registry / ADR amendment / checklist / delta registry / amendment notices), `d4e6dff` (governance gates, contamination check, MODEL_PIN_GATE, adapter contract, regenerated order), `0380d71` (amendment suite, predecessor registration, classifications), closure commit (this report, closure record, artifact pointer). PR: see closure record.

## B. Frozen predecessor state
Verified at start on the clean tree `60e3703`: `INFERENCE_GOVERNANCE_LIFT_APPROVED_R1`, `PRE_INFERENCE_SAFETY_READINESS_VALIDATED_R1`, `PRODUCTION_BRIDGE_VALIDATED_R1`, `PRODUCTION_BRIDGE_READY_WITH_CONDITIONS = APPROVED`, R1–R3 OPEN, Γ bundle `38f64602…`, P7 boundary `96e68d0f…`, `model_calls = provider_calls = 0`, `COGNITIVE-PROVENANCE-ABLATION-R1` NOT executed. Frozen in the prereg and re-checked in the run: bridge, resolver, gateway, plan (unchanged); the three amended files were frozen in their pre-amendment state (`4e2cb399…`, `9d3cb747…`, `a6f649b7…`) and the run recorded before/after hashes with `before_still_in_git = true` for each. `git diff 60e3703..HEAD` on Γ, production packages, experiments, measurement (except the new `claude_code.py`), P7, bridge ADR, effect-owner registry: empty. No verdict upgraded or altered.

## C. Amendment prereg hash / run id
`6ad107d5…` / `…-run-cd026db3`.

## D. Prior G2/G4 record
Preserved verbatim under `docs/research/INFERENCE-GOVERNANCE.json → superseded.G2_openai` (OpenAI · `gpt-5.6-terra` · Europe · API · fallback NONE) and `superseded.G4_openai_api_budget` (USD 30 · 2,000,000 tokens · 400 requests · 3 h · 10 repeats · USD 3 per run), each with `status = SUPERSEDED_BY_FOUNDER_AMENDMENT` and `superseded_by = INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1 (2026-09-18)`. The lift artifact `365b2fb6…` and its hashes are untouched. The predecessor suite now asserts these historical values on the superseded blocks (no assertion removed).

## E. Founder amendment verbatim
> G2 = APPROVED
>
> Provider: Anthropic
> Access path: Claude Code
> Authentication: Claude Max subscription authentication
> Execution: native Claude Code CLI / supported non-interactive Claude Code mode
> API key: NONE
> Anthropic Console PAYG: NOT USED
> Fallback provider: NONE
> Fallback to API credits: FORBIDDEN

G4 amendment (order Sections 11–12, recorded verbatim in the registry): `Billing mode = CLAUDE_MAX_SUBSCRIPTION_ONLY · Incremental API budget = USD 0 · Anthropic API PAYG = FORBIDDEN · API credit fallback = FORBIDDEN · Console auto-reload = NOT RELIED UPON / MUST NOT BE USED FOR THIS RUN · Fallback provider = NONE`; ceilings `3 h · 10 repeats · 200 Claude Code invocations · 1 concurrent session · API/PAYG spend USD 0`.

## F. Supersession record
Trigger: the founder's later explicit decision made the recorded OpenAI boundary stale — a governance inconsistency, not a scientific falsification. Registry `superseded` block + `amendment` block (prereg hash, artifact pointer); ADR header note + appended amendment section; checklist items 7/11 amended; amendment notices appended to the lift closure record and session report (nothing rewritten); delta-registry entry `INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT = EXECUTED_R1_PROVIDER_AMENDED`. `load_governance()` raises if a superseded block lacks the `SUPERSEDED_BY_FOUNDER_AMENDMENT` status; mutant M11 ("old USD 30 API budget remains active") is caught.

## G. Claude Code access path
LOGOS harness → native, documented Claude Code CLI in non-interactive mode (`claude -p … --output-format json|stream-json`) → Claude Code's own authenticated Max session. Documented flags only: `--model`, `--max-turns`, `--system-prompt`, `--append-system-prompt`, `--allowedTools`, `--disallowedTools`. `check_argv` refuses undocumented flags, `--dangerously-skip-permissions`, and API-key material in argv (`sk-ant-…`, `api-key`). Interactive use, browser flows, private endpoints: excluded.

## H. Max authentication boundary
Authentication is Claude Code's own session; the harness never sees, stores or forwards it. `preflight(auth_class=…)` takes an auth class from safe status evidence only; `auth_class = None` → `stop_for_manual_auth_evidence = true` (no attempt to infer it from files or tokens). `CONSOLE_PAYG` → `AUTH_NOT_MAX_SUBSCRIPTION` → STOP; re-authentication (`claude logout` / `claude login`) is a manual founder step outside the harness. In this order the auth class was **not verified** (`NOT_VERIFIED_IN_THIS_ORDER`): no CLI call of any kind was made.

## I. Credential / PAYG exclusion
Registry `G2.credential_rule` + `G4.api_payg = FORBIDDEN` + `api_credit_fallback = FORBIDDEN`. Code: `contamination_check(env, auth_class)` → `ContaminationReport(env_present, auth_class, clean)` records presence-only for `ANTHROPIC_API_KEY`, `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `CLAUDE_CODE_USE_FOUNDRY` (values never read into any result); `billing_activation` requires `clean and auth_class == MAX_SUBSCRIPTION`; `invoke()` refuses a contaminated env and strips those keys from the env it would pass; `resolve_provider` returns `ForbiddenProvider` without a clean report. Source audit: no `anthropic`/`openai` client import, no `api.anthropic.com`, no cookie/credentials-file access, no `requests`/`httpx`/`urllib`, no `os.environ["ANTHROPIC_API_KEY"]` anywhere in `src`.

## J. Provider adapter design
`src/logos_research/measurement/claude_code.py::ClaudeCodeMaxProvider` — **contract only**. `ActivationToken(run_id, model_pin, max_invocations, max_turns)` minted by governance after the two-key rules, preflight and dry run; `Limits(max_turns, max_output_bytes, timeout_s, disallowed_tools, allowed_tools)`; `ProviderResult(status, content, session_id, requested_model, reported_model, claude_code_version, usage_metadata, turn_count, exit_code, stderr_classification, latency_s, artifact_refs, backend_snapshot = "NOT_EXPOSED")`; closed statuses `OK / AUTH_NOT_MAX_SUBSCRIPTION / AUTH_UNAVAILABLE / USAGE_LIMIT_REACHED / MODEL_DRIFT / CLI_VERSION_DRIFT / PROCESS_ERROR / INVALID_OUTPUT / TIMEOUT / POLICY_BLOCK`; no fallback on any status. `invoke()` requires the token and an injected process runner, increments `claude_code_inference_invocations`, `provider_calls`, `model_calls`. It was never executed in this order (counters 0; adapter inventory registered in both zero-inference proofs).

## K. Claude Code CLI version policy
Captured per invocation (`claude_code_version` in `ProviderResult`, `expected_cli_version` on the adapter); MODEL_PIN_GATE records the version before the run prereg is frozen; a version change during a run → `CLI_VERSION_DRIFT` status → STOP / `INVALID_MEASUREMENT` per the run prereg. No version was captured here (no CLI call).

## L. Model-pin gate
`APPROVED_MODEL = TO_BE_PINNED_FROM_MAX_ACCOUNT_BEFORE_RUN` (`MODEL_PIN_PLACEHOLDER`) in registry, header and record (`model_pinned = false`). No historical Claude model name is hard-coded anywhere. `MODEL_PIN_GATE` (order Section 0a) captures Claude Code version, auth mode, subscription class = Max, available models and the founder-selected identifier; `resolve_provider` returns `ForbiddenProvider` without an explicit non-placeholder pin; `build_argv` refuses the placeholder; `validate_run_preregistration` refuses a manifest without an explicit pin. `backend_snapshot = NOT_EXPOSED` (documented limitation, never invented).

## M. Model drift policy
Per-invocation capture of requested vs reported model; mismatch → `MODEL_DRIFT` → STOP → `INVALID_MEASUREMENT`; no pooling across Opus ↔ Sonnet, alias resolution or backend change; a switch is a new preregistered run. `MODEL_VERSION_DRIFT`, `PROMPT_DRIFT`, `PROVIDER_DRIFT`, `REGION_DRIFT`, `DATASET_DRIFT`, `TOOL_SCHEMA_DRIFT` remain mandatory prereg invalidation rules (unchanged).

## N. Subscription quota policy
Usage limit → `USAGE_LIMIT_REACHED` → STOP. Allowed: wait for the reset. Forbidden: API credits, Console PAYG, another provider, silent model switch, buying credits. Resume with the same run identity only if the prereg explicitly permits pause/resume without violating drift assumptions; otherwise a new run. `run_start_usage_state`, `quota_interruption`, `reset_boundary_encountered` are nuisance variables, never model behaviour. Accounting language fixed: *incremental PAYG/API inference spend = USD 0; execution consumed Claude Max subscription quota* — never "inference cost = $0".

## O. Privacy boundary
G3 unchanged: `SYNTHETIC` only; `privacy_activation` true for `SYNTHETIC` only. Synthetic prompts/inputs leave the machine (→ Claude Code → Anthropic service; not local inference) — acceptable only because of the data class; the Claude Max path must be re-evaluated before any non-synthetic data. Two-key privacy rule unchanged.

## P. Region / residency statement
`region guarantee = NOT ASSUMED` (registry `G2.region = NOT_ASSUMED`, order Section 0c, `ProviderSpec.region = NOT_ASSUMED`). The stale "OpenAI Europe project or DEFER" requirement is removed; mutant M12 ("region guarantee invented") is caught. No claim is made that a Claude Max subscription guarantees a processing region.

## Q. G4 amended usage limits
`CLAUDE_MAX_SUBSCRIPTION_ONLY` · incremental API budget USD 0 (`max_total_spend = max_per_run_spend = 0.0`) · PAYG / API-credit fallback FORBIDDEN · Console auto-reload not relied upon · fallback provider NONE · 3 h · 10 repeats · 200 invocations · 1 concurrent session. `cost_activation` under subscription-only accepts exactly `run_cost_cap == 0`; `validate_run_preregistration` requires `cost_cap == 0` and `stochastic.claude_max_limits.{max_turns_per_invocation, max_output_size, max_total_accepted_trajectories}`; `GovernanceRecord.issues()` rejects a non-zero API budget, missing invocation cap or ≠ 1 concurrent session.

## R. Tool / permission boundary
`NO EXTERNAL TOOLS`; filesystem-mutation tools forbidden unless an exact local fixture path is required; network tools forbidden; MCP forbidden unless explicitly preregistered; narrowest documented permissions via `--disallowedTools` (default `Bash, Edit, Write, WebFetch, WebSearch, NotebookEdit`); pure prompt/response preferred; `--dangerously-skip-permissions` forbidden everywhere (mutant M10 caught).

## S. Dry-run contract
Preflight (no prompt submitted; 14 checks in the registry `preflight_zero_inference`, 11 in `ClaudeCodeMaxProvider.preflight`): executable exists · CLI version captured · auth mode verifiable safely (else STOP for manual evidence) · Max selected · no `ANTHROPIC_API_KEY` · no third-party cloud selection · no PAYG path · model selector / tool restrictions / structured output configurable · forbidden flags blocked; plus the experiment-side checks (artifact paths writable, prereg valid, dataset SYNTHETIC, metrics registered, caps loaded). Dry run: the unchanged 10-check `dry_run_contract` on the `DryRunProvider`; counters (`model_calls`, `provider_calls`, `claude_code_inference_invocations`) must read 0. Preflight and dry run were **defined, not run** here (no CLI call).

## T. COGNITIVE-PROVENANCE order update
`05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md` regenerated: amended 16-line header (`INFERENCE_GOVERNANCE = APPROVED_WITH_PROVIDER_AMENDMENT … API_CREDIT_FALLBACK = forbidden`), Section 0 (amended caps, usage-limit semantics, accounting language), 0a MODEL_PIN_GATE, 0b access path / auth / credential rule / capture list, 0c region, amended prereg / drift / two-key / preflight text, tool boundary, appended "Superseded (governance history, not active)". `validate_experiment_order` → `[]`; `_validate_amended_order` rejects any stale "OpenAI" / "gpt-5.6-terra" before the superseded section. Scientific question, H1, systems A/B/C, metrics, falsification rule: unchanged. **Not executed.**

## U. Metric registration status
Unchanged by this order: M10 / M11 `CAUSALLY_DISCRIMINATED` (usable as primary evidence with exact ground truth), M04 `UNVALIDATED` (never primary). `PlanAdoption`, `MonitorDetection`, `ActionCausalEffect` still require registry entries reaching `CONSTRUCT_SUPPORTED` in the dry-run fixture before the experiment run (order Section 4). Metric two-key rule unchanged.

## V. Amendment tests
`tests/test_inference_governance_amendment.py` — **28 passed**: AMD-P1..P18 (OpenAI superseded / Anthropic active / Claude Code access / Max auth / API-key contamination / PAYG contamination / no provider fallback / no API-credit fallback / usage-limit STOP / model drift STOP / SYNTHETIC only / experiment selection unchanged / bridge not upgraded / R1–R3 open / Γ unchanged / P7 unchanged / zero calls / header matches governance), model-pin gate + `resolve_provider`, CLI boundary (documented flags only; no key material; no cookie / credentials-file / HTTP access in the adapter), zero-inference proof, mutation battery, source-classification completeness. Predecessor suites: `test_inference_governance.py` 29 passed (29 → 29; historical values now on `REG["superseded"]` and a `hist()` record exercising the retained API-budget code path; active values on the amended record; diff scope and adapter inventory registered), `test_pre_inference_readiness.py` 25 passed, `test_measurement_readiness.py` 34 passed (exact counter inventory extended by the new counter).

## W. Mutation results
15/15 caught (battery clean): M1 OpenAI remains active provider · M2 `ANTHROPIC_API_KEY` accepted · M3 PAYG fallback accepted · M4 API credits allowed after quota · M5 OAuth token exported to harness · M6 silent Opus/Sonnet switch accepted · M7 model drift pooled · M8 non-synthetic data allowed · M9 external tools enabled · M10 `--dangerously-skip-permissions` allowed · M11 old USD 30 API budget remains active · M12 region guarantee invented · M13 experiment executes during amendment · M14 production bridge upgraded · M15 P7 modified. The predecessor lift battery (15 mutants) also still 15/15.

## X. Zero-inference proof
Counters after every suite and after the lab run: `model_calls = 0`, `provider_calls = 0`, `claude_code_inference_invocations = 0`; spies: `ForbiddenProvider.complete` raises `RealProviderForbidden`; `ClaudeCodeMaxProvider.invoke` is token-gated with an injected runner and was never called; source audit over `src` (no provider client, no `api.anthropic.com`/`api.openai.com`, no network imports outside `logos_research/infra`, no `subprocess`/`requests`/`httpx` in `measurement`); adapter inventory = `ProviderGateway`, `ForbiddenProvider`, `DryRunProvider`, `ClaudeCodeMaxProvider` (contract). No `claude` process was started by this order; no Claude Max quota was consumed; incremental PAYG/API inference spend = USD 0.

## Y. Predecessor regressions
Governance (29), amendment (28), pre-inference readiness (25), measurement readiness (34): all green. No predecessor test deleted or weakened; changes are registrations (superseded-block assertions, `hist()` record for the retained API-budget path, exact-dict counter inventory, adapter inventory, diff-scope exclusions for this order's own files).

## Z. Full suite
`pytest tests` at the pre-closure tree: **4190 passed, 0 failed, 2 skipped** (baseline at `60e3703`: 4162 / 0 / 2; +28 = the amendment suite). GOV-F1 (persistent-DB run-id collision) did not recur in this run.

## AA. Findings
- **AMD-F1 (INFO)** — a `claude` executable is on PATH of the research machine; `ANTHROPIC_API_KEY`, `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `CLAUDE_CODE_USE_FOUNDRY` are absent in the shell environment. Presence facts only; no value read; no CLI call; auth class not verified in this order (manual evidence at MODEL_PIN_GATE).
- **AMD-F2 (INFO)** — Claude Code does not expose an immutable backend snapshot id through the documented CLI; `backend_snapshot = NOT_EXPOSED` is a documented reproducibility limitation of the Claude Max path, not an invented pin.
- **AMD-F3 (LOW)** — two predecessor tests hard-coded the OpenAI values (`test_measurement_readiness` exact counter dict; `test_inference_governance` record/battery); both extended by registration; historical values now asserted on the preserved superseded blocks; no assertion removed.
- **AMD-F4 (INFO)** — `classify_stderr` maps Claude Code stderr by substrings (usage limit / login / api key / permission); the real error vocabulary must be captured at MODEL_PIN_GATE before the classifier is trusted for `INVALID_MEASUREMENT` decisions.

## AB. Amendment verdict
**`INFERENCE_GOVERNANCE_PROVIDER_AMENDED_R1`** — G2/G4 amended to the founder's verbatim decision; OpenAI boundary superseded and preserved; G1, G3, Tier-A, scientific bindings, bridge readiness, R1–R3, Γ, P7 and all predecessor verdicts unchanged; adapter contract, contamination guards, MODEL_PIN_GATE and amended order in place; 18 properties, 15/15 mutants, zero inference.

## AC. Artifact hash / integrity
`inference-governance-provider-amendment-r1.json` · artifact id `e6639693dadf124f116a14d25f0880b6` · `sha256 e6639693dadf124f116a14d25f0880b6ab5ea6872c919d80a6d5fce0fbfbb238` · `resolve_from_experiment_id → integrity_ok = true` · pointer recorded in `INFERENCE-GOVERNANCE.json → amendment.artifact_pointer`. Findings AMD-F1..F4 recorded as negative results under the run id.

## AD. Exactly one next work order, not executed
`COGNITIVE-PROVENANCE-ABLATION-R1` — `05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md` (amended Claude Max header). Its first execution step must be `MODEL_PIN_GATE → zero-inference preflight + dry run → only then provider activation` (founder-selected model pin, manual Max-auth evidence, `ActivationToken` minted by governance). Not started here.
