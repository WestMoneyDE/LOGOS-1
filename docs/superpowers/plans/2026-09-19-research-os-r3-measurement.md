# Research OS R3 — Gates & Measurement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A thesis can travel the whole governed path inside the dashboard — validate prereg → freeze → approve work order → dry run → measurement run → verdict proposal → registry draft — with every gate a founder click and every number derived from frozen rules. Spec: `docs/superpowers/specs/2026-09-19-research-os-r3-gates-and-measurement-design.md`.

## Global Constraints
- Measurement runs: `ClaudeCodeMaxProvider`, `--output-format json`, **no `--verbose`** (amendment R1 covers agent jobs only); cap 1 for measurements; agent cap 3 per new amendment `INFERENCE-GOVERNANCE-CONCURRENCY-AMENDMENT-R1`.
- No LLM judges: scorers are deterministic functions; `None` = unscorable → missingness, never success.
- Verdicts are *proposals* derived mechanically from the frozen falsification rule; the founder decides; registries are never written automatically.
- Prereg freeze goes through `logos_research.infra` (`freeze_preregistration`) and must pass `governance.validate_run_preregistration`.
- Dry run performs zero model calls; `CALLS` counters asserted 0.
- Tests deterministic with exact counts; fake runner; TEST-ROS rows cleaned.

### Task 1: Scorers + falsification rules + verdict derivation (pure, no DB)
Files: `src/logos_dashboard/measurement_contract.py` (schemas, hashes, scorer library, rules, `derive_verdict`), tests.
Produces: `SCORERS`, `score_item(scorer, parsed, expected, target_field)`, `dataset_hash(ds)`, `prompt_bundle_hash(pr)`, `validate_dataset/prompts/measurement`, `arm_rates(items)`, `derive_verdict(rates, rule)`.

### Task 2: Prereg build, validate, freeze (lab Postgres) + `ros_gate_log`
Files: `src/logos_dashboard/control/prereg.py`, migration v4, tests (each governance rule violated once; freeze idempotency).

### Task 3: Dry run job (deterministic worker, zero inference) + thesis transitions
Files: extend `control/worker.py` (`dry_run` kind), `control/prereg.py::dry_run_checks`, tests (all ten checks, counters 0, failure path → BLOCKED_BY_GOVERNANCE).

### Task 4: Measurement runner (`control/measurement.py`) + job kind + caps
Budget, token v2, per-item invocation, scorers, drift/cap/usage-limit stops, run events, `ros_measurements` + `ros_measurement_items`; tests with fake runner (exact item counts, four stop paths, missingness).

### Task 5: API (gate chain, measurement start/stop, verdict decide, registry draft) + concurrency amendment record.

### Task 6: UI (gate card in the thesis workspace, `/measurements/[id]`, leitstand chain, browser notifications, traces card) + Playwright.

### Task 7: Gate — pytest, Playwright, classification, session report, closure, commit, push.
