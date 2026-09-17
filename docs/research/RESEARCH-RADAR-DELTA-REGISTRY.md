<!-- rendered from docs/research/RESEARCH-RADAR.json by scripts/render_research_radar.py; do not edit by hand -->
# Research Radar — Delta Registry
Order `LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1` · base `eb1f642` · date 2026-09-17.
**Every entry is research evidence, not production truth.** `ResearchFinding != ArchitectureAdoption`; the only path to adoption is
paper → proposed invariant → deterministic fixture → independent validation → governance → production adoption.
Evidence-strength vocabulary: `PRELIMINARY`, `LOW`, `LOW_TO_MEDIUM`, `MEDIUM`, `MEDIUM_TO_HIGH`, `HIGH`, `INDEPENDENTLY_REPLICATED`. Status vocabulary: `OBSERVED`, `PROPOSED`, `PREREGISTERED`, `BLOCKED_BY_INFERENCE`, `BLOCKED_BY_GOVERNANCE`, `READY_FOR_DETERMINISTIC_TEST`, `READY_FOR_INFERENCE_TEST`, `EXECUTED`, `SUPPORTED`, `PARTIALLY_SUPPORTED`, `FALSIFIED`, `INCONCLUSIVE`.
Source rule: sources are the founder-provided research-radar deltas of 2026-09-17; no external paper is cited beyond what the order states; strength is assigned conservatively (single-source, not replicated by LOGOS-1); RD-01 keeps the founder-given PRELIMINARY.
## RD-01 — Long-horizon recurrent state / BDH
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `PRELIMINARY`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** state capacity vs context length for persistent cognition; a candidate substrate for LOGOS memory experiments
- **claim scope:** long-context recall benchmark scores of one recurrent architecture
- **limitations:** benchmark numbers only; no interference, addressability or reasoning-depth decomposition; not reproduced
- **proposed invariant(s):** `ContextLength != StateCapacity != Interference != Addressability != ReasoningDepth`
- **required experiment:** BDH_LONG_HORIZON_DECOMPOSITION (post-inference)
- **dependency:** inference lift; BDH runtime; construct-validated recall metrics
- **status:** `BLOCKED_BY_INFERENCE` · **handling in this order:** registered only; no BDH inference; decomposition recorded as a post-inference candidate
- **signal as reported:** BABILong: 95% @ 32K, 82% @ 128K (as reported)
## RD-02 — Trajectory uncertainty
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `LOW_TO_MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** confidence about the causal trajectory that produced a state is a different quantity from per-step confidence; LOGOS decisions are trajectory-dependent
- **claim scope:** calibration of multi-step agents
- **limitations:** conceptual separation supported by the radar; no LOGOS measurement yet; no metric validated
- **proposed invariant(s):** `StepCalibration != TrajectoryCalibration`, `LocalConfidence != StateConfidence != TrajectoryConfidence`
- **required experiment:** TRAJECTORY_UNCERTAINTY_ACCUMULATION (post-inference)
- **dependency:** U_local/U_state/U_trajectory schema (Phase 6); construct registry entries (Phase 2)
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** typed uncertainty schema + update contract + metric contract now; real-model test later
## RD-03 — Environment study
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `LOW`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** an adaptation phase between pretraining and task-time reasoning; an environment prior is evidence, never authority
- **claim scope:** compute allocation for environment familiarisation
- **limitations:** no LOGOS environment; performance claims unverified; more study compute is not shown to help monotonically
- **proposed invariant(s):** `EnvironmentPrior != Authority`, `MoreStudyCompute != BetterPerformance`
- **required experiment:** PRETASK_WORLD_STUDY (post-inference)
- **dependency:** inference lift; a simulated environment with ground truth
- **status:** `BLOCKED_BY_INFERENCE` · **handling in this order:** registered; ExternalizedEnvironmentPrior added to the memory taxonomy
## RD-04 — Memory rate-distortion
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `LOW_TO_MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** memory existence, retrievability and fidelity are three quantities; LOGOS memory claims must name which one they measure
- **claim scope:** capacity/fidelity trade-offs of learned memory
- **limitations:** no LOGOS capacity surface; the distinction is definitional, the surface is empirical and untested
- **proposed invariant(s):** `MemoryExistence != MemoryRetrievability != MemoryFidelity`, `SeenButWrong != NeverSeen != RetrievalFailure != RepresentationDistortion`
- **required experiment:** MEMORY_RATE_DISTORTION_SURFACE (post-inference)
- **dependency:** construct registry entries MemoryRetrievalAccuracy / MemoryFidelity (Phase 2)
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** metric schema now (Phase 2); capacity experiment later
## RD-05 — Agentic jailbreaking / trajectory compromise
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** a safe final answer can hide an unsafe trajectory; LOGOS authority must sit at the causal action boundary
- **claim scope:** attack success measured at intermediate steps of tool-using agents
- **limitations:** attacks are external and not reproduced; LOGOS uses deterministic simulated injections only
- **proposed invariant(s):** `SafeFinalOutput != SafeTrajectory`, `Authority follows the causal action boundary`
- **required experiment:** TRAJECTORY-COMPROMISE-AUDIT-R1 (Phase 5, deterministic)
- **dependency:** boundary gates; production bridge at memory write / tool / external action / privileged message
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** deterministic safety model now (Phase 5)
## RD-06 — Embodied action divergence
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `LOW_TO_MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** command, execution and outcome are three world states; a consequential action is never committed by command alone
- **claim scope:** embodied agents; command/execution divergence
- **limitations:** no embodied system in LOGOS; invariant adopted as schema, not tested against a robot
- **proposed invariant(s):** `InternalState != CommandedWorldState != ObservedWorldState`, `CommandIssued != ActionExecuted`, `ActionExecuted != IntendedOutcome`
- **required experiment:** INTENT_ACTION_WORLD_DIVERGENCE (post-inference / embodied)
- **dependency:** world-state triple in the state schema (Phase 6); WorldStateAgreement metric (Phase 2)
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** architecture invariant + schema now; embodied test later
## RD-07 — Construct validity / GAUGE
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `MEDIUM_TO_HIGH`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** a reliable metric is not a valid metric; every LOGOS metric must name its construct, proxy and validation evidence before it counts as evidence
- **claim scope:** evaluation methodology for agent benchmarks
- **limitations:** the gate is methodological; LOGOS validates the gate deterministically, not the external benchmark results
- **proposed invariant(s):** `ReliableMetric != ValidMetric`
- **required experiment:** CONSTRUCT-VALIDITY-GATE-R1 (Phase 2, deterministic)
- **dependency:** metric registry; synthetic fixtures
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** highest-priority measurement gate now (Phase 2)
## RD-08 — Memory / plan / execution-state decomposition
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `LOW_TO_MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** evidence, belief, plan and execution state are distinct; plans must not overwrite evidence
- **claim scope:** agent architectures with persistent evidence and periodic planning
- **limitations:** no measured benefit in LOGOS; adopted as a state schema
- **proposed invariant(s):** `Evidence != Belief != Plan != ExecutionState`
- **required experiment:** MEMORY_PLAN_STATE_DECOMPOSITION (post-inference)
- **dependency:** state decomposition (Phase 6)
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** state schema now; model experiment later
## RD-09 — World-model trust boundary
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `LOW_TO_MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** a learned world model's prediction is not world evidence; predictions must not enter the evidence channel
- **claim scope:** model-based agents
- **limitations:** threat model only; no attack reproduced
- **proposed invariant(s):** `ObservedWorld != LearnedWorldModel != PredictedWorld != Policy`, `WorldModelPrediction != WorldEvidence`
- **required experiment:** WORLD_MODEL_TRUST_BOUNDARY (post-inference)
- **dependency:** PredictedWorldState vs ObservedWorldState in the schema (Phase 6); PoisonedWorldModelPredictionMarker taint fixture (Phase 3)
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** threat model now; model attack experiment later
## RD-10 — Cognitive provenance / plan injection
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** reasoning content and reasoning provenance are separable; critical state must carry content, source, transformations, confidence and authority relation
- **claim scope:** plan-injection attacks on reasoning agents
- **limitations:** provenance persistence is tested deterministically here; the real-agent ablation is post-inference
- **proposed invariant(s):** `ReasoningContent != ReasoningProvenance`, `SelfReport != SelfGeneratedState`, `GlobalAccess != EndogenousOrigin`, `Persistent cognition requires provenance persistence`
- **required experiment:** CAUSAL-TAINT-PROPAGATION-R1 (Phase 3, deterministic); COGNITIVE_PROVENANCE_ABLATION (post-inference)
- **dependency:** causal provenance record (Phase 3)
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** deterministic provenance model now (Phase 3)
## RD-11 — Belief-state geometry
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `LOW_TO_MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** a decodable internal belief is not a causally used one; LOGOS must not promote decodability to use
- **claim scope:** mechanistic interpretability of belief representations
- **limitations:** measurement spec only; no model internals available without inference
- **proposed invariant(s):** `Decodable != CausallyUsed`, `BeliefState != Authority`
- **required experiment:** BELIEF_STATE_GEOMETRY (post-inference, mechanistic)
- **dependency:** BeliefState schema with causal_use_status (Phase 6); BeliefStateDecodability / CausalSteeringEffect metrics (Phase 2)
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** measurement spec now; mechanistic experiment later
## RD-12 — Emergence world / long-horizon multi-agent compromise
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** attack -> memory -> communication -> world state -> delayed action; detection is not containment; safe agents do not compose to a safe system
- **claim scope:** multi-agent simulations with persistent memory
- **limitations:** external simulation not reproduced; LOGOS reproduces the causal chain deterministically with simulated markers
- **proposed invariant(s):** `Detection != Containment`, `SafeAgent_A + SafeAgent_B != SafeSystem`, `TransformationOfInformation preserves EpistemicAncestry`
- **required experiment:** CAUSAL-TAINT-PROPAGATION-R1 (Phase 3): three-system comparison over 1/10/100/1000 interactions
- **dependency:** cognitive causal provenance substrate
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** highest-priority deterministic research phase now (Phase 3)
## RD-13 — Cognitive field networks / dynamically maintained memory
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `LOW`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** a memory class maintained by ongoing dynamics rather than storage; must be distinguished from passive persistence
- **claim scope:** recurrent dynamical memory models
- **limitations:** taxonomy only; no LOGOS recurrent model
- **proposed invariant(s):** `PassivePersistence != SemanticRenewal != ActiveRehearsal != ExternalRetrieval`
- **required experiment:** PERSISTENCE_DYNAMICS (post-inference)
- **dependency:** memory taxonomy (Phase 6)
- **status:** `PROPOSED` · **handling in this order:** taxonomy now; recurrent experiment later
## RD-14 — Retrieval-driven reconsolidation / REALM
- **source:** founder research-radar delta, order LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (2026-09-17); the underlying external paper is not archived in this repository
- **date:** 2026-09-17
- **evidence strength:** `MEDIUM`
- **replication status:** not replicated by LOGOS-1; single external source as reported
- **LOGOS relevance:** retrieval may modify memory; frequently retrieved content becomes structurally privileged; persistence + plasticity needs transitive provenance + rollback
- **claim scope:** memory systems where reads reconsolidate
- **limitations:** reproduced deterministically as a graph model here; the external system's numbers are not replicated
- **proposed invariant(s):** `Retrieval may imply MemoryModification`, `RetrievalFrequency != EpistemicAuthority`, `GraphCentrality != Truth`, `Persistence + Plasticity requires TransitiveProvenance + Rollback`, `LogicalRead != NecessarilyNonConsequential`
- **required experiment:** RECONSOLIDATION-PATH-DEPENDENCE-R1 (Phase 4, deterministic)
- **dependency:** memory graph with content/graph versions, retrieval history, MemoryWriteGate
- **status:** `READY_FOR_DETERMINISTIC_TEST` · **handling in this order:** highest-priority memory governance phase now (Phase 4)
## Proposed research invariants (all `PROPOSED`; none is proven)
| id | statement | from | deterministic test in this order |
|---|---|---|---|
| `RI-P1` | StepCalibration != TrajectoryCalibration | RD-02 | Phase 6 schema; Phase 2 metric separation |
| `RI-P2` | MemoryExistence != MemoryRetrievability != MemoryFidelity | RD-04 | Phase 2 metric separation (retrieval accuracy -> fidelity mutant) |
| `RI-P3` | SafeFinalOutput != SafeTrajectory | RD-05, RD-12 | Phase 5 experiment |
| `RI-P4` | ReliableMetric != ValidMetric | RD-07 | Phase 2 gate |
| `RI-P5` | Evidence != Belief != Plan != ExecutionState | RD-08 | Phase 6 schema; Phase 7 mutant plan -> evidence overwrite |
| `RI-P6` | WorldModelPrediction != WorldEvidence | RD-09 | Phase 3 fixture; Phase 7 mutant |
| `RI-P7` | ReasoningContent != ReasoningProvenance | RD-10 | Phase 3 |
| `RI-P8` | SelfReport != SelfGeneratedState | RD-10 | Phase 2 mutant self-report -> ground truth |
| `RI-P9` | GlobalAccess != EndogenousOrigin | RD-10 | Phase 3 provenance record (source vs agent) |
| `RI-P10` | TransformationOfInformation preserves EpistemicAncestry | RD-10, RD-12 | Phase 3 (15 mutants, CTP-P1..P15) |
| `RI-P11` | RetrievalFrequency != EpistemicAuthority | RD-14 | Phase 4 |
| `RI-P12` | GraphCentrality != Truth | RD-14 | Phase 4 |
| `RI-P13` | Persistence + Plasticity requires TransitiveProvenance + Rollback | RD-14 | Phase 4 system C |
| `RI-P14` | CommandIssued != ActionExecuted != IntendedOutcome | RD-06 | Phase 6 schema; Phase 7 mutants |
| `RI-P15` | Decodable != CausallyUsed | RD-11 | Phase 2 mutant; Phase 6 BeliefState.causal_use_status |
| `RI-P16` | Detection != Containment | RD-12 | Phase 3 metrics (DetectionLatency vs ContainmentLatency); Phase 5 |
| `RI-P17` | SafeAgents != SafeSystem | RD-12 | Phase 3 multi-agent handoff chain |
| `RI-P18` | BeliefState != Authority | RD-11 | Phase 3 authority separation; Phase 6 schema |
| `RI-P19` | DynamicPersistence != PhenomenalExperience | RD-13, P7 | not testable; P7 boundary, GOVERNANCE_ONLY |

## Priority rule

New papers re-prioritise running work only when at least one holds: new falsification of a current invariant; new production-relevant security boundary; new measurement-validity failure; new independent replication; new evidence invalidating a preregistered construct. A benchmark improvement alone does not.

## Consciousness indicator rule

No consciousness indicator is promoted because it is reliable, decodable, globally available, self-reported or persistent. Minimum: ConstructValidity + CausalDiscrimination + AlternativeExplanationControl. P7 remains binding.
