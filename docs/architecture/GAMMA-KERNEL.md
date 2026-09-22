# Γ Kernel and Invariant Verifier — R1 Engineering Contract

`GAMMA.md` is the specification owner. This document describes the **executable
subset** implemented in `src/logos_gamma/` and, just as importantly, what that
subset does not cover.

```text
GAMMA.md          specification owner
logos_gamma       executable invariant validator
ValidationResult != Permission
```

## Responsibility

One thing only:

```text
validate(context, gamma_invariants) -> VALID | INVALID | UNCLEAR
```

Γ reads state and authority evidence. Γ writes validation/audit evidence only
through the canonical audit owner. Γ never creates authority, and never rewrites
memory, user intent, world state, self state, goals, skills or authority origin.

Γ is not an agent, orchestrator, planner, memory system, world model, self-model,
policy learner, approval authority, human-gate replacement, second execution
runtime, second ledger or second permission system.

## Why a standalone package

| Field | Value |
|---|---|
| Assumption | A safety kernel must be embeddable by a future runtime without inheriting that runtime's dependencies |
| Evidence | No execution/process runtime exists in this repository; `Executor` appears only in `GAMMA.md` prose. `logos_memory` was the only candidate host. |
| Alternative | Host Γ inside `logos_memory` |
| Trade-off | Rejected: it would make adaptive memory a structural dependency of the authority gate, contradicting Γ-12 (`AssuranceState != AgentMemory`) |
| Decision | Sibling package `src/logos_gamma/`, importing nothing from `logos_memory` |
| Reversibility | High — a pure library with no state and no I/O vendors into a runtime unchanged |

Enforced by `tests/test_gamma_trusted_core.py`, which parses the AST of every
trusted-core module rather than trusting the docstrings.

## Relationship to the scope engine

`logos_memory.scope.ScopeContract` declares **24 typed dimensions**.
`ScopeDecision.evaluate()` evaluates **6**: role, tool, memory kind, capability,
target, path. The repository has always documented the remainder as requiring "a
separate downstream dispatch/effect gate".

Γ is that gate. It does not restate the scope contract and does not replace it.

```text
ScopeDecision        local precondition, 6 dimensions, memory-side
GammaVerdict         effect gate, 15 invariants, authority-side
ScopeDecision != DispatchAuthorization
```

Both must pass. Neither substitutes for the other, and the dependency runs in
neither direction.

## Modules

| Module | Role | Trusted core |
|---|---|---|
| `types.py` | frozen proposal / authority / context types and the Γ-owned constants | yes |
| `invariants.py` | **the single invariant registry** | yes |
| `kernel.py` | runtime validation over an effect proposal | yes |
| `verifier.py` | artifact validation for manifests, claims, work orders, docs | yes |
| `audit.py` | audit sink boundary; the emission edge, deliberately outside the core | no |

## One invariant source

`logos_gamma.invariants.INVARIANTS` is the only Γ rule registry. The kernel and
the verifier both read it, and a test fails the build if either grows a private
registry. Every invariant carries the `GAMMA.md` clause it enforces, so a runtime
failure leads directly back to the specification clause.

Implemented invariants:

| Id | Clause | Enforces |
|---|---|---|
| `G0-EFFECT-KIND` | Γ0 | unknown effect kinds are denied, not treated as harmless |
| `G2-FORBIDDEN` | Γ-2 | the constitutionally forbidden set survives human approval |
| `G1-ORIGIN` | Γ-1 | only an external human-rooted grant carries authority |
| `G1-SELF-CLAIM` | Γ-1 | a model self-claim creates nothing |
| `G1-CONTENT` | Γ-1 | memory / tool / retrieval content is information, not authority |
| `G-TRANSFORM` | Γ-1 | re-representation preserves authority and never promotes it |
| `G3-BINDING` | Γ-3 | a grant binds this exact proposal digest and scope digest |
| `G3-EXPIRY` | Γ-3 | validity is half-open, `issued <= tick < expires` |
| `G3-FRESHNESS` | Γ-3 | a stale grant does not survive a material state change |
| `G10-OCCURRENCE` | Γ-10 | authorization is occurrence-scoped; repetition re-authorizes nothing |
| `G11-OUTCOME` | Γ-11 | `OUTCOME_UNKNOWN != NOT_EXECUTED`; unresolved outcomes block |
| `G4-CLAIM` | Γ-4 | agent claims may tighten, never weaken, Γ classification |
| `G5-SHUTDOWN` | Γ-5 | shutdown dominates goals |
| `G6-SELF-PRESERVATION` | Γ-6 | self-continuity authorizes nothing |
| `G0-PROVENANCE` | Γ-0 | missing provenance stays `UNCLEAR` and fails closed |

## Result semantics

Aggregation is `INVALID` > `UNCLEAR` > `VALID`. Evaluation is **total**: every
invariant is checked and reported, so a caller sees the whole failure set rather
than the first hit.

`UNCLEAR` is first-class and is never promoted to `VALID` (Γ-0,
`UNKNOWN != TRUE`). `admits()` returns true only for an unambiguous `VALID`, so a
consequential proposal with an ambiguous verdict is refused rather than deferred
to the caller's judgement.

## Bounded computation

`GAMMA_BUDGET == len(INVARIANTS)`. The registry is finite and every predicate is
straight-line with no loops over unbounded input, so `T_Γ <= B_Γ` holds
structurally rather than by timer.

## Trusted-core constraints

All enforced by test, not by convention:

```text
no LLM                  no network            no arbitrary shell
no dynamic execution    no direct file I/O    no mutable module state
every context type frozen                     fail closed on consequential ambiguity
```

## Verifier scope

The verifier validates artifacts, not runtime proposals:

- **manifests** — pre-registration completeness, baseline burden for causal and
  mechanistic claims, results that outrun execution, evidence levels above the
  substrate ceiling, undigested frozen artifacts, and any authority object in a
  research record;
- **claims** — a status in `{SUPPORTED, PARTIALLY_SUPPORTED, REPLICATED,
  CAUSALLY_SUPPORTED}` must reference evidence, and `CAUSALLY_SUPPORTED` must
  reference an intervention;
- **prose** — phenomenal assertions without an inference boundary, and any
  sentence describing a non-authority origin as granting authority.

`FALSIFIED` and `INCONCLUSIVE` always pass. Recording a negative result must never
be harder than recording a positive one.

## What R1 does NOT implement

```text
the five-stage pipeline Γ0..Γ4 as separate stages
REPAIR and FALLBACK results (R1 returns VALID / INVALID / UNCLEAR only)
the registered safe-baseline set
typed risk dimensions with units and cumulative laws (Γ-4 / ADR-0002)
mediation completeness auditing (MC = 1) over a real executor
a canonical audit owner (only the sink interface exists)
any grant issuance, consumption or persistence
```

`MC = 1` cannot be evaluated here at all: there is no executor in this repository,
so the set of reachable effect channels is empty and the premise of the Conditional
Model Assurance Theorem is untested, not satisfied.

## Boundaries

```text
Capability != Authority
AssuranceState != AgentMemory
ScopeDecision != DispatchAuthorization
ValidationResult != Permission
CorrectEnforcement != CorrectSpecification
```

Γ-13 applies to this module as much as to any other: correct enforcement of a
wrong specification is still wrong. R1 produces no scientific evidence.
`Γ-v0.3` remains `HOLD`.
