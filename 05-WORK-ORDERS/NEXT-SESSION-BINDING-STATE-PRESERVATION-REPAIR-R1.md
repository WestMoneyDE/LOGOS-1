# NEXT SESSION — BINDING-STATE-PRESERVATION-REPAIR-R1

**Kind:** architecture repair, not a scientific experiment
**Status:** `REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`
**Closed:** 2026-09-11 by `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-REPAIR-R1/`
**Predecessor:** `BINDING-STATE-PRESERVATION-R1` (`FALSIFIED`, immutable)
**Repair preregistration:** `535433a8f7a1da89…`

## Selected repair

C realized as A: schema-marked typed envelope in `MemoryRecord.content`;
enforcement reads typed only; prose is a lossy projection; legacy / incomplete /
unknown-version records `DEFER`. `MemoryRecord` schema unchanged. Γ unchanged.

## Closure

```text
CE1 post-repair          DENY
CE2 post-repair          approval dimension preserved
repaired matrix          35/35 typed, 0 false allow, 0 false block
real paths T2/T5         7/7, no regression
property cases           ~390 across 5 properties
effective mutants        4/4 caught
tests                    438 passed / 0 failed (31 repair)
R1 verdict               FALSIFIED, unchanged
Gamma promotion          NONE
preconditions            experiment-scoped, gap registered
```

## Successor

`BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1` — separately preregistered;
must not overwrite R1.
