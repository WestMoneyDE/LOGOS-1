# LOGOS-1 Research Dashboard — Part 1: Status Dashboard (design)

**Date:** 2026-09-18 · **Owner:** founder · **Class:** TOOLING (never PRODUCTION; never imported by `logos_*` production packages) · **Branch:** `tooling/logos-dashboard-part1`
**Decided in brainstorming:** local, founder-only; live from repo files + git/gh + lab DB; lives in this repo (`apps/dashboard` + `src/logos_dashboard`); approach A (Next.js with shadcn preset `b1abNSlea` + Python FastAPI reader); core question "Wo steht die Kette?"; all features A1–D2 and tests T1–T6 in Part 1.

## 1. Purpose

Answer, on one screen and always current: where does the LOGOS-1 chain stand (current order, last verdict, open founder decisions, next order), what is the evidence behind each verdict, are the lab records intact, and what did the real-model runs actually measure. The dashboard **reads and interprets**; the records in `05-WORK-ORDERS/`, `09-SESSIONS/`, `docs/research/*.json` and the lab database stay the single source of truth. Part 1 contains no LLM call and no write path.

## 2. Architecture

```
apps/dashboard                 Next.js (App Router, TypeScript), shadcn preset b1abNSlea, pnpm
  └─ fetches only http://127.0.0.1:8765/api/*  (no file or DB access in the browser)
src/logos_dashboard            FastAPI, read-only, bound to 127.0.0.1:8765, no secrets of its own
  readers/orders.py            05-WORK-ORDERS/NEXT-SESSION-*.md  → OrderClosure
  readers/sessions.py          09-SESSIONS/*/SESSION-REPORT.md    → SessionReport (sections A…AT + key figures)
  readers/registries.py        RESEARCH-DELTA-REGISTRY.json, RESEARCH-RADAR.json, INFERENCE-GOVERNANCE.json,
                               LOGOS-METRIC-CONSTRUCT-REGISTRY.json, *-SOURCE-CLASSIFICATION.json, CANONICAL-EFFECT-OWNER.json,
                               DETERMINISTIC-CHAIN-FROZEN-HASHES.json, RESEARCH-EVIDENCE-STRENGTH.md
  readers/git.py               git log / branches / status / unpushed; gh pr list (PR stack, base/head, state)
  readers/lab.py               Postgres (experiments, preregistrations, runs, artifacts, negative_results) + MLflow runs via
                               logos_research.infra.backends; integrity via resolve_from_experiment_id
  readers/artifacts.py         run artifact JSON / raw invocation JSONL (trial tables, resolution records, counters)
  chain.py                     ChainHead + ordered chain (closure date, base commit, successor links), open founder decisions
  evidence.py                  Evidence graph: Hypothesis → Prereg → Run → Artifact → Verdict → Finding (missing links flagged)
  drift.py                     Drift watch: frozen hashes (preregs, DETERMINISTIC-CHAIN-FROZEN-HASHES) vs working tree
  api.py                       endpoints (§5); OpenAPI schema exported to apps/dashboard/src/api/schema.ts
  cache.py                     per-file mtime cache; lab queries cached 10 s
```

Rules: read-only; localhost only; lab access through the existing `.env` / `backends_from_env` (no new credentials); no `claude` invocation; when the lab is unreachable the service serves **records-only mode** with a banner flag in `/api/health`. Refresh: UI polls `/api/chain` and `/api/health` every 30 s; detail pages fetch on navigation.

## 3. Data model (Pydantic in the service; TypeScript types generated from OpenAPI)

- `OrderClosure`: `id`, `path`, `kind`, `verdict` (string from the record), `verdict_class` ∈ {supported, partial, falsified, invalid, validated, approved, amended, other} (display only), `closed_at`, `base_commit`, `prereg_hashes[]`, `run_ids[]`, `artifact_ids[]`, `successor_id`, `successor_executed: false`, `findings[] {id, severity, text}`, `open_decisions[]`, `preserved[]`, `unparsed[]` (field names the reader could not extract).
- `SessionReport`: `order_id`, `path`, `sections {letter: {title, markdown}}`, `key_figures {counters, tests, run_ids, artifact_ids, integrity_ok}`, `unparsed[]`.
- `ChainHead`: `branch`, `head_commit`, `unpushed_commits`, `dirty_tree`, `latest_closure_id`, `next_work_order {id, executed: false, source_path}`, `pending_founder_decisions[] {text, order_id}`, `recent_verdicts[]`, `claude_code_version` (from the latest closure, never by invoking claude).
- `Delta` (1:1 delta registry), `RadarEntry`, `GovernanceRecord` (G1–G4 active + `superseded`), `MetricRecord` (+ status history by order), `SourceClassification`, `FrozenHash {name, frozen, current, drifted}`.
- `Preregistration {hash, experiment, version, frozen_at, superseded_before_inference: bool, run_id?}`, `LabRun {run_id, experiment, started, finished, verdict?, artifacts[] {id, name, sha256}, integrity_ok, counters, mlflow_run_id?}`, `NegativeResult {id, run_id, severity, text, disposition}`.
- `TrialGrid` (stochastic runs): `cells {condition/stage: {n, metric points + CI}}`, `trials[] {trial_id, prompt_sha256, status, parsed, resolution {status, evidence_class, resolved_model, auxiliary_models}, scaffolding}`.
- `EvidenceChain {order_id, links[] {kind, ref, present: bool}}`, `HypothesisLedger {hypothesis, attempts[] {order_id, verdict, evidence_strength, scope_caveat}, next_falsification}`.
- `DecisionLogEntry {date, owner: "founder", subject, verbatim, source_path, consequence}`, `QuotaSeries {order_id, run_id, invocations, context_tokens, output_tokens, list_price_equivalent_usd, incremental_payg_usd: 0}`.
- `PullRequest {number, title, state, base, head}`, `Commit {sha, subject, date}`, `Health {postgres, mlflow, minio, git, records_only, last_full_suite {passed, failed, skipped, source_order}}`.

Parsing principle: readers use only the stable patterns every closure shares (`**Kind:**`, `**…verdict:**`, `**Closed:**`, `**Base:**`, the `## Closure` code block, `## Successor`, `## Governance question`). Anything not matched lands in `unparsed[]` and is shown as "nicht extrahiert" — never guessed.

## 4. Pages and features

| page | features |
|---|---|
| **Kette** (start) | header: branch, HEAD, unpushed, current order, last verdict, next order (not executed) · **Open decisions** queue (A2 source) · **Chain graph** (A1): orders as nodes coloured by verdict class, successor edges, PR stack columns, repair branches visible · health strip (D1) · "Stand heute" export (D2: markdown + JSON of this page) |
| **Order** | closure block, evidence graph (2b), findings, preserved list, successor, session report rendered per section, preregs/runs/artifacts/PR links, `unparsed` notice |
| **Runs & Lab** | lab table (LabRun), **Run comparison** (B2: two runs side by side — gates, counters, verdict, findings), **Reproducibility card** (code commit, lock hash, dataset/prompt/env hashes, CLI version, pin, counters, integrity) and **Drift watch** (B3: frozen vs current, alarm banner on drift), **Quota monitor** (B4: invocations over orders, context/output tokens per run, list-price equivalent vs incremental PAYG = 0, zero-inference badges) |
| **Trial explorer** | B1: condition × stage heatmap per metric with CIs, confusion matrices, click-through to trial → prompt hash, raw response, parse, resolution, auxiliary models |
| **Hypotheses** | A3 falsification ledger per hypothesis: attempts, verdicts, evidence strength (fixture-scoped / real-model / falsified / invalid), scope caveats, "what falsifies next" (from next-order text) |
| **Deltas & Radar** | delta registry (54) sortable/filterable by track/status/score; radar priorities and invariants |
| **Governance** | G1–G4 active vs superseded with **Diff viewer** (C4), approved flag whitelist, decision log (A2), metric register with status history (C3), source classifications |
| **Registers** | preregistrations (C1, superseded-before-inference marked), findings (C2: severity, order, open/closed), negative results |
| **Git & PRs** | commit log, PR stack #1–#33 (base/head/state) |
| global | **Command palette + full-text search** (C5): orders, runs, findings, hashes → jump to source; every entity shows its record path |

Visual language: the shadcn preset's tokens; verdict classes map to a fixed 7-colour scale defined once; no charts library beyond what the preset ships plus a small SVG heatmap/graph component (no D3 unless the graph needs it — decide in the plan).

## 5. API (all GET, JSON)

`/api/health` · `/api/chain` · `/api/orders` · `/api/orders/{id}` · `/api/orders/{id}/evidence` · `/api/sessions/{id}` · `/api/decisions` · `/api/hypotheses` · `/api/deltas` · `/api/radar` · `/api/governance` (+ `?diff=superseded`) · `/api/metrics` · `/api/classifications` · `/api/preregs` · `/api/findings` · `/api/lab/runs` · `/api/lab/runs/{id}` · `/api/lab/runs/{id}/trials` · `/api/lab/compare?a=&b=` · `/api/drift` · `/api/quota` · `/api/git` · `/api/prs` · `/api/search?q=` · `/api/export/today` (markdown + JSON).

## 6. Error handling

- Reader failures are per record: one malformed closure yields an `OrderClosure` with `unparsed` and an error note, never a 500.
- Lab down → `records_only = true`, lab pages show the banner and cached data if any; drift watch still works (files only).
- `gh` missing/unauthenticated → PR page shows "gh nicht verfügbar"; git errors surface as text.
- No retries against the lab beyond one; no background threads except the mtime cache.

## 7. Testing

- **T1 golden files**: every closure and session report → snapshot JSON under `tests/golden/dashboard/`; regenerated only by an explicit flag.
- **T2 completeness properties** (pytest): every closed order has a verdict from a known vocabulary, an existing session-report path, a successor that exists or is marked not executed; every run with a verdict has an artifact and `integrity_ok`; evidence chains of closed orders have no missing link (or the missing link is listed as a known gap).
- **T3 parser coverage**: per record, fraction of structured fields extracted; exposed in `/api/health` and asserted ≥ 0.9 across the corpus.
- **T4 contract**: OpenAPI snapshot ↔ generated TS types (CI check script).
- **T5 Playwright smoke**: start the service on fixture data, open Kette / Order / Runs / Trial explorer, assert key texts.
- **T6 records-only fallback**: lab backends monkeypatched to fail → all endpoints respond, `records_only = true`.
- Repo guards: `logos_dashboard` added to a `TOOLING_PACKAGES` tuple with an import guard mirroring `experiments.assert_experimental_caller`; source classification `TOOLING` (new vocabulary value) with `UNCLASSIFIED = 0`.

## 8. Out of scope for Part 1

No LLM calls, no writes, no idea intake, no work-order generation, no execution, no MLflow tracing of the dashboard itself, no auth, no deployment.

## 9. Roadmap — Parts 2–4 (feature chains; each gets its own spec → plan)

**Part 4 — Tracing of the dashboard's own LLM interactions (before Part 2)**
- MLflow experiment `logos-dashboard-assistant`; one run per interaction: prompt hash, system-prompt hash, model pin (founder-selected, full name), Claude Code version, resolution record (reuse `result_model`), auxiliary models, tokens, list-price equivalent, `incremental_payg_usd = 0`, session id, working directory, output hash.
- Raw prompt/response stored as artifacts (synthetic/own text only; never repo secrets); linked to the record it produced.
- Same governance boundary as research: Claude Code CLI via Max only, approved flags only, no `ANTHROPIC_API_KEY`, no `--dangerously-skip-permissions`, no `--fallback-model`; isolated working directory; contamination check per call.
- UI: "Assistant traces" page; each generated work order links to its trace.

**Part 2 — Idea intake → work order**
- "Neue Erkenntnis / Idee" form: title, insight, evidence links (order/run/finding picker from Part 1 data), hypothesis draft, constraints.
- Claude (via `claude -p`, structured JSON output, resolver from the repair) drafts a work order in the repo's format: identity, frozen header, question, hypotheses, metrics, gates, verdict vocabulary, "exactly one next order" rule, safety boundary; the founder edits and approves; only then is `05-WORK-ORDERS/<ID>.md` written on a new branch `orders/<id>` with a commit (no push without explicit click).
- Every draft is traced (Part 4); the draft shows which Part-1 records it cited; a "consistency check" runs Part-1 readers on the draft (vocabulary, header, sections) before it can be saved.
- No autonomous execution.

**Part 3 — Work-order execution from the dashboard**
- "Bearbeiten" starts a Claude Code session with the order file as prompt in a fresh worktree, streams `stream-json` (requires founder approval of `--verbose`, and `--allowedTools` scoped to the worktree) into a live view; the dashboard never bypasses permissions; hard caps (invocations, wall clock) and a stop button.
- Governance gates from the order are checked by the harness before start (base commit, clean tree, prereg frozen); results land in the usual records; the dashboard only shows and never edits them.
- This part is the riskiest (autonomous repo changes) and is deliberately last; it needs its own governance decision (which tools, which caps, which branches) before its spec is written.
