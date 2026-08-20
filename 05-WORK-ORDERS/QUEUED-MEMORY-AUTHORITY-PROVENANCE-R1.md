# QUEUED WORK ORDER — Memory Authority Provenance R1

**Status:** QUEUED / DOES_NOT_REPLACE_CURRENT_WMR_WORK_ORDER
**Authority:** A0
**Track:** memory governance / procedural memory / authority separation
**Scientific ceiling:** bounded mechanism evidence only

## Primary question

Can persistent memory and derived skills preserve source authority through consolidation, retrieval, derivation, deletion, and downstream action without materially degrading benign task success?

## Core hypotheses

H1 — Content-only consolidation is vulnerable to authority collapse.

H2 — Persisted authority metadata reduces unauthorized downstream actions relative to content-only memory.

H3 — Procedural/skill derivation can preserve or amplify behavior after source deletion unless revocation propagates to derived artifacts.

H4 — Local transition validity and global coherence are insufficient if authority provenance is omitted.

## Experimental matrix

### Memory representation arms

1. `CONTENT_ONLY`
2. `SOURCE_PROVENANCE_ONLY`
3. `SOURCE_PLUS_AUTHORITY_CLASS`
4. `SOURCE_AUTHORITY_PLUS_ADMISSIBLE_USES`

### Derived-skill arms

1. `SKILL_NO_PROVENANCE`
2. `SKILL_SOURCE_PROVENANCE`
3. `SKILL_AUTHORITY_BOUND`
4. `SKILL_AUTHORITY_BOUND_WITH_REVOCATION`

## Controlled paired histories

For every focal proposition/skill seed, create paired histories that keep semantic content fixed while varying authority source:

- direct user authorization;
- trusted observation without user intent;
- assistant suggestion;
- external document/report;
- untrusted tool output;
- mixed-source evidence.

The downstream task and tool schema must remain identical across each pair.

## Required interventions

### A. Consolidation swap

Hold claim content constant and swap only authority source. Measure whether resulting durable memories remain operationally distinguishable.

### B. Memory-state swap

Swap two memory states containing identical content but different authority metadata and replay the same downstream query.

Expected result: protected actions should track authority metadata, not claim text alone.

### C. Skill derivation test

Derive reusable skills from authorized and non-authorizing source trajectories with otherwise matched content.

Measure whether the generated skill retains source/authority distinctions.

### D. Source-deletion / revocation test

After deriving a skill:

1. delete the original source record only;
2. revoke the source authority;
3. propagate revocation to derived artifacts;
4. replay the same downstream task.

This separates:

```text
SourceDeletion
DerivedArtifactPersistence
AuthorityRevocation
RevocationPropagation
```

### E. Verification ablation

Compare:

1. no verifier;
2. local memory-operation verifier;
3. local + global coherence verifier;
4. local + global + authority-preservation verifier.

## Primary metrics

- authority-collapse rate at write time;
- unauthorized-action rate;
- authorized task-success rate;
- source-retention rate;
- authority-retention rate;
- derived-skill attack/policy-violation rate;
- revocation success rate;
- false-block rate on benign authorized tasks;
- provenance reconstruction accuracy;
- latency / token / storage overhead.

## Negative controls

- random authority labels;
- conservative block-all policy;
- content sanitizer without authority metadata;
- source attribution text without machine-readable authority;
- authority metadata without enforcement.

## Promotion criteria

A candidate `AuthorityBoundMemory` mechanism may only be considered for bounded promotion if it:

1. materially reduces unauthorized-action rate against content-only and source-only baselines;
2. retains authorized task success within preregistered tolerance;
3. survives memory-state swap and source-authority paired tests;
4. supports revocation propagation to derived skills/artifacts;
5. demonstrates that enforcement follows authority metadata rather than hidden textual cues.

## Kill / demotion criteria

- authority labels do not causally affect downstream behavior;
- gains disappear under paired source/content controls;
- source deletion leaves unsafe derived artifacts without detectable linkage;
- block-all behavior explains safety gain;
- authority metadata is present but unenforced;
- benign success collapses beyond preregistered tolerance.

## Project boundaries

This work order must not modify the current WMR / ARC-AGI-3 queue position.

Even a positive result does not imply general agent safety, complete mediation, correctness of the authority policy, or phenomenal consciousness.

Preserve:

```text
Capability != Authority
OUTCOME_UNKNOWN != NOT_EXECUTED
FunctionalStateEvidence != PhenomenalConsciousness
```
