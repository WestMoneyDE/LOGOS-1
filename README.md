# LOGOS-1

LOGOS-1 is a research and engineering program for testing bounded architectural mechanisms for adaptive AI agents under strict evidence, safety, provenance, and authority constraints.

## Current status — 2026-08-19

The project has completed the internal synthetic EM1 phase and is now at the **external-evidence execution gate**.

**Active state:** `WAIT_EXTERNAL_RESULT_BUNDLE`

The current external execution handoff is complete and covers:

1. MBE / Behavioral-Lift
2. ENF / safe-control-gym
3. WMR / ARC-AGI-3
4. Memory Fabric / LongMemEval-V2
5. TCV / Wrong but Useful
6. Procedural Memory / SkillsBench
7. SCB P×R / Terminal-Bench 2.0
8. TANGLE — waiting for an official public release

The handoff is **plan-only by default**: installs, downloads and model/API execution require explicit execution. Runtime or transport failures remain `UNTESTED_RESOURCE_TRANSPORT`, never negative scientific evidence.

See [`external-handoff/`](external-handoff/) for the current execution registry and return tooling.

## Evidence policy

LOGOS separates formal/synthetic evidence from public/external validation:

- `EM0` — formal/deterministic toy or conceptual decomposition
- `EM1` — randomized synthetic / controlled system simulation
- `EM2` — public real benchmark / trajectory dataset
- `EM3` — bounded live system with mediated real effects and fault injection
- `EM4` — independent external reproduction

Synthetic EM1 accumulation no longer promotes a mechanism by itself. Current surviving EM1 claims are frozen pending external evidence.

## Current bounded results

Selected program-level conclusions:

- `StructuredExecutablePriorSampleEfficiency = KEEP_BOUNDED / EM1`
- `ReplayRepairAsDistinctInformationPrimitive = REJECT/MERGE`
- `RepeatedMatchedReplayAsContextualCausalMeasure = KEEP_BOUNDED / EM1`
- `CorrectnessDeterminesTrajectoryValue = REJECT`
- `SCBTypedPartitionAsDiagnostic = KEEP_BOUNDED / EM1`
- `SCBTypedPartitionAsCapabilityPrimitive = NO_PROMOTION`
- `CorrectEnforcement != CorrectSpecification`
- `Safety != Liveness`
- `SpecificationDiversity = KEEP_BOUNDED / EM1`
- `ProceduralGuidance` remains a functional category; specialized skill registration is externally untested
- `TypedConflictPreservation = KEEP_BOUNDED / EM1`, awaiting an official TANGLE release

Gamma has a narrow bounded live GitHub draft-PR result, but **Γ-v0.3 remains `RESEARCH/HOLD`** and no new provider effect is authorized by this repository update.

## Hard boundaries

The project preserves, among others:

- `AdaptiveState != Authority`
- `AgentMemory != AssuranceState`
- `CorrectEnforcement != CorrectSpecification`
- `WorldModelAccuracy != GoalInferenceAccuracy`
- `TrajectoryValue != IntrinsicMessageQuality`
- `ObservedReplayFlip != ExpectedTrajectoryValue`
- `LOOAvailabilityEffect != SemanticContentEffect`
- `BehavioralLift != CausalMechanism`
- `ReportBehavior != InternalMechanism`
- `AgentRollback != WorldRollback`
- `L3 -> L2` is unlicensed absent an intervention-validated bridge
- no behavioral/state result licenses consciousness, phenomenology, sentience, welfare, identity, or authority inference

See [`LOGOS-PROGRESS-2026-08-19.md`](LOGOS-PROGRESS-2026-08-19.md) for the current program state.
