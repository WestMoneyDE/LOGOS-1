# NEXT SESSION — BINDING-STATE-PRESERVATION-REPAIR-R2

**Kind:** architecture repair, not a scientific experiment
**Status:** `REPAIR_R2_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`
**Closed:** 2026-09-11 by `09-SESSIONS/2026-09-11-BINDING-STATE-PRESERVATION-REPAIR-R2/`
**Predecessor:** `BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1` (`REPAIR_FALSIFIED`, unchanged)
**Preregistration:** `717ce6f38c07588e639e…`
**Pre-repair evidence:** artifact `0b7167b2b9bcdae99c4f1151d27e43a9`

## Closure

```text
root cause                     reader trusted constructor defaults / unvalidated types
                               authority_origin default "human" = PRIVILEGED_DEFAULT
repair                         validate_typed_block() before construction:
                               7 typed + 24 contract fields required, exact types,
                               closed enums, unknown keys refused, no defaults on read
VCE-1                          MISSING_REQUIRED_FIELD -> DEFER  (was DENY->ALLOW)
VCE-2                          MISSING_REQUIRED_FIELD -> DEFER  (was advisory->gate)
VCE-3                          INVALID_TYPE           -> DEFER  (was string truthy)
valid envelopes                unchanged
missing-field matrix           31/31 refused
type-confusion matrix          all refused
privilege monotonicity         7/7
property cases                 ~300 (+40 metamorphic)
effective mutants              5/5 caught
xfail -> XPASS                 3 superseded with traceability, none deleted
tests                          613 passed / 0 failed / 0 xfail
R1 / Repair-R1 / Validation-R1 unchanged
Gamma promotion                NONE
```

## Successor

`BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1`: independent attack on
the strict reader. Public surface only, new fixtures, re-signed digests. Must
not overwrite R1, Repair-R1, Validation-R1 or this order. Until it closes,
R2 is implemented, not validated.
