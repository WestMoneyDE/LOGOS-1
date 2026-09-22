# Research OS Phase 2 — Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the dashboard a durable control plane — theses with a governed lifecycle, work orders with a dependency DAG, founder decisions, a Postgres job queue and an append-only event store — with the thesis workspace, board, work-order, decision and queue pages replacing their Phase 1 placeholders. No executor yet (Phase 3): jobs are enqueued and observed, never run.

**Architecture:** `src/logos_dashboard/db` owns `ros_*` tables in the existing lab Postgres (own version table `ros_schema_version`, idempotent migrations, records-only fallback when the DB is down). `src/logos_dashboard/control` holds pure state machines (`transition(state, event, actor)`), the DAG, the queue (`FOR UPDATE SKIP LOCKED`, idempotency key) and a thin service layer that writes events + audit rows in the same transaction. FastAPI exposes CRUD/transition endpoints; Next.js pages consume them with the Phase 1 `DataTable` + inspector.

**Tech Stack:** psycopg 3 (already in `.venv` via lab infra), FastAPI, Next.js 16 / shadcn preset, Playwright.

## Global Constraints
- Git registries remain the scientific record; the DB never holds a claim status the registry does not (spec §3).
- Founder-only gates: `PREREG_FROZEN`, `WORK_ORDER_READY` (APPROVE), `READY_TO_RUN`, cap increase, benchmark definition, claim status. Actor `agent` may never pass them; illegal transitions raise `IllegalTransition`.
- Every transition writes exactly one `ros_thesis_events` / `ros_audit` row in the same transaction.
- Queue idempotency key `(work_order_id, run_id, kind, attempt_group)`; a duplicate enqueue returns the existing job (no second row).
- Tests are deterministic with exact counts; DB tests use ids prefixed `TEST-ROS-` and delete them in a fixture. No test is deleted or weakened.
- No inference; `ros_jobs.kind = claude` may be enqueued but stays `waiting_governance` (no executor in this phase).
- DE default UI, scientific vocabulary stays English.
- Thesis lifecycle (RESEARCH-OS-TARGET-ARCHITECTURE.md §6): `IDEA → TRIAGE → PRIOR_ART → QUESTION_DEFINED → HYPOTHESIS_DEFINED → METRICS_DEFINED → PREREG_DRAFT → PREREG_FROZEN → WORK_ORDER_READY → DRY_RUN → READY_TO_RUN → RUNNING → ANALYSIS → VERDICT → REPLICATION → PUBLICATION_CANDIDATE → CLOSED` plus `BLOCKED_BY_GOVERNANCE`, `BLOCKED_BY_DEPENDENCY`, `INVALID_MEASUREMENT`, `FALSIFIED`, `INCONCLUSIVE`, `SUPERSEDED`.

---

### Task 1: DB layer + migrations
**Files:** Create `src/logos_dashboard/db/__init__.py`, `src/logos_dashboard/db/migrations.py`; Test `tests/test_ros_control_plane.py`.
**Produces:** `db.connect() -> psycopg.Connection | None` (None ⇒ records-only), `db.ensure_schema(conn) -> int` (version), `MIGRATIONS` tuple, `ROS_TABLES` list (14 names).
- [ ] Test `test_ros_migrations_idempotent`: `ensure_schema` twice returns same version; all `ROS_TABLES` exist in `information_schema.tables`.
- [ ] Implement: version 1 creates `ros_theses, ros_thesis_events, ros_work_orders, ros_work_order_deps, ros_runs, ros_run_events, ros_jobs, ros_decisions, ros_inbox_items, ros_radar_items, ros_notes, ros_artifacts, ros_trace_links, ros_audit` (+ `ros_benchmark_suites, ros_benchmark_snapshots, ros_metric_results, ros_monthly_snapshots` in Phase 5's migration, not here).
- [ ] Run, commit `research-os(p2): ros schema v1`.

### Task 2: State machines (pure)
**Files:** Create `src/logos_dashboard/control/__init__.py`, `control/state_machines.py`.
**Produces:** `THESIS_STATES`, `THESIS_TRANSITIONS: dict[(state, event)] -> state`, `FOUNDER_GATES`, `WORK_ORDER_STATES/TRANSITIONS`, `JOB_STATES`, `DECISION_STATES`, `transition(kind, state, event, actor) -> str` raising `IllegalTransition(state, event, actor, reason)`.
- [ ] Tests: happy path IDEA→…→PREREG_DRAFT as `agent` (7 events); `agent` + `freeze_prereg` raises; `founder` + `freeze_prereg` → `PREREG_FROZEN`; unknown event raises; work order DRAFT→APPROVED only by founder; exact count of thesis transitions = 27.
- [ ] Implement; commit `research-os(p2): thesis/work-order/job/decision state machines`.

### Task 3: Control service (theses, events, decisions, audit)
**Files:** Create `control/service.py`.
**Produces:** `create_thesis(conn, thesis_id, claim_ids, title, track, actor)`, `advance(conn, thesis_id, event, actor, reason, source_record=None, git_commit=None) -> dict`, `list_theses(conn)`, `thesis_detail(conn, id)` (thesis + events + work orders + decisions + jobs), `open_decision(conn, kind, subject_ref, why, impact, if_approved, if_rejected, blocks)`, `decide(conn, decision_id, verdict, actor)`.
- [ ] Tests: create + advance writes 1 thesis event + 1 audit row per call (exact counts); founder gate via `advance(..., actor="agent")` raises and writes nothing; `decide` by agent raises; `decide` by founder APPROVED unblocks (`blocks` list stored).
- [ ] Commit `research-os(p2): control service`.

### Task 4: Work orders + DAG
**Files:** Create `control/dag.py`; extend `service.py`.
**Produces:** `create_work_order(conn, work_order_id, thesis_id, spec: dict, actor)` validating §12 mandatory fields `question, scope, hypothesis, falsification_criterion, metrics, governance, caps`; `add_dependency(conn, child, parent, mandatory=True)` rejecting cycles; `dag.ready(conn) -> list[str]` (APPROVED work orders whose mandatory parents are VALIDATED/FALSIFIED/SUPERSEDED-with-successor); `dag.graph(conn) -> {nodes, edges}`; `wo_transition(conn, id, event, actor, reason)`.
- [ ] Tests: missing field → `ValueError` listing the field; cycle A→B→A raises; `ready()` exact list with one parent VALIDATED; agent `approve` raises.
- [ ] Commit `research-os(p2): work orders + DAG`.

### Task 5: Queue
**Files:** Create `control/queue.py`.
**Produces:** `enqueue(conn, kind, work_order_id, run_id, payload, attempt_group=0) -> job` (idempotent), `dequeue(conn, worker_id, kinds) -> job | None` (`FOR UPDATE SKIP LOCKED`, `queued → running`, sets `locked_by/locked_at`), `complete(conn, job_id, result)`, `fail(conn, job_id, error)`, `pause/resume/stop`, `stats(conn) -> {state: n}`. `claude` jobs are enqueued as `waiting_governance` (Phase 3 lifts them).
- [ ] Tests: enqueue twice → same `job_id`, count 1; dequeue with two workers → distinct jobs, none twice; `claude` kind → `waiting_governance`; stats exact.
- [ ] Commit `research-os(p2): postgres job queue`.

### Task 6: API endpoints
**Files:** Modify `src/logos_dashboard/api.py`; test additions in `tests/test_ros_control_plane.py` (TestClient).
**Produces:** `GET /api/ros/theses`, `POST /api/ros/theses` (body `thesis_id, claim_ids, title, track`), `GET /api/ros/theses/{id}`, `POST /api/ros/theses/{id}/advance` (`event, actor, reason`), `GET/POST /api/ros/work-orders`, `POST /api/ros/work-orders/{id}/transition`, `GET /api/ros/dag`, `GET /api/ros/decisions`, `POST /api/ros/decisions/{id}/decide`, `GET /api/ros/queue`, `POST /api/ros/queue/enqueue`, `POST /api/ros/queue/{id}/{pause|resume|stop}`, `GET /api/ros/events?thesis_id=`, `GET /api/ros/status` (db reachable, schema version). Founder actions carry header `X-Logos-Actor: founder` (localhost single-user; recorded in audit). 503 with `records_only` when DB down.
- [ ] Tests via TestClient with exact JSON assertions; commit.

### Task 7: UI — thesis workspace, board, work orders, decisions, queue
**Files:** Create `apps/dashboard/src/app/theses/[id]/page.tsx`, `src/app/board/page.tsx`, replace placeholders `work-orders`, `decisions`, `queue`; components `thesis-lifecycle.tsx` (state stepper + advance buttons, founder gates marked 🔒), `dag-view.tsx` (SVG layered DAG), `decision-card.tsx`, `queue-table.tsx`; server actions call the API with `X-Logos-Actor: founder`. i18n keys added to `de.ts/en.ts`. Extend `/theses` to "Anlegen" a `ros_thesis` from a selected claim (IDEA).
- [ ] Playwright: `e2e/control-plane.spec.ts` — create TEST thesis via API, open `/theses/TEST-ROS-…`, advance to TRIAGE as agent, verify event row appears, founder-gate button disabled for agent; cleanup via API `DELETE /api/ros/theses/{id}` (test-only, id must start with `TEST-ROS-`). Routes added to `e2e/routes.ts` (`/board`, `/theses/<id>` skipped when absent).
- [ ] Full matrix green, update snapshots, commit.

### Task 8: Gate
- [ ] `pytest tests -q` green; Playwright matrix green; classification files registered; command center stats `queued_work_orders`/`running_agents` read from the DB (replace Phase-2 pending); commit `research-os: Phase 2 complete`, push.
