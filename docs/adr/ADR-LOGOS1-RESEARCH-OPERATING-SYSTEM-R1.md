# ADR — LOGOS-1 Research Operating System (R1)

**Status:** ACCEPTED (founder decisions 2026-09-19) · **Order:** `LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1` · **Supersedes:** nothing (extends the scientific-core dashboard; PR #34)

## Context
The dashboard shows the scientific state (claims, experiments, invariants, papers) but cannot plan, queue, execute, observe or compare research. The founder wants selected theses worked on by agents, a run console with start/stop, MLflow tracing with statistics, a German UI, and agents in Docker — while the governance (Claude Max subscription only, no credential copies, `max_concurrent_sessions = 1`, founder APPROVE before execution, no autonomous status changes) stays in force.

## Decisions
1. **Hybrid execution.** Claude Code runs only through a **host executor** (`claude -p`, documented flags, Max session, isolated worktree). Deterministic workers, the API, the web app, Postgres, MinIO, MLflow and the OTel collector run in Docker. Rejected: Claude in Docker (requires copying `~/.claude` credentials — violates the provider amendment and §9); everything on host (no isolation for parallel deterministic jobs).
2. **Run console, not chat.** The "chat window" is an event-stream console with Start/Pause/Stop per thesis job; founder messages become stored notes/decisions injected into the next job. Rejected: interactive session (`--resume`/`--verbose` not approved; quota-intensive; blurs the gate model).
3. **Agent autonomy ends at the frozen preregistration.** Agents may take a thesis from `IDEA` to `PREREG_DRAFT` + work-order DRAFT (prior art via the deep-research skill when the agent judges it necessary, question, hypotheses, metrics, falsification criterion, deterministic tests). `PREREG_FROZEN`, `APPROVE` and `READY_TO_RUN` are founder gates; no "run anyway" (§75, §97).
4. **PostgreSQL job queue** in the existing lab database (`FOR UPDATE SKIP LOCKED`, idempotency keys, attempts, durable state). Rejected: Redis (second state store, durability config) and Temporal (operational weight for a one-person lab). Revisit if DAG fan-out or multi-host workers exceed what a table queue handles.
5. **German UI as default with an EN switch**; scientific vocabulary (statuses, verdicts, ids, hashes) stays English to match the registries.
6. **Source of truth stays split and explicit:** git registries = scientific record; Postgres = operational state; MLflow/MinIO = evidence references. Any scientific change goes DB draft → founder approve → generated registry diff → commit → hash recorded.
7. **Concurrency governor** reads the governed cap from `INFERENCE-GOVERNANCE.json`; the dashboard can model several sessions but raising the cap creates a founder gate instead of activating it.

## Consequences
- Two processes on the host during research (executor + optional dev server); the rest via `infra/docker-compose.yml` extensions (`dashboard-api`, `dashboard-web`, `worker-det`).
- MLflow moves to the Postgres backend with MinIO artifacts (no second artifact store).
- New tables `ros_*` in the lab database; migrations versioned; research tables untouched.
- Playwright matrix is a release gate for every UI phase.
- Phase order fixed by the order (§98); Phase 1–3 before any MLflow/benchmark work.

## Non-goals (R1)
LLM judges as ground truth, autonomous approval or status changes, cross-tenant/multi-user auth, cloud deployment.
