# Research OS R2 — Autopilot, Live-Stream, Leitstand (design)

**Order:** LOGOS1-RESEARCH-OS-AUTOPILOT-R2 (founder request 2026-09-19 after R1 closure). Base: `09cf0cf`.

## 0. Founder decisions (brainstorm, 2026-09-19)
1. **`--verbose` approved for agent jobs** (`thesis_advance`, `prior_art`, `radar_process`) together with `--output-format stream-json`, so the founder can watch what an agent reads, writes and searches. Measurement runs (experiments) keep `json` without `--verbose`. Recorded as founder amendment `INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1` (decision_owner founder, 2026-09-19); never a change to the measurement whitelist in `logos_research.measurement.claude_code`.
2. **Autopilot up to `PREREG_DRAFT`**: one switch per thesis ("arbeiten lassen") + one master switch ("Forschung EIN"). Job finished → next stage enqueued and started automatically; founder gates (`freeze_prereg`, `approve_work_order`, `ready_to_run`) stay clicks with a one-sentence explanation in the attention list.
3. **Workers controlled from the UI**: host executor (Claude) and Docker worker (tests/benchmarks) get a Start/Stop switch with a status lamp; Stop is graceful.
4. **Work orders from documents + from theses**: every `05-WORK-ORDERS/*.md` is imported as a repository order (state from its closure), chained by successor; at `METRICS_DEFINED → draft_prereg` the agent writes `WORK-ORDER-DRAFT.json` and the executor creates the `ros_work_orders` DRAFT.
5. **Research skills for agents** (installed user-level via skillfish from `affaan-m/ecc`): `deep-research`, `scientific-thinking-literature-review`, `scientific-thinking-scholar-evaluation`, `research-ops`, `eval-harness`; project skill `logos-prior-art-research`. The packet names the allowed skills per job kind; the agent decides when to use them.

## 1. What stays true (governance, unchanged)
Subscription-only CLI path; governed cap = 1 parallel Claude session (theses run **one after another**, deterministic jobs in parallel); `USAGE_LIMIT_REACHED` → STOP until founder reset; contamination presence-only; agents never edit registries, never approve, never claim verdicts; every agent output lives on its own branch `ros/<thesis>/<run>` under the allowlisted directory; auth evidence ≤ 24 h. Autopilot does not weaken a gate: it only replaces the per-stage *Start* click by one founder decision per thesis ("this thesis may be worked on autonomously up to PREREG_DRAFT"), recorded in `ros_audit` as `autopilot.enable` with the gate snapshot.

## 2. Live stream (agent provider)
`control/agent_provider.py` — a sibling of `ClaudeCodeMaxProvider` for agent jobs only: same token/counter/contamination contract, argv `claude -p <prompt> --output-format stream-json --verbose --model <pin> --max-turns N --allowedTools … --disallowedTools … --append-system-prompt …` (its own allowlist `AGENT_FLAGS = DOCUMENTED_FLAGS + ("--verbose",)`, re-checked by the runner), `subprocess.Popen` reading stdout line by line. Each stream line becomes a condensed `ros_run_events` row (`agent.init`, `agent.text`, `agent.tool` {name, target}, `agent.tool_result` {ok, bytes}, `agent.result`), full raw stream stored as MLflow artifact `claude_stream.jsonl`. Producer model resolved with Tier-1 evidence (`assistant.message.model`) through the existing `resolve_result_model(…, "stream-json")`. Stop → `terminate()` the process, job `stopped`, branch discarded. Privacy: tool inputs are truncated (path/query only), never env or credentials.

## 3. Autopilot scheduler
`control/autopilot.py`, run inside the host daemon loop every tick: for each thesis with `autopilot = true` (per-thesis setting) and master switch on: if no open job for the thesis and state index < ceiling and thesis not blocked → enqueue `thesis_advance` (attempt_group = stage index) and start it (gate evaluated; failure → attention item, autopilot for that thesis paused with reason). `prior_art` sub-jobs are started the same way. Reaching `PREREG_DRAFT` → thesis autopilot switches itself off and an attention item says exactly what the founder must do next. Cap 1 means the daemon processes theses round-robin, one at a time.

## 4. Worker control
`control/procs.py`: host daemon as a detached subprocess (PID + heartbeat in `ros_worker_heartbeats.info`), stop via `ros_settings.host_daemon_stop` flag (graceful) then terminate after grace; Docker worker via `docker compose --profile ros up -d ros-worker` / `stop ros-worker` (never `down -v`). API `/api/ros/workers/{host|docker}/{start|stop}`; UI lamps green/amber/grey.

## 5. Work orders from documents
`control/repo_orders.py`: parse `05-WORK-ORDERS/<ID>.md` (master orders) + `NEXT-SESSION-<ID>.md` (closures) → `ros_work_orders` rows `REPO:<ID>` with `spec.origin = "repository"`, fields extracted where present (question = first `## 1`/goal heading or title; scope/hypothesis/falsification/metrics from headings if found, else `NOT_EXTRACTED`), `state` from the closure verdict class (supported/validated/approved/amended/other-with-closure → `VALIDATED`; falsified/invalid → `FALSIFIED`; open successor without own file → `DRAFT`), DAG edges closure → successor, thesis links via claim ids / track keywords. Re-import is idempotent (state of repository orders is never edited by hand: it mirrors the documents).

## 6. Leitstand (home) for a non-scientist
Home = `/` rebuilt as **Forschungsleitstand**: (A) *Läuft gerade* — worker lamps + Start/Stop, master switch Forschung EIN/AUS, live ticker of the current run (last 5 agent events in plain German); (B) *Thesen* — one card per thesis: title in one sentence, stage stepper (Idee → Sichtung → Vorarbeiten → Frage → Hypothese → Messung → Prereg-Entwurf → 🔒 Deine Freigabe), switch "arbeiten lassen", last result in one sentence, links; "These hinzufügen" from the claim list with plain explanations; (C) *Deine Entscheidungen* — attention list with one sentence + the buttons. Every page keeps a collapsible "Was ist das?" box (DE/EN) explaining the page for a layperson, and an "Erste Schritte" checklist (Preflight → These wählen → Forschung EIN) on the home page until done.

## 7. Traces as statistics
`/traces` top: bar charts (Recharts) — runs per day by state; tokens per run (input/cache/output stacked); mean phase duration; tool calls per run by tool; per-thesis runs. Run detail: waterfall + tool-call histogram + token card. All charts show n, method, version; no percentages without a denominator.

## 8. Run console fix
The console shows: run state, phase strip, live agent feed (from §2), the packet summary (what the agent was asked), the result summary (files, proposed event, next step), and — when there are no events yet — a plain explanation of *why* (job waiting for Start / daemon not running / quota) with the button that fixes it.

## 9. Testing
Fake stream runner (jsonl fixture) for the agent provider (exact event counts, Tier-1 resolution, stop mid-stream); autopilot scheduler tests (round-robin under cap 1, pause at ceiling, gate failure → attention); repo-orders import idempotency + state mapping on the real documents (exact counts for today's 25 orders); worker control with a fake process spawner; Playwright: leitstand switches, live feed with synthetic events, traces charts render with n.

## 10. Out of scope
Raising the Claude cap; measurement runs through the agent provider; any registry edit by an agent; automatic prereg freezing.
