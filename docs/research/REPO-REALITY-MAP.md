# LOGOS-1 Repository Reality Map

**Session:** Master Work Order — Research/Falsification/Evaluation/Persistence/Sandbox infrastructure, Phase Zero.
**Repo state at audit:** `b0f2b20` (`main`, clean, synchronized with `origin/main`).
**Audit scope:** whole repository, excluding `.git`.
**Status of this document:** repository forensics only. No infrastructure was implemented in the audited state.

```text
AuditFinding != ScientificClaim
Documented != Implemented
Implemented != Validated
```

## 0. Method

Every entry is rated with exactly one of:

| Rating | Meaning |
|---|---|
| `EXISTS` | implemented in-repo and covered by a runnable test or a byte-verifiable artifact |
| `PARTIAL` | implementation exists but does not satisfy the architecture it is documented against |
| `SPECIFIED` | documented/contracted in-repo but not implemented here |
| `HYPOTHETICAL` | research proposal or open queue item only |
| `UNKNOWN` | cannot be established from this repository |

`SPECIFIED` is frequently the correct rating rather than a gap: `AGENTS.md` states that this GitHub repository is the **compact** projection of a larger transported project state, and that the active work order plus session/evidence records are the authoritative navigation path here.

## 1. Measured baseline

```text
top-level dirs      00-MAIN-STATE 05-WORK-ORDERS 09-SESSIONS assets docs
                    external-handoff external-runs src tests
markdown files      67
python files        31  (12 src, 8 tests, 5 external-handoff/common, 6 external-runs)
yaml/json files     34
pytest              112 passed / 0 failed   (Python 3.12.8)
CI workflows        3   (all external scientific execution, all workflow_dispatch)
```

Installed and available in the audited environment: `numpy 2.2.6`, `scipy 1.17.0`,
`pandas 3.0.0`, `pydantic 2.13.4`, `torch 2.6.0+cu124`, `pytest 9.1.1`.
Not present: `hypothesis`, `ruff`, `mypy`/`pyright`, `mlflow`, `dvc`, any database driver,
any OpenTelemetry or Langfuse package.

`pyproject.toml` declares a single distribution `logos-pstate-adapters` with **no
runtime dependencies** and only a `pytest` configuration. There is no lockfile,
no dependency pin set and no packaging of `logos_memory`.

## 2. Canonical owners already established

The repository already has a single named owner for most concerns the master work
order asks to create. These owners must be extended, not duplicated.

| Concern | Canonical owner in-repo | Rating |
|---|---|---|
| Invariant safety kernel / inference boundary | `GAMMA.md` (Γ-v0.2, Γ-0 … Γ-14) | `EXISTS` as specification |
| Agent operating contract, 16 atomic rules | `AGENTS.md` | `EXISTS` |
| Coding-agent contract | `CLAUDE.md` | `EXISTS` |
| Active research queue | `CURRENT-WORK-ORDER.md` + `05-WORK-ORDERS/` | `EXISTS` |
| Durable run/evidence persistence | `09-SESSIONS/<SESSION-ID>/` | `EXISTS` |
| Capability inventory | `CAPABILITIES.md` | `EXISTS` |
| Evidence maturity ladder `EM0..EM3` | `README.md` evidence table | `EXISTS` |
| Change propagation / push discipline | `docs/engineering/PUSH-PROTOCOL.md` | `EXISTS` |
| External-execution boundary ("sandbox") | `external-handoff/` + `.github/workflows/` | `EXISTS` |
| Cross-track experiment index | `external-handoff/TRACK-REGISTRY.json` | `EXISTS` |
| Pre-registration | `external-runs/*/FROZEN-EXPERIMENT.json`, `external-runs/enf-r1/PREREGISTRATION.md` | `EXISTS` |
| Memory substrate | `src/logos_memory/` + `docs/architecture/MEMORY-SYSTEM.md` | `EXISTS` |
| Scope/precondition gate | `src/logos_memory/scope.py` + `docs/architecture/SCOPE-ENGINE.md` | `EXISTS` |
| Persistent-state intervention adapters | `src/logos_pstate/` + `docs/architecture/PERSISTENT-STATE-ADAPTERS.md` | `EXISTS` |
| Engineering roadmap | `docs/engineering/CODING-READY-ROADMAP.md` | `EXISTS` |

## 3. Concept-by-concept map

### 3.1 State, memory, persistence

| Concept | Rating | Evidence |
|---|---|---|
| Memory record with provenance, append-only JSONL store | `EXISTS` | `src/logos_memory/store.py`, `records.py`; `tests/test_memory_store.py` |
| Guarded consolidation with conflict retention, weakest-authority intersection | `EXISTS` | `src/logos_memory/consolidation.py`, `factory.py`; `tests/test_memory_factory.py` |
| Deterministic scope-first BM25 retrieval, expiring minimum-context projections | `EXISTS` | `src/logos_memory/retrieval.py`; `tests/test_memory_factory.py` |
| Crash/restart recovery and coding-agent replay | `EXISTS` | `tests/test_memory_recovery.py` |
| Authority firewall (`memory` does not mint grants) | `EXISTS` | `src/logos_memory/store.py`, `scope.py`; `docs/architecture/MEMORY-SYSTEM.md` authority-firewall section |
| Six-way memory decomposition (working / episodic / semantic / procedural / evidence / governance) | `EXISTS` | `docs/architecture/MEMORY-SYSTEM.md` functional concerns |
| Token-context intervention adapter (full / 512-truncation / A-to-B substitution) | `EXISTS` | `src/logos_pstate/token_context.py`; `tests/test_token_context.py` |
| Deterministic BM25 external-retrieval adapter with prompt/source hashes | `EXISTS` | `src/logos_pstate/retrieval.py`; `tests/test_retrieval.py` |
| Recurrent latent state capture/restore/fresh/swap/permute/digest (Mamba) | `PARTIAL` | `src/logos_pstate/mamba_state.py`; static tests pass, **real model never executed** |
| Fast-weight / TTT adapter | `SPECIFIED` | `TTT_R3 = SOURCE_ADAPTER_UNRESOLVED` (`CURRENT-WORK-ORDER.md`) |
| RULER dataset freeze utility (file + per-row SHA-256) | `EXISTS` | `src/logos_pstate/ruler_freeze.py`; `tests/test_ruler_freeze.py` |
| RULER materialized dataset hashes | `SPECIFIED` | `RULER_DATASET_FREEZE_R3 = NOT_MATERIALIZED_RESOURCE_TRANSPORT`; blocking gate of R4 |
| D/O/C validation ladder (`Decodable` / `Operational` / `Causal`) | `SPECIFIED` | `CAPABILITIES.md`; `docs/architecture/PERSISTENT-STATE-ADAPTERS.md` |
| Explicit **state taxonomy** across the 18 classes the master order names | `PARTIAL` | four persistent-state families plus six memory concerns exist; `ControlState`, `SelfState`, `BeliefState`, `WorldState`, `CalibrationState`, `MeasurementInstrumentState`, `HarnessState`, `RelationalState` are **not** canonically typed anywhere |

### 3.2 Governance, authority, safety

| Concept | Rating | Evidence |
|---|---|---|
| Γ five-stage gate `{ALLOW, REPAIR, DEFER, DENY, FALLBACK}` | `SPECIFIED` | `GAMMA.md`; **no Γ kernel source exists in this repository** |
| Mediation completeness `MC = 1` audit | `SPECIFIED` | `GAMMA.md` mediation-completeness section |
| Occurrence-scoped authorization, `OUTCOME_UNKNOWN != NOT_EXECUTED` | `SPECIFIED` | Γ-10, Γ-11 |
| `ScopeDecision` typed intersection and fail-closed evaluation | `EXISTS` | `src/logos_memory/scope.py`; `tests/test_scope_engine.py` |
| Dispatch/effect gate beyond scope (budgets, time validity, externality, reversibility, approval) | `SPECIFIED` | explicitly disclaimed in `AGENTS.md`, `CLAUDE.md`, `CAPABILITIES.md` |
| ADR-0001, ADR-0002 | `UNKNOWN` | cited by `GAMMA.md`; **no `adr/` or `decisions/` directory exists here** |
| `governance/SPECIFICATION-ASSURANCE.md` (Γ-13) | `UNKNOWN` | referenced, absent from this repository |
| `research/biocode/BIOCODE-GAMMA-BOUNDARY-AUDIT.md` (Γ-14) | `UNKNOWN` | referenced, absent from this repository |

**This is the single largest structural finding.** The repository's most load-bearing
safety artifact, Γ, is fully specified and mathematically detailed but has **no
executable implementation in this repository**, and three documents it cites as
its own evidence base are not present here. Any infrastructure that claimed Γ
mediation inside this repo would be asserting a property nothing here can check.

### 3.3 Experiment, falsification, evidence

| Concept | Rating | Evidence |
|---|---|---|
| Pre-registration with frozen null hypothesis, arms, metrics, kill rules | `EXISTS` | `external-runs/wmr-r1/FROZEN-EXPERIMENT.json`, `external-runs/mbe-r1/FROZEN-EXPERIMENT.json`, `external-runs/enf-r1/PREREGISTRATION.md` |
| Immutability of frozen criteria | `EXISTS` (enforced by hash, not by code) | SHA-256 of each frozen file verified in the matching `.github/workflows/*.yml` before execution |
| Equal-information / equal-budget contract between arms | `EXISTS` | `equal_information_resource_contract` in `FROZEN-EXPERIMENT.json` |
| Kill rules / falsification criteria per experiment | `EXISTS` | `kill_rules` block |
| Distinction transport failure vs. negative evidence | `EXISTS` | `UNTESTED_RESOURCE_TRANSPORT` across `TRACK-REGISTRY.json`, work orders, sessions |
| Machine-readable **cross-experiment** manifest schema | `PARTIAL` | each `FROZEN-EXPERIMENT.json` declares its own `schema:` string; there is no shared schema, no validator and no schema version registry |
| Queryable experiment registry | `PARTIAL` | `external-handoff/TRACK-REGISTRY.json` is a hand-maintained index; no query interface, no code reads it |
| Evidence maturity ladder | `EXISTS` | `README.md`; applied consistently (`RULER <= EM1`) |
| Negative-result registry | `PARTIAL` | negative and parked outcomes are preserved in `09-SESSIONS/` and `TRACK-REGISTRY.json`, but there is no `research/negative-results/` and no discoverability mechanism beyond grep |
| Claim-to-evidence graph | `SPECIFIED` | `CAPABILITIES.md` carries claim-status prose and an "Explicitly not claimed" section; there is no `claim_id` and no machine-readable link from a README claim to an experiment |
| Instrument-first validation (characterize evaluator before use) | `HYPOTHETICAL` | the principle appears in prose; no repeatability/bias/false-positive characterization of any evaluator exists |
| `INVALID_MEASUREMENT` as an outcome distinct from falsification | `SPECIFIED` | `UNTESTED_RESOURCE_TRANSPORT` covers transport failure; measurement-instability failure has **no** distinct outcome value anywhere |
| Statistical validation (CIs, bootstrap, effect sizes, permutation) | `UNKNOWN` | not present in the audited code; may exist in returned external bundles not mirrored here |
| Seed sweeps | `EXISTS` | `seeds: [73000..73003]` frozen in WMR and persistent-state envelopes |
| Benchmark-leakage discipline | `EXISTS` | atomic rule 12; `validate_source_isolation.py`; `source_leakage` kill rule |

### 3.4 Sandbox and execution isolation

| Concept | Rating | Evidence |
|---|---|---|
| External-action boundary as policy | `EXISTS` | `AGENTS.md` external-action boundary; `TRACK-REGISTRY.json` `default_mode: PLAN_ONLY` |
| One-shot / no-auto-retry execution discipline | `EXISTS` | atomic rule 16; `PUSH-PROTOCOL.md` section 3 |
| Level-0 deterministic simulation | `EXISTS` | all 112 tests are offline, fixture-based, network-free |
| Level-1 container sandbox | `PARTIAL` | GitHub Actions `ubuntu-24.04`, `permissions: contents: read`, pinned `PYTHONHASHSEED`, hash-verified inputs — but this is a CI runner, not a declared sandbox profile; no CPU/RAM/PID quota, no seccomp, no capability drop, no read-only root |
| Level-2 controlled egress with allowlist and request logging | `SPECIFIED` | source pins are exact and verified post-clone, but egress inside the runner is unrestricted and unrecorded |
| Level-3 strong isolation (gVisor / Firecracker / Kata) | `HYPOTHETICAL` | absent |
| Tool-action classification `PURE / REVERSIBLE / MUTATING / EXTERNAL / IRREVERSIBLE` | `SPECIFIED` | conceptually implied by Γ0 effect classification; not implemented, no `Mock` / `Sandbox` / `Real` adapter triad exists |
| Secret discipline | `EXISTS` | `external-handoff/ENV.example` (names only); "never store API-key values in return bundles" in `TRACK-REGISTRY.json`; no secret found in the audited tree |

### 3.5 Observability, reproducibility, tooling

| Concept | Rating | Evidence |
|---|---|---|
| Content-hash provenance for code and data | `EXISTS` | SHA-256 verification of every frozen file in each workflow; `hash_path.py`; `ruler_freeze.py` |
| Git/source pinning of external dependencies | `EXISTS` | exact commit checkout plus `rev-parse` assertion in workflows; `verify_git_pin.py` |
| Return-bundle packing and validation | `EXISTS` | `external-handoff/common/{handoff,collect_return,validate_return}.py` |
| Deterministic execution controls (`PYTHONHASHSEED`, frozen seeds) | `EXISTS` | workflows plus frozen envelopes |
| Environment hash / dependency lock / container digest capture | `PARTIAL` | Python version is pinned in CI; there is no lockfile, no image digest, no environment hash |
| Structured tracing (OpenTelemetry) | `HYPOTHETICAL` | absent |
| LLM-trace observability (Langfuse) | `HYPOTHETICAL` | absent |
| Metrics stack (Prometheus / Grafana / Loki) | `HYPOTHETICAL` | absent |
| Experiment tracking (MLflow) | `HYPOTHETICAL` | absent |
| Data versioning (DVC) | `HYPOTHETICAL` | absent |
| Relational persistence (PostgreSQL) | `HYPOTHETICAL` | absent; current canonical persistence is git-tracked JSON/JSONL/Markdown |
| Object storage (MinIO / S3) | `HYPOTHETICAL` | absent |
| Research CLI | `HYPOTHETICAL` | absent; no console entry point in `pyproject.toml` |
| Lint / typecheck / security CI gates | `HYPOTHETICAL` | absent; the three workflows are scientific execution only, none runs `pytest` |
| Property-based testing | `HYPOTHETICAL` | absent; `hypothesis` is not a dependency |
| Fault-injection suite | `PARTIAL` | `tests/test_memory_recovery.py` covers restart/replay; there is no reusable injector for stale/corrupt/conflicting evidence, expired authority, dropped messages or crashed orchestrators |

### 3.6 Consciousness-adjacent research tracks

| Track | Rating | Evidence |
|---|---|---|
| Inference boundary `FunctionalArchitecture != PhenomenalExperience` | `EXISTS` | `README.md` invariants; atomic rule 5; Γ-8; `CAPABILITIES.md` "Explicitly not claimed" |
| CPV as functional marker vector, explicitly not a sentience score | `SPECIFIED` | atomic rule 5; no CPV implementation in this repo |
| Persistent-state track (token / recurrent / fast-weight / retrieval) | `PARTIAL` | adapters implemented, **no model benchmark executed**; `R4` is the blocking gate |
| World-model track (prediction vs. intervention) | `PARTIAL` | WMR-R2 executed and imported at `EM2`, on next-frame prediction only; `P(s'|do(a),s)` vs `P(s'|s)` is not separated |
| Metacognition / calibration | `PARTIAL` | MBE behavioral-lift evidence imported at `EM2`; multi-probe stability of any metacognition indicator is **not** established |
| Self-model track (baselines, causality, lesions) | `HYPOTHETICAL` | no `SelfState` type, no self-model baseline ladder, no lesion protocol |
| Global-workspace track | `HYPOTHETICAL` | the term does not appear anywhere in the repository |
| Multi-agent integration / emergence | `HYPOTHETICAL` | one incidental mention; no population harness, no emergence controls |
| IIT / integration measures | `HYPOTHETICAL` | mentioned as prior-art context only |
| Free energy / active inference | `HYPOTHETICAL` | the ENF track is a **safety-boundary** experiment (`safe-control-gym`), not an active-inference agent study |
| Zombie / minimal-function controls | `HYPOTHETICAL` | the negative-control principle exists per experiment; no reusable minimal-architecture control suite |

## 4. Missing infrastructure, ranked by load-bearing weight

1. **No cross-experiment manifest schema or validator.** Each frozen experiment
   invents its own shape. Nothing prevents a future experiment from omitting a
   null hypothesis, a kill rule or a baseline.
2. **No `INVALID_MEASUREMENT` outcome.** The repo distinguishes transport failure
   from a scientific null, but cannot distinguish *"the instrument is noisier than
   the effect"* from *"the hypothesis is false"*.
3. **No instrument characterization step.** No evaluator in this repository has a
   measured repeatability, bias or false-positive rate.
4. **No machine-readable claim-to-evidence graph.** README and `CAPABILITIES.md`
   claims are governed by prose discipline and human diligence only.
5. **No declared sandbox profile.** Isolation is currently an emergent property of
   GitHub Actions defaults rather than a stated, testable contract.
6. **No quality-gate CI.** 112 tests exist and pass locally; no workflow runs them.
7. **No dependency lock or environment hash.** Source pins for *external* material
   are excellent; the repo's *own* environment is unpinned.
8. **No property-based invariant tests** for the separations the project treats as
   non-negotiable (`Capability != Authority`, provenance preservation under
   transformation, expiry, revocation transitivity).
9. **No typed state taxonomy** beyond memory concerns and persistent-state families.
10. **No Γ implementation in this repository**, while Γ is cited as the mediating
    authority of every effect path.

## 5. Duplication hazards for any follow-up work

Any new subsystem must be checked against these existing owners before creation:

```text
new experiment registry   -> duplicates external-handoff/TRACK-REGISTRY.json
new session/run store     -> duplicates 09-SESSIONS/
new memory store          -> duplicates src/logos_memory/store.py
new scope/permission type -> duplicates src/logos_memory/scope.py
new capability list       -> duplicates CAPABILITIES.md
new evidence tier scheme  -> duplicates README.md EM0..EM3
new work queue            -> duplicates CURRENT-WORK-ORDER.md + 05-WORK-ORDERS/
new push/propagation rule -> duplicates docs/engineering/PUSH-PROTOCOL.md
new authority concept     -> duplicates GAMMA.md (specification owner)
```

## 6. Architecture conflicts to resolve before implementation

| # | Conflict | Detail |
|---|---|---|
| C1 | Canonical persistence | The current truth store is **git-tracked JSON/JSONL/Markdown**, hash-verified and reviewable in a PR diff. A service-backed registry (PostgreSQL, MLflow, MinIO) would move experiment truth out of the reviewable diff and out of the one-shot external-execution model. |
| C2 | Sandbox level | `AGENTS.md` requires a **separate safety review** before any network/shell/deployment tooling. Provisioning containers, egress proxies or a service stack is exactly that class of change. |
| C3 | Γ ownership | Γ is `SPECIFIED` here and implemented (if at all) in the transported full project state. Implementing a Γ-like gate inside this repo would create a second authority owner and violate single-ownership. |
| C4 | Work-queue precedence | `CURRENT-WORK-ORDER.md` is `READY_PERSISTENT_STATE_DATASET_MATERIALIZATION_R4`. `AGENTS.md` coding-agent rule 1 forbids silently replacing the active scientific queue. |
| C5 | New dependencies | The repo currently has **zero runtime dependencies**. Every proposed tool must map to a stated requirement. |

## 7. What this audit does not establish

- whether Γ, ADR-0001/0002, `governance/SPECIFICATION-ASSURANCE.md` or the BIOCODE
  boundary audit are implemented in the transported full project state (`UNKNOWN`);
- whether external return bundles contain statistical analysis not mirrored here;
- any scientific verdict whatsoever. This document changes no Γ verdict.
  `Γ-v0.3` remains `HOLD`.

```text
RepoForensics != Evidence
AbsenceInCompactRepo != AbsenceInProject
```

---

## Addendum — 2026-09-10

The Phase-Zero audit above describes commit `b0f2b20` and is left unedited. Two
later sessions closed some of the gaps it identified. Re-rated:

| Gap (section 4) | Was | Now | Owner |
|---|---|---|---|
| 1. no cross-experiment manifest schema | missing | `EXISTS` | `logos_research.manifest` |
| 2. no `INVALID_MEASUREMENT` outcome | missing | `EXISTS` | `logos_research.manifest.Outcome` |
| 3. no instrument characterization | missing | `EXISTS` | `logos_research.instrument` |
| 4. no claim-to-evidence graph | missing | `PARTIAL` | `logos_research.claims`; README not yet derived from it |
| 5. no declared sandbox profile | missing | `PARTIAL` | `logos_research.sandbox`; L0 only |
| 6. no quality-gate CI | missing | still missing | — |
| 7. no dependency lock | missing | still missing | — |
| 8. no property-based invariant tests | missing | `EXISTS` | `hypothesis`, across Γ and research tests |
| 9. no typed state taxonomy | missing | still missing | — |
| 10. no Γ implementation | missing | `PARTIAL` | `logos_gamma`; 10 of 15 canonical clauses |

Gaps 6, 7 and 9 remain open and are not claimed as covered.
