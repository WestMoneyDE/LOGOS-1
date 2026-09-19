# Research OS — target architecture (R1)

**Order:** `LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1` · decisions taken with the founder on 2026-09-19: **hybrid execution** (Claude on the host, everything else in Docker), **run console with control** (not a free chat), **agent autonomy up to the frozen preregistration** (founder gate before any inference), **PostgreSQL job queue** in the existing lab database, **German UI with EN switch**.

## Four planes, one source-of-truth rule

```
KNOWLEDGE (git)            CONTROL PLANE (Postgres)         OBSERVABILITY (MLflow/OTel)      PERFORMANCE (snapshots)
docs/research/dashboard/*  theses · work_orders · runs      experiments = tracks/theses      benchmark_suites
closures · session reports run_events · decisions · jobs    parent run = work order          benchmark_snapshots
INFERENCE-GOVERNANCE.json  radar_items · notes · audit      child run = arm/replicate        monthly_snapshots
                           worker_jobs · artifacts refs     trace = agent execution          comparability badge
                           (operational state)              span = stage/tool/model/parser   N · CI · version
scientific truth           never scientific truth           evidence refs (hash-addressed)   never a truth score
```
Sync is explicit: DB draft → founder APPROVE → generated registry change → git diff → commit → registry hash recorded back in the DB (§68).

## Components
| component | where | responsibility |
|---|---|---|
| `apps/dashboard` (Next.js + shadcn, DE/EN) | Docker (`dashboard-web`) or host dev | five-area IA (OPERATE / ANALYZE / KNOWLEDGE / PUBLISH / SYSTEM), Command Center, Thesis Workspace, run console, DataTables with inspector, charts (Recharts via shadcn Chart), command palette, QA page |
| `src/logos_dashboard` API (FastAPI) | Docker (`dashboard-api`) or host dev | registries + integrity validation (existing), control-plane CRUD, state machines, queue enqueue, event store, MLflow/OTel links, benchmark statistics, snapshots, SSE stream for run consoles |
| `logos_dashboard.worker.deterministic` | Docker (`worker-det`, N replicas) | deterministic jobs: prior-art briefs (deep-research skill runs *inside Claude Code on the host* — see executor), tests, dataset build, dry run, re-score, Playwright QA, snapshot freeze |
| `logos_dashboard.executor` (Claude host worker) | **host only** | polls `jobs` where `kind = claude`, runs approved `claude -p` (documented flags, resolver, contamination check, isolated worktree/cwd), streams stdout events → `run_events`, writes traces to MLflow; never exposes credentials; honours `ConcurrencyGovernor` (governed cap `max_parallel_claude_sessions = 1` from `INFERENCE-GOVERNANCE.json`; raising it = founder gate) |
| Postgres (existing lab DB) | Docker | research repository tables (unchanged) + new `ros_*` control-plane tables + job queue (`FOR UPDATE SKIP LOCKED`, idempotency keys, attempts) |
| MLflow (existing, moved to Postgres backend + MinIO artifacts) | Docker | experiments per track/thesis, parent/child runs, GenAI traces (OTLP ingest), evaluation datasets, code-based scorers |
| OTel collector (existing) | Docker | receives spans from API/worker/executor; exports to MLflow tracing; `gen_ai.*` + `logos.*` attributes; privacy class per trace |
| MinIO (existing) | Docker | hash-addressed artifacts (raw outputs, trace exports, datasets, plots, screenshots, Playwright traces, snapshots) |
| Playwright | host/CI | viewport matrix, overflow/clipping/console gates, visual snapshots, route inventory → `/system/qa` |

## Thesis lifecycle (state machine, §6) and autonomy boundary
`IDEA → TRIAGE → PRIOR_ART → QUESTION_DEFINED → HYPOTHESIS_DEFINED → METRICS_DEFINED → PREREG_DRAFT → PREREG_FROZEN → WORK_ORDER_READY → DRY_RUN → READY_TO_RUN → RUNNING → ANALYSIS → VERDICT → REPLICATION → PUBLICATION_CANDIDATE → CLOSED` (+ `BLOCKED_BY_GOVERNANCE`, `BLOCKED_BY_DEPENDENCY`, `INVALID_MEASUREMENT`, `FALSIFIED`, `INCONCLUSIVE`, `SUPERSEDED`). Every transition = event (timestamp, actor, reason, source record, git commit, event id). **Agents may advance a selected thesis autonomously up to `PREREG_DRAFT` (incl. a work-order DRAFT); `PREREG_FROZEN`, `WORK_ORDER_READY` (APPROVE) and `READY_TO_RUN` are founder gates.** The agent chooses itself whether a deep-research (prior-art) job is needed (heuristic: track has < 3 citations or the claim has none).

## Run console (founder decision "Run-Konsole mit Steuerung")
`/runs/[run_id]/live`: SSE stream of `run_events` (phase, Claude invocation metadata, tests, artifacts, quota, retries, hard-stop status), **Start / Pause / Stop** per thesis job (graceful STOP: finish atomic write, flush trace, persist last event, `STOPPED_BY_USER`), a message box whose entries are stored as founder notes/decisions and injected into the next job's context — no interactive session, no free shell.

## Execution isolation (§11) and security (§91)
Per approved work order: `work_order_id`, `run_id`, branch `orders/<id>`, git worktree under `E:/logos-worktrees/<id>` (host, executor) or container volume (deterministic), artifact dir, trace root, MLflow parent run, logs. Conflict graph (files/packages/registries) serialises conflicting jobs. Browser never receives Claude tokens or env secrets; commands allowlisted (no shell textbox).

## Benchmarks (§28–33)
Fixed suites from the deterministic fixtures + golden datasets; `BASELINE_AGENT` vs `LOGOS_AGENT` vs `LOGOS_ABLATION` under identical model/dataset/prompts/tool boundary; per-metric scorecard with N, Wilson/Newcombe CIs, comparability badge; hard safety gates (AuthorityFalseAllow > 0 ⇒ `FAILED_SAFETY_GATE`); monthly immutable snapshots; `NOT_COMPARABLE` disables MoM %.

## Phase plan for R1 (order §98) — implemented in this sequence
0 inventory/ADR (done) · 1 layout/Playwright foundation + IA + DE/EN · 2 control plane (theses, state machine, work orders, DAG, decisions, queue, events) · 3 Claude host executor + isolation + concurrency governor · 4 MLflow/OTel run hierarchy + trace explorer · 5 benchmark lab + statistics + snapshots · 6 inbox/radar pipeline · 7 monthly report, evidence debt, paper readiness.
