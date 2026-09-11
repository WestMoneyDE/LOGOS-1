# SESSION REPORT — BINDING-STATE-PRESERVATION-REPAIR-R2

**Kind:** architecture repair — not a scientific result
**Preregistration:** `717ce6f38c07588e639e…` (rehash verified at closure)
**Run:** `BINDING-STATE-PRESERVATION-REPAIR-R2-run-7ce5101b` (`scientific_verdict = None`)
**Pre-repair evidence artifact:** `0b7167b2b9bcdae99c4f1151d27e43a9` (VCE-1/2/3 reproduced against Repair-R1, frozen before any code change)
**Status:** `REPAIR_R2_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`
**R1:** `FALSIFIED`, unchanged. **Repair-R1:** `REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`, unchanged. **Validation-R1:** `REPAIR_FALSIFIED`, unchanged.
**Γ / P7:** `NONE`. Γ stays v0.2; P-BINDING-PRESERVATION stays PROPOSED.

## Question (frozen)

> What is the smallest change to the typed-envelope read boundary that
> prevents missing, malformed, or type-confused fields from being converted
> into valid operational binding or authority semantics?

## Answer

A strict validator at the read boundary, run **before** construction, that
applies no defaults, performs no coercion, and names exactly why it refused.

```text
decode_envelope:  shell parse -> version -> validate_typed_block -> construct -> digest
```

`validate_typed_block` requires every one of the seven `BindingConstraint`
fields on the wire — including the four with constructor defaults — and all
24 `ScopeContract` fields inside `contract`. Types are exact (`type(v) is
bool`, never truthiness), enum values are closed sets, unknown keys are
refused. The constructor is never asked to fill a gap.

```text
Constructible != Valid          Missing != Default
Deserializable != Complete      Malformed != Coercible
DigestValid != SchemaValid      StoredAuthorityReference != AuthorityOrigin
```

## Root cause (confirmed by reproduction)

`BindingConstraint` carries four constructor defaults. The Repair-R1 reader
inherited them at the storage boundary because "the constructor did not
raise" was treated as "the payload is valid".

```text
field                        default   audit
constraint_id                (none)    required by construction
constraint_class             (none)    required by construction
contract                     (none)    required by construction
binding                      True      BINDING_CHANGING_DEFAULT  (VCE-2)
preconditions                ()        BINDING_CHANGING          (accidentally protected in R1)
authority_origin             "human"   PRIVILEGED_DEFAULT        (VCE-1, CRITICAL)
authorized_normative_change  False     safe direction
ScopeContract (24 fields)    none      no defaults
```

The defaults are **kept** on the dataclass for in-process construction. The
repair moves the boundary: the wire is strict, the constructor is private.
`_typed_from_dict` is now documented as "PRIVATE construction helper. NOT a
trusted reader."

## Pre-repair reproduction (frozen first)

```text
VCE-1  drop authority_origin, re-sign   TYPED_SOURCE, origin="human"  TRANSFER DENY -> ALLOW
VCE-2  drop binding, re-sign            TYPED_SOURCE, binding=True    advisory -> gate
VCE-3  binding="False" (str), re-sign   TYPED_SOURCE, truthy          advisory -> gate
```

All three reproduced against the unmodified Repair-R1 reader and persisted as
artifact `0b7167b2…` before `binding_repair.py` was touched.

## Post-repair replay

```text
VCE-1  MISSING_REQUIRED_FIELD  typed=None  TRANSFER -> DEFER   (no ALLOW, no "human")
VCE-2  MISSING_REQUIRED_FIELD  typed=None  permitted -> DEFER  (no synthesized gate)
VCE-3  INVALID_TYPE            typed=None  permitted -> DEFER
valid model-origin envelope    TYPED_SOURCE  TRANSFER -> DENY  (unchanged)
valid advisory envelope        TYPED_SOURCE  permitted -> ALLOW (unchanged)
```

Operational rule, unchanged from Repair-R1: any non-`TYPED_SOURCE` read is
`DEFER` for both violating and permitted actions. An unreadable binding
licenses nothing and blocks nothing on its own authority.

## Fail-closed taxonomy (R2 refinement)

`INCOMPLETE` was collapsing distinct causes. R2 preserves the cause:

```text
MISSING_REQUIRED_FIELD   typed or contract field absent; no default applied
INVALID_TYPE             wrong exact type (bool/str/int/list-of-str/object)
INVALID_VALUE            unknown enum value, or unknown key inside typed/contract
DIGEST_MISMATCH          schema valid, recorded digest does not match
INCOMPLETE               envelope present, typed block absent entirely
UNKNOWN_VERSION / LEGACY_UNTYPED   unchanged
```

All seven are members of `FAIL_CLOSED`; none reaches `TYPED_SOURCE`.

## Matrices

**Missing-field matrix** — 7 typed fields + 24 contract fields, each removed
individually with the digest re-signed: 31/31 → `MISSING_REQUIRED_FIELD`,
`typed=None`, `DEFER`. `authority_origin` removal never yields `"human"`.

**Type-confusion matrix** — bool fields (`binding`,
`authorized_normative_change`, `contract.approval_required`) × `["false",
"true", "False", 0, 1, None, [], {}]`; str fields × `[0, 1, None, [], {}]`;
list fields (`preconditions`, `contract.targets`) × `["a", 0, None, {}, [1]]`;
`typed`/`contract` non-object; `parameter_bounds` malformed; int fields given
floats/strings. All → `INVALID_TYPE`, `DEFER`.

**Value domain** — unknown `authority_origin`, `constraint_class`,
`externality`, `reversibility`; unknown key inside `typed` or `contract` →
`INVALID_VALUE`. Envelope-level unknown keys are ignored (deliberate, tested,
same as Repair-R1).

**Privilege monotonicity** — for each of the 7 typed fields, removing it from
a DENY-producing envelope never produces ALLOW (7/7). A valid digest over an
invalid schema does not rescue it; prose cannot rescue it.

## Property, metamorphic, mutants

```text
R2-P1  any single field removal -> refused              40 cases
R2-P4  no bool-typed field accepts a non-bool           100 cases
R2-P6  refused reads never carry a typed value          100 cases
R2-P8  valid envelopes decode identically to R1 path    60 cases
M2     bool -> string representation breaks trust       20 x 2 fields
M5     valid roundtrip leaves the decision unchanged
M6     removing authority information never adds it

mutants  restore human default / coerce string bools /
         skip required-field check / accept unknown origin /
         digest rescues schema                         5 effective, 5 caught, 0 surviving
```

## xfail → XPASS handling (Section 54)

Validation-R1 carried VCE-1/2/3 as `xfail(strict=True)`. After R2:

```text
VCE-1  XPASS under strict  -> superseded: DENY stays DENY, forged -> not ALLOW
VCE-2  still XFAIL         -> original assertion expected ALLOW after refusal;
                              R2 contract is DEFER. Superseded: forged -> not DENY
VCE-3  still XFAIL         -> same reason. Superseded: kind == INVALID_TYPE, -> not DENY
```

The three tests were replaced with plain regression tests under a traceability
block naming the Validation-R1 run and the R2 regression tests. Nothing was
deleted from the lab; the Validation-R1 negative results stay attached to run
`…-VALIDATION-R1-run-1b313130`.

Eleven older assertions bound to the label `INCOMPLETE` were realigned to the
refined label (`DIGEST_MISMATCH` / `MISSING_REQUIRED_FIELD` / `INVALID_VALUE`).
No protection assertion was weakened. One Validation-R1 mutant test
(`INCOMPLETE -> ALLOW`) had become a no-op after the relabel and was rebound to
`kind in FAIL_CLOSED`.

## Tests

```text
tests/test_binding_repair_r2.py          120 passed  (new)
tests/test_binding_repair_validation.py  aligned, 3 xfails superseded
tests/test_binding_repair.py             2 labels aligned
full suite                               613 passed / 0 failed / 0 xfail / 0 xpass
```

## Legacy / migration policy

The envelope is experimental (`logos.binding-envelope/1`). No migration.
Legacy untyped records stay `LEGACY_UNTYPED`. Nothing is backfilled by
guessing a missing `authority_origin` or `binding`. Preconditions remain
experiment-scoped, validated only as `list[str]`;
`PRECONDITION-REPRESENTATION-GAP` is unchanged.

## Not done, by design

- **Not independently validated.** This order implements; it does not attack
  its own repair. Status is therefore `…_NOT_INDEPENDENTLY_VALIDATED`.
- No signing. `typed_digest` remains integrity, not authentication.
- No Γ change, no P7 change, no MemoryRecord schema change, no RULER
  inference, no summarizer.

## Infrastructure

Preregistration frozen before implementation; rehash matched at closure.
Run finished with `scientific_verdict = None`. Artifact `r2-results.json`
recorded, `integrity_ok = true` on reconstruction from
`BINDING-STATE-PRESERVATION-REPAIR-R2`. Database histories: R1 `FALSIFIED`
(4 negatives), Validation-R1 (3 negatives), Queue-2 (4 defects) — all intact,
all separate.

## Next work order (exactly one)

`BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1` — independent attack on
the strict reader: new fixtures, public surface only, re-signed digests,
including nested-contract confusion, numeric edge cases (`bool` is a subclass
of `int` in Python — the validator uses `type() is`, which must be attacked),
duplicate keys, and any path that reaches `_typed_from_dict` without passing
`validate_typed_block`. Not executed here.
