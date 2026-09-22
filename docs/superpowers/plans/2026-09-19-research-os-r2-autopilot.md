# Research OS R2 — Autopilot / Live-Stream / Leitstand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Research OS usable by a non-scientist: one master switch runs the selected theses autonomously up to `PREREG_DRAFT` (one at a time under the governed cap), every agent step is visible live, workers start/stop from the UI, repository work orders appear as a chain, traces become bar-chart statistics.

**Architecture:** new `control/agent_provider.py` (stream-json + `--verbose`, agent jobs only), `control/autopilot.py` (scheduler in the daemon tick), `control/procs.py` (worker processes), `control/repo_orders.py` (document import), API additions, rebuilt home + console + traces pages. Spec: `docs/superpowers/specs/2026-09-19-research-os-r2-autopilot-design.md`.

## Global Constraints
- Governed cap 1 (theses sequential); founder gates untouched; `--verbose` only in the agent provider (`AGENT_FLAGS`), never in `logos_research.measurement.claude_code`.
- Founder amendment recorded in `docs/research/INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1.json` (decision_owner founder, 2026-09-19), referenced by the governor and shown on `/system/governance`.
- Tests deterministic; fake stream fixture; TEST-ROS rows cleaned; predecessor tests extended by registration only.

### Task 1: Flag amendment record + agent provider (stream-json, live events, stop)
Files: `docs/research/INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1.json`, `src/logos_dashboard/control/agent_provider.py`, executor integration (`kind in CLAUDE_KINDS` → agent provider), fixture `tests/fixtures/ros/agent_stream.jsonl`, tests.
Produces: `AgentProvider.invoke(prompt, model_pin, run_context, limits, token, on_event, stop_check) -> ProviderResult` (+ `stream_events` list, `raw_lines`), `condense(event) -> dict | None`, `AGENT_FLAGS`.
### Task 2: Autopilot scheduler + per-thesis switch + master switch (settings, audit, attention on pause)
### Task 3: Worker control (`procs.py`, API, UI lamps)
### Task 4: Repository work orders import (`repo_orders.py`, API, DAG chain, thesis links) + agent WORK-ORDER-DRAFT.json → DRAFT
### Task 5: Leitstand home + help boxes + first-steps checklist + console fix + traces statistics
### Task 6: Gate — pytest, Playwright, classification, session report addendum, commit, push
