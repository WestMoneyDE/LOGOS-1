# Research OS Phase 4 — MLflow / OTel Run Hierarchy + Trace Explorer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every executor run is mirrored into the lab observability stack (MLflow run in experiment `logos-research-os`, OTel spans per phase, Langfuse generation for the Claude call), linked from `ros_trace_links`, and explorable in `/traces` (waterfall from run events, invocation card, MLflow deep link, re-score without inference).

**Architecture:** `control/telemetry.py` wraps the existing lab adapters (`MLflowRunTracker`, `OpenTelemetryTraceSink`, `LangfuseTraceSink` from `logos_research.infra.backends`) with OBSERVABILITY semantics: any failure degrades (recorded in the run summary + a `note` event) and never blocks the job. Executor calls `telemetry.start/phase/generation/finish`. The trace explorer reads `ros_runs` + `ros_run_events` + `ros_trace_links` and fetches MLflow params/metrics on demand.

## Global Constraints
- OBSERVABILITY, never CANONICAL: telemetry failures cannot fail a job; the canonical record stays `ros_run_events` + git branch.
- No secrets in tags/params; content sent to Langfuse is the agent's draft output (local stack), never auth material.
- Re-score = re-parse the stored `claude_result.json` artifact; it never invokes Claude.
- Tests use fake adapters (exact param/metric sets); MLflow/OTel/Langfuse are not required for the test suite.

### Task 1: telemetry.py — `RunTelemetry(stack, identity_like)`: `start(run, job, packet_meta)`, `phase(name, attrs)`, `generation(res, packet)`, `artifact(name, bytes)`, `finish(state, summary)`; `links()`; degraded list. `stack_from_env()` builds adapters lazily; `null_stack()` for tests.
### Task 2: executor integration + `ros_trace_links` + `ros_artifacts` rows (claude_result.json sha256, prompt.txt).
### Task 3: API — `GET /api/ros/traces`, `GET /api/ros/runs/{id}/trace` (links, waterfall, mlflow fetch, artifacts), `POST /api/ros/runs/{id}/rescore`.
### Task 4: UI — `/traces` table + `/traces/[run_id]` (waterfall bars from event timestamps, invocation card, MLflow link, re-score panel); run console gains "Trace" link.
### Task 5: Gate — pytest, Playwright, classification, commit, push.
