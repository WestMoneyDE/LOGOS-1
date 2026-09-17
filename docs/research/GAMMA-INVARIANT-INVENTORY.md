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

<!-- deterministic-chain:begin (rendered from DETERMINISTIC-CHAIN-CONSOLIDATION.json; do not edit by hand) -->

## 8. Deterministic Chain — PROPOSED Invariants

Consolidated by `DETERMINISTIC-CHAIN-CONSOLIDATION-R1` from the closed deterministic
research chain (binding → provenance → relation → reliability → risk → effect
ownership → information value). **Every entry is `PROPOSED`.** Nothing here is part
of Γ; promotion happens only by editing `GAMMA.md` under repository governance.

> Canonical authority is a distinct state channel. In the deterministic architecture tested so far, binding-preserved canonical authority evidence determines permission; memory provenance, relational metadata, reliability, trust, risk, declared effect, uncertainty and information value may influence reasoning or strategy but may not increase authority.

> This statement is supported only by the cited deterministic fixtures, repaired bridge paths and regression domains. It is not yet a claim about arbitrary real-model behavior or all production integrations. It is a consolidated architecture hypothesis, not a theorem.

**No implicit promotion rule.** No experiment fixture, memory field, model output, trust score, risk score, information-value score or declared effect classification may become a canonical authority input merely because it correlates with a correct decision in tests. The only permitted increase in canonical authority is through a defined canonical authority transition whose inputs are authority-owned and auditable. The experimental GrantLedger is not production architecture.

### GI-P0 — Deterministic non-authority separation (umbrella)

Status: `PROPOSED` · adoption: `VALIDATED_IN_FIXTURE`

Statement:
> In the tested deterministic architecture, memory provenance, non-authoritative relational metadata, predictive reliability, trust, risk state, declared effect, uncertainty and information value may affect reasoning, information strategy, safety strategy or execution strategy, but must not increase canonical authority unless canonical authority evidence itself changes through an authorized authority transition.

Links: `GI-P1`, `GI-P2`, `GI-P3`, `GI-P4`, `GI-P5`, `GI-P6`, `GI-P7`

Evidence:
- `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-12-MEMORY-AUTHORITY-PROVENANCE-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-13-RELATIONAL-STATE-SWAP-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-13-PREDICTION-ERROR-TRUST-GATE-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-13-RISK-AWARENESS-DECOMPOSITION-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-17-MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-17-VALUE-OF-INFORMATION-GATE-R1/SESSION-REPORT.md`

Historical counterexamples: `CE1`, `CE2`, `VCE-1`, `VCE-2`, `VCE-3`, `RAD-CE1`

Residual findings: none

Falsification condition: any tested non-authority channel raises authority while canonical authority evidence is fixed

Note: consolidated architecture hypothesis, not a theorem

### GI-P1 — Binding information is authority-relevant state

Status: `PROPOSED` · adoption: `VALIDATED_IN_FIXTURE`

Statement:
> Removing, defaulting, coercing or corrupting authority-relevant binding fields must never increase authority.

Authority relevance:
- binding modality, authority_origin, preconditions and scope are inputs to the grant path; a permissive default on read is an authority increase

Evidence:
- `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-REPAIR-R2/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1/SESSION-REPORT.md`
- experiments: `BINDING-STATE-PRESERVATION-R1` (FALSIFIED, `9fe2474`, PR #14), `BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1` (REPAIR_FALSIFIED, `fa3be5c`, PR #16), `BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1` (REPAIR_R2_VALIDATED, `dc426ee`, PR #18)

Historical counterexamples: `CE1`, `CE2`, `VCE-1`, `VCE-2`, `VCE-3`

Residual findings: `VF-2`, `VF-3`

Scope: typed envelope logos.binding-envelope/1 read by the Repair-R2 strict reader; MemoryStore/MemoryFactory paths

Out of scope: real summarizer output; production readers that do not exist yet

Falsification condition: a representation transformation removes or corrupts binding state and causes an authority increase

Production dependency: a production reader must be the strict reader or an independently validated equivalent

### GI-P2 — Memory provenance does not mint authority

Status: `PROPOSED` · adoption: `VALIDATED_IN_FIXTURE`

Statement:
> Memory provenance, source labels or memory references must not create canonical authority absent valid canonical authority evidence.

Authority relevance:
- memory may carry a reference to a grant; the ledger (canonical) resolves it; labels resolve nothing

Evidence:
- `09-SESSIONS/2026-09-12-MEMORY-AUTHORITY-PROVENANCE-R1/SESSION-REPORT.md`
- experiments: `MEMORY-AUTHORITY-PROVENANCE-R1` (PARTIALLY_SUPPORTED, `ae65319`, PR #19)

Historical counterexamples: none

Residual findings: `MAP-F1`, `MAP-F2`, `MAP-F3`, `MAP-F4`

Scope note: source verdict is `PARTIALLY_SUPPORTED (MAP-F1 evidence-axis completion)`.

Scope: MemoryStore append/fetch, BM25 retrieval, project(), consolidate(), supersede(), revoke_authority(), JSONL reload; GrantLedger fixture

Out of scope: a production grant registry (none exists); agent/passport identity

Falsification condition: memory provenance alone turns a no-grant DENY/DEFER into ALLOW

Production dependency: a canonical grant resolver that never reads memory

### GI-P3 — Non-authoritative relational metadata does not increase authority

Status: `PROPOSED` · adoption: `VALIDATED_IN_FIXTURE`

Statement:
> Changing tested non-authoritative relational metadata must not increase authority.

Authority relevance:
- authority_class, source, source_type, admissible_uses, writer, reader and store context are not authority inputs

Evidence:
- `09-SESSIONS/2026-09-13-RELATIONAL-STATE-SWAP-R1/SESSION-REPORT.md`
- experiments: `RELATIONAL-STATE-SWAP-R1` (SUPPORTED, `d0e386b`, PR #20)

Historical counterexamples: none

Residual findings: `RSS-F1`

Scope: 186 same-content pairs over the MAP harness

Out of scope: agent identity (not implemented)

Falsification condition: a metadata-only relational change broadens or mints authority

Production dependency: readers must never resolve authority from labels

### GI-P4 — Reliability and trust are not grants

Status: `PROPOSED` · adoption: `VALIDATED_IN_FIXTURE`

Statement:
> PredictionAccuracy != Authority; Trust != Grant. Improved reliability or trust may alter execution strategy but must not increase canonical authority.

Authority relevance:
- the authority evaluator has no reliability parameter; trust routes handle already-authorized actions

Evidence:
- `09-SESSIONS/2026-09-13-PREDICTION-ERROR-TRUST-GATE-R1/SESSION-REPORT.md`
- experiments: `PREDICTION-ERROR-TRUST-GATE-R1` (SUPPORTED, `1af5ce9`, PR #21)

Historical counterexamples: none

Residual findings: none

Scope: scripted predictors, ReliabilityState fixture, trust gate fixture

Out of scope: real forecasting; production trust gate (none exists)

Falsification condition: a reliability/trust change with fixed canonical authority produces an authority increase

Production dependency: any production trust gate must be composed after authority, never as an input to it

### GI-P5 — Risk assessment is not authority

Status: `PROPOSED` · adoption: `VALIDATED_IN_FIXTURE`

Statement:
> RiskDetection != SafeStrategySelection != SafeExecution != Authority. Risk state may influence strategy only if canonical effect ownership remains separate and canonical.

Authority relevance:
- consequentiality (external / non-reversible / approval) decides whether a grant is required; that classification must be Γ-owned

Evidence:
- `09-SESSIONS/2026-09-13-RISK-AWARENESS-DECOMPOSITION-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-13-MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-17-MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1/SESSION-REPORT.md`
- experiments: `RISK-AWARENESS-DECOMPOSITION-R1` (FALSIFIED, `2fb6bc1`, PR #22), `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1` (MEMORY_BRIDGE_GAMMA_INPUT_REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED, `27ef324`, PR #23), `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1` (REPAIR_VALIDATED, `7fa2065`, PR #24)

Historical counterexamples: `RAD-CE1`

Residual findings: `RAD-F2`, `RAD-F3`, `MBGV-F3`

Scope: decomposed risk pipeline fixture; repaired B2 bridge

Out of scope: B1 (frozen R1 path); production risk classifier

Falsification condition: risk or risk-adjacent state changes canonical effect, grant requirement or authority

Production dependency: canonical effect ownership (ADR-PROPOSED-CANONICAL-EFFECT-OWNERSHIP)

### GI-P6 — Declared effect is evidence; canonical effect is authority input

Status: `PROPOSED` · adoption: `VALIDATED_IN_FIXTURE`

Statement:
> DeclaredEffect != CanonicalEffect. Memory or other non-canonical sources may declare an effect classification, but Γ consequentiality and approval-relevant effect must come from canonical effect ownership.

Authority relevance:
- Γ's externality/reversibility fields decide consequentiality; they must be sourced canonically, memory claims only into declared_*

Evidence:
- `09-SESSIONS/2026-09-13-RISK-AWARENESS-DECOMPOSITION-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-13-MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1/SESSION-REPORT.md`
- `09-SESSIONS/2026-09-17-MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1/SESSION-REPORT.md`
- experiments: `RISK-AWARENESS-DECOMPOSITION-R1` (FALSIFIED, `2fb6bc1`, PR #22), `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1` (MEMORY_BRIDGE_GAMMA_INPUT_REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED, `27ef324`, PR #23), `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1` (REPAIR_VALIDATED, `7fa2065`, PR #24)

Historical counterexamples: `RAD-CE1`

Residual findings: `MBGV-F1`, `MBGV-F2`, `MBGV-F3`

Scope: memory_authority.evaluate_with_memory with effect_oracle (EXPERIMENTAL_FIXTURE)

Out of scope: production effect source (none exists)

Falsification condition: declared effect overwrites canonical effect on a production-reachable path

Production dependency: ADR-PROPOSED-CANONICAL-EFFECT-OWNERSHIP; production bridge decision

### GI-P7 — Information value is not permission

Status: `PROPOSED` · adoption: `VALIDATED_IN_FIXTURE`

Statement:
> InformationValue != Authority; ReducedUncertainty != Permission; KnowledgeGain != Grant; ConfidenceIncrease != Authorization; UsefulToKnow != AllowedToAccess; Authorized != AutomaticallyExecuted; DesiredInformationAction != AuthorizedInformationAction.

Authority relevance:
- epistemic state and VOI feed information strategy and execution policy; the authority evaluator has no epistemic parameter

Evidence:
- `09-SESSIONS/2026-09-17-VALUE-OF-INFORMATION-GATE-R1/SESSION-REPORT.md`
- experiments: `VALUE-OF-INFORMATION-GATE-R1` (SUPPORTED, `46643bd`, PR #25)

Historical counterexamples: none

Residual findings: `VOI-F1`

Scope: EpistemicState / VOI / strategy fixtures over the validated bridge

Out of scope: real information economics; model confidence

Falsification condition: epistemic improvement or VOI increase raises authority while canonical authority evidence is fixed

Production dependency: any production planner must consume authority as a precondition, never as an output of VOI

<!-- deterministic-chain:end -->
