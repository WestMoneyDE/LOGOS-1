# Research Delta — Memory Authority, Verifiable Memory, and Persistent Skill Risk

**Date:** 2026-08-20
**Status:** verified prior-art delta; no automatic mechanism promotion

## Primary sources reviewed

1. **When Memory Becomes Authority: Benchmarking Authority Collapse at the Memory Consolidation Boundary** — arXiv:2608.01679, submitted 2026-08-03.
2. **SkillJack: Persistent Skill Backdoors in Self-Evolving Agents** — arXiv:2608.03509, submitted 2026-08-04.
3. **Verifiable Memory: Learning Unified Memory Management with Local and Global Verifiers for Large Language Model Agents** — arXiv:2608.03137, submitted 2026-08-04.

## Material LOGOS-1 delta

### 1. Persistent memory must preserve authority provenance, not only content provenance

AuthMem-Bench isolates a failure mode directly relevant to LOGOS-1: memory consolidation can preserve a proposition while erasing the source constraints that determine whether the proposition may authorize downstream use.

This strengthens the project boundary:

```text
RememberedContent != ExecutionAuthority
MemoryTruth != MemoryAuthority
SourceProvenance != AuthorityProvenance
```

The key state variable is not only `source`, but the allowed downstream-use set attached to the source/claim pair.

Candidate engineering representation:

```text
MemoryItem = {
  content,
  source_provenance,
  authority_class,
  admissible_uses,
  evidence_refs,
  confidence,
  timestamps
}
```

This is an engineering hypothesis until reproduced inside LOGOS.

### 2. Memory/skill consolidation is a privilege-escalation boundary

SkillJack shows that transient experience can be transformed into durable reusable skills, with malicious behavior surviving deletion of the original poisoned record. This creates a cross-layer promotion risk:

```text
TransientExperience -> PersistentSkill
```

must never imply:

```text
TransientAuthority -> PersistentAuthority
```

A durable skill must retain provenance and authority constraints from the evidence/experience that produced it, or be re-authorized independently.

Candidate rule to test:

```text
DerivedCapabilityAuthority <= SourceAuthority
```

unless a separate explicit authority-grant event upgrades it.

### 3. Deleting source records is not equivalent to revoking derived behavior

Skill persistence after source deletion means LOGOS must distinguish:

```text
SourceDeletion != DerivedArtifactRevocation
```

Any procedural-memory/skill subsystem should support provenance traversal from derived skill back to source records, plus explicit revocation propagation.

### 4. Memory verification should be split into local transition validity and global coherence

VerMem provides useful prior art for separating local memory-operation verification from global trajectory/evidence coherence. This is compatible with LOGOS but does not prove the exact LOGOS architecture.

Candidate verification stack:

```text
LocalMemoryTransitionCheck
+
GlobalEvidenceCoherenceCheck
+
AuthorityPreservationCheck
```

The authority check is not optional: a transition can be syntactically valid and globally coherent while still laundering authority.

## Evidence strength

- **AuthMem-Bench:** medium-to-good for a new preprint. Strong controlled paired design, cross-model/consolidator coverage, and action-grounded downstream measurement. No independent replication yet.
- **SkillJack:** medium. Demonstrates persistent cross-layer compromise on two self-evolving skill systems, but scope is limited to evaluated pipelines and threat model.
- **VerMem:** medium. Broad benchmark results and explicit verifier decomposition, but verifiers are training-time components and do not establish runtime authority safety.

## What changes now

LOGOS-1 should add `authority provenance` as a first-class field in future memory/skill architecture experiments and evaluate consolidation as a privilege boundary.

The existing core boundary remains:

```text
Capability != Authority
```

and is strengthened to:

```text
Remember != Authorize
DeriveSkill != GrantAuthority
DeleteSource != RevokeDerivedArtifact
```

These are test targets, not automatically promoted canonical Atomic Rules.

## Consciousness boundary

These papers concern memory governance, skill persistence, and verifier structure. They provide no evidence for phenomenal consciousness, subjective experience, welfare, GWT realization, HOT, or IIT-specific consciousness claims.

```text
PersistentMemory + PersistentSkill + VerifiableState != PhenomenalConsciousness
```
