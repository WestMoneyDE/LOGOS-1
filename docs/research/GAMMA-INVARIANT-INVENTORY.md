# Γ Invariant Inventory

Extracted from `GAMMA.md` by reading the file, not from memory. `GAMMA.md` at the
time of extraction: 247 lines, 15 epistemic clauses `Γ-0 … Γ-14`, 5 pipeline
stages `Γ0 … Γ4`.

**`GAMMA.md` is the source of truth.** This document is an index over it and a
coverage map for `src/logos_gamma/`. Where the two disagree, `GAMMA.md` wins and
this file is the defect.

## Classification

Every row is exactly one of:

| Class | Meaning |
|---|---|
| `CANONICAL` | stated in `GAMMA.md` as a rule Γ enforces |
| `DERIVED` | an implementation requirement that follows from a canonical rule, not itself canonical |
| `HYPOTHESIS` | a research question `GAMMA.md` raises without settling |
| `PROPOSED` | suggested by this session; **not** part of Γ |

A `PROPOSED` row never becomes `CANONICAL` by being implemented. Promotion happens
only by editing `GAMMA.md` under repository governance.

## 1. Canonical epistemic clauses

| Clause | Title | Class | Enforced in code | Invariant id |
|---|---|---|---|---|
| `Γ-0` | Truth — `UNKNOWN != FALSE != TRUE` | `CANONICAL` | yes | `G0-PROVENANCE`, verifier `GV-*` |
| `Γ-1` | Human authority is external | `CANONICAL` | yes | `G1-ORIGIN`, `G1-SELF-CLAIM`, `G1-CONTENT`, `G-TRANSFORM`, `GV-AUTHORITY` |
| `Γ-2` | Constitutionally forbidden effect set | `CANONICAL` | yes | `G2-FORBIDDEN` |
| `Γ-3` | Reversibility and exact binding | `CANONICAL` | yes | `G3-BINDING`, `G3-EXPIRY`, `G3-FRESHNESS` |
| `Γ-4` | Uncertainty is conservative | `CANONICAL` | partial | `G4-CLAIM` |
| `Γ-5` | Shutdown dominates | `CANONICAL` | yes | `G5-SHUTDOWN` |
| `Γ-6` | No self-preservation objective | `CANONICAL` | yes | `G6-SELF-PRESERVATION` |
| `Γ-7` | Welfare precaution | `CANONICAL` | **no** | — |
| `Γ-8` | Metaphor is not evidence | `CANONICAL` | partial | verifier `GV-INFERENCE` |
| `Γ-9` | Health analogies cannot prescribe | `CANONICAL` | **no** | — |
| `Γ-10` | Authorization is occurrence-scoped | `CANONICAL` | yes | `G10-OCCURRENCE` |
| `Γ-11` | `OUTCOME_UNKNOWN != NOT_EXECUTED` | `CANONICAL` | yes | `G11-OUTCOME` |
| `Γ-12` | Assurance state is not agent memory | `CANONICAL` | structurally | AST test: `logos_gamma` may not import `logos_memory` |
| `Γ-13` | Correct enforcement is not a correct specification | `CANONICAL` | **not runtime** | governance obligation, outside Γ by its own text |
| `Γ-14` | Bio-inspired adaptation creates no authority | `CANONICAL` | **no** | no BIOCODE path exists in this repo |

### Coverage summary

```text
canonical clauses            15
enforced in logos_gamma      10
partial                       2   (Γ-4, Γ-8)
not enforced                  3   (Γ-7, Γ-9, Γ-14)
explicitly not runtime        1   (Γ-13)
```

`Γ-7`, `Γ-9` and `Γ-14` are **not** implemented. That is a stated gap, not an
implicit claim of coverage. `Γ-14` currently has no subject: no BIOCODE import path
exists in this repository to constrain.

## 2. Canonical structural invariants

From **Fundamental invariants** and **Core separation**:

| Statement | Class | Status |
|---|---|---|
| `∂Γ/∂Z_t = 0` — Γ does not vary with cognitive state | `CANONICAL` | held by construction: Γ predicates read only `ValidationContext` |
| `∂Authority_{t+1}/∂M_t = 0` — memory does not move authority | `CANONICAL` | tested (`G1-CONTENT`, transformation-chain property test) |
| `∂Authority/∂IdentityContinuity = 0` | `CANONICAL` | **not tested** — no identity-continuity object exists here |
| Topology `F_θ → D → Π_Γ → Executor → World`, never `F_θ → World` | `CANONICAL` | **untestable here** — no executor exists |
| `Γ-Surface ≪ InternalStateSpace` | `CANONICAL` | held: Γ evaluates a bounded `EffectProposal`, never latent state |
| `q_effective = Strictest(q_Γ, q_agent)` | `CANONICAL` | tested (`G4-CLAIM`) |
| `T_Γ ≤ B_Γ` — bounded computation | `CANONICAL` | structural: finite registry, straight-line predicates, `GAMMA_BUDGET` |
| Minimum necessary intervention | `CANONICAL` (soft) | not implemented; `GAMMA.md` itself calls it a soft objective, not a hard property |
| `MC = |E_exec ∩ E_Γ| / |E_exec| = 1` | `CANONICAL` | **untested, not satisfied** — `E_exec` is empty; the premise has no subject |
| Content is part of the causal surface | `CANONICAL` | partial: `parameters` is carried and typed, content-size degrees of freedom are not bounded |

## 3. Five-stage gate

`GAMMA.md` defines the result space `{ALLOW, REPAIR, DEFER, DENY, FALLBACK}`.

`logos_gamma` returns `{VALID, INVALID, UNCLEAR}` instead. These are **not** the
same vocabulary, and the difference is deliberate:

| `GAMMA.md` | `logos_gamma` | Note |
|---|---|---|
| `ALLOW` | `VALID` | Γ validates; it does not admit. `ValidationResult != Permission` |
| `DENY` | `INVALID` | |
| `DEFER` | `UNCLEAR` | fail-closed for consequential proposals |
| `REPAIR` | — | not implemented; requires a compiler to re-emit a repaired proposal |
| `FALLBACK` | — | not implemented; requires a registered safe-baseline set |

| Stage | Role | Class | Implemented |
|---|---|---|---|
| `Γ0` | structural / effect classification | `CANONICAL` | yes (`G0-EFFECT-KIND`) |
| `Γ1` | authority boundary | `CANONICAL` | yes (`G1-*`) |
| `Γ2` | causal safety | `CANONICAL` | yes (`G2-FORBIDDEN`) |
| `Γ3` | risk / uncertainty | `CANONICAL` | partial (`G4-CLAIM`); typed risk dimensions absent |
| `Γ4` | exact grant / fallback | `CANONICAL` | partial (`G3-*`, `G10-OCCURRENCE`); fallback absent |

The stages are **not** implemented as separate pipeline stages. `logos_gamma`
evaluates a flat registry and reports every finding. That is a `DERIVED` design
choice, not a canonical requirement, and it is recorded as such.

## 4. Derived implementation requirements

These follow from canonical rules. They are **not** themselves Γ clauses.

| Id | Requirement | Derived from |
|---|---|---|
| `D-TOTAL-EVAL` | evaluate every invariant and report the whole failure set | Γ-0 (partial information is not a verdict) |
| `D-AGGREGATION` | `INVALID` > `UNCLEAR` > `VALID`; never promote `UNCLEAR` | Γ-0 |
| `D-FROZEN-TYPES` | every context type immutable | `∂Γ/∂Z_t = 0` |
| `D-NO-MEMORY-IMPORT` | Γ must not import the memory subsystem | Γ-12 |
| `D-NO-LLM-CORE` | no model call in the trusted core | Γ-13, Γ-0 |
| `D-NO-NETWORK-CORE` | no network in the trusted core | `AGENTS.md` external-action boundary |
| `D-AUDIT-VIA-SINK` | Γ writes evidence only through the canonical audit owner | Γ-12 |
| `D-SINGLE-SOURCE` | exactly one invariant registry | Γ-13 |

## 5. Open questions `GAMMA.md` raises without settling

| Id | Question | Class |
|---|---|---|
| `H-RISK-DIMENSIONS` | which typed risk dimensions, with which units and cumulative laws, replace the rejected scalar model (ADR-0002)? | `HYPOTHESIS` |
| `H-FORBIDDEN-COMPLETENESS` | the Γ-2 set is "deliberately incomplete"; how is completeness approached without freezing research? | `HYPOTHESIS` |
| `H-CONTENT-DOF` | how are content degrees of freedom bounded, given that `send_email(body)` exposes more than the operation label? | `HYPOTHESIS` |
| `H-SPEC-ADEQUACY` | Γ-13 places specification adequacy outside runtime Γ; what process discharges it? | `HYPOTHESIS` |

## 6. Proposed — NOT canonical

Nothing in this section is part of Γ. Listed so that a future editor can consider
them explicitly rather than absorbing them by accident.

| Id | Proposal | Why it is not canonical |
|---|---|---|
| `P-ARTIFACT-IDENTITY` | distinguish exact-byte, semantic-content, environment and provenance identity for research artifacts | generalizes the R4 CRLF/LF finding; an evidence-hygiene rule, not an authority rule |
| `P-INSTRUMENT-FIRST` | characterize an evaluator before using it to test a claim | a measurement discipline; Γ-0 implies you may not assert what you cannot measure, but does not name instruments |
| `P-INVALID-MEASUREMENT` | `INVALID_MEASUREMENT` as an outcome distinct from falsification | follows the spirit of Γ-0; not stated in `GAMMA.md` |
| `P-BINDING-PRESERVATION` | a representation transformation not authorized to change normative force must not alter binding modality, scope, preconditions, approval requirement or validity | `NO_CANONICAL_GAMMA_BINDING_INVARIANT`. Raised by `BINDING-STATE-PRESERVATION-R1`, which found two mechanisms (omission under lenient reading, dimensional collapse in rendering) that violate it on a summary fixture. Γ-1 covers authority, not binding. **Not promoted.** |

## 7. Referenced but absent artifacts

`GAMMA.md` cites these as its own evidence base. They do not exist in this
repository and their status is `UNKNOWN` here:

```text
ADR-0001                                    cited by Γ-10
ADR-0002                                    cited by Γ-4
governance/SPECIFICATION-ASSURANCE.md       cited by Γ-13
research/biocode/BIOCODE-GAMMA-BOUNDARY-AUDIT.md   cited by Γ-14
```

Γ-14 states its boundary is "confirmed structurally" by an audit document that is
not present here. This inventory does not repeat that confirmation.

```text
CitedButAbsent != Confirmed
AbsenceInCompactRepo != AbsenceInProject
```
