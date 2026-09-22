# NEXT SESSION — BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1

**Kind:** independent architecture validation, not a scientific experiment
**Status:** `REPAIR_FALSIFIED`
**Closed:** 2026-09-11 by `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1/`
**Predecessor:** `BINDING-STATE-PRESERVATION-REPAIR-R1` (`REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`, unchanged)
**Preregistration:** `8584e4c2e16f700abf05…`

## Closure

```text
CE1 / CE2 replay on new fixtures      blocked by the repair
prose / digest / version / legacy /
partial / bypass-writer attacks       all fail closed
counterexamples                       3, one class: reader trusts dataclass
                                      defaults and unvalidated types
  VCE-1 CRITICAL   authority_origin dropped -> "human" -> FALSE ALLOW
  VCE-2 HIGH       binding dropped -> True -> advisory becomes gate
  VCE-3 HIGH       binding="False" (string) accepted -> strengthening
property cases                        ~440
metamorphic relations                 6
effective mutants                     5/5 caught (1 fixture error corrected)
tests                                 490 passed / 3 xfailed (the VCEs)
repaired                              NOTHING — PR #15 untouched
R1 verdict                            FALSIFIED, unchanged
Gamma promotion                       NONE
```

## Successor

`BINDING-STATE-PRESERVATION-REPAIR-R2`: strict typed-block validation in the
reader (required fields, exact types, no defaults on read) and an
`authority_origin` with **no default** — or a default that is not
authority-bearing. Must be re-validated separately. Must not overwrite R1,
Repair-R1 or this validation.
