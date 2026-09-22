# Research OS Phase 3 — Host Executor, Isolation, Governor, Run Console

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the queue executable under governance: a Claude host executor for agent jobs (`thesis_advance`, `prior_art`), a deterministic worker (Docker) for `tests`/`snapshot`, a ConcurrencyGovernor, git-worktree isolation with an output allowlist, an append-only run event stream with SSE, and the run console with Start / Pause / Stop.

**Architecture:** `control/governor.py` (pure caps + quota state), `control/worktree.py` (git worktree add/commit/remove + changed-file allowlist), `control/packet.py` (thesis packet prompt + result contract `ros-agent-result/1`), `control/executor.py` (job → run → events; provider = `ClaudeCodeMaxProvider` with an injected runner; `claude_runner.make_runner` semantics re-used), `control/host_daemon.py` (host loop, single instance), `control/worker.py` (Docker loop), `ros_api` additions (start gate, runs, SSE, settings/attestation, governor), Next.js `/runs`, `/runs/[id]`, `/system/claude`, `/system/workers`, `/system/quotas`.

**Tech Stack:** psycopg 3, FastAPI `StreamingResponse` (SSE), subprocess, git worktree, Next.js `EventSource`.

## Global Constraints (in addition to Phase 2)
- Only the documented CLI path: `claude -p … --output-format json --model <pin> --max-turns N --allowedTools/--disallowedTools --append-system-prompt`. No `--verbose`, `--resume`, `--mcp-config`, `--bare`, `--dangerously-skip-permissions`. Never `ANTHROPIC_API_KEY`; contamination = presence only.
- Founder pin `claude-opus-5` from `INFERENCE-GOVERNANCE.json`/registry; `max_concurrent_sessions = 1` is read from the governance record and cannot be raised through the API (code refuses; a founder amendment order is required).
- `USAGE_LIMIT_REACHED` → job `waiting_quota`, `quota_state` set, every Claude job blocked until the founder resets; no provider/model fallback, no automatic retry.
- Agent jobs need a founder **Start** (pre-run integrity gate: DB ok, attestation fresh ≤ 24 h, contamination clean, governance record status, thesis ≤ agent ceiling, worktree clean). Every Claude invocation writes a `claude.invoke` + `claude.result` event with requested/resolved model, evidence class, status, turns, latency, stdout hash.
- Agent outputs are confined to `docs/research/dashboard/theses/<thesis_id>/` (and `docs/research/dashboard/research-briefs/` for `prior_art`) inside an isolated worktree on branch `ros/<thesis_id>/<run_id>`; any other change → `INTEGRITY_VIOLATION`, job failed, worktree discarded. Registries are never edited by agents.
- The agent's `proposed_event` is applied with actor `agent` through the Phase 2 state machine — founder gates cannot be passed by construction.
- Spec deviation (recorded): `prior_art` is a Claude host job (the deep-research skill needs Claude + web tools), not a deterministic Docker job. `dataset`, `dry_run`, `rescore`, `playwright_qa` stay `NOT_IMPLEMENTED` (fail closed with reason) until Phases 4/5.
- Tests use a fake `claude` runner and a temporary git repository; the real CLI is never invoked by the test suite (`CALLS["claude_code_inference_invocations"]` unchanged).

### Task 1: Governor + settings (migration v2 `ros_settings`, `ros_worker_heartbeats`)
`governor.py`: `Governor.from_record()` (caps: `max_parallel_claude_sessions` = governance `max_concurrent_sessions`, `max_claude_invocations_per_job` = 5 default / cap 200, `max_active_theses` = 3, `max_parallel_deterministic_jobs` = 2), `state(conn)` (running counts, quota_state, attestation), `can_dispatch(conn, kind) -> (bool, reason)`, `set_quota_state(conn, state, actor)`, `attest_auth(conn, auth_class, cli_version, actor)` (founder only), `attestation_fresh(conn)`.
Tests: cap 1 → second claude job refused with `CONCURRENCY_CAP`; quota state blocks; stale attestation blocks; raising the cap raises `GovernanceError`.

### Task 2: Worktree isolation
`worktree.py`: `create(repo, run_id, thesis_id) -> path` (branch `ros/<thesis>/<run_id>` from HEAD), `changed_files(path)`, `check_allowlist(files, allowed_prefixes) -> violations`, `commit(path, message) -> sha|None`, `remove(repo, path)`. Tests on a temp git repo.

### Task 3: Packet + result contract
`packet.py`: `build_thesis_packet(thesis_detail, regs, notes, prior_art_count) -> {prompt, system, allowed_tools, disallowed_tools, expected_files}`; `parse_agent_result(text) -> AgentResult(proposed_event, files, needs_prior_art, summary, uncertainties)` — JSON block contract `ros-agent-result/1`, invalid → `INVALID_OUTPUT`.
Tests: packet contains claim statement, notes, ceiling rule, allowed dir; parse strict.

### Task 4: Executor
`executor.py`: `run_job(conn, job, *, repo, runner_factory, provider_factory, clock) -> dict`. Steps: gate → run row → worktree → packet → invoke (≤ `max_claude_invocations_per_job`, one by default) → allowlist → commit → apply `proposed_event` (agent) → enqueue `prior_art` when `needs_prior_art` → complete. Statuses map: OK → done; USAGE_LIMIT_REACHED → waiting_quota (+quota_state); AUTH_* → failed + attestation cleared; INVALID_OUTPUT/PROCESS_ERROR → failed; violation → failed `INTEGRITY_VIOLATION`; Stop requested → stopped (graceful: no further invocation; running process killed by runner timeout/terminate).
Tests (fake runner): happy path exact events (`phase`×N, `claude.invoke`, `claude.result`, `artifact`, `commit`, `thesis.event`), usage limit, violation, stop, idempotent restart.

### Task 5: Daemons
`host_daemon.py` (`python -m logos_dashboard.control.host_daemon --once|--loop`), `worker.py` (deterministic: `tests` via allowlisted `pytest <path> -q`, `snapshot` registries JSON; other kinds fail closed). `infra/ros-worker.Dockerfile` + compose service `ros-worker` (profile `ros`), heartbeat rows.

### Task 6: API
`POST /queue/{id}/start` (founder gate → `queued` + audit), `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/events?after=`, `GET /runs/{id}/stream` (SSE), `POST /runs/{id}/stop|pause`, `GET /governor`, `POST /governor/attest`, `POST /governor/quota-reset`, `GET /workers`, thesis workspace `POST /theses/{id}/agent-job` (enqueue thesis_advance).

### Task 7: UI
`/runs` (DataTable), `/runs/[id]` (console: header, phase strip, event stream via EventSource with fallback polling, Start/Pause/Stop, notes box, links), `/system/claude` (attestation form, preflight card, contamination presence), `/system/workers`, `/system/quotas`; thesis workspace "Agent-Job starten" button; command center live running agents. Playwright: `e2e/executor.spec.ts` (attest, enqueue, start gate, console shows events from a fake run inserted via API test hook `POST /api/ros/test/fake-run` — enabled only for `TEST-ROS-*` ids).

### Task 8: Gate — pytest, Playwright matrix, classification, commit, push.
