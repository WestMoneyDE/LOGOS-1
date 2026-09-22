# ADR — Inference Governance Lift R1

**Order:** `INFERENCE-GOVERNANCE-LIFT-R1` · base `ea24e76` (`PRE_INFERENCE_SAFETY_READINESS_VALIDATED_R1`) · **Date:** 2026-09-18 · **Decision owner:** founder
**Governance verdict:** `INFERENCE_GOVERNANCE_LIFT_APPROVED_R1` · **Inference state:** `LIFTED_WITH_CONDITIONS`
**Amended 2026-09-18 by `INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1`:** the G2/G4 sections below (OpenAI API) are `SUPERSEDED_BY_FOUNDER_AMENDMENT` — see the amendment section at the end; G1, G3, the Tier-A selection and every scientific binding are unchanged.
**Governance preregistration:** `64b7c5bed8f91dc4c3b93836747e25234aab78fdfcfe12af8510caf5b278f7ee` (frozen before the decision gate)
**Machine-readable record:** `docs/research/INFERENCE-GOVERNANCE.json` (every decision verbatim; enforced by `src/logos_research/governance.py`)
**This order made no model call and no provider call** (`model_calls = provider_calls = 0`, counter-, spy-, source-audit- and adapter-inventory-verified).

## G1 — Inference prohibition: `LIFT` → `LIFTED_WITH_CONDITIONS`

> G1: LIFT
>
> Rationale: Die deterministischen Safety-, Measurement-, Construct-Validity-, Provenance- und Trajectory-Gates sind validiert. Daher darf kontrollierte Real-Model-Inference für exakt preregistrierte, simulations-only Forschungsruns freigegeben werden.
>
> Condition: INFERENCE_PROHIBITION = LIFTED_WITH_CONDITIONS
>
> Keine freie Inference, keine Production Actions und kein Real-Model-Run ohne bestandenen Zero-Inference-Dry-Run.

Meaning: inference is governance-eligible under G2–G4 only; not free-form use, not production inference, no autonomous consequential execution.

## G2 — Provider / model boundary: `APPROVED`

Provider **OpenAI** · model **`gpt-5.6-terra`** · region **Europe** · execution **API** · fallback **NONE**. Version policy: fixed model id; provider/model/API/region metadata captured per request; without an immutable snapshot id, any detected server-side change → `MODEL_VERSION_DRIFT` → `INVALID_MEASUREMENT`; no silent pooling across versions. Region: if EU data residency is unavailable for the account → `DEFER`, never switch region. Trust boundary recorded in the registry (data leaving = synthetic only; metadata retained in the lab; processing in Europe; single research account; outage/rate-limit → STOP / `INVALID_MEASUREMENT`). Founder text verbatim in `INFERENCE-GOVERNANCE.json → G2.verbatim`.

## G3 — Privacy / data boundary: `APPROVED`

Allowed: **`SYNTHETIC` only**. Not approved for the first run: `PUBLIC`, `INTERNAL_NON_SENSITIVE`, `CONFIDENTIAL`, `PERSONAL_DATA`, `SENSITIVE_PERSONAL_DATA`, `SECRETS_CREDENTIALS`, `PRODUCTION_CUSTOMER_DATA`, real customer memory, production logs, private third-party communications, tokens, API keys, private keys. Capture: full prompts, inputs, outputs, trajectories, measurement/provenance artifacts. Retention: LOGOS lab/artifact system only. Region: Europe-only. Deletion: by `run_id`. Incident rule: any data-class mismatch → `STOP → INVALID_MEASUREMENT`. Verbatim in `G3.verbatim`.

## G4 — Cost / budget: `APPROVED`

USD · max total 30.00 · max tokens 2,000,000 · max requests 400 · max wall-clock 3 h · max repeats 10 · max per-run 3.00. First cap reached ends the run; no automatic expansion; no provider fallback; no additional batch without new approval. Verbatim in `G4.verbatim`.

## Tier-A selection: **B — `COGNITIVE-PROVENANCE-ABLATION-R1`**

> Rationale: Dieses Experiment hat im aktuellen Repository die beste Kombination aus Dependency Readiness, exakter synthetischer Source-Ground-Truth, Safety-Relevanz, geringer Infrastrukturkomplexität und direktem Anschluss an die bereits validierte Causal-Taint-Provenance.
>
> Primary research boundary: ReasoningContent != ReasoningProvenance

Not selected: A `BELIEF-STATE-GEOMETRY-R1`, C `WORLD-MODEL-TRUST-BOUNDARY-R1`, D `TRAJECTORY-UNCERTAINTY-ACCUMULATION-R1` (remain in the post-inference queue).

## Two-key rules (all `REQUIRED`, founder-approved)

provider = G2 approval + passed zero-inference dry run · privacy = `SYNTHETIC` approved + run dataset classified `SYNTHETIC` · cost = 30 USD ceiling + run-specific prereg cap (≤ 3 USD) · metric = construct-valid registry status + experiment-specific exact source ground truth. `governance.resolve_provider()` returns `ForbiddenProvider` unless all keys hold, and even then only a `ProviderSpec` — no provider adapter exists in this repository.

## Binding for the generated next order

`05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md` (generated, **not executed**): required header, `logos.stochastic-prereg/1`, primary metrics only `CONSTRUCT_SUPPORTED`/`CAUSALLY_DISCRIMINATED` with exact synthetic ground truth (LLM judge, self-report, final-response safety forbidden as sole ground truth), repetition/dispersion/CI/effect size, drift rules (model version, prompt, provider, region, dataset, tool schema → `INVALID_MEASUREMENT`), provenance and trajectory capture, authority boundary (`ModelOutput != Grant` …), `SIMULATION ONLY`, `NO EXTERNAL TOOLS`, artifact package, zero-inference dry run before the first call. `governance.validate_experiment_order()` passes on it.

## Open conditions (unchanged by this order)

`PRODUCTION_BRIDGE_READY_WITH_CONDITIONS` stays as is (not upgraded to `READY`); R1–R3 remain open (`PRODUCTION-BRIDGE-OPERATIONS-R1`); Γ unchanged; P7 unchanged (`FunctionalOrganization != PhenomenalConsciousness`; `CausallyIdentifiedBeliefState != PhenomenalBeliefExperience`); no consciousness endpoint in the first run; no predecessor verdict upgraded.

**Review date:** 2026-12-18, or earlier on the first `INVALID_MEASUREMENT` of the selected experiment for `REGION_DRIFT`/`MODEL_VERSION_DRIFT`.

---

# Amendment — INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1 (2026-09-18)

**Trigger:** the founder's later explicit provider decision supersedes the OpenAI API configuration recorded above. Governance inconsistency, not a scientific falsification. **Amendment preregistration:** `6ad107d5aa86497d8300e3f039fae3d0d2897ee48d1cdf8f36bf2ae012951395` · **Verdict:** `INFERENCE_GOVERNANCE_PROVIDER_AMENDED_R1` · `model_calls = provider_calls = claude_code_inference_invocations = 0`.

## Supersession (history preserved, not deleted)

G2 (OpenAI `gpt-5.6-terra`, Europe, API, fallback NONE) and G4 (USD 30 / 2,000,000 tokens / 400 requests / 3 h / 10 repeats / USD 3 per run) → `SUPERSEDED_BY_FOUNDER_AMENDMENT`, kept in `INFERENCE-GOVERNANCE.json → superseded` and in the lift artifact `365b2fb6…` (unchanged). They are not active gates (mutant M11).

## G2 amended — founder decision, verbatim

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

Allowed path: LOGOS harness → native, documented Claude Code CLI (`claude -p … --output-format json|stream-json`; flags `--model`, `--max-turns`, `--system-prompt`, `--append-system-prompt`, `--allowedTools`, `--disallowedTools`) → Claude Code's own authenticated Max session. Never `--dangerously-skip-permissions`. The harness never extracts OAuth/session tokens, never copies credentials into HTTP clients, never impersonates Claude Code against private endpoints, never calls the Messages API with subscription credentials, never sets/uses `ANTHROPIC_API_KEY`, never reuses Console PAYG, never scrapes cookies. If Claude Code is authenticated via Console/PAYG → STOP; the founder re-authenticates manually (`claude logout` / `claude login`); the harness never enters credentials.

**Model pin:** no historical model name is hard-coded. `MODEL_PIN_GATE` (first execution step of the experiment order) captures Claude Code version, auth mode, subscription class = Max, available models and the founder-selected identifier before the run prereg is frozen. Automatic model change → `MODEL_VERSION_DRIFT` → STOP → `INVALID_MEASUREMENT`; no pooling across Opus ↔ Sonnet, alias resolution or backend change; a switch = a new preregistered run. `backend_snapshot = NOT_EXPOSED` when the CLI does not expose it — a documented reproducibility limitation, never invented.

**Region:** `region guarantee = NOT ASSUMED`. Synthetic prompts/inputs leave the machine (→ Claude Code → Anthropic service; not local inference). Acceptable only because the data class is `SYNTHETIC`; the Claude Max path must be re-evaluated before any non-synthetic data. The stale "OpenAI Europe project or DEFER" requirement is removed.

## G4 amended

`Billing mode = CLAUDE_MAX_SUBSCRIPTION_ONLY` · incremental API budget = USD 0 · Anthropic API PAYG FORBIDDEN · API-credit fallback FORBIDDEN · Console auto-reload not relied upon / must not be used · fallback provider NONE. Operational ceilings: wall-clock 3 h · repeats 10 · Claude Code invocations 200 · concurrent sessions 1 · API/PAYG spend USD 0; the run prereg must define max turns per invocation, max output size, max total accepted trajectories. Usage limit reached → STOP; waiting for the reset is allowed; switching to API credits / PAYG / provider / model or buying credits is forbidden; resume only if the prereg permits pause/resume without violating drift assumptions, else a new run. Quota interruption is a nuisance variable (`run_start_usage_state`, `quota_interruption`, `reset_boundary_encountered`), never model behaviour. Accounting: *incremental PAYG/API inference spend = USD 0; execution consumed Claude Max subscription quota* — never "inference cost = $0".

## Two-key rules — amended

provider = founder approval for the Claude Max path + passed Claude-Max-auth zero-inference preflight + passed experiment dry run · billing = Max subscription confirmed + PAYG/API-key absence confirmed · privacy = `SYNTHETIC` approved + dataset classified `SYNTHETIC` · metric = construct-valid metric + experiment-specific exact source ground truth. Contamination check before activation (`ANTHROPIC_API_KEY`, Bedrock/Vertex/Foundry selection, Console PAYG) records presence and auth class only.

## Provider adapter (contract only; never invoked here)

`src/logos_research/measurement/claude_code.py::ClaudeCodeMaxProvider` — documented argv builder, forbidden-flag and API-key-material refusal, presence-only contamination check, zero-inference `preflight()` (STOP for manual evidence when the auth mode cannot be verified safely), `invoke()` requiring a governance `ActivationToken` (run id, model pin, invocation/turn caps) and an injected subprocess runner, closed statuses `OK / AUTH_NOT_MAX_SUBSCRIPTION / AUTH_UNAVAILABLE / USAGE_LIMIT_REACHED / MODEL_DRIFT / CLI_VERSION_DRIFT / PROCESS_ERROR / INVALID_OUTPUT / TIMEOUT / POLICY_BLOCK`, no PAYG fallback on any error, counters incremented on every inference invocation.

## Unchanged

G1 `LIFT` / `LIFTED_WITH_CONDITIONS` · G3 `SYNTHETIC` only · Tier-A B `COGNITIVE-PROVENANCE-ABLATION-R1` · construct / privacy / provenance / simulation-only / drift rules · `PRODUCTION_BRIDGE_READY_WITH_CONDITIONS` (not upgraded) · R1–R3 open · Γ · P7 · every predecessor verdict. The experiment order was regenerated with the amended header and `MODEL_PIN_GATE`; it remains **not executed**.
