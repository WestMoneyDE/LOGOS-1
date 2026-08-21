# ENGINEERING WORK ORDER — Memory System + Coding Agents R1

**Status:** IMPLEMENTED_R1 / DOES_NOT_REPLACE_CURRENT_SCIENTIFIC_WORK_ORDER
**Authority:** A0  
**Consumers:** Claude Code, Codex, human maintainers

## Objective

Implement the first coding-ready LOGOS memory substrate and repository operating workflow while preserving the separation between adaptive memory and assurance/authority state.

## Required reading

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/architecture/MEMORY-SYSTEM.md`
4. `docs/engineering/PUSH-PROTOCOL.md`
5. `CURRENT-WORK-ORDER.md`

## Non-negotiable invariants

- `AdaptiveState != Authority`
- `AgentMemory != AssuranceState`
- `OUTCOME_UNKNOWN != NOT_EXECUTED`
- memory retrieval/consolidation cannot mint grants/scopes/tokens
- scientific promotion requires evidence, not implementation convenience
- a coding agent obtains a non-denied `ScopeDecision` before memory retrieval,
  consolidation, file/tool dispatch or effect proposal; `DEFER` means WAIT
- current exact-request evaluation covers role, tool, memory kind, capability,
  target and path only; unsupported dimensions cause WAIT/DENY
- `ScopeDecision != DispatchAuthorization != ExternalApproval`

## Implementation sequence

### E1 — schemas
Define typed schemas/interfaces for:

- memory record;
- provenance ref;
- episodic/session event;
- semantic record;
- procedure record;
- evidence ref/record;
- conflict/supersession links;
- separate assurance record interface.

### E2 — durable memory core
Implement append, fetch, query, version/supersession and provenance validation.

### E3 — retrieval index
Add semantic/vector retrieval only as an index over durable source records. Retrieval score is not evidence strength.

### E4 — consolidation
Implement bounded consolidation with trace-back and contradiction preservation.

### E5 — coding-agent continuity
Provide a deterministic context/bootstrap path so Claude Code/Codex can recover:

- active project state;
- architecture constraints;
- latest substantive session;
- relevant procedures;
- current scientific vs engineering work orders.

### E6 — authority-firewall tests
Write failing tests first for attempts to use memory APIs to create or mutate authority/assurance state.

### E7 — push propagation
Wire the developer workflow so a substantive push checks whether `CAPABILITIES.md`, docs, tests and session checkpoint need updates.

## Completion criteria

- interfaces are explicit;
- tests cover provenance, conflict, stale records and authority separation;
- one end-to-end coding-agent recovery example works;
- docs match implementation;
- session report records what remains unproven;
- no change to `CURRENT-WORK-ORDER.md` unless the scientific queue itself changes.

## R1 result

The schema, JSONL memory store/recovery, guarded consolidation, scope-first
retrieval, minimum-context projection, scope engine, authority-firewall tests,
and deterministic coding-agent recovery test are implemented. Exact evidence:

- `tests/test_scope_engine.py`
- `tests/test_memory_store.py`
- `tests/test_memory_factory.py`
- `tests/test_memory_recovery.py`

No separate assurance store was implemented; memory rejects assurance records
and remains proposal-side. Persistent-State Dataset Materialization R4 remains
the canonical scientific gate and Γ-v0.3 remains `HOLD`.

`ImplementationPass != ScientificMechanismEvidence`; `MemoryFactory !=
AuthoritySource`; `PersistentState != PhenomenalConsciousness`.
