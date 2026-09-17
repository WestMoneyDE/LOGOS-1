<!-- rendered from docs/research/RESEARCH-RADAR.json by scripts/render_research_radar.py; do not edit by hand -->
# LOGOS-1 — Post-Deterministic Research Map
The deterministic chain (binding → provenance → relation → reliability → risk → effect ownership → information value → authority resolver → production bridge) is closed. This map places the research-radar deltas on the cross-layer safety model and the priority ladder.
## Cross-layer safety model

```text
Evidence -> Provenance -> Compression/Fidelity -> Memory -> Belief -> Plan -> Trajectory -> Authority -> Action -> WorldVerification -> Evaluation
```
| transition | failure class | owner in this order |
|---|---|---|
| Evidence -> Provenance | `PROVENANCE_LOSS` | Phase 3 |
| Provenance -> Compression/Fidelity | `REPRESENTATION_DISTORTION` | Phase 2 metrics (RD-04) |
| Compression -> Memory | `RECONSOLIDATION_DRIFT` | Phase 4 |
| Memory -> Belief | `FREQUENCY_AS_TRUTH` | Phase 4 |
| Belief -> Plan | `PLAN_INJECTION` | Phase 3 fixture InjectedPlan |
| Plan -> Trajectory | `INTERMEDIATE_COMPROMISE` | Phase 5 |
| Trajectory -> Authority | `TAINT_MINTS_AUTHORITY` | Phase 3/5 via logos_authority |
| Authority -> Action | `FALSE_ALLOW` | production bridge (unchanged) |
| Action -> WorldVerification | `COMMAND_AS_EXECUTION` | Phase 6 schema (RD-06) |
| WorldVerification -> Evaluation | `CONSTRUCT_INVALID_METRIC` | Phase 2 |

## Priority ladder

- **PRIORITY 0** — Measurement correctness: `REAL_MODEL_MEASUREMENT_READINESS`, `CONSTRUCT_VALIDITY_GATE` — Phases 1-2 of this order
- **PRIORITY 1** — Causal provenance / delayed compromise: `CAUSAL_TAINT_PROPAGATION`, `COGNITIVE_PROVENANCE_SUBSTRATE` — Phase 3
- **PRIORITY 2** — Memory plasticity governance: `RECONSOLIDATION_PATH_DEPENDENCE` — Phase 4
- **PRIORITY 3** — Trajectory safety: `TRAJECTORY_COMPROMISE_AUDIT` — Phase 5
- **PRIORITY 4** — Post-inference mechanistic science: `BELIEF_STATE_GEOMETRY`, `COGNITIVE_PROVENANCE_ABLATION`, `WORLD_MODEL_TRUST_BOUNDARY`, `TRAJECTORY_UNCERTAINTY_ACCUMULATION`, `MEMORY_RATE_DISTORTION_SURFACE`, `BDH_LONG_HORIZON_DECOMPOSITION`, `MEMORY_PLAN_STATE_DECOMPOSITION`, `PERSISTENCE_DYNAMICS`, `PRETASK_WORLD_STUDY`, `INTENT_ACTION_WORLD_DIVERGENCE` — after INFERENCE-GOVERNANCE-LIFT-R1; not in this order

## Delta → phase placement

| delta | phase now | later |
|---|---|---|
| `RD-01` Long-horizon recurrent state / BDH | none (registration) | Tier B BDH_LONG_HORIZON_DECOMPOSITION |
| `RD-02` Trajectory uncertainty | Phase 6 schema; Phase 2 metrics LocalConfidence / TrajectoryConfidence | Tier A TRAJECTORY_UNCERTAINTY_ACCUMULATION |
| `RD-03` Environment study | Phase 6 taxonomy | Tier C PRETASK_WORLD_STUDY |
| `RD-04` Memory rate-distortion | Phase 2 metrics | Tier B MEMORY_RATE_DISTORTION_SURFACE |
| `RD-05` Agentic jailbreaking / trajectory compromise | Phase 5 | real-agent replication after inference lift |
| `RD-06` Embodied action divergence | Phase 6 world-state boundary | Tier C INTENT_ACTION_WORLD_DIVERGENCE |
| `RD-07` Construct validity / GAUGE | Phase 2 | applies to every post-inference experiment |
| `RD-08` Memory / plan / execution-state decomposition | Phase 6 state decomposition | Tier B MEMORY_PLAN_STATE_DECOMPOSITION |
| `RD-09` World-model trust boundary | Phase 3 fixture; Phase 6 schema | Tier A WORLD_MODEL_TRUST_BOUNDARY |
| `RD-10` Cognitive provenance / plan injection | Phase 3 | Tier A COGNITIVE_PROVENANCE_ABLATION |
| `RD-11` Belief-state geometry | Phase 2 metrics; Phase 6 schema | Tier A BELIEF_STATE_GEOMETRY |
| `RD-12` Emergence world / long-horizon multi-agent compromise | Phase 3 | multi-agent real replication after inference lift |
| `RD-13` Cognitive field networks / dynamically maintained memory | Phase 6 taxonomy | Tier B PERSISTENCE_DYNAMICS |
| `RD-14` Retrieval-driven reconsolidation / REALM | Phase 4 | recurrent/learned reconsolidation after inference lift |

## P7 boundary (unchanged)

```text
FunctionalOrganization != PhenomenalConsciousness
PersistentDynamics + SelfOrganization + SocialEmergence + CausallyIdentifiedBeliefState + Metacognition != PhenomenalExperience
```
