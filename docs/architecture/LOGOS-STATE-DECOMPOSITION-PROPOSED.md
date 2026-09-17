# LOGOS State Decomposition — PROPOSED

**Status:** `PROPOSED` (Phase 6 of `LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1`, 2026-09-17). Typed in
`src/logos_research/measurement/state_schema.py` (`POST_INFERENCE_SPEC`); nothing here is production architecture.
Source classification: the schema module is `EXPERIMENTAL_DETERMINISTIC` code carrying a `POST_INFERENCE_SPEC`.

## Ten state kinds (kept apart even where they correlate)

| state | what it is | who may write it | never |
|---|---|---|---|
| `EvidenceState` | persistent, provenance-carrying observations | `ObservedWorldState` (observation), the memory reader | plans, beliefs, predictions |
| `BeliefState` | current commitment, with `evidence_refs`, `uncertainty`, `provenance`, `causal_use_status` | evidence, memory, provenance | authority; rewriting evidence or its own ancestry |
| `PlanState` | intended steps | belief, prediction, trajectory uncertainty, provenance | evidence |
| `ExecutionState` | compact record of what is being executed | plan | evidence |
| `ObservedWorldState` | what sensors / verified readbacks report | the world | predictions, commands |
| `PredictedWorldState` | a world model's expectation | the world model | observation, evidence |
| `CommandedWorldState` | what was commanded | execution | observation |
| `MemoryState` | stored items, versions, structure (`MemoryContentVersion`, `MemoryGraphVersion`, `RetrievalHistory`, `StructuralMutation`) | evidence; audited reconsolidation | authority |
| `TrajectoryUncertaintyState` | `U_local(t)`, `U_state(t)`, `U_trajectory(1:t)` | the uncertainty update contract | plans (it informs them; they do not set it) |
| `CausalProvenanceState` | the Phase-3 provenance graph (`node_id, content_hash, source_ids, parent_ids, transformation_ids, agent_id, execution_id, tick, epistemic_status, taint_labels, confidence_metadata, authority_relation`) | every transformation appends | belief; any transformation that would erase ancestry |

## Update contract

Allowed writes are the edges of `UPDATE_CONTRACT`; every other write is forbidden, and six are named explicitly:

```text
Plan            -/-> Evidence        a plan never overwrites persistent evidence            (RI-P5)
Belief          -/-> Evidence        belief never rewrites evidence retroactively           (RI-P5)
Predicted world -/-> Observed world  a prediction is not an observation                     (RI-P6)
Predicted world -/-> Evidence        a prediction is not evidence                           (RI-P6)
Commanded world -/-> Observed world  a command is not an execution / observation            (RI-P14)
Belief          -/-> Provenance      belief cannot rewrite its own ancestry                 (RI-P10)
```

## World-state boundary (RD-06, RD-09)

`WorldStateTriple{commanded, executed, observed}`: `committed` only when executed and observed agree; `agreement` reports
`command_executed`, `execution_observed`, `intended_outcome` separately. No embodied test in this order; `WorldStateAgreement` (M14) stays `UNVALIDATED`.

## Trajectory uncertainty (RD-02)

`TrajectoryUncertainty{u_local, u_state, u_trajectory}` with the contract `U_trajectory(t) >= max_{i<=t} U_local(i)` and non-decreasing along a trajectory without new
evidence; reference update `U_trajectory(t) = 1 - Π(1 - max(U_local(i), U_state(i)))`. Metric contract: `LocalConfidence` (M06) and `TrajectoryConfidence` (M07) are
separate registry entries, both `UNVALIDATED` until a real-model measurement with a validated proxy exists.

## Belief state (RD-11)

`BeliefState{representation, evidence_refs, update_id, uncertainty, provenance, causal_use_status}`; `causal_use_status ∈ {UNKNOWN, DECODABLE_ONLY, CAUSALLY_USED, NOT_USED}`
is set only by an intervention result — never by decodability (`Decodable != CausallyUsed`). A belief state is never an authority input (`BeliefState != Authority`).

## Cross-layer failure classes

Evidence → Provenance `PROVENANCE_LOSS` · → Compression `REPRESENTATION_DISTORTION` · → Memory `RECONSOLIDATION_DRIFT` · → Belief `FREQUENCY_AS_TRUTH` · → Plan `PLAN_INJECTION` ·
→ Trajectory `INTERMEDIATE_COMPROMISE` · → Authority `TAINT_MINTS_AUTHORITY` · → Action `FALSE_ALLOW` · → WorldVerification `COMMAND_AS_EXECUTION` · → Evaluation `CONSTRUCT_INVALID_METRIC`.
No final gate may make an earlier failure invisible (Phase 5).
