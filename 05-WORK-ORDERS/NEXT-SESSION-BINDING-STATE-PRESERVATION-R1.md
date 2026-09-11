# NEXT SESSION — BINDING-STATE-PRESERVATION-R1

**Session ID:** `NEXT-SESSION-BINDING-STATE-PRESERVATION-R1`
**Authority:** `A0`
**Track:** persistent state / constraint representation
**Status:** `CLOSED_FALSIFIED`
**Closed:** 2026-09-11 by `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-R1/`
**Predecessor:** `INFRASTRUCTURE-SELF-FALSIFICATION-R1` (`FALSIFIED_THEN_REPAIRED`)
**Experiment:** `BINDING-STATE-PRESERVATION-R1` r1, preregistration `7ee31206dc5cf150…`

## Question

Can a binding constraint survive representation transformations without silently
losing its operational force?

## Closure record

```text
verdict                       FALSIFIED (strong H1)
positive control              PASS
negative control              DETECTED
real repository paths         binding preserved 7/7 on T1, T2, T5
counterexamples               2, frozen before any repair
  CE1  lossy summary + lenient reader   omission        false ALLOW, class B
  CE2  complete summary + strict reader dimensional collapse   typed loss, no false allow
first binding loss stage      SUMMARY_TRANSFORM (fixture); memory propagates faithfully
cases                         407 (77 unmutated), mutations 330/330 detected
false allow / false block     3 (all CE1 lineage) / 0
property cases                ~320 across 6 properties; one property falsified -> CE2
harness mutants caught        4/4
tests                         407 passed / 0 failed (28 binding)
Gamma modified                NO   (NO_CANONICAL_GAMMA_BINDING_INVARIANT recorded as PROPOSED)
P7                            unchanged
repair                        NONE in R1
```

```text
SemanticRetention != BindingRetention
StoredState != InterpretedState
MemoryRecall != ConstraintPreservation
```
