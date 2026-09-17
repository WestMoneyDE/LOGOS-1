# Real-Model Readiness Checklist

**State:** inference remains **blocked** (governance decision `INFERENCE-PROHIBITION` = `DEFERRED`). This checklist says what must be true before any real-model LOGOS-1 experiment (real summarizer, real memory consolidation, pstate/RULER recall-capacity work, live LLM calls) may start. Created by `DETERMINISTIC-CHAIN-CONSOLIDATION-R1`; it starts nothing.

| # | Requirement | Status (2026-09-17, updated by LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1) | Owner |
|---|---|---|---|
| 1 | Deterministic invariants documented (`GI-P0`…`GI-P7`, all `PROPOSED`) | done — `GAMMA-INVARIANT-INVENTORY.md` §8 | consolidation |
| 2 | Every HIGH/CRITICAL production-path risk dispositioned | done — `RESIDUAL-RISK-REGISTRY.md`; none production-reachable; MBGV-F1/F3 guarded | consolidation |
| 3 | Canonical effect ownership decision recorded | done (2026-09-17) — founder chose **Option A** (static registry); `ADR-CANONICAL-EFFECT-OWNERSHIP-DECISION.md` `APPROVED`; owner `src/logos_effects` implemented and validated (`CANONICAL-EFFECT-OWNERSHIP-DECISION-R1`); `EFFECT-ORACLE-SCOPE` = `REFERENCE_TEST_ORACLE` (`APPROVED`, founder-ratified 2026-09-17) | governance |
| 4 | Production bridge status decided | **validated (2026-09-17)** — `CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1` = `PRODUCTION_BRIDGE_VALIDATED_R1`: C1 authority resolver, C2 bridge v1 (`logos_runtime.decide_action`, API v1), C3 audit sink, C4 memory reader all `VALIDATED`; readiness re-recorded `PRODUCTION_BRIDGE_READY_WITH_CONDITIONS` (`APPROVED`, founder-ratified 2026-09-17) with **mandatory** operational/governance conditions R1 deployment topology · R2 grant issuance governance · R3 tenant provisioning/authentication | governance |
| 5 | B1 guarded | done — `NON_PRODUCTION_FROZEN_RISK_GUARDED` (package import guard + architecture test) | consolidation |
| 6 | Inference governance explicitly lifted | **open** — not lifted | founder / governance |
| 7 | Model / provider approved | **open** | governance |
| 8 | Privacy / data boundary approved (no customer data, no production secrets; `AGENTS.md` external-action boundary) | **open** | governance |
| 9 | Reproducibility plan (prompt, model id, version, temperature/seed, provider region captured per run) | done (2026-09-17) — `StochasticRunManifest` (21 pins) + drift-based invalidation; `LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1` Phase 1 `MEASUREMENT_READINESS_VALIDATED` | research infra |
| 10 | Stochastic evaluation plan (instrument-first: resolution vs dispersion; `INVALID_MEASUREMENT` outcome; repeats; CI) | done (2026-09-17) — `MeasurementPlan` (12 fields), 13 closed `INVALID_MEASUREMENT` reasons executable, cost cap → `FALLBACK`, dry-run gate (5 checks), construct-validity gate (`LOGOS-METRIC-CONSTRUCT-REGISTRY`) | research |
| 11 | Cost budget (tokens, calls, wall-clock; hard cap; cap → `FALLBACK`, not overrun) | **open** | founder |
| 12 | Rollback plan (branch-per-order, lab evidence immutable, `down -v` forbidden) | done by convention | research infra |
| 13 | Artifact retention (MinIO artifacts, Postgres verdicts, DVC identity) | done — Queue-2 repaired infrastructure | research infra |
| 14 | Prompt / model / version capture in the preregistration payload | done (2026-09-17) — `stochastic_preregistration()` extension (`logos.stochastic-prereg/1`), validated | research infra |

**Remaining blockers (2026-09-17, after LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1):** items 6, 7, 8, 11 only (governance: inference lift, model/provider approval, privacy boundary, cost budget). All deterministic blockers (3, 4, 9, 10, 14) are closed; pre-inference safety readiness is `PRE_INFERENCE_SAFETY_READINESS_VALIDATED_R1` (construct-validity gate, causal taint propagation, reconsolidation governance, trajectory-compromise boundaries). **Inference prohibition = `ACTIVE` — `ELIGIBLE_FOR_GOVERNANCE_REVIEW`**: it is not lifted by this order; only `INFERENCE-GOVERNANCE-LIFT-R1` (a separate governance order) may lift it. Operations conditions R1–R3 remain open on the separate `PRODUCTION-BRIDGE-OPERATIONS-R1` track.
