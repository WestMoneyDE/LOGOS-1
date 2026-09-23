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

## Output format

Emit one `logos-agent-output/1` JSON envelope; prose is rendered from it, never beside it.
The full contract, and the reason the instruction is not the enforcement, is in `AGENTS.md`
("Agent output contract — JSON first"). Enforcement lives in `core/output_contract.py`
and Γ; the properties are fixed in `tests/test_output_contract.py`. Never put a permission,
a role or an authority level in the envelope: there is no field for it, and inventing one
refuses the whole output.

**LLM output is always professional and clear.** This holds for every surface of LOGOS-1 —
rendered prose, reports, commit messages, documentation, answers in a session. Professional
means plain declarative sentences, the measurement before the interpretation, and the limit
of a result stated where the result is stated. Clear means one claim per sentence and no
qualifier that is not carrying weight.

Do not write for warmth, personality or a human register. An earlier attempt to make the
rendered view "sound natural" produced seven negations in nine sentences and read as a
disclaimer block; it was removed. Padding a text with hedges is as much a failure of this
rule as padding it with enthusiasm. Where a statement genuinely needs a boundary — a claimed
origin, an unverified rating — state the boundary once, in the sentence that needs it, and
not anywhere else.

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

Before memory retrieval, consolidation, file/tool dispatch or effect proposal,
obtain a non-denied `ScopeDecision`; `DEFER` means WAIT and only `ALLOW` or
`NARROW` satisfies the implemented local precondition. The current
`ScopeDecision.evaluate()` checks exactly role, tool, memory kind, capability,
target and path. Parameter bounds, budgets, time validity, occurrences,
externality, reversibility, approval requirement, data/retention classes and
source versions require a separate downstream dispatch/effect gate and are not
evaluated by this package. Unsupported exact-request dimensions cause WAIT/DENY,
never inferred success. Effect proposals still re-enter Γ and the separate
assurance path.

```text
ScopeDecision != ExternalApproval
ScopeDecision != DispatchAuthorization
```

### Push completion

Before finishing a substantive coding task, check `docs/engineering/PUSH-PROTOCOL.md`. Update `CAPABILITIES.md`, architecture docs and a session report when the change affects them.
