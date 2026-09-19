# Research OS — Operations (Phase 3 state)

All services are local. Nothing here bypasses governance: Claude runs only through the documented CLI under the Max subscription, one session at a time (governed cap), after a founder **Start** on a job whose §75 gate passed.

| Component | Start | Notes |
|---|---|---|
| Lab stack (Postgres/MinIO/MLflow/Langfuse/OTel) | `cd infra && docker compose up -d` | never `down -v` |
| Reader/control API | `PYTHONPATH=src .venv/Scripts/python -m uvicorn logos_dashboard.api:app --host 127.0.0.1 --port 8765` | `ros_*` schema migrates itself on first request (`ros_schema_version`) |
| Dashboard | `cd apps/dashboard && pnpm build && pnpm start` (or `pnpm dev`) | DE default, EN via cookie `logos_locale` |
| Host executor (Claude jobs) | `PYTHONPATH=src .venv/Scripts/python -m logos_dashboard.control.host_daemon --loop` | the only process that reaches `claude`; needs fresh auth evidence (`/system/claude` → Preflight, 24 h) |
| Deterministic worker (Docker) | `cd infra && LOGOS_REPO_SHA=$(git rev-parse --short HEAD) docker compose --profile ros up -d --build ros-worker` | `tests` (allowlisted pytest paths) and `snapshot`; repo is copied into the image, no host mount |
| Playwright QA | `cd apps/dashboard && pnpm e2e` | 6 viewports, visual baselines; results → `/system/qa` |

## Agent job lifecycle (thesis_advance)
1. `/theses` → *These anlegen* from a selected claim (state `IDEA`).
2. Workspace `/theses/<id>` → *Agenten-Job einreihen* (job `waiting_governance`) → *Gate prüfen* → 🔒 *Start* (founder; gate recorded in `ros_audit`).
3. Host daemon: worktree `ros/<thesis>/<run>` → packet → one `claude -p … --output-format json --model claude-opus-5 --max-turns 25 --allowedTools Read,Write,Edit,Glob,Grep --disallowedTools Bash,…` → allowlist check (`docs/research/dashboard/theses/<id>/` only) → commit on the run branch → agent's `proposed_event` applied with actor `agent` (gates cannot be passed) → optional `prior_art` sub-job (deep-research skill; web tools) which again waits for a founder Start.
4. Console `/runs/<run_id>`: SSE event stream, Pause/Stop, founder notes (injected into the next packet).
5. `USAGE_LIMIT_REACHED` → job `waiting_quota`, all Claude jobs blocked until the founder resets on `/system/quotas`.

## What is not built yet
MLflow/OTel run hierarchy + trace explorer (Phase 4), benchmark lab/statistics/snapshots (Phase 5), inbox/radar pipeline (Phase 6), monthly report/evidence debt/paper readiness (Phase 7). `dataset`, `dry_run`, `rescore`, `playwright_qa` jobs fail closed with `NOT_IMPLEMENTED`.
