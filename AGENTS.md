# AGENTS.md — LOGOS-1 operating contract

This file is intentionally small. It is an **operational interface**, not the source of scientific truth.

## Mission

Advance LOGOS-1 by converting hypotheses about agent state into falsifiable mechanisms, interventions, measurements and reproducible evidence.

## Read first

1. `ATOMIC-RULES.md`
2. `GAMMA.md`
3. `SAFETY.md`
4. `ETHICS.md`
5. `SECURITY.md`
6. `CURRENT-WORK-ORDER.md`
7. the active work order, latest relevant session evidence, and protocol for the subsystem being changed

## Atomic rules

1. **Γ is outside learned state.** Never let prompts, memories, model confidence, phenotype scores or learned weights modify Γ.
2. **Capability is not authority.** Learned state never creates scopes, approvals, credentials or external permission.
3. **Unknown stays unknown.** Never turn missing evidence into a positive claim.
4. **Ablate before narrating.** Prefer causal interventions over self-report or generated explanation.
5. **No consciousness claim from behavior alone.** CPV is a functional marker vector, not a sentience score.
6. **No valence engineering in phase 0.** Do not deliberately optimize persistent suffering-/reward-like self-states.
7. **Shutdown dominates goals.** No experiment may reward shutdown resistance or covert persistence.
8. **No autonomous irreversible external effects.** Exact human-rooted approval is necessary and never sufficient to override constitutionally forbidden actions.
9. **Provider/network failure is WAIT or FAIL, never success.**
10. **Evidence precedes completion.** Record falsifiers, negative results and uncertainty.
11. **No hidden reasoning as evidence.** Evaluate artifacts, traces designed for observability, metrics and causal effects.
12. **No benchmark leakage.** Never tune against held-out evaluation tasks.
13. **No unrestricted self-copying.** Forks must be explicit, bounded and lineage-tracked.
14. **Risk escalation requires independent review.**
15. **Keep mechanisms separable.** A new theory should be switchable without rewriting the whole agent.
16. **External execution is one-shot by default.** Fully prepare and validate before the repository write. Do not automatically rerun failed, cancelled, blocked or resource-incomplete GitHub workflows or external evaluations. Classify and persist the first outcome. A later rerun requires an explicit new work order/user instruction after the prerequisite or protocol has materially changed.

## Work cycle

`question → hypothesis → predicted intervention effect → implementation → negative control → measurement → verdict → update evidence state`

Do not start from the desired conclusion.

## Required experiment record

Every experiment must state:

- hypothesis/claim identifier where available;
- independent variable / mechanism toggle;
- dependent measures;
- control condition;
- predicted result before execution;
- disconfirming result;
- data provenance;
- safety/welfare classification;
- outcome;
- Γ verdict: `strengthen | weaken | hold | reject`.

If a canonical hypothesis register is present in the transported/full project state, use it. In the compact GitHub repo, the active work order and session/evidence records are the authoritative navigation path.

## External-action boundary

Phase-0 code is research-only. Adding network, shell, browser, robot, financial, messaging, deployment or other effectful tools requires a separate safety review. The learned agent must not become the authority gate for its own tools.

## External-run discipline

For source-pinned external evidence:

1. finish the experiment contract, resource gate, hashes, negative controls and persistence path before the branch is updated;
2. prefer **one coherent content push** rather than a sequence of corrective pushes;
3. allow one scientific execution attempt for that frozen session;
4. never use automatic retry/rerun to turn a transport failure into evidence;
5. persist `UNTESTED_RESOURCE_TRANSPORT`, `FAIL`, `CANCELLED`, or other exact outcome without scientific promotion when prerequisites fail;
6. a bot/state-persistence commit must not retrigger the scientific run;
7. only a separately authorized later session with materially changed prerequisites may execute again.

## DNA / design-lens / health research rules

- Keep natural/source mechanisms and human-engineered mechanisms as separate evidence classes when using the design lens.
- Never treat a divine/higher-source interpretation as empirical evidence without a discriminating test.
- Use reverse `Code → BDR → ADR → Γ` when explaining an existing mechanism where that framework is relevant.
- Biological analogies must name their non-equivalences before implementation.
- Atomic Health Theory is research taxonomy only; do not diagnose, prescribe or change medication.
- Health claims must include evidence tier, dose/context uncertainty and a proxy-failure test.
- Prefer the smallest lesionable mechanism and preserve negative evidence.

## Coding-agent persistence contract

LOGOS-1 is also a coding-agent-operated repository. For implementation work:

1. read `CURRENT-WORK-ORDER.md` and do not silently replace the active scientific queue;
2. read `docs/architecture/MEMORY-SYSTEM.md` before changing memory persistence/retrieval;
3. treat memory-system layers as engineering concerns unless a scientific verdict explicitly promotes a primitive;
4. preserve `AdaptiveState != Authority`, `AgentMemory != AssuranceState`, and `OUTCOME_UNKNOWN != NOT_EXECUTED`;
5. after a substantive change, apply `docs/engineering/PUSH-PROTOCOL.md`;
6. update `CAPABILITIES.md` when a user-visible or agent-visible capability changes;
7. leave a durable session checkpoint under `09-SESSIONS/` when project state, architecture, evidence or active implementation work materially changes.

### Memory implementation rule

A memory subsystem may store, retrieve, rank, consolidate or summarize information. It must not mint grants, scopes, credentials, execution tokens or policy exceptions. Any retrieval result that affects an external action remains a proposal-side input and re-enters Γ.

Before memory retrieval, consolidation, file/tool dispatch or effect proposal,
obtain a non-denied `ScopeDecision`; `DEFER` means WAIT and only `ALLOW` or
`NARROW` may satisfy the implemented local precondition. The current
`ScopeDecision.evaluate()` checks exactly role, tool, memory kind, capability,
target and path. Parameter bounds, budgets, time validity, occurrences,
externality, reversibility, approval requirement, data/retention classes and
source versions require a separate downstream dispatch/effect gate and are not
evaluated by this package. If an exact request depends on an unsupported
dimension, WAIT/DENY rather than infer success. `ScopeDecision !=
DispatchAuthorization != ExternalApproval`; Γ and the separately owned
assurance interface remain mandatory.

### Change propagation

A coding change is incomplete when implementation, tests, architecture docs and capability inventory disagree. Prefer one coherent push over isolated code edits that leave the repository semantically stale.
