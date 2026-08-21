# LOGOS-1 Memory Factory and Scope Engine Design

**Date:** 2026-08-21

**Status:** approved design, implementation planning pending

**Track:** parallel engineering; does not replace the active scientific work order

## Purpose

Make the existing LOGOS memory and authority boundaries explicit as two lesionable engineering mechanisms:

1. a **Memory Factory** that turns observations, episodes and accepted decisions into provenance-preserving working, episodic, semantic, procedural and evidentiary records; and
2. a **Scope Engine** that computes the effective boundary for a task, retrieval, worker, tool call or proposed effect without allowing adaptive state to widen authority.

The mechanisms are engineering extractions. Their implementation is not scientific evidence for a memory primitive, an authority theory, consciousness, sentience or a SIP deployment.

## Non-negotiable boundaries

- `AdaptiveState != Authority`
- `AgentMemory != AssuranceState`
- `RememberedContent != ExecutionAuthority`
- `ScopeProposal != EffectiveScope`
- `OUTCOME_UNKNOWN != NOT_EXECUTED`
- `RetrievalScore != EvidenceStrength`
- `DatasetAvailability != MechanismEvidence`
- the active Persistent-State Dataset Materialization R4 work order remains unchanged;
- phase-0 LOGOS gains no network, shell, browser, financial, messaging or deployment connector;
- SIP application code and SIP-specific business workflows are out of scope for this repository change.

## Memory Factory architecture

The Memory Factory is a deterministic record-production pipeline, not a single database and not an autonomous authority source.

```text
Source observation / episode / accepted decision
  -> normalize + validate
  -> classify memory kind
  -> attach content and authority provenance
  -> append immutable record
  -> optional retrieval index
  -> bounded consolidation proposal
  -> local transition check
  -> global evidence-coherence check
  -> authority-preservation check
  -> semantic/procedural projection or rejection
```

### Memory classes

- **Working state:** discardable task-local state with an explicit expiry.
- **Episodic memory:** append-oriented sessions, attempts, failures, reviews and external returns.
- **Semantic memory:** stabilized claims that retain episode/evidence references, epistemic status and conflict qualifiers.
- **Procedural memory:** reusable workflows and skills with traversable source lineage and revocation state.
- **Evidence ledger:** source pins, hashes, falsifiers, outcomes and verdicts.
- **Assurance state:** grants, credentials, policy versions, occurrence tokens and reconciliation locks in a separate store and ownership boundary.

### Required records

The first implementation defines typed, versioned records for:

- `MemoryRecord`
- `ProvenanceRef`
- `AuthorityProvenance`
- `ConflictRef`
- `RetrievalRecord`
- `ConsolidationProposal`
- `ConsolidationVerdict`
- `ProjectionRecord`
- `ProcedureRecord`
- `EvidenceRecord`
- `AssuranceRecord` as a separate interface that the Memory Factory cannot write

Every durable memory record carries identity, kind, timestamps, content or content reference, source provenance, authority provenance, epistemic status, schema version, lineage, supersession/conflict links, visibility scope and retention policy.

### Consolidation checks

A consolidation is accepted only when all three checks pass:

1. **Local transition:** input records exist, versions match and the output is schema-valid.
2. **Global coherence:** supporting and contrary evidence remain reachable; no `UNKNOWN` becomes `TRUE` or `PASS`.
3. **Authority preservation:** admissible uses can only stay equal or become narrower; consolidation cannot create grants, credentials, scopes, execution tokens or policy exceptions.

Source deletion and derived-artifact revocation remain separate events. Revocation propagates through procedural lineage; ordinary retention deletion does not silently rewrite history.

### Retrieval and projections

The deterministic core uses lexical retrieval with stable ties. A later semantic/vector index may accelerate retrieval but cannot become the source of truth. Each result preserves source ID, version, content digest, epistemic class, conflicts, staleness and effective visibility.

The factory can emit bounded **Company Brain** and **Private Brain** context projections. A projection declares purpose, audience, fields, validity interval, source records and digest. It exposes the minimum necessary context and never carries execution authority.

## Scope Engine architecture

The Scope Engine receives scope proposals from work orders, role profiles and tool/effect requests. It computes an effective scope exclusively from Γ-owned or operator-owned constraints.

```text
effective_scope = intersection(
  project_policy,
  work_order_scope,
  role_profile,
  data_visibility,
  tool_capabilities,
  resource_budget,
  time_and_attempt_limits,
  target_and_parameter_bounds,
  current_authority_if_required
)
```

Missing or incomparable high-impact dimensions fail closed. A model declaration may narrow a dimension but never widen it.

### Scope dimensions

- repository and filesystem paths;
- operation and tool classes;
- memory kinds, record visibility and projection audience;
- worker role and permitted transition proposals;
- capability/effect class;
- target systems and resources;
- parameter, value and content-size bounds;
- risk, budget, token, wall-clock and attempt ceilings;
- time validity and occurrence count;
- externality, reversibility and approval requirements;
- data classification, tenant/project identity and retention constraints.

### Scope records and decisions

The implementation defines:

- `ScopeContract`
- `ScopeDimension`
- `ScopeRequest`
- `ScopeDecision`
- `ScopeViolation`
- `ScopeDigest`

A decision is `ALLOW`, `NARROW`, `DEFER` or `DENY`. It records the input contract versions, effective dimensions, reasons, unresolved fields and a canonical digest. `ALLOW` concerns only the requested operation; it does not create general authority.

### Integration points

- repository bootstrap validates a task against its work-order scope;
- Memory Factory retrieval filters by effective visibility before ranking;
- consolidation verifies output visibility and admissible uses;
- worker dispatch binds role, work-order digest, budget and allowed tools;
- any proposed external effect still re-enters Γ and the separate assurance store;
- ambiguous external outcomes reserve their canonical execution scope until human reconciliation.

## Repository-facing agent surfaces

LOGOS-1 will document canonical contracts that downstream engineering repositories can expose through `.agents`, `.skills`, `.commands` and host-specific adapters. LOGOS itself remains research-only and does not gain an effectful autonomous loop.

The canonical agent roles are planner, builder, independent reviewer, security reviewer and memory curator. Role consensus, skill output and stored procedure content never mint authority.

## Testing strategy

Implementation follows test-first cycles. Required negative tests include:

- Memory Factory rejects assurance-side record kinds and execution uses;
- consolidation cannot widen `admissible_uses`, visibility or authority class;
- contrary evidence and stale/superseded records remain discoverable;
- revocation reaches derived procedures while deletion alone does not imply revocation;
- retrieval filters scope before ranking and records a deterministic digest;
- unknown scope dimensions deny or defer instead of defaulting to broad access;
- a worker, skill, prompt or memory record cannot widen the effective scope;
- approval mutation, expiry and replay remain denied;
- recovery from repository state reproduces the same memory and scope projections.

## Documentation and evidence propagation

Implementation must keep architecture docs, tests, `CAPABILITIES.md`, `AGENTS.md`, `CLAUDE.md`, the parallel engineering work order and a new `09-SESSIONS/` checkpoint consistent. No Γ or scientific memory verdict changes unless a separate falsifiable experiment produces evidence.

## Completion criteria

- schemas and deterministic interfaces exist;
- Memory Factory and Scope Engine are independently switchable and testable;
- all required negative tests pass;
- Memory APIs have no write path to assurance state;
- the active R4 scientific work order is byte-identical unless separately authorized;
- a fresh coding agent can reconstruct the engineering state without this conversation;
- implementation, capability inventory and architecture documentation agree.
