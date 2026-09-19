# Research OS — current state inventory (Phase 0)

**Order:** `LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1` · **Date:** 2026-09-19 · **Baseline:** PR #34 (`tooling/logos-dashboard-part1`, HEAD `5207d21`)

## Stack (as built by LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1)
- **UI:** `apps/dashboard` — Next.js 16.3 (App Router, RSC), TypeScript, Tailwind 4, shadcn preset `b1abNSlea` (style `base-sera`, Inter/Geist Mono, teal primary, `cn` package). Components installed: badge, button, card, checkbox, command, dialog, input, input-group, progress, scroll-area, separator, sheet, table, tabs, textarea, tooltip. Custom: `Shell` (sidebar + header), `Section`, `Table`, `Src`, badges (status/strength/kind/verdict/severity), `ClaimCard`, `InvariantGraph` (SVG, client), `ThesesSelector`, `ExportButton`. English only. Server-rendered pages fetch the service with `cache: "no-store"`.
- **Service:** `src/logos_dashboard` — FastAPI on `127.0.0.1:8765`, TOOLING with import guard. Modules: `registries.py` (load + `validate()` 12 rule families + counts), `readers.py` (closures, session reports, git/gh, lab via `logos_research.infra.backends`, records-only fallback), `research_intake.py` (queue, brief validation, founder-reviewed merge), `api.py` (29 GET routes + `POST /api/theses/active` + `POST /api/research-briefs/validate`). In-memory TTL cache; no DB of its own.
- **Structured state (git):** `docs/research/dashboard/*.json` — claims 23 (+7 counterexamples, 6 tracks), experiments 22, invariants 30, prior art 14, publications 6, replication 7, open questions 7, active theses, research briefs (empty).
- **Existing infrastructure (repo):** `infra/docker-compose.yml` → Postgres (research repository: experiments, preregistrations, runs, negative_results, …), MinIO (artifacts), MLflow tracking (`http://127.0.0.1:55000`, one experiment used by `ResearchRun`), Langfuse, OTel collector. `logos_research.infra` (`backends_from_env`, `ExperimentIdentity`, `ResearchRun`, `resolve_from_experiment_id` integrity). Claude Code executor: `logos_research.measurement.claude_code.ClaudeCodeMaxProvider` (token-gated `invoke`, resolver `result_model`, status classifier) + `cognitive_provenance_r1.claude_runner` (`make_runner(token, cwd)`; the only `claude` process-start site). Governance: `logos_research.governance` (two-key gates, contamination check, flag whitelist, `max_concurrent_sessions = 1`).
- **QA:** `@playwright/test` 1.63 (added in this order) with six viewport projects; `e2e/smoke.spec.ts` = route inventory (26 routes) × overflow/clipping/console/failed-request checks + theses roundtrip; JSON inventory for `/system/qa`.
- **Routes (26):** `/`, `/tracks`, `/tracks/[6]`, `/claims`, `/claims/[id]`, `/experiments`, `/experiments/[id]`, `/invariants`, `/counterexamples`, `/negative-results`, `/falsification`, `/replication`, `/publications`, `/publications/[id]`, `/prior-art`, `/open-questions`, `/research`, `/timeline`, `/reproducibility`, `/p7`, `/theses`.

## Source-of-truth map
| kind | where | writer |
|---|---|---|
| scientific status (claims, verdicts, invariants, papers) | `docs/research/dashboard/*.json` + closures/session reports (git) | orders only |
| preregistrations, runs, artifacts, negative results | lab Postgres + MinIO (`logos_research.infra`) | orders' prereg/run scripts |
| MLflow runs | MLflow server (SQLite/file backend today — to verify) | `ResearchRun` |
| governance (provider, flags, caps) | `docs/research/INFERENCE-GOVERNANCE.json` | founder decisions via orders |
| founder selection of theses | `ACTIVE-THESES.json` | dashboard (only write) |
| operational state (queue, jobs, decisions, events) | **does not exist** | — |

## UX problems observed (baseline screenshots `apps/dashboard/e2e/results/screenshots/`)
Registry pages are tables/cards stacked vertically with long hashes; tables use an inner `overflow-x-auto` (page-level overflow passes, but 64-char hashes widen columns); no inspector/detail drawer; sidebar hidden below `md` with no sheet replacement; no live run/queue/trace views; timeline is a flat closure list; Playwright matrix passes for layout but density and language (English) do not match the founder's request (German, denser, statistics).

## Gaps versus the Research-OS target (§99)
No thesis state machine, no work-order lifecycle/DAG, no durable queue or worker, no Claude executor service (only in-order scripts), no MLflow run hierarchy/OTel spans for dashboard-driven runs, no trace explorer, no benchmark lab, no monthly snapshots, no inbox/radar pipeline, no decision center, no notes, no QA page, no German localisation, no chat/run console.
