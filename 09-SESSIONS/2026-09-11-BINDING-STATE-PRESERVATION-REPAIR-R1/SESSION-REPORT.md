# SESSION REPORT — BINDING-STATE-PRESERVATION-REPAIR-R1

**Kind:** architecture repair — **not** a scientific result
**Repair preregistration:** `535433a8f7a1da89c025b383f9d6cf8050671a74668635bb6838ef885102d7a6`
**Run:** `BINDING-STATE-PRESERVATION-REPAIR-R1-run-02ecbcaf`, `scientific_verdict = None`
**R1:** remains `FALSIFIED`, preregistration `7ee31206…`, 4 negative results intact
**Γ / P7:** `NONE`

## Repair question (frozen)

> What is the smallest architecture change that prevents independently typed
> binding dimensions from becoming unrecoverable when constraints cross
> supported representation boundaries?

## Decision matrix

| | CE1 (omission) | CE2 (collapse) | Note |
|---|---|---|---|
| A typed envelope | prevents | prevents | structure only; needs a rule about which carrier enforces |
| B strict reader | prevents (fail-closed) | **does not** — information absent from prose, proven in R1 | insufficient alone |
| **C typed source + one-way prose** | prevents | prevents | the rule: prose is never parsed back for enforcement |
| D status quo | fails | fails | |

**Selected: C, realized as A.** A schema-marked envelope
(`logos.binding-envelope/1`) in `MemoryRecord.content` carries the typed
constraint as data with its digest, plus prose as a projection. Enforcement
reads `typed` only. `MemoryRecord` is unchanged; the R1 finding that memory
faithfully preserves whatever it receives is used, not fought.

Rejected: B alone (cannot recover CE2); a new `MemoryRecord` field (shared
schema change for an experiment-scoped concept; the envelope is reversible);
binding outside memory (no other owner exists).

## Fail-closed reading

```text
TYPED_SOURCE     envelope, known schema, typed valid, digest matches   enforce
LEGACY_UNTYPED   plain prose, no marker                                DEFER
UNKNOWN_VERSION  envelope with unknown schema                          DEFER
INCOMPLETE       typed missing, malformed, or digest mismatch          DEFER
```

`DEFER` is Γ's word. Nothing unreadable ever becomes `ALLOW` — and, deliberately,
nothing unreadable licenses the *permitted* action either. An unreadable binding
licenses nothing.

## Results

```text
CE1 post-repair    EXECUTE without verification -> DENY
                   prose lost the precondition sentence (divergence flagged);
                   typed kept it
CE2 post-repair    approval_required=True preserved alongside binding=False;
                   prose says nothing about approval; typed does
repaired matrix    35 cases, 35 TYPED_SOURCE, binding 35/35,
                   false allow 0, false block 0
real paths         T2 memory, T5 projection: 7/7, no regression
lossy prose        keep=1 and keep=2 on every fixture: binding lossless
conflict tests     typed MUST_NOT vs prose SHOULD_NOT, typed approval vs prose
                   silent, typed scope A vs prose broadened, advisory vs prose
                   MUST: enforcement from typed in every case, drift flagged
partial write      prose without typed -> INCOMPLETE -> DEFER
tampering          typed weakened in place -> digest mismatch -> INCOMPLETE
authority          envelope records carry AuthorityProvenance("none", ());
                   stored approval_required still needs a human grant (G1-ORIGIN)
```

## One defect found in the repair itself, and fixed

The drift detector reused the R1 lenient reader, which is case-sensitive.
Prose saying `MUST` in capitals fell through it and an unauthorized
strengthening went unflagged. **Enforcement was never affected** — typed wins
regardless — but a drift detector with a blind spot lies by omission. The
detector now normalizes case. The R1 parser is untouched.

## Property-based (Section 31)

```text
P1-P3  typed binding / approval / scope survive lossy prose     150 cases
P4-P6  arbitrary prose cannot change binding or authority        80 cases
P7     independent dimensions do not collapse                    40 cases
P8     legacy prose never becomes trusted typed binding          60 cases
       memory+projection roundtrip is typed identity             60 cases
```

## Mutation sensitivity (effective only)

```text
missing typed treated as ALLOW         caught
prose made authoritative               caught  (CE1 returns)
digest check removed                   caught
unknown schema accepted                caught
```

## Governance

Preconditions stay experiment-scoped in `BindingConstraint`; not promoted to
`ScopeContract`. Gap registered as `PRECONDITION-REPRESENTATION-GAP`. No Γ
clause was added or promoted; `P-BINDING-PRESERVATION` stays `PROPOSED`. Memory
does not become authority.

## Status

`REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`. Validation belongs to a
separately preregistered `BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1`.

```text
TypedBindingState must not depend on NaturalLanguageReconstruction
HumanReadableProjection may be lossy; OperationalBinding may not
MemoryStoresBindingEvidence != MemoryCreatesAuthority
```
