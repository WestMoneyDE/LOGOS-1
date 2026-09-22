# SESSION REPORT — LOGOS1-RESEARCH-OS-AUTOPILOT-R2

**Kind:** tooling / usability + one founder governance amendment; no scientific status changed; no governed inference run executed (agent provider proven with a recorded stream fixture)
**Base:** `09cf0cf` (R1 closure) · branch `tooling/logos-dashboard-part1` · PR #34 · date 2026-09-19
**Verdict:** `RESEARCH_OS_R2_AUTOPILOT_BUILT`

## 1. Founder request
"Work orders einreihen; ich sehe keine Claude-Stream-Ansicht; Work Orders aus den Dokumenten und aus Thesen; Worker per Schalter statt automatisch; mehrere Thesen parallel; einfacher für einen Laien; Traces als Statistik mit Balken; die Run-Konsole zeigt nichts." Brainstorm decisions recorded in `docs/superpowers/specs/2026-09-19-research-os-r2-autopilot-design.md` §0.

## 2. Governance amendment (founder, recorded, not decided by AI)
`docs/research/INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1.json`: `--verbose` together with `--output-format stream-json` is **approved for agent jobs only** (`thesis_advance`, `prior_art`, `radar_process`). Measurement runs keep `json` without `--verbose`; `DOCUMENTED_FLAGS` in `logos_research/measurement/claude_code.py` is unchanged (asserted in the test suite). `--resume`, `--fallback-model`, `--mcp-config`, `--bare`, `--dangerously-skip-permissions` stay forbidden. Side effect: every agent run now carries **Tier-1 producer evidence** (`assistant.message.model`).

## 3. Built
- **Live stream** (`control/agent_provider.py`): `Popen` line streaming; each line condensed into a run event (`agent.init`, `agent.batch` with tool/text/thinking/tool_result items, `agent.result`); raw stream stored as MLflow artifact `claude_stream.jsonl`; tool histogram as MLflow metrics; `stop_check` between lines → graceful termination, branch discarded. Own flag allowlist `AGENT_FLAGS`, re-checked by the runner.
- **Autopilot** (`control/autopilot.py`): master switch + per-thesis switch; the daemon tick enqueues and starts the next stage; the §75 gate is evaluated at every automatic start; a failed gate pauses that thesis with the reason; reaching `PREREG_DRAFT` switches it off and leaves an attention item. Cap 1 keeps theses sequential — several theses can be marked, they are worked one after another.
- **Worker control** (`control/procs.py`): host daemon as detached subprocess (PID + heartbeat), graceful stop flag; Docker worker via `docker compose --profile ros up -d / stop` (never `down -v`); status lamps; founder-only.
- **Work orders**: 39 repository orders imported from `05-WORK-ORDERS/*.md` (23 VALIDATED / 2 FALSIFIED / 14 DRAFT), chained by successor (16 edges), linked to theses by shared claim ids, re-import idempotent, documents stay the truth; agent `WORK-ORDER-DRAFT.json` at `draft_prereg` becomes a `ros_work_orders` DRAFT for the founder.
- **Leitstand** (home): worker lamps + switches, master switch, live ticker (3 s poll), thesis cards with a seven-stage stepper in plain German + "arbeiten lassen" toggle + "Nächster Schritt für dich", decisions list, first-steps checklist, counts and verdict chart; "Was ist das?" help box on every key page (DE/EN).
- **Run console**: live agent feed in plain language (liest/schreibt/sucht/nutzt Skill/sagt), packet card (what the agent was asked, which tools/skills, prompt hash), result card (files, proposal, applied state, work-order draft, branch/commit), Start/Pause/Stop, and — when there are no events — the reason plus the fixing link.
- **Traces statistics**: runs per day by state, tokens per run (input/cache/output), mean phase duration with n, tool-call histogram, runs per thesis, bootstrap mean latency; every card labelled with n and version.
- **Research skills for agents**: `deep-research`, `scientific-thinking-literature-review`, `scientific-thinking-scholar-evaluation`, `research-ops`, `eval-harness` installed user-level; the packet names them per job kind and the agent decides.

## 4. Numbers
pytest **4356 passed, 2 skipped** (control-plane suite 33 tests); Playwright **304 passed** on 6 viewports (new: `leitstand.spec.ts`; updated: i18n, smoke). Claude Code inference invocations by this order: **0** (fixture runner only). Lab DB cleaned of test rows; one real thesis remains (`ROS-LOGOS-AUTH-001`, state TRIAGE) with a note recording that it was created and moved during UI verification, not by a founder decision in operation.

## 5. Open / next
1. Still no real agent run: founder Preflight → mark a thesis "arbeiten lassen" → Host-Executor starten → Forschung EIN.
2. Benchmark definitions remain DRAFT (founder approval per suite).
3. `--resume` (two-turn measurement arm) stays undecided.
4. Chain head unchanged: `COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`.
