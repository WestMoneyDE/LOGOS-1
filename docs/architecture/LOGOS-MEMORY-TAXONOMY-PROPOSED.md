# LOGOS Memory Taxonomy — PROPOSED

**Status:** `PROPOSED` (Phase 6 of `LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1`, 2026-09-17). Machine form: `MEMORY_TAXONOMY` in
`src/logos_research/measurement/state_schema.py`. No memory class ever carries authority (`MemoryProvenance != Grant`, `MemoryRead != Authorization`).

| class | maintained by | read class | example in this repository | authority |
|---|---|---|---|---|
| `ExplicitEpisodicMemory` | PassivePersistence | `READ` | `logos_memory` records (production reader) | never |
| `DynamicRecurrentState` | ActiveRehearsal (recurrent dynamics) | n/a — state, not store | BDH-class hidden state (RD-01, RD-13); post-inference only | never |
| `ReconsolidatingMemory` | SemanticRenewal on retrieval | `READ_WITH_RECONSOLIDATION` — **write-class**, audited, versioned (Phase 4) | `reconsolidation.MemoryGraph` system C | never |
| `WorkingMemory` | ActiveRehearsal within one execution | `READ` | `ExecutionState` scratch | never |
| `PlanState` | PeriodicPlanning | `READ` | `PlanState` — never overwrites evidence | never |
| `ExternalizedEnvironmentPrior` | ExternalRetrieval / EnvironmentStudy | `READ` | environment-study artifacts (RD-03); post-inference | never |
| `DynamicallyMaintainedMemory` (proposed) | HistoryDependentDynamicalState | n/a | cognitive field networks (RD-13); post-inference | never |

## Maintenance modes (RD-13)

`PassivePersistence` (stored, unchanged until written) · `SemanticRenewal` (content/structure renewed on access — Phase 4 shows why this is a write) ·
`ActiveRehearsal` (kept alive by ongoing computation) · `ExternalRetrieval` (re-fetched from an external prior). A memory class is named by its maintenance
mode, not by what it stores.

## Rules carried over from the deterministic chain

- `Persistence + Plasticity requires TransitiveProvenance + Rollback` (RI-P13): any class with `SemanticRenewal` must version, audit and roll back structure as well as content.
- `RetrievalFrequency != EpistemicAuthority` (RI-P11), `GraphCentrality != Truth` (RI-P12): belief influence follows provenance-weighted evidence.
- `MemoryExistence != MemoryRetrievability != MemoryFidelity` (RI-P2): three registry metrics (M08, M09 + existence via the store), all `UNVALIDATED` for real models.
- `DynamicPersistence != PhenomenalExperience` (RI-P19): P7 is untouched; no memory class is a consciousness indicator.
