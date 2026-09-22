# NEXT SESSION — BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1

**Kind:** independent architecture validation, not a scientific experiment
**Status:** `REPAIR_R2_VALIDATED`
**Closed:** 2026-09-11 by `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1/`
**Predecessor:** `BINDING-STATE-PRESERVATION-REPAIR-R2` (`REPAIR_R2_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`, unchanged)
**Preregistration:** `6f099f67e73e53a9979d…`
**Run:** `…-REPAIR-R2-VALIDATION-R1-run-06cb8043` · artifact `e3202bf5c061cdc4…` `integrity_ok = true`

## Closure

```text
VCE-1 / VCE-2 / VCE-3 replay (fresh fixtures, 3 paths)   blocked
removal matrix                                          30/30 (R2 said 31/24; dataclass has 23 — VF-1)
bool/int edge set, bool-in-int, nested contract,
closed enums, unknown keys, partial writes,
collections, canonicalization, digest-vs-schema,
prose-vs-schema, authority monotonicity, origin != grant  all fail closed
_typed_from_dict bypass                                 unreachable (AST-proven, one call site, validate first)
alternate readers                                       none consequential; R1 reader isolated
alternate writers                                       LEGACY_UNTYPED / DEFER
false allow / false block                               0 / 0 of 32
property cases                                          740 (V2-P1..P10)
metamorphic                                             7 relations, 280 cases
effective mutants                                       11 / 11 caught / 0 surviving
findings                                                VF-1 LOW doc miscount; VF-2 MEDIUM domain gap
                                                        (NaN/Infinity, negative ints; no decision reads them);
                                                        VF-3 MEDIUM duplicate-key cross-parser ambiguity
tests                                                   973 passed / 0 failed / 0 xfail / 0 xpass
repaired                                                NOTHING — PR #17 untouched
R1 / Repair-R1 / Validation-R1 / Repair-R2              unchanged
Gamma promotion                                         NONE
```

## Successor

`MEMORY-AUTHORITY-PROVENANCE-R1` (queued at
`05-WORK-ORDERS/QUEUED-MEMORY-AUTHORITY-PROVENANCE-R1.md`). The reader is now
independently trustworthy; the digest is integrity, not authentication; the
untested side of the boundary is what a writer may put into memory with which
authority. Needs nothing that is prohibited. `REAL-MODEL-BINDING-SUMMARIZATION-R1`
stays behind the inference prohibition.
