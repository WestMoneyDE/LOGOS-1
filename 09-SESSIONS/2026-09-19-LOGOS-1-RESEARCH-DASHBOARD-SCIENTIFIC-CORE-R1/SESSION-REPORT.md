# SESSION REPORT — LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1

**Kind:** tooling + structured scientific state (no scientific status changed; no model call; no production package touched)
**Verdict:** `DASHBOARD_SCIENTIFIC_CORE_PHASE1_COMPLETE` (Definition of Done §41 checked below)
**Base:** `88d4757` (design spec on `tooling/logos-dashboard-part1`) · **Branch:** `tooling/logos-dashboard-part1` · **PR:** #34 (base PR #33)
**Stack:** Next.js 16.3 (App Router, TypeScript) + shadcn preset `b1abNSlea` (style base-sera, Inter, teal primary) in `apps/dashboard`; FastAPI service `src/logos_dashboard` on `127.0.0.1:8765`; registries in `docs/research/dashboard/`.

## A. Dashboard stack / architecture
Markdown = narrative, JSON registries = structured state, lab artifacts = evidence. Service reads registries, closures, session reports, git/gh and the lab (records-only fallback); the UI reads the service only. The one write path is the founder's thesis selection (`POST /api/theses/active` → `ACTIVE-THESES.json`). Import guard: `logos_dashboard` is TOOLING and refuses import from production packages.

## B. Existing components reused
No dashboard existed before; the approved Part-1 design spec (`docs/superpowers/specs/2026-09-18-logos-dashboard-part1-design.md`) supplied the architecture. Reused from the repository: `logos_research.infra.backends` (lab access), the closure/session record formats, `RESEARCH-RADAR.json` (RD/RI ids, evidence-strength vocabulary), `DETERMINISTIC-CHAIN-CONSOLIDATION.json`, `COUNTEREXAMPLE-REGISTRY.md`, `RESIDUAL-RISK-REGISTRY.md`, `DETERMINISTIC-CHAIN-EVIDENCE-MATRIX.md`, `LOGOS-METRIC-CONSTRUCT-REGISTRY.json`, the shadcn preset (badge, button, card, table, tabs, command, dialog, tooltip, …).

## C. New structured registries (`docs/research/dashboard/`)
`CLAIM-REGISTRY.json` (23 claims + 7 counterexamples + 6 tracks), `EXPERIMENT-REGISTRY.json` (22), `INVARIANT-REGISTRY.json` (30, 7 relation types), `PRIOR-ART-REGISTRY.json` (14 real references; `search_status = NO SYSTEMATIC …`), `PUBLICATION-REGISTRY.json` (6 papers), `REPLICATION-REGISTRY.json` (7 findings), `OPEN-QUESTIONS.json` (7), `ACTIVE-THESES.json`, `research-briefs/` (empty), plus `SCIENTIFIC-DASHBOARD-SCHEMA.md`, `SCIENTIFIC-INTEGRITY-RULES.md`, `PUBLICATION-ROADMAP.md`.

## D. Claim count by status
SUPPORTED 7 · VALIDATED_IN_FIXTURE 4 · OBSERVED 3 · READY_FOR_DETERMINISTIC_TEST 3 · PARTIALLY_SUPPORTED 2 · FALSIFIED 1 · INVALID_MEASUREMENT 1 · READY_FOR_INFERENCE_TEST 1 · PROPOSED 1 (total 23). Strength: HIGH 2 · MEDIUM_TO_HIGH 3 · MEDIUM 12 · LOW_TO_MEDIUM 5 · PRELIMINARY 1. No claim is `INDEPENDENTLY_REPLICATED`.

## E. Experiment count by verdict
22 entries: SUPPORTED 3, FALSIFIED 2, PARTIALLY_SUPPORTED 1, INVALID_MEASUREMENT 1, COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1 1, REPAIR_FALSIFIED 1, REPAIR_R2_VALIDATED 1, REPAIR_VALIDATED 1, two REPAIR_*_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED, CPA_INSTRUMENT_REPAIR_VALIDATED_R1 1, PRODUCTION_BRIDGE_VALIDATED_R1 1, OWNER_IMPLEMENTATION_VALIDATED 1, CONSOLIDATED 1, CAUSAL_TAINT_PROPAGATION_SUPPORTED 1, RECONSOLIDATION_GOVERNANCE_SUPPORTED 1, TRAJECTORY_COMPROMISE_BOUNDARIES_SUPPORTED 1, CONSTRUCT_VALIDITY_GATE_VALIDATED 1. Verdict strings are copied from the closures.

## F. Invariant count — 30 (CANONICAL 9 incl. Γ-1 and P7; PROPOSED 21): VALIDATED_IN_FIXTURE 12, SUPPORTED 6, READY_FOR_DETERMINISTIC_TEST 6, READY_FOR_INFERENCE_TEST 2, OBSERVED 2, FALSIFIED 1 (ReasoningContent != ReasoningProvenance), PROPOSED 1.
## G. Negative-results coverage — 5 experiments flagged negative (BSP-R1, BSP-VAL-R1, RAD-R1, CPA-R1, CPA-RERUN) + REPAIR_FALSIFIED; page `/negative-results` with "why it matters / learned / changed next" and the lab's negative-result records (213 rows).
## H. Counterexample coverage — CE1, VCE-1, RAD-CE1, MBGV-F1, DCC-F1, CPA-F5, CPA attribution floor: counterexample → violated assumption → severity → repair → validation → remaining risk → learned.
## I. Authority track completeness — 6 claims, 15 experiments/repairs/validations, 9 invariants, 5 counterexamples, 2 citations, 2 open questions, PAPER-2 (INTERNAL_DRAFT).
## J. Provenance track completeness — 3 claims, 2 experiments (CTP; TCA secondary), 3 invariants, 3 citations, 1 open question, PAPER-5 (NOT_READY).
## K. Cognitive provenance completeness — 4 claims (H1 FALSIFIED with floor caveat; baseline disregard OBSERVED; three-construct separation PROPOSED; instrument defect INVALID_MEASUREMENT), 3 experiments (invalid run, repair, rerun), 3 invariants, 2 citations, 1 open question, PAPER-3 (INTERNAL_DRAFT); next falsification `COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`.
## L. Measurement track — 3 claims, 2 experiments, 5 invariants, 4 citations, 2 open questions, PAPER-4 (NOT_READY).
## M. Memory track — 3 claims, 2 experiments (RPD; CTP secondary), 5 invariants, 1 citation, 1 open question, PAPER-5.
## N. Trajectory track — 3 claims, 1 experiment, 4 invariants, 2 citations, 0 open questions (gap), PAPER-6 (NOT_READY).
## O. Prior-art coverage — 14 references (Saltzer & Schroeder, Miller, Denning, Myers & Liskov, Buneman et al., Greshake et al., Turpin et al., Kadavath et al., Cronbach & Meehl, Nosek et al., Nader et al., Ha & Schmidhuber, Amodei et al., Popper); novelty ≤ CLEAR_DIFFERENTIATION (only PA-006); **no systematic search performed yet** — 24 research-queue tasks generated for the `logos-prior-art-research` skill (wraps the installed `deep-research` skill; firecrawl/exa MCPs not configured → WebSearch/WebFetch fallback recorded in briefs).
## P. Publication candidates — PAPER-1/2/3 INTERNAL_DRAFT, PAPER-4/5/6 NOT_READY; readiness criteria explicit; export endpoint produces a Markdown research brief per paper (claim/evidence table, experiments, limitations, related-work matrix, blockers, outline).
## Q. Publication readiness gaps — every paper misses a related-work matrix and a reproducibility package; PAPER-4/5/6 additionally miss evidence beyond fixtures / negative evidence; PAPER-3 depends on the attribution-floor order; none is PREPRINT_READY.
## R. Replication gaps — real-model findings 0/5; deterministic findings 1/5 (same-model = independent validation orders in this repository); no different-model/provider/external replication anywhere; queue: different model, different provider, external dataset, independent lab, peer review, formal proof, larger N.
## S. Integrity checks — `registries.validate()` = 0 violations (12 rule families: evidence, falsified→run, scope, novelty, negative omitted, status copied, invalid ≠ result, fixture ≠ production, external replication, forbidden words, broken references, readiness inflation).
## T. Test results — `tests/test_dashboard_scientific_core.py` 48 passed (validation, integrity, 29 API routes, track completeness, theses roundtrip, records-only fallback, tooling guard, research intake, classification); affected predecessor suites green after registering repair/dashboard records in one diff scope; full suite 4320 passed + that registration; `next build` OK; all 26 required routes return 200 against the live service.
## U. Remaining scientific blockers — (1) attribution floor unexplained (largest bottleneck; PAPER-3); (2) no real-model actor behind the bridge (PAPER-2 scope); (3) no non-fixture construct validation (PAPER-4); (4) no systematic related-work search (all papers); (5) `--verbose` governance decision for Tier-1 producer evidence; (6) trajectory track has no open question recorded.

## Founder request beyond the order
"Click which thesis to work on, several at once" → `/theses`: multi-select of hypothesis/invariant/architecture claims, saved to `ACTIVE-THESES.json`, shown on the overview with each thesis's next falsification test. Execution is deliberately **not** started from the dashboard (Part 3 of the roadmap needs its own governance decision).
"Integrate deep-research for the dashboard workflows" → project skill `.claude/skills/logos-prior-art-research` + `research_intake.py` (queue from the claim registry, brief schema, validation, founder-reviewed merge into PRIOR-ART-REGISTRY; novelty never STRONG) + page `/research`.

## V. Exactly one next work order (not executed)
**`COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`** — the missing falsification test for the strongest empirical claim (priority 1 of §45): probe-wording arm (input-presence vs reliance), non-tie design where the plan target is correct only when the plan is used, optional two-turn arm if `--verbose`/`--resume` are approved; same founder pin `claude-opus-5`, new preregistration, ≤ 200 invocations. Already named by the repair order; confirmed here as the largest scientific bottleneck.
