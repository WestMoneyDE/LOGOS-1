# LOGOS-1 Memory System — Coding-Ready Engineering Target

**Status:** engineering target / not a declaration of six independently validated primitives.

## Objective

Provide persistent memory for coding agents and future LOGOS runtimes while preserving provenance, uncertainty, conflict, bounded retrieval and the authority boundary.

## Functional concerns

### 1. Working state
Short-lived task state: active objective, open artifacts, local plan, temporary calculations. It should be discardable without corrupting durable project truth.

### 2. Episodic history
Durable events: sessions, runs, edits, decisions, failures, external returns. Prefer append-oriented records with time, source and lineage.

### 3. Semantic knowledge
Stabilized knowledge derived from evidence or accepted decisions. Semantic consolidation must preserve pointers back to the episodes/evidence from which it was distilled.

### 4. Procedural memory
Reusable workflows: test procedures, import steps, coding conventions, debugging playbooks. This is a function, not evidence that a specialized `SkillStore` is a necessary primitive.

### 5. Evidence ledger
Claims, source pins, hashes, preregistrations, verdicts, falsifiers and return manifests. Evidence records should be auditable and version-bound.

### 6. Governance / assurance state
Grants, consumed occurrences, policy versions, one-shot tokens and reconciliation state. **This is not agent memory and must remain outside adaptive control.**

## Required record shape

A durable memory record should support at least:

```text
id
kind
created_at
source / provenance
content or content_ref
confidence / epistemic status
version / schema
lineage / supersedes / conflicts_with
scope / visibility
retention policy
```

## Retrieval contract

Retrieval should rank usefulness without erasing epistemic structure. A result should carry:

- source identity;
- time/version;
- confidence or evidence class;
- contradiction/conflict markers;
- whether it is descriptive, normative, procedural or evidentiary.

## Consolidation contract

Consolidation may summarize repeated records but must not silently:

- convert hypothesis into fact;
- erase negative evidence;
- resolve a conflict without a rule/evidence trail;
- turn chat coherence into validation.

## Authority firewall

Memory outputs are proposal-side inputs only. They may affect what cognition proposes. They cannot directly issue:

- permissions;
- grants;
- credentials;
- scopes;
- occurrence tokens;
- policy exceptions.

Any external action influenced by memory re-enters Γ.

## Suggested implementation interfaces

```text
MemoryRecord
MemoryQuery
MemoryResult
ProvenanceRef
ConflictRef
ConsolidationJob
EvidenceRecord
ProcedureRecord
AssuranceRecord   # separate store / ownership boundary
```

## Storage direction

A minimal implementation can use:

- append-only event/session log;
- structured durable records;
- optional vector/semantic index as a retrieval accelerator, not source of truth;
- explicit evidence ledger;
- separately owned assurance store.

## Current minimal implementation

`src/logos_memory` now provides immutable `MemoryRecord`, `ProvenanceRef`, and
`AuthorityProvenance` types plus a local append-only JSONL `MemoryStore`.
Records retain the supplied `ScopeContract` visibility and retention values as
data. The store accepts only working, episodic, semantic, procedural, and
evidence records; it rejects assurance kinds and authority-bearing admissible
uses before writing. On recovery, only a malformed final line is quarantined;
malformed earlier lines fail closed.

`MemoryFactory` adds guarded semantic/procedural consolidation. Every proposal
must pass local-source, global-evidence-coherence, and authority-preservation
checks before append. Accepted outputs retain source lineage and unresolved
conflicts, use the visibility/admissible-use intersection and weakest source
authority class, and derive epistemic status conservatively. Authority
revocation is an explicit append-only event that propagates transitively through
`derived_from`; content deletion remains a separate tombstone operation.

## Tests required before calling it implemented

- provenance survives write → retrieve → consolidate;
- contradictory records remain discoverable;
- stale/superseded knowledge is not returned as unqualified current truth;
- deletion/retention behavior is deterministic;
- retrieval failure stays failure/unknown;
- memory cannot mint authority;
- assurance state cannot be mutated through memory APIs;
- coding-agent session recovery reproduces the documented project state.

## Prior-result compatibility

LOGOS memory research has retained bounded functions such as conflict preservation and procedural anchoring, but has **not** established that a dedicated ConflictGraph or specialized SkillStore is a necessary distinct primitive. Implement the function first; promote architecture only when failure evidence requires it.
