# Scientific dashboard — data architecture and schemas

**Order:** `LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1` · **Rule:** Markdown = narrative · JSON registries = structured state · lab artifacts = evidence. The UI never infers a scientific status from free text.

| file | schema | content | who writes it |
|---|---|---|---|
| `CLAIM-REGISTRY.json` | `logos.claim-registry/1` | claims (id, track, type, statement, status, evidence_strength + basis, scope, prereg, artifacts, counterevidence, limitations, falsification test, next test, replication, publication target, kind), tracks, counterexamples | orders (closure) · founder decisions |
| `EXPERIMENT-REGISTRY.json` | `logos.experiment-registry/1` | experiments/repairs/validations with verdict copied from the closure, prereg/run/artifact hashes, controls, metrics, construct status, limitations, next experiment, negative_result flag | orders |
| `INVARIANT-REGISTRY.json` | `logos.invariant-registry/1` | invariants (CANONICAL from GAMMA.md, PROPOSED from the radar) with definition, origin, status, evidence, relations (`supports, depends_on, refines, contradicts, falsified_by, validated_by, scoped_by`) | orders |
| `PRIOR-ART-REGISTRY.json` | `logos.prior-art-registry/1` | citations with claim_supported / claim_not_supported / novelty (`UNKNOWN, POSSIBLE_INCREMENTAL, CLEAR_DIFFERENTIATION, STRONG_NOVELTY_EVIDENCE`) | research briefs after founder review |
| `PUBLICATION-REGISTRY.json` | `logos.publication-registry/1` | paper series with claims, blockers, required experiments/related work/replication, outline, readiness criteria met/missing, manuscript status | orders |
| `REPLICATION-REGISTRY.json` | `logos.replication-registry/1` | per finding: same_model / different_seed / different_model / different_provider / external_researcher, notes, external validation needs | orders |
| `OPEN-QUESTIONS.json` | `logos.open-questions/1` | question, why important, current evidence, missing, minimal decisive experiment, dependency, blocked_by, leverage | orders |
| `ACTIVE-THESES.json` | `logos.active-theses/1` | founder selection of theses to work on (several); selection only | dashboard (`POST /api/theses/active`) |
| `research-briefs/*.json` | `logos.research-brief/1` | deep-research output (sources, synthesis, novelty assessment, limitations, reviewed_by_founder) | `logos-prior-art-research` skill |

## Vocabularies
Status: `PROPOSED OBSERVED PREREGISTERED READY_FOR_DETERMINISTIC_TEST READY_FOR_INFERENCE_TEST VALIDATED_IN_FIXTURE SUPPORTED PARTIALLY_SUPPORTED FALSIFIED INVALID_MEASUREMENT INCONCLUSIVE BLOCKED_BY_GOVERNANCE BLOCKED_BY_INFERENCE EXTERNALLY_REPLICATED` · Strength: `PRELIMINARY LOW LOW_TO_MEDIUM MEDIUM MEDIUM_TO_HIGH HIGH INDEPENDENTLY_REPLICATED` (basis: independent tests, falsification attempts, sample size, construct validity, causal discrimination, replication, external validation, measurement quality) · Kind: `THEORY EMPIRICAL_SCIENCE DETERMINISTIC_ENGINEERING GOVERNANCE SPECULATION` · Manuscript: `NOT_READY INTERNAL_DRAFT PREPRINT_READY EXTERNAL_REPLICATION_NEEDED WORKSHOP_READY SUBMISSION_READY`.

## Service and UI
`src/logos_dashboard` (FastAPI, TOOLING, localhost:8765): `registries.py` (load + `validate()` integrity rules + counts), `readers.py` (closures, session reports, git/gh, lab), `research_intake.py` (queue, brief validation, merge), `api.py` (routes). `apps/dashboard` (Next.js 16, shadcn preset `b1abNSlea`, style base-sera): routes `/`, `/tracks`, `/tracks/{authority|provenance|cognitive-provenance|measurement|memory|trajectory}`, `/claims`, `/claims/[id]`, `/experiments`, `/experiments/[id]`, `/invariants` (graph), `/counterexamples`, `/negative-results`, `/falsification`, `/replication`, `/publications`, `/publications/[id]` (export), `/prior-art`, `/open-questions`, `/research`, `/timeline`, `/reproducibility`, `/p7`, `/theses`.

Run: `PYTHONPATH=src uvicorn logos_dashboard.api:app --host 127.0.0.1 --port 8765` and `cd apps/dashboard && pnpm dev`.
