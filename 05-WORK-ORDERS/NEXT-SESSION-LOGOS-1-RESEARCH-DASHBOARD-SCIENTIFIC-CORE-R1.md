# NEXT SESSION — LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1

**Kind:** tooling + structured scientific state; no scientific status changed; no model call
**Verdict:** `DASHBOARD_SCIENTIFIC_CORE_PHASE1_COMPLETE`
**Closed:** 2026-09-19 by `09-SESSIONS/2026-09-19-LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1/`
**Base:** `88d4757` · branch `tooling/logos-dashboard-part1` · PR #34

## Closure

```text
registries  docs/research/dashboard: CLAIM (23 + 7 counterexamples), EXPERIMENT (22), INVARIANT (30), PRIOR-ART (14, no systematic search yet), PUBLICATION (6: 3 INTERNAL_DRAFT, 3 NOT_READY),
            REPLICATION (7; 0/5 real-model, 1/5 deterministic), OPEN-QUESTIONS (7), ACTIVE-THESES, schema/integrity/roadmap docs
service     src/logos_dashboard (FastAPI, TOOLING, import guard): registries + validate() (0 violations), readers (closures/sessions/git/gh/lab, records-only fallback),
            research_intake (queue 24 tasks, brief validation, founder-reviewed merge), api (29 routes + theses selection + research queue + paper export)
ui          apps/dashboard (Next.js 16 + shadcn preset b1abNSlea): overview, tracks x6, claims, claim detail (evidence graph), experiments, invariants (interactive graph),
            counterexamples, negative results, falsification ("what could prove us wrong?"), replication, publications + export, prior art, open questions, research queue,
            timeline, reproducibility, P7, theses (multi-select; selection only) — all 26 routes 200; next build OK
integrity   status != strength on every claim; THEORY/EMPIRICAL/ENGINEERING/GOVERNANCE labels; forbidden words absent; every artifact/record/citation/relation resolves
skill       deep-research installed (skillfish) + project skill logos-prior-art-research (briefs never edit registries; novelty <= CLEAR_DIFFERENTIATION)
tests       tests/test_dashboard_scientific_core.py 48 passed; full suite 4320 passed (+ one predecessor diff-scope registration); UNCLASSIFIED = 0 (DASHBOARD-SOURCE-CLASSIFICATION.json)
preserved   Γ, P7, production packages, every verdict and prereg — unchanged; PRODUCTION_PACKAGES untouched
first-milestone depth  authority / provenance / cognitive-provenance complete per Section 40; measurement / memory / trajectory populated at lower depth
```

## Definition of Done (§41) — answerable from the dashboard without the author
What exactly is claimed → `/claims` (23, each with statement, scope, status, strength) · strongest claim → LOGOS-AUTH-001 (MEDIUM_TO_HIGH, fixture) and LOGOS-P7-001 (HIGH, boundary) · still hypotheses → PROPOSED/READY_* rows · falsified → `/negative-results` (RAD, BSP, CPA run 1 invalid, CPA rerun falsified with floor) · raw evidence → artifact paths and hashes on every claim/experiment, `/reproducibility` · what falsifies each claim → `/falsification` · difference from prior work → `/prior-art` (honestly: no systematic search yet; 24 queued tasks) · external replication needs → `/replication` · which paper can be written now → none PREPRINT_READY; PAPER-2/3 INTERNAL_DRAFT with explicit missing criteria.

## Run
`PYTHONPATH=src .venv/Scripts/python.exe -m uvicorn logos_dashboard.api:app --host 127.0.0.1 --port 8765` · `cd apps/dashboard && pnpm dev` (deps: `requirements-dashboard.txt`, `pnpm install`).

## Successor (exactly one, NOT executed)
`COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1` — missing falsification test for the strongest empirical claim (§45 priority 1). Not started here.
