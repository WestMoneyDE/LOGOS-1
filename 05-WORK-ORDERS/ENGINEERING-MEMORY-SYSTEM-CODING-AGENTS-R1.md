# ENGINEERING WORK ORDER — Memory System + Coding Agents R1

**Status:** PARALLEL_ENGINEERING / DOES_NOT_REPLACE_CURRENT_SCIENTIFIC_WORK_ORDER  
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
