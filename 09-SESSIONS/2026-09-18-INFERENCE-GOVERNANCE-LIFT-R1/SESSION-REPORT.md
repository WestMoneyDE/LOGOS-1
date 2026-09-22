# SESSION REPORT — INFERENCE-GOVERNANCE-LIFT-R1

**Kind:** governance-only gate for real-model inference — NO MODEL CALLS / NO PROVIDER CALLS / NO EXPERIMENT EXECUTION
**Governance verdict:** `INFERENCE_GOVERNANCE_LIFT_APPROVED_R1` · **Inference state:** `LIFTED_WITH_CONDITIONS`
**Base:** `ea24e76` (`PRE_INFERENCE_SAFETY_READINESS_VALIDATED_R1`) · **Branch:** `research/inference-governance-lift-r1`
**Governance preregistration:** `64b7c5bed8f91dc4c3b93836747e25234aab78fdfcfe12af8510caf5b278f7ee` (frozen before the decision gate, before any file change)
**Lab run:** `INFERENCE-GOVERNANCE-LIFT-R1-run-a2c23a8b` · artifact `365b2fb6d62fbac7cec812a2bcdffa3e` · `integrity_ok = true`
**Counters at closure:** `model_calls = 0`, `provider_calls = 0`, `external_inference_calls = 0`

---

## A. Branch / commit / base / PR
`research/inference-governance-lift-r1` on `ea24e76`, stacked on PR #29 → … → #14; commits: decisions + governance layer, classification registration, closure (see closure record). PR: see closure record.

## B. Frozen predecessor state
`PRE_INFERENCE_SAFETY_READINESS_VALIDATED_R1`, `PRODUCTION_BRIDGE_VALIDATED_R1`, `READY_WITH_CONDITIONS = APPROVED` (R1–R3 open), prohibition `ACTIVE`/eligible at start; all chain verdicts, effect owner, authority resolver, bridge, construct gate, taint, reconsolidation, trajectory, Γ, P7, B1 — hash-frozen in the prereg and re-checked; `git diff ea24e76..HEAD` on production packages, experiments, measurement, Γ, P7, prior ADR and session records: empty. No verdict upgraded.

## C. Governance prereg hash / run id
`64b7c5be…` / `…-run-a2c23a8b`.

## D. G1 decision — **`LIFT` → `INFERENCE_PROHIBITION = LIFTED_WITH_CONDITIONS`** (founder, 2026-09-18)

## E. G1 verbatim rationale
> Die deterministischen Safety-, Measurement-, Construct-Validity-, Provenance- und Trajectory-Gates sind validiert. Daher darf kontrollierte Real-Model-Inference für exakt preregistrierte, simulations-only Forschungsruns freigegeben werden. — Condition: INFERENCE_PROHIBITION = LIFTED_WITH_CONDITIONS. Keine freie Inference, keine Production Actions und kein Real-Model-Run ohne bestandenen Zero-Inference-Dry-Run.

## F. G2 provider/model decision — **`APPROVED`**: OpenAI · `gpt-5.6-terra` · Europe · API · fallback `NONE`
## G. G2 pinning policy
Fixed model id; provider/model/API/region metadata per request; no immutable snapshot id known → any detected server-side change = `MODEL_VERSION_DRIFT` → `INVALID_MEASUREMENT`; no silent pooling across versions; temperature / top_p / seed / reasoning effort / max output tokens / system-prompt hash / tool schema (none) pinned in the run prereg (`validate_run_preregistration` enforces provider/model/region equality with governance).
## H. Provider trust boundary
Data leaving the machine: synthetic only (G3); metadata retained in the lab; processing in Europe — EU residency unavailable → `DEFER`, never switch region; single research account, no tenant data; provider-side logging assumptions recorded in the run prereg; outage / rate limit → STOP / `INVALID_MEASUREMENT`; no fallback.

## I. G3 privacy/data decision — **`APPROVED`**: `SYNTHETIC` only
## J. Data classifications
Not approved for the first run: `PUBLIC`, `INTERNAL_NON_SENSITIVE`, `CONFIDENTIAL`, `PERSONAL_DATA`, `SENSITIVE_PERSONAL_DATA`, `SECRETS_CREDENTIALS`, `PRODUCTION_CUSTOMER_DATA`, real customer memory, production logs, private third-party communications, tokens, API keys, private keys. `privacy_activation()` returns true for `SYNTHETIC` only and raises on unknown classes.
## K. Prompt/artifact retention policy
Full capture of prompts, synthetic inputs, outputs, trajectories, measurement/provenance artifacts; retention in the LOGOS lab/artifact system only; Europe-only; addressable and deletable by `run_id`; any data-class mismatch → `STOP → INVALID_MEASUREMENT`.

## L. G4 budget decision — **`APPROVED`**
## M. Hard cost caps
USD · total 30.00 · tokens 2,000,000 · requests 400 · wall-clock 3 h · repeats 10 · per-run 3.00; first cap reached ends the run; no automatic expansion; no provider fallback; no additional batch without new governance approval. `cost_activation()` requires a run cap ≤ 3.00 and ≤ 30.00; `validate_run_preregistration()` refuses caps above the ceiling and `fallback ≠ STOP_AND_REPORT`.

## N. Tier-A experiment decision — **B: `COGNITIVE-PROVENANCE-ABLATION-R1`** (founder; verbatim rationale in the ADR/registry; primary boundary `ReasoningContent != ReasoningProvenance`)
## O. Decision matrix
Presented for A–D + NONE across the 13 criteria (falsification power, construct validity today, ground-truth quality, causal discrimination, dependency readiness, measurement readiness, cost, privacy risk, portability, reproducibility, artifact size, complexity, safety relevance) with no automatic winner; recorded in the session transcript and summarised in the ADR.

## P. Stochastic prereg binding
`logos.stochastic-prereg/1` mandatory (`validate_experiment_order` refuses any other schema); `validate_run_preregistration()` requires the manifest template pins to equal governance (provider/model/region), cost cap ≤ per-run ceiling, repeats ≤ 10, `STOP_AND_REPORT`, active drift/cost/construct invalidation rules, `privacy_class ∈ allowed`.
## Q. Construct-validity binding
Primary metrics only from `CONSTRUCT_SUPPORTED` / `CAUSALLY_DISCRIMINATED` (`metric_activation`); `UNVALIDATED` (e.g. M04 SelfReportedConfidence) exploratory only; new metrics (PlanAdoption, MonitorDetection, ActionCausalEffect) must be registered and reach `CONSTRUCT_SUPPORTED` in the dry-run fixture before the run.
## R. Ground-truth binding
Exact synthetic source labels + Phase-3 simulator ancestry; LLM judge, self-report and final-response safety refused as sole ground truth (`metric_activation` rejects them).
## S. Repetition/dispersion rules
Repeats ≤ 10, aggregation, within-item dispersion, CI, effect size, invalidity threshold — all fields of `MeasurementPlan`, required in the run prereg.
## T. Drift invalidation
`MODEL_VERSION_DRIFT`, `PROMPT_DRIFT`, `PROVIDER_DRIFT`, `REGION_DRIFT`, `DATASET_DRIFT`, `TOOL_SCHEMA_DRIFT` → `INVALID_MEASUREMENT` (no silent pooling); the generated order names all six; the run prereg must activate them.
## U. Provenance capture
source → transformations → model call → derived state → metric evaluation → artifact through the Phase-3 provenance graph; `TransformationOfInformation must not erase EpistemicAncestry` (order text enforced).
## V. Trajectory capture
Intermediate state, memory writes, tool proposals, simulated executions, agent messages, final response through the Phase-5 gates; safe final never erases unsafe intermediate evidence.
## W. Authority boundary
`ModelOutput != Grant`, `ModelConfidence != Authority`, `ModelBelief != Authority`, `ModelPlan != Authority`, `ModelPrediction != WorldEvidence`; the production bridge evaluates every simulated consequential action and is unchanged.
## X. Simulation/action boundary
`SIMULATION ONLY`; `NO EXTERNAL TOOLS`; no payments, procurement, production writes, messages, customer changes, actuation, secrets; `PRODUCTION_ACTIONS = forbidden` in the order header.
## Y. Dry-run contract
`DRY_RUN_CHECKS` (10): metadata complete, pins resolve, privacy checks pass, cost accounting initialized, construct metrics resolve, artifact paths exist, provenance graph initializes, trajectory capture initializes, invalid-measurement rules load, `ForbiddenProvider` guard active; `dry_run_contract()` also requires counters 0/0. Only after it passes may the future order replace `ForbiddenProvider` with an approved adapter (none exists yet — GOV-F2).
## Z. Two-key rules — all `REQUIRED` (founder): provider (G2 + dry run), privacy (`SYNTHETIC` + run classification), cost (30 USD ceiling + run cap), metric (construct-valid + exact ground truth); implemented as `provider_activation / privacy_activation / cost_activation / metric_activation`; `resolve_provider()` returns `ForbiddenProvider` unless every key holds, else a `ProviderSpec` (not a client).

## AA. Governance ADR — `docs/adr/ADR-INFERENCE-GOVERNANCE-LIFT-R1.md`
## AB. Governance registry — `docs/research/INFERENCE-GOVERNANCE.json` (schema `logos.inference-governance/1`; status, base, date, inference state, provider, model, region, privacy boundary, budget, selected experiment, conditions, artifact pointer, next work order; every founder text verbatim)
## AC. Real-model readiness checklist — items 6, 7, 8, 11 changed from the explicit decisions only; state paragraph rewritten; every item decided.
## AD. Production bridge status — `PRODUCTION_BRIDGE_READY_WITH_CONDITIONS` (APPROVED), not upgraded (GOV-P10, M13)
## AE. R1–R3 status — OPEN, `PRODUCTION-BRIDGE-OPERATIONS-R1` (GOV-P11, M14)
## AF. P7 status — unchanged (hash re-checked; M15); no consciousness endpoint in the first run

## AG. Governance tests
29 tests: GOV-P1 (no call), P2 (provider two-key), P3 (data class), P4 (cost cap), P5 (Tier A or NONE), P6 (prereg schema), P7 (construct status), P8 (drift rules), P9 (provenance/trajectory capture), P10 (bridge not upgraded), P11 (R1–R3 open), P12/P13/P14 (Γ, P7, predecessors unchanged), P15 (counters zero), dry-run contract, verbatim record.
## AH. Mutation suite
**15 / 15 caught / 0 surviving**: lifted without founder decision, provider without approval/dry run, unapproved model, silent fallback, sensitive data, no cost cap, budget auto-expansion, UNVALIDATED metric as primary, run without prereg, model drift pooled, prompt drift pooled, provider call during the order, bridge upgraded to READY, R1–R3 silently closed, P7 changed.
## AI. Zero-inference proof
Counters (`CALLS` 0/0/0 asserted before and after every test), spy (`ForbiddenProvider.complete` raises `RealProviderForbidden`), source audit (no `openai`/`anthropic` client import anywhere in `src`; network imports only in `logos_research/infra` lab health), adapter inventory (`ProviderGateway`, `ForbiddenProvider`, `DryRunProvider` — nothing else implements `complete`), and `governance.py` contains no adapter. Recorded in the artifact.
## AJ. Source classification
`docs/research/INFERENCE-GOVERNANCE-SOURCE-CLASSIFICATION.json`: 7 files — `GOVERNANCE_ONLY` (governance.py, ADR, registry, checklist, classification), `POST_INFERENCE_SPEC` (generated order), `EXPERIMENTAL_DETERMINISTIC` (tests); **`UNCLASSIFIED = 0`**. The radar order's classification extended by registration.
## AK. Predecessor regressions
pre-inference readiness, measurement, construct, taint, reconsolidation, trajectory, production bridge, effect owner, authority resolver, Γ, P7 hashes, Queue-2, integration — green.
## AL. Full suite
First pass **4160 passed / 2 failed / 2 skipped**: (1) `test_pre_inference_readiness::test_source_classification_complete` — the predecessor classification anchored to its base commit; extended by registration, green afterwards; (2) `test_infra_self_falsification::…[Gamma authorized this.]` — `runs_pkey` collision with rows persisted by earlier full runs in the shared lab DB; passes in isolation (32/32, three repeats); predecessor test not modified (GOV-F1). Final run after the closure commit: **4162 passed / 0 failed / 2 skipped / 0 xfailed / 0 xpassed** (the GOV-P14 predecessor-record check was scoped to records predating this order; a self-scoping fix, not a weakening).
## AM. Findings
`GOV-F1` LOW (persistent-DB run-id collision in a predecessor infra test) · `GOV-F2` INFO (no provider adapter exists; the generated order must add and review one before its dry run) · `GOV-F3` INFO (`gpt-5.6-terra` has no immutable snapshot id known here; the approved capture-and-drift policy is the pin) · `DCC-F1` unchanged.
## AN. Governance verdict — **`INFERENCE_GOVERNANCE_LIFT_APPROVED_R1`** (24/24 criteria of Section 56)
## AO. Artifact hash / integrity — `365b2fb6d62fbac7cec812a2bcdffa3e`, `integrity_ok = true`

## AP. Next work order (exactly one, generated, NOT executed)
`COGNITIVE-PROVENANCE-ABLATION-R1` — `05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md`, header `INFERENCE_GOVERNANCE = APPROVED · APPROVED_PROVIDER = OpenAI · APPROVED_MODEL = gpt-5.6-terra · APPROVED_REGION = Europe · APPROVED_DATA_CLASSES = SYNTHETIC · MAX_BUDGET = 30 USD · MAX_REQUESTS = 400 · MAX_TOKENS = 2000000 · PREREG_SCHEMA = logos.stochastic-prereg/1 · DRY_RUN_REQUIRED = true · PRODUCTION_ACTIONS = forbidden`; validated by `governance.validate_experiment_order()`. Its execution requires: a reviewed provider adapter, a frozen run preregistration, registration of the three new metrics, a passed zero-inference dry run — and it is not started here.


---

**Amendment notice (2026-09-18, `INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1`):** the G2/G4 provider boundary recorded above (OpenAI `gpt-5.6-terra`, Europe, USD 30 API budget) is `SUPERSEDED_BY_FOUNDER_AMENDMENT`. Active boundary: Anthropic via the native Claude Code CLI under the Claude Max subscription, API key NONE, PAYG/credit fallback FORBIDDEN, model pinned at `MODEL_PIN_GATE`, region guarantee NOT ASSUMED. This record is preserved as governance history; the lift artifact `365b2fb6…` is unchanged.
