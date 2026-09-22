# SESSION REPORT — LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1

**Kind:** tooling + control plane + governed executor; no scientific status changed; no governed inference run executed (executor exercised with a fake `claude` runner only)
**Base:** `88d4757` (PR #34 head at order start) · branch `tooling/logos-dashboard-part1` · commits `c117c0d` … `74c7f04` (18) · date 2026-09-19
**Verdict:** `RESEARCH_OS_R1_BUILT_WITH_CONDITIONS` (all seven phases built and gated; the conditions are listed in §5 — none of them is a defect in what was built, each is a founder gate or a missing governed run)

## 1. What was ordered and how it was executed
Master order LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1 (107 sections) + founder additions (Playwright, German UI, tracing with statistics, Docker agents on selected theses using deep research when the agent judges it necessary, run console with Start/Stop). Planned with the superpowers skills (brainstorm → spec `docs/superpowers/specs/2026-09-19-research-os-r1-design.md` → ADR → one plan per phase under `docs/superpowers/plans/`), executed inline phase by phase; every phase closed with pytest + the full Playwright matrix + classification registration + a pushed commit.

Brainstorm decisions (founder): hybrid execution (Claude on the host, deterministic work in Docker); run console with Start/Pause/Stop instead of free chat (founder messages become notes injected into the next job); agent autonomy up to `PREREG_DRAFT` + work-order DRAFT; PostgreSQL job queue in the lab Postgres; German default with EN switch.

## 2. Built (by phase)
| Phase | Commit | Delivered |
|---|---|---|
| 0 inventory/ADR | `c117c0d`, `ed5751f` | current-state + target-architecture docs, ADR, spec, Phase-1 plan |
| 1 layout/QA | `f31f479` | IA in five areas, DE/EN dictionary + cookie switch, collapsible sidebar + resizable inspector, `DataTable` (filter/sort/columns/inspector), Playwright matrix (6 viewports, overflow/clipping/console/failed-request gates, visual baselines, route inventory → `/system/qa`), command center |
| 2 control plane | `cb02fb7` | `ros_*` schema v1 (own version table), pure state machines (thesis 23 states / 48 transitions, work order, job, decision; founder gates by construction), control service (event + audit per transition), work-order DAG (cycle-free, readiness), Postgres queue (`FOR UPDATE SKIP LOCKED`, idempotency key), `/api/ros/*`, thesis workspace, board (drag = same transition function), work orders + DAG view, decisions, queue |
| 3 executor | `e22100d` (+ `f014a0c`) | ConcurrencyGovernor (governed cap 1 read from INFERENCE-GOVERNANCE.json, not settable via API), auth evidence from documented `claude auth status --json` (class fields only, 24 h TTL), quota state (USAGE_LIMIT_REACHED → STOP, founder reset), git-worktree isolation + output allowlist (`INTEGRITY_VIOLATION` discards the branch), thesis packet + result contract `ros-agent-result/1`, host executor (documented `claude -p … --output-format json --model claude-opus-5 --max-turns --allowedTools/--disallowedTools`; one invocation per job; agent event applied with actor `agent`), Docker deterministic worker (`ros-worker`, repo copied, no host mount, DSN assembled from parts), run console (SSE, Start/Pause/Stop, notes), `/system/claude|workers|quotas`, ops runbook |
| 4 telemetry | `56ce792` | MLflow experiment `logos-research-os` (run per job, params/metrics/artifacts `prompt.txt` + `claude_result.json`), OTel span per phase, Langfuse generation; degrade-never-block; `ros_trace_links` + `ros_artifacts`; `/traces` + `/traces/[run]` (waterfall, invocation card, MLflow deep link, re-score without inference) — verified against the real lab stack (0 degraded) |
| 5 benchmarks/statistics | `388d9e9` | `logos_dashboard.stats` (Wilson/Newcombe identical to the CPA formulas, bootstrap, Cohen h, pp/relative/error-reduction/efficiency, confusion, ECE, exact McNemar; NOT_DEFINED on zero denominators; every result with method/assumptions/n/missingness/version), benchmark lab (6 golden suites as DRAFT until founder approval; agent modes NO_DATA; deterministic fixture dimension executed by the Docker worker — REGRESSION_GOLDEN 129/129, Wilson [0.971, 1.000]), immutable snapshots (DB trigger), monthly progress |
| 6 inbox/radar | `a915c37` | inbox quick capture (6 kinds), deterministic radar pipeline RAW → … → ACTION_PROPOSED with BEFORE/PROPOSED/EVIDENCE/WHY/WHAT-WOULD-FALSIFY-IT, founder review → DRAFT (work-order DRAFT or `radar-drafts/*.json`, never a registry edit), optional AI_PROPOSAL Claude job (`radar_process`, founder Start, input/prompt hashes + model + trace ids stored), attention queue, lab notebook with promote |
| 7 reports | `74c7f04` | evidence debt (24 items today: 0 HIGH / 18 MEDIUM / 6 LOW, each citing its record), paper readiness (criteria counted k/8 per paper; readiness stays a founder decision), monthly report (Markdown + JSON, deterministic sha; founder freeze → file + immutable month) |

## 3. Numbers (exact)
- pytest: **4349 passed, 2 skipped** (full suite; `tests/test_ros_control_plane.py` 26 tests, `tests/test_dashboard_scientific_core.py` 21). Predecessor exact-set tests extended by registration only (`READERS` entry for `executor.py`; classification files; schema-version assertions).
- Playwright: **303 passed** on 6 viewports (40+ routes × layout gates; behaviour specs: control-plane, executor, benchmarks, radar, reports; pixel baselines for the record pages, live control-plane pages excluded from pixel comparison by design).
- Living source classifications: every file of this order registered in PRE-INFERENCE / INFERENCE-GOVERNANCE-AMENDMENT / COGNITIVE-PROVENANCE / CPA-INSTRUMENT-REPAIR / DASHBOARD (309 sites each) and PRODUCTION-BRIDGE (`benchmarks.py` NON_CONSEQUENTIAL: token hit is a fixture path string); `UNCLASSIFIED = 0`.
- Claude Code inference invocations by this order: **0** (`CALLS["claude_code_inference_invocations"]` in the suite is incremented only by the fake runner and asserted as such). Zero-inference commands used: `claude --version`, `claude auth status --json` (class-level fields recorded; identifiers never read).
- Docker: image `logos-ros-worker:local` (profile `ros`), heartbeat alive; executed one `tests` job and one `benchmark` job end-to-end.

## 4. Governance record
- Provider path unchanged: only the documented CLI under the Max subscription; `--verbose/--resume/--mcp-config/--bare/--dangerously-skip-permissions` remain outside the whitelist (the harness re-checks argv). No `ANTHROPIC_API_KEY`; contamination recorded as presence only. Founder pin `claude-opus-5` (source: MODEL-PIN-GATE.md) is a code constant; a change is a founder decision.
- Raising `max_parallel_claude_sessions` via API is refused in code (`GovernanceError`); the path is a founder amendment order.
- AI never approves: decisions, prereg freeze, work-order approve, ready_to_run, cap increase, benchmark definition, claim status, snapshot freeze, month freeze, radar review are founder-only at the API and the state-machine level (tested).
- GitGuardian on PR #34 (incident 37137572): false positive on the compose interpolation `${POSTGRES_PASSWORD:?…}`; fixed anyway by assembling the DSN from parts (`f014a0c`). No secret was committed.
- Spec deviation recorded: `prior_art` is a Claude host job (deep-research skill needs Claude + web tools), not a Docker job; `dataset`/`dry_run`/`rescore`/`playwright_qa` worker kinds fail closed with `NOT_IMPLEMENTED` reasons.

## 5. Conditions / open items (why "WITH_CONDITIONS")
1. No real agent job has run yet: the executor is proven with a fake runner and the observability stack with a synthetic run; the first real `thesis_advance` needs the founder's Preflight (`/system/claude`), a thesis (`/theses` → *These anlegen* from LOGOS-AUTH-001), *Agenten-Job einreihen*, *Start*, and the host daemon (`python -m logos_dashboard.control.host_daemon --loop`).
2. Benchmark definitions are DRAFT (founder approval per suite); agent modes stay NO_DATA until governed inference runs exist.
3. Open governance question (unchanged from the repair order): `--verbose` (Tier-1 producer evidence) and `--resume` are not approved.
4. Known flake outside this order: `tests/test_infra_self_falsification.py::test_attack_authority_claims_in_infrastructure_stores_create_nothing` uses `hash(lie) % 10000` as a run id and can collide with rows left by earlier runs (seen once; passes on rerun; not modified).
5. Test hygiene leaves audit rows (`ros_audit`) from fixture actions in the lab DB; counts in the monthly report are audit counts, labelled as such.

## 6. Preserved
Γ, P7, production packages, every verdict, preregistration and closure — unchanged. B1 `NON_PRODUCTION_FROZEN_RISK_GUARDED`; production bridge `READY_WITH_CONDITIONS` (R1–R3 open). `ACTIVE-THESES.json` untouched (founder selection LOGOS-AUTH-001; the e2e roundtrip restores it).

## 7. Successor
Exactly one, unchanged chain head: `COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1` (not executed). The first agent run is a founder operation through the dashboard (see the closure file), not a new order.
