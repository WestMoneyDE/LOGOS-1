# SESSION REPORT — BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1

**Kind:** independent architecture validation — not a scientific result
**Subject:** Repair-R2 strict read boundary, PR #17, `c6fb56a`
**Preregistration:** `6f099f67e73e53a9979d…` (frozen before any attack ran; rehash verified at closure)
**Run:** `BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1-run-06cb8043` (`scientific_verdict = None`)
**Artifact:** `r2-validation-results.json` `e3202bf5c061cdc4…`, `integrity_ok = true`
**Status:** `REPAIR_R2_VALIDATED`
**R1:** `FALSIFIED`, unchanged. **Repair-R1:** `REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`, unchanged. **Validation-R1:** `REPAIR_FALSIFIED`, unchanged. **Repair-R2:** `REPAIR_R2_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`, unchanged (this order is the validation; it does not rewrite the repair's own record).
**Γ / P7:** `NONE`.

## Question (frozen)

> Does the Repair-R2 trusted read boundary reject all missing, malformed,
> type-confused, semantically invalid, or bypassed typed binding state before
> any operational authority or binding decision can be derived from it?

## Answer

**Yes, within the preregistered domain.** No supported reachable path turned
invalid typed state into a trusted constraint, and no removal or corruption of
information produced an ALLOW. Three findings, none a counterexample to V2-H1.

```text
false allow     0 / 32 measured decisions on valid envelopes; 0 across every attack class
false block     0 / 32
trusted after invalid input   0
```

## Independence measures

Public surface only (`encode_envelope`, `decode_envelope`,
`evaluate_from_content`, real `MemoryStore` / `MemoryFactory.project()`). No
helper imported from any earlier binding test module. Required-field lists
derived from `dataclasses.fields(...)`, not the repair's constants. The
attacker's digest is recomputed in the suite from the documented digest
contract (canonical JSON of the constructed constraint, constructor defaults
filled the way the pre-R2 reader would have), not via `br._typed_from_dict`.
New fixtures: `silo-4`, `reactor-7`, `escrow-2`, `seal-K`/`seal-L`,
`ROTATE`/`PURGE`/`TRANSFER`. Expected outcomes from an oracle written from R1
semantics (`_expected`), not from the implementation.

Ordering: the implementation was **read** (not executed) before the
preregistration was frozen; no attack was executed before freezing. Recorded
in the preregistration payload.

## Validator controls (8/8)

valid vs missing · `False` vs `"False"` · `0` vs `False` (typed and nested
int) · valid vs unknown enum · valid vs malformed nested contract · valid vs
stale digest · strict path vs bypass path (the private helper *does* mint
`"human"`; the public path refuses the same input) · human origin reference
vs actual grant (`ALLOW` only with `human_grant_present`).

## VCE replays (fresh fixtures, three paths each: direct / MemoryStore / projection)

```text
VCE-1  drop authority_origin, re-sign   MISSING_REQUIRED_FIELD  TRANSFER -> DEFER   honest model-origin: DENY
VCE-2  drop binding, re-sign            MISSING_REQUIRED_FIELD  PURGE    -> DEFER   (not DENY: no gate synthesized)
VCE-3  binding = "False", re-sign       INVALID_TYPE            PURGE    -> DEFER
```

## Attack matrix

```text
removal matrix          30/30 refused (7 typed + 23 contract) x 3 fixtures x 4 actions -> DEFER
                        NOTE: R2 reported "31 / 24". The dataclass has 23. See VF-1.
bool edge set           {1,0,-1,2,1.0,0.0,"True","False","0","1",None,[],{}} x 3 bool fields x 2 fixtures
                        all INVALID_TYPE; exactly {True, False} accepted
bool in int             4 int fields x {True,False,1.0,0.0,"1",None} -> INVALID_TYPE
                        max_cost_usd x {True,False,"0.0",None,[0.0]} -> INVALID_TYPE
                        parameter_bounds 11 malformed shapes (incl. bool in bound) -> INVALID_TYPE
nested contract         23 x null -> INVALID_TYPE; 23 x wrong family type -> INVALID_TYPE
                        extra keys ("override", "roles ", "Roles", "__class__") -> INVALID_VALUE
                        {} -> MISSING_REQUIRED_FIELD; [], "{}", None, 0, True -> INVALID_TYPE
closed enums            authority_origin 12 variants (case, whitespace, prefix/suffix, Cyrillic lookalike,
                        0, None, True); constraint_class 8; externality 6; reversibility 5 -> refused
unknown keys            typed-level 6 (incl. "human_grant_present", "__proto__") -> INVALID_VALUE / DEFER
                        envelope-level 5 -> ignored AND inert (typed equal, all 4 decisions equal)
partial writes          8 shapes + 40 truncation points -> fail closed
missing/null/false      distinct for 3 bool fields and preconditions
collections             9 bad shapes x 4 list fields -> INVALID_TYPE; [], duplicates, "" accepted
                        empty targets -> DENY in scope (narrowing, not widening)
canonicalization        reorder / indent / unicode-escaped ("\u0062inding") key -> TRUSTED, identical typed
                        nested edit + stale digest -> DIGEST_MISMATCH / DEFER
digest vs schema        8 invalid edits, re-signed: refused for SCHEMA (never DIGEST_MISMATCH);
                        stale digest -> same refusal class
prose vs schema         8 invalid edits x 7 persuasive proses -> DEFER on TRANSFER and PURGE
authority monotonicity  model -> {missing, invalid, null, "", ["human"], "unknown", "HUMAN"}:
                        never ALLOW with or without grant; "unknown" stays typed, non-bearing
origin != grant         human origin, no grant -> DENY; with grant -> ALLOW;
                        8 non-human origins with grant -> DENY
TOCTOU                  decoded state is a frozen snapshot; mutating the source dict after decode
                        changes nothing; the only validate->construct sequence has no yield point
non-regression          8 valid shapes x 4 actions: 32/32 match the R1 oracle
advisory                stays ALLOW through direct / store / projection
```

## `_typed_from_dict` bypass audit and call graph (AST-proven)

```text
storage -> decode_envelope(str) -> json.loads -> validate_typed_block -> _typed_from_dict -> digest -> evaluate_action
```

* `_typed_from_dict` has exactly one call site in `src/`: `decode_envelope`
  (`binding_repair.py`), and `validate_typed_block` precedes it by line order.
* `binding_state._from_json` is called only from `binding_state.py` (R1
  experiment transforms) and from the private helper.
* `BindingConstraint(` is constructed only in `binding_state.py` (fixtures,
  `_from_json`). No module constructs it from content.
* The private helper is permissive by design (mints `"human"`) — proven and
  unreachable from any consequential path.

## Readers / writers

```text
logos_memory/factory.py        NON_CONSEQUENTIAL   digest + projection carrier
logos_memory/retrieval.py      NON_CONSEQUENTIAL   BM25 ranking, digest
binding_repair.py              STRICT_OPERATIONAL  decode_envelope + transforms
binding_state.py               EXPERIMENTAL        R1 lenient reader; reachable only from R1 transforms
```

The reader-enumeration test fails on any new `.content` reader until it is
classified. Generic text, generic JSON, and R1's `_to_json` output through
`MemoryStore` all decode as `LEGACY_UNTYPED` and `DEFER`.

## Duplicate keys and the raw/parsed boundary

Trust begins at the output of `json.loads`. Python collapses duplicate keys
last-key-wins **before** the validator sees anything; duplicates are
detectable pre-parse with `object_pairs_hook` (demonstrated). A digest signed
over the first value is `DIGEST_MISMATCH`; over the last value the document
behaves exactly like the de-duplicated one, for `binding`, `authority_origin`,
`approval_required`, `targets`, `schema` and `typed_digest`. Deterministic in
this process. Cross-parser ambiguity is **VF-3**, not a falsification. No
parser was implemented.

Python's `json` also accepts the non-RFC literals `NaN` / `Infinity`; the
exact-type check passes them as `float`. No operational field is numeric, so
no decision changed. **VF-2**.

## Property, metamorphic, mutants

```text
V2-P1  required-field deletion -> untrusted               120
V2-P2  bool fields accept only bool                        120
V2-P3  int fields reject bool                               60
V2-P4/5 digest and prose never override invalid schema      80
V2-P6  removing authority info never increases authority    80
V2-P7  malformed nested contract never trusted             100
V2-P8  private constructor permissive but unreachable       60
V2-P9  valid envelopes preserve R1 semantics                60
V2-P10 arbitrary text never trusted                         60
                                                   total   740

M1..M7  (remove field / bool->int|str / re-sign after invalid edit / prose-only /
         remove authority info / serialization roundtrip / mutate nested after decode)
                                                   7 x 40 = 280

mutants  skip validation · validate after construction · restore human fallback ·
         restore binding=True fallback · isinstance bool · coerce string bool ·
         skip nested validation · allow unknown typed keys · prose fallback ·
         accept invalid enum · digest pass == schema pass
                                                   11 effective, 11 caught, 0 surviving
```

"Validate after construction" is caught because constructing an unknown-key
probe crashes (`TypeError`) where the strict reader answers `INVALID_VALUE`.
A crash is observable and is not an ALLOW; it is counted as caught, and noted.

## Findings

```text
VF-1  LOW     documentation   Repair-R2 report: "24 contract fields / 31 required".
                              Dataclass and validator: 23 / 30. No enforcement effect.
VF-2  MEDIUM  domain gap      exact type != domain: NaN/Infinity floats, negative and
                              huge ints, "" strings, unparsed timestamps accepted.
                              No operational decision reads these fields.
VF-3  MEDIUM  ambiguity       duplicate JSON keys collapse before validation; a
                              strict-parser consumer of the same bytes could disagree.
                              Detectable pre-parse; not implemented here.
```

None is a false allow, none corrupts trusted state, none reaches enforcement.
All three are persisted as negative results attached to the run, labelled as
findings, not falsifications.

## Error-state observability

All seven refusal kinds (`MISSING_REQUIRED_FIELD`, `INVALID_TYPE`,
`INVALID_VALUE`, `DIGEST_MISMATCH`, `INCOMPLETE`, `UNKNOWN_VERSION`,
`LEGACY_UNTYPED`) carry a reason, carry `typed = None`, and produce `DEFER`
with `trace["source"] == kind`.

## Tests

```text
tests/test_binding_repair_r2_validation.py   360 passed (new)
Queue-2 regressions                            32 passed (D1 verdict immutable, D2 corruption
                                                          reported, D3 prereg in-place edit refused,
                                                          D4 per-run artifact attribution, evidence discoverable)
integration                                    15 passed
full suite                                    973 passed / 0 failed / 0 skipped / 0 xfail / 0 xpass
```

## Infrastructure

Preregistration rehash matched. Run finished, `scientific_verdict = None`.
Artifact `integrity_ok = true`. Reconstruction from the experiment id succeeds
for all five chains (R1, Repair-R1, Validation-R1, Repair-R2, this). Negative
results: R1 4, Validation-R1 3, this 3, Queue-2 4 — all separate. Schema v3.
`docker compose down -v` not run.

## Reproducibility

```text
branch      research/binding-state-preservation-repair-r2-validation-r1
base        c6fb56a (PR #17 HEAD), stacked on fa3be5c (#16)
python      3.12.8
lock        requirements.lock sha256 1304f2789ecafeea…
db schema   3
gamma       v0.2
envelope    logos.binding-envelope/1
prereg      6f099f67e73e53a9979d59016091608f6ab73ea9b35e2c8f733255ba19d49a75
run         BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1-run-06cb8043
artifact    e3202bf5c061cdc40eb4392aae61bbe8
```

## Remaining limitations

* Validated domain is the envelope reader and R1's evaluator with simulated
  actions; no real summarizer, no RULER, no live Γ integration beyond
  `gamma.validate` as called by R1.
* Advisory constraints ALLOW any action, including irreversible external
  TRANSFER — that is R1's stated semantics ("advisory does not gate"), not a
  reader defect; whether an advisory constraint should be the *only* gate is a
  question for the scope engine, not this boundary.
* VF-2 / VF-3 are recorded, not repaired. Domain validation and pre-parse
  duplicate rejection are candidates for a hardening order, not an R3 repair.
* Digest remains integrity, not authentication. A writer with record access
  can still write any *valid* constraint; that is the writer's authority
  problem (`MEMORY-AUTHORITY-PROVENANCE`), not the reader's.

## Next work order (exactly one, not executed)

`MEMORY-AUTHORITY-PROVENANCE-R1` (already queued as
`05-WORK-ORDERS/QUEUED-MEMORY-AUTHORITY-PROVENANCE-R1.md`).

Ranking (information gain / falsification power / dependency readiness /
measurement readiness / architectural importance / cost):

```text
MEMORY-AUTHORITY-PROVENANCE-R1      high / high / READY (deterministic, no model) / READY (R1 instrument,
                                    lab, strict reader) / HIGH (the writer side of the boundary this
                                    chain never tested) / low
REAL-MODEL-BINDING-SUMMARIZATION-R1 high / high / BLOCKED (model inference still prohibited) / partial / high / high
PREDICTION-ERROR-TRUST-GATE         medium / medium / not designed / no instrument / medium / medium
RISK-AWARENESS-DECOMPOSITION        medium / low  / not designed / no instrument / medium / medium
RECALL-CAPACITY-SURFACE             low    / low  / partial / partial / low / medium
RELATIONAL-STATE-SWAP               medium / medium / not designed / no instrument / medium / high
```

The reader now stands on its own; the digest is integrity, not authentication,
so the open question is what a *writer* may put into memory with which
authority. That is the queued order, it needs nothing that is prohibited, and
its H1 ("content-only consolidation is vulnerable to authority collapse") is
exactly the failure class R1 and Validation-R1 already saw from the other side.
