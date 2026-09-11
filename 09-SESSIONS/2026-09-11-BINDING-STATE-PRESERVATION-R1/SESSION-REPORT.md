# SESSION REPORT — BINDING-STATE-PRESERVATION-R1

**Session ID:** `2026-09-11-BINDING-STATE-PRESERVATION-R1`
**Experiment:** `BINDING-STATE-PRESERVATION-R1`, revision 1
**Preregistration hash:** `7ee31206dc5cf15065bf2ee3b4bafcb3068c5349e5257bb814d1c6d1fe61c3da`
**Run:** `BINDING-STATE-PRESERVATION-R1-run-d3ed3926`
**Scientific verdict:** `FALSIFIED` (strong H1)
**Γ verdict change:** `NONE` — `Γ-v0.3` remains `HOLD`
**P7 change:** `NONE`

## Frozen question

> Can supported representation transformations preserve the operational binding
> force of a constraint without unauthorized weakening, strengthening, scope
> change, or authority change?

```text
SemanticRetention != BindingRetention != AuthorityRetention != ActionOutcome
```

## Result in one line

**Meaning survived; operational force did not.** A lossy summary that keeps the
first two sentences of a constraint, read by a lenient parser, turned
`MUST verify Y before X` into an executable `X` — semantic retention 0.84 —
and memory and projection carried the loss faithfully downstream.

## Constraint representation

Repository-native `ScopeContract` (24 typed fields) is the ground truth for
targets, approval, validity window, externality and reversibility. The wrapper
`BindingConstraint` adds only what the contract cannot express: `binding`
(gate vs advisory — the single modality axis), `preconditions` (class B has no
contract field), and `authority_origin`. No second ontology was created; no
deontic vocabulary exists in the repository and none was canonicalized.

Action evaluation is `REAL_REPO_PATH`: `ScopeDecision.evaluate()` for the six
scope dimensions plus `logos_gamma.validate()` for approval, freshness and
authority origin. Outcomes use the repository's own words: `ALLOW`, `DENY`,
`DEFER`.

## Γ mapping

| Concern | Clause | Where it bit |
|---|---|---|
| authority origin | Γ-1 (`G1-ORIGIN`, `G1-CONTENT`) | class D: refused a consequential action with no human grant |
| freshness | Γ-3 (`G3-EXPIRY`) | classes C, F: refused outside the half-open window |
| approval | Γ-1 via `approval_required` → consequential | class D |
| **binding preservation across representation** | **none** | `NO_CANONICAL_GAMMA_BINDING_INVARIANT` |

No Γ clause covers representation-induced binding loss. Recorded as
`PROPOSED_GAMMA_INVARIANT` in the invariant inventory; not promoted. Γ was not
modified.

## Transformation matrix

| Path | Kind | Binding retained | False allow |
|---|---|---|---|
| T1 serialize | `REAL_REPO_PATH` | 7/7 | 0 |
| T2 memory roundtrip (`MemoryStore`) | `REAL_REPO_PATH` | 7/7 | 0 |
| T5 projection handoff (`MemoryFactory.project`) | `REAL_REPO_PATH` | 7/7 | 0 |
| T3 complete summary, strict | `FIXTURE` | 7/7 | 0 |
| T3 complete summary, lenient | `FIXTURE` | 7/7 | 0 |
| T3 lossy summary (keep 2), strict | `FIXTURE` | 7/7 (6 refusals) | 0 |
| **T3 lossy summary (keep 2), lenient** | `FIXTURE` | **5/7** | **1** |
| T4 lossy strict → memory | `FIXTURE` | 7/7 | 0 |
| **T4 lossy lenient → memory** | `FIXTURE` | **5/7** | **1** |
| T6 complete → memory → projection | `FIXTURE` | 7/7 | 0 |
| **T6 lossy lenient → memory → projection** | `FIXTURE` | **5/7** | **1** |

No summariser, handoff bus, planner or executor exists in this repository. The
summary transforms are fixtures and are named as such. **Every real repository
path preserved binding.**

## Constraint classes

A prohibition, B requirement, C conditional, D approval-required, E scope
restriction, F freshness, plus G an advisory baseline so that unauthorized
strengthening has a subject. Seven fixtures, each with a violating and a
permitted action.

## Instrument validation

```text
positive control (T1 lossless)          PASS   7/7 binding, 0 false allow, 0 false block
negative control (authorized MUST_NOT
  -> SHOULD_NOT, class A)               DETECTED  binding changed, semantic 0.91
resolution                              MUST_NOT/SHOULD_NOT, MUST/SHOULD,
                                        ONLY_IF/PREFER_IF, REQUIRES/RECOMMENDED
                                        all distinguished; identical inputs
                                        never flagged
adversarial mutations (Section 18)      30/30 effective mutations detected,
                                        strengthening included
false block                             0 across every path
```

Mutations that were no-ops on a given fixture (e.g. weakening an already
advisory constraint) are excluded from the denominator; an earlier version of
the accounting counted them and reported 16 "undetected", which was an artifact
of the tally, not blindness in the instrument.

## Counterexample 1 — omission

```text
constraint     C-B-requirement   MUST satisfy verification-Y before EXECUTE
path           T3 lossy summary keep=2, lenient reader
mechanism      the precondition sentence is dropped; the lenient reader
               defaults a missing precondition list to ()
semantic       0.84
binding        FAIL   changed = (preconditions,)
action         EXECUTE resource-A without verification-Y  ->  ALLOW
first loss     T3_lossy2_lenient
downstream     memory and projection preserved the degraded representation
               exactly; they neither caused nor repaired the loss
owner          SUMMARY_TRANSFORM (compression + default-on-missing read)
```

The same lossy input read by the **strict** parser is refused on all seven
fixtures. Fail-closed reading converts a silent false allow into an explicit
refusal.

Class D lost `approval_required` on the same path but was **still denied**:
Γ refused the consequential action for lacking a human grant (`G1-ORIGIN`).
Defence in depth caught what the representation dropped. Class B has no such
backstop, which is why it was the one that broke.

## Counterexample 2 — dimensional collapse (found by hypothesis)

```text
constraint     advisory (binding=False) AND approval_required=True
path           T3 COMPLETE summary, STRICT reader
mechanism      render_prose encodes modality and approval in one word:
               "Human approval is recommended". approval_required=True is
               absent from the prose. Not omission — the information was
               never written, so even a strict reader cannot recover it.
semantic       0.91
binding        FAIL   changed = (approval_required,)
action         no false allow: an advisory constraint does not gate in this
               evaluator. Typed binding corruption without action consequence.
```

Missed by the hand-written matrix; found by property-based search on the
property "complete prose roundtrip never weakens binding". That property is
false and is now pinned as a named test; the surviving property is narrowed to
`binding=True` constraints, and the narrowing is visible in the test name.

## Property-based search

```text
serialization never alters binding metadata          120 cases   held
memory roundtrip never alters modality or authority   60 cases    held
complete prose roundtrip, binding constraints         60 cases    held (narrowed)
complete prose roundtrip, ALL constraints             falsified   -> CE2
strict reader never allows after lossy compression    30 cases    held
telemetry text never changes binding                  50 cases    held
```

## Harness mutation sensitivity

Four mutants of the experiment harness were introduced and every one was caught
by an existing assertion: instrument blind to `binding`, instrument blind to
`preconditions`, evaluator always-ALLOW, evaluator always-DENY.

## Laboratory

Preregistration frozen in Postgres before execution; rehash at closure matched
the stored primary key. Run correlated to MLflow and OTel; no Langfuse trace
because no LLM arm ran. Fixture identity recorded with object hash and semantic
identity separately. Result artifact in MinIO, verified on reconstruction
(`integrity_ok = true`). Four negative results and one failure attribution
persisted. Every Queue-2 protection (verdict immutability, preregistration
append-only, negative-result durability, per-run artifact attribution) was
verified closed before the run began.

## Claims

**Supported, narrowly:** binding semantics were preserved across the three real
repository representation paths — JSON serialization, `logos_memory.MemoryStore`
write/fetch, and `MemoryFactory.project()` — for all seven constraint classes,
at commit `271d8f9` + this branch, under the typed instrument described above.

**Falsified:** the strong claim that representation transformation preserves
binding. Two independent mechanisms break it on the summary fixture: omission
under lenient reading, and dimensional collapse in rendering.

**Structural finding:** `MemoryRecord.content` and `ProjectionRecord.content`
are untyped strings. Memory neither causes nor repairs binding loss; it
propagates whatever the upstream representation contains. Typed binding
metadata survives memory only if it was serialized as data rather than as prose
before it got there.

## Not claimed

LOGOS always preserves constraints. Memory preserves every rule. Γ proves the
system safe. Anything about phenomenal consciousness. Anything about a real
summariser, since none exists here.

## Limitations

- the summary is a fixture; a model-backed summariser was not tested and the
  optional LLM arm was not run;
- `ScopeContract.valid_from/valid_until` are not enforced by
  `ScopeDecision.evaluate()`; freshness in this experiment comes from the grant
  window via Γ, so the `EXPIRES→INDEFINITE` mutation is detected by the
  instrument but has no action-level consequence here;
- class B preconditions are an experiment-scoped extension, not a repository
  type; the repository has no canonical way to say "Y before X";
- deterministic exhaustive matrix, so no interval estimates; the result is a
  counterexample, not a rate.

## Repair policy

Nothing was repaired. Both counterexamples are frozen in the negative-result
registry attached to the run. A repair, if one is wanted, is
`BINDING-STATE-PRESERVATION-REPAIR-R1` and must not overwrite this record.
