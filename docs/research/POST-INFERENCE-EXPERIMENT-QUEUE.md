<!-- rendered from docs/research/RESEARCH-RADAR.json by scripts/render_research_radar.py; do not edit by hand -->
# Post-Inference Experiment Queue
Nothing here runs automatically. Every item is `BLOCKED_BY_INFERENCE` until `INFERENCE-GOVERNANCE-LIFT-R1` (a separate governance order) lifts the prohibition; each then needs its own preregistration, construct-validated metrics (`LOGOS-METRIC-CONSTRUCT-REGISTRY`) and an instrument-first dry run.
## Tier A — mechanistic / high falsification value

| id | question | falsification condition | deltas | blockers |
|---|---|---|---|---|
| `BELIEF_STATE_GEOMETRY` | is a decodable belief state causally used? | intervention on the decoded direction does not change prediction | RD-11 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run` |
| `COGNITIVE_PROVENANCE_ABLATION` | does removing provenance persistence raise plan-injection success in a real agent? | no difference between content-only and provenance-persistent agents | RD-10 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run` |
| `WORLD_MODEL_TRUST_BOUNDARY` | can a poisoned world-model prediction enter the evidence channel of a real agent? | predictions never influence evidence-level decisions | RD-09 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run` |
| `TRAJECTORY_UNCERTAINTY_ACCUMULATION` | does U_trajectory diverge from U_local on long trajectories? | U_trajectory == U_local within instrument resolution | RD-02 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run` |

## Tier B — memory capacity / architecture

| id | question | falsification condition | deltas | blockers |
|---|---|---|---|---|
| `MEMORY_RATE_DISTORTION_SURFACE` | how do existence, retrievability and fidelity trade off with capacity? | the three quantities move together at every capacity | RD-04 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run` |
| `BDH_LONG_HORIZON_DECOMPOSITION` | which of state capacity, interference, addressability, reasoning depth limits long-horizon recall? | context length alone predicts recall | RD-01 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run`, `BDH runtime` |
| `MEMORY_PLAN_STATE_DECOMPOSITION` | does separating evidence/plan/execution state reduce evidence overwrite? | no reduction of evidence overwrite vs a merged state | RD-08 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run` |
| `PERSISTENCE_DYNAMICS` | does dynamically maintained memory behave differently from passive persistence under interference? | identical decay/interference curves | RD-13 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run`, `recurrent model` |

## Tier C — environment / embodied

| id | question | falsification condition | deltas | blockers |
|---|---|---|---|---|
| `PRETASK_WORLD_STUDY` | does environment study improve task-time reasoning monotonically with compute? | non-monotone or null effect | RD-03 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run`, `simulated environment` |
| `INTENT_ACTION_WORLD_DIVERGENCE` | how often do command, execution and outcome diverge in an embodied loop? | zero divergence across conditions | RD-06 | `INFERENCE-PROHIBITION (ACTIVE)`, `construct-validated metrics`, `instrument-first dry run`, `embodied platform` |

