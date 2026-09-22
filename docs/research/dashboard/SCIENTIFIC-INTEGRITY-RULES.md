# Scientific integrity rules (enforced by `logos_dashboard.registries.validate` and `tests/test_dashboard_scientific_core.py`)

Hard fail on:
1. **claim without evidence** — SUPPORTED / PARTIALLY_SUPPORTED / VALIDATED_IN_FIXTURE / OBSERVED / FALSIFIED / INVALID_MEASUREMENT need `supporting_artifacts` that exist in the repository.
2. **falsified without run** — a FALSIFIED claim names a preregistration hash that an experiment carries, and counterevidence referencing the run.
3. **scope inflation** — every empirical claim carries a `scope`; statements of the form "LLMs do X" are refused.
4. **unsupported novelty** — `STRONG_NOVELTY_EVIDENCE` is never set; a research brief can raise novelty to at most `CLEAR_DIFFERENTIATION` with ≥ 3 sources and an explicit differentiation.
5. **negative result omitted** — negative verdicts must be flagged `negative_result: true` and appear on `/negative-results`.
6. **falsified hypothesis rewritten as supported** — statuses are copied from closures; the validation compares the CPA rerun verdict/hashes with the closure text.
7. **invalid measurement as scientific result** — INVALID_MEASUREMENT claims must say they are not a scientific result.
8. **fixture as production proof** — fixture-scoped claims may not state production proof; nothing is `PRODUCTION_ADOPTED`.
9. **internal replication as external** — `external_researcher` replication requires an external artifact; none exists.
10. **forbidden words** — `PROVEN, CONFIRMED FOREVER, SOLVED, REVOLUTIONARY, BREAKTHROUGH, game-changing, world-first, AGI solved, ultimate architecture` (except inside a verbatim external quote).
11. **broken references** — every artifact, record, evidence path, citation locator, relation target and paper claim must resolve.
12. **readiness inflation** — a paper is PREPRINT_READY only when every preprint criterion is met; no automatic promotion.

Status of hypothesis ≠ strength of evidence: both are shown on every claim. Theory / empirical science / deterministic engineering / governance / speculation are labelled on every claim and experiment. P7: no result is evidence about phenomenal consciousness.
