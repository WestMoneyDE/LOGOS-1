# Real-Model Readiness Checklist

**State:** inference remains **blocked** (governance decision `INFERENCE-PROHIBITION` = `DEFERRED`). This checklist says what must be true before any real-model LOGOS-1 experiment (real summarizer, real memory consolidation, pstate/RULER recall-capacity work, live LLM calls) may start. Created by `DETERMINISTIC-CHAIN-CONSOLIDATION-R1`; it starts nothing.

| # | Requirement | Status (2026-09-17) | Owner |
|---|---|---|---|
| 1 | Deterministic invariants documented (`GI-P0`…`GI-P7`, all `PROPOSED`) | done — `GAMMA-INVARIANT-INVENTORY.md` §8 | consolidation |
| 2 | Every HIGH/CRITICAL production-path risk dispositioned | done — `RESIDUAL-RISK-REGISTRY.md`; none production-reachable; MBGV-F1/F3 guarded | consolidation |
| 3 | Canonical effect ownership decision recorded | **open** — `ADR-PROPOSED-CANONICAL-EFFECT-OWNERSHIP.md` = `PROPOSED` | governance |
| 4 | Production bridge status decided | **open** — `DEFERRED` | governance |
| 5 | B1 guarded | done — `NON_PRODUCTION_FROZEN_RISK_GUARDED` (package import guard + architecture test) | consolidation |
| 6 | Inference governance explicitly lifted | **open** — not lifted | founder / governance |
| 7 | Model / provider approved | **open** | governance |
| 8 | Privacy / data boundary approved (no customer data, no production secrets; `AGENTS.md` external-action boundary) | **open** | governance |
| 9 | Reproducibility plan (prompt, model id, version, temperature/seed, provider region captured per run) | **open** — infra supports pins (`ExperimentIdentity`, artifacts) | research infra |
| 10 | Stochastic evaluation plan (instrument-first: resolution vs dispersion; `INVALID_MEASUREMENT` outcome; repeats; CI) | **open** — `assess_instrument` exists | research |
| 11 | Cost budget (tokens, calls, wall-clock; hard cap; cap → `FALLBACK`, not overrun) | **open** | founder |
| 12 | Rollback plan (branch-per-order, lab evidence immutable, `down -v` forbidden) | done by convention | research infra |
| 13 | Artifact retention (MinIO artifacts, Postgres verdicts, DVC identity) | done — Queue-2 repaired infrastructure | research infra |
| 14 | Prompt / model / version capture in the preregistration payload | **open** — schema extension needed before first run | research infra |

Open items 3, 4, 6, 7, 8, 9, 10, 11, 14 block real-model work. Completing the deterministic chain does **not** lift the prohibition.
