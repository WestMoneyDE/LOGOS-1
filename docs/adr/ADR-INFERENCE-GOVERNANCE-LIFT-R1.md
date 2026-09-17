# ADR — Inference Governance Lift R1

**Order:** `INFERENCE-GOVERNANCE-LIFT-R1` · base `ea24e76` (`PRE_INFERENCE_SAFETY_READINESS_VALIDATED_R1`) · **Date:** 2026-09-18 · **Decision owner:** founder
**Governance verdict:** `INFERENCE_GOVERNANCE_LIFT_APPROVED_R1` · **Inference state:** `LIFTED_WITH_CONDITIONS`
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
