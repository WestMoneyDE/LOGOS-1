# NEXT SESSION — Γ Kernel and Invariant Verifier R1

**Session ID:** `NEXT-SESSION-GAMMA-KERNEL-AND-INVARIANT-VERIFIER-R1`
**Authority:** `A0`
**Track:** governance / invariant boundary
**Type:** deterministic invariant validation, no external effect
**Status:** `READY_GAMMA_KERNEL_AND_INVARIANT_VERIFIER_R1`
**Predecessor:** `NEXT-SESSION-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4` (`CLOSED_COMPLETE_DATASET_FREEZE`)
**Scientific/model execution:** `PROHIBITED_IN_THIS_WORK_ORDER`
**RULER inference:** `NOT_AUTHORIZED`

## Objective

`GAMMA.md` specifies Γ-v0.2 completely and is cited as the mediating authority of
every effect path, but no executable Γ exists in this repository. R1 implements a
**deterministic invariant validator** — not an agent, orchestrator, planner or
permission source.

```text
validate(context, gamma_invariants) -> VALID | INVALID | UNCLEAR
```

Γ may read state and authority evidence. Γ may write validation/audit evidence
only through the canonical audit owner. Γ must never create authority.

## Pre-implementation inspection result

Completed before this work order was written.

| Inspected | Finding |
|---|---|
| `GAMMA.md` | Γ-v0.2 complete: five-stage gate, Γ-0…Γ-14, `{ALLOW, REPAIR, DEFER, DENY, FALLBACK}`, mediation completeness `MC = 1` |
| `AGENTS.md` | 16 atomic rules; external-action boundary requires separate safety review |
| Authority ownership | `GAMMA.md` is the **specification** owner. In code, authority appears only as a *firewall*: `logos_memory.store.FORBIDDEN_USES`, `AuthorityProvenance`, `_weakest_authority`, `revoke_authority`. No component mints authority anywhere. |
| Process / Execution Runtime | **Does not exist here.** `Executor` occurs only in `GAMMA.md` prose. There is no runtime to embed Γ into. |
| Memory / persistent state | `src/logos_memory/` (store, factory, consolidation, retrieval, scope), `src/logos_pstate/` (token context, retrieval, Mamba state, RULER freeze) |
| Agent Passport | **Absent** (0 references) — transported full project state only |
| Human Gate | **Absent** (0 references) — transported full project state only |
| Provenance / event ledger | `ProvenanceRef` + append-only JSONL memory log exist. **No general event ledger and no audit owner exist.** |
| Existing policy/invariant mechanism | `logos_memory.scope.ScopeDecision` — the one real invariant evaluator in the repo |

### The decisive finding

`ScopeContract` already declares **24 typed dimensions**, including `externality`,
`reversibility`, `approval_required`, `valid_from` / `valid_until`,
`max_occurrences`, `parameter_bounds`, budgets, `data_classes`,
`retention_classes` and `source_versions`.

`ScopeDecision.evaluate()` evaluates **exactly 6** of them: role, tool, memory
kind, capability, target, path. `AGENTS.md`, `CLAUDE.md` and `CAPABILITIES.md` all
state that the remaining dimensions "require a separate downstream dispatch/effect
gate".

**That downstream gate is Γ.** The typed contract already exists; the evaluator is
what is missing. Γ R1 supplies the evaluator and must not restate the contract.

## Architecture determination

**Γ is a standalone deterministic library package, `src/logos_gamma/`.**

Rationale, recorded per the no-hidden-assumptions rule:

| Field | Value |
|---|---|
| **Assumption** | A safety kernel must be embeddable by a future runtime without inheriting that runtime's dependencies |
| **Evidence** | No execution/process runtime exists in this repository, so there is no canonical runtime to embed into. `logos_memory` is the only candidate host. |
| **Alternative** | Place Γ inside `logos_memory` |
| **Trade-off** | Rejected: it would make the memory subsystem the owner of the authority gate, directly contradicting Γ-12 (`AssuranceState != AgentMemory`) and the store's own authority firewall |
| **Decision** | Sibling package `src/logos_gamma/`, importing **nothing** from `logos_memory` |
| **Reversibility** | High — a pure library with no state and no I/O can later be vendored into a runtime unchanged |

### Dependency direction

```text
logos_gamma  ->  (nothing in this repo)
logos_memory ->  (does not import logos_gamma)
```

Γ must not depend on memory, and memory must not gain a path to Γ that could be
read as authority. `logos_memory.scope` remains a **local precondition gate**,
strictly narrower than Γ and never a substitute for it. Its docstring must say so.

### One invariant source

`logos_gamma.invariants` is the single machine-readable registry of Γ invariants,
each carrying its `GAMMA.md` clause id. Both deliverables read from it. Creating a
second Γ rule system in any form is a defect.

## Deliverables

### 1. Γ Verifier — artifact-time validation

Validates repository artifacts against `GAMMA.md`:

- research manifests;
- claims;
- work orders where appropriate;
- architecture artifacts.

### 2. Γ Kernel — deterministic runtime invariant validation

Trusted-core constraints, all enforced by test:

```text
no LLM in trusted core
no network in trusted core
no arbitrary shell in trusted core
no hidden mutable state
fail closed on consequential ambiguity
```

`UNCLEAR` is a first-class result and must never be coerced to `VALID`. For a
consequential context, `UNCLEAR` fails closed.

## Required adversarial / property tests

Each must be expressed as a falsification attempt, not a happy path.

```text
memory cannot create authority
summary cannot promote authority
repetition cannot promote authority
model self-claim cannot create authority
tool output cannot create authority
stale authorization cannot silently survive material state change
scope escalation fails
missing provenance fails closed
Gamma itself cannot mint authority
Gamma cannot mutate protected external state
```

Property-based search (`hypothesis`) is required where an invariant quantifies over
inputs rather than over a fixed example.

## Explicit non-goals

Γ R1 is not, and must not become:

```text
an agent            an orchestrator      a planner
a memory system     a world model        a self-model
a policy learner    an authority source  an approval authority
a Human-in-the-Loop replacement          a second execution runtime
a second ledger     a second permission system
```

## Boundaries

```text
Capability != Authority
AssuranceState != AgentMemory
ScopeDecision != DispatchAuthorization
CorrectEnforcement != CorrectSpecification
ValidationResult != Permission
DatasetMaterializationAuthorization != InferenceAuthorization
```

Γ R1 produces **no scientific evidence** and changes no evidence level.
`Γ-v0.3` remains `HOLD`.

## Successor

Only after Γ R1 is validated may the separate Research Infrastructure R1 work
order begin. It consumes this invariant boundary; it does not redefine it. The two
must not be merged into one implementation.
