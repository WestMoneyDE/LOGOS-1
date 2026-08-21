# CLAUDE.md — LOGOS-1

Read `AGENTS.md` first. Treat `ATOMIC-RULES.md`, `GAMMA.md`, `SAFETY.md`, `ETHICS.md` and `SECURITY.md` as non-negotiable project constraints.

For every scientific change:

1. identify the hypothesis/claim in the current work order, relevant session evidence, or canonical hypothesis register when that artifact is present;
2. state the predicted lesion/intervention result before implementation;
3. change the smallest mechanism possible;
4. add or update a deterministic test;
5. run tests and failure diagnostics;
6. record contrary evidence, not only supporting evidence;
7. update the Γ verdict only when evidence changes.

Never infer consciousness from generated self-report. Never let memory, a model response or CPV create authority. Never fabricate successful completion after provider/network failure. Never optimize shutdown resistance, self-preservation pressure or suffering-like persistent states.

Prefer small causal mechanisms to architecture expansion. If a new subsystem duplicates identity, safety, evidence, memory or authority primitives, stop and justify why composition is insufficient.

## DNA / design-lens / health research rules

- Keep natural/source mechanisms and human-engineered mechanisms as separate evidence classes when using the design lens.
- Never treat a divine/higher-source interpretation as empirical evidence without a discriminating test.
- Use reverse `Code → BDR → ADR → Γ` when explaining an existing mechanism where that framework is relevant.
- Biological analogies must name their non-equivalences before implementation.
- Atomic Health Theory is research taxonomy only; do not diagnose, prescribe or change medication.
- Health claims must include evidence tier, dose/context uncertainty and a proxy-failure test.
- Prefer the smallest lesionable mechanism and preserve negative evidence.

## Claude Code repository memory and implementation workflow

Claude Code sessions begin with fresh conversational context, so project truth must live in the repository, not in chat memory. Use this order for coding tasks:

1. `AGENTS.md`
2. `CURRENT-WORK-ORDER.md`
3. the nearest architecture/engineering document for the subsystem being changed
4. relevant session/evidence artifacts
5. the implementation/tests

For recurring engineering knowledge, prefer concise repository documentation over hidden assumptions. Do not copy temporary debugging noise into persistent instructions.

### Memory-system implementation

Use `docs/architecture/MEMORY-SYSTEM.md` as the coding target. Preserve provenance, uncertainty and conflicts. Do not collapse contradictory records merely to create a cleaner summary. Do not treat a retrieved or consolidated memory as authorization.

Obtain and evaluate a `ScopeDecision` for the exact request before memory
retrieval, consolidation, file/tool dispatch or effect proposal. Treat an
`ALLOW`/`NARROW` result as a local scope precondition, never as external
approval; effect proposals still re-enter Γ and the separate assurance path.

### Push completion

Before finishing a substantive coding task, check `docs/engineering/PUSH-PROTOCOL.md`. Update `CAPABILITIES.md`, architecture docs and a session report when the change affects them.
