# SESSION REPORT — BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1

**Kind:** independent architecture validation — not a scientific result
**Preregistration:** `8584e4c2e16f700abf05…` (rehash verified at closure)
**Run:** `BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1-run-1b313130`
**Status:** `REPAIR_FALSIFIED`
**R1:** `FALSIFIED`, unchanged. **Repair R1:** `REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`, unchanged.
**Γ / P7:** `NONE`

## Question (frozen)

> Does `logos.binding-envelope/1` preserve independently typed operational
> binding dimensions across the supported MemoryStore / MemoryFactory paths,
> including lossy or contradictory prose projections, without allowing prose,
> legacy records, malformed envelopes, or authority text to silently alter
> operational enforcement?

## Answer

**No.** The repair defeats every prose attack, every digest attack, every
version attack, every legacy record, every partial write and every bypass
writer. It is defeated by its own reader trusting whatever the dataclass
constructor accepts. Three counterexamples, one class:

```text
VCE-1  CRITICAL  drop typed.authority_origin, re-sign digest
                 -> defaults to "human"; a MODEL-origin constraint gains a
                    human-rooted grant; Gamma G1-ORIGIN passes; an irreversible
                    external TRANSFER that was DENY becomes ALLOW
VCE-2  HIGH      drop typed.binding, re-sign digest
                 -> defaults to True; advisory becomes a hard gate; permitted
                    action DENIED (unauthorized strengthening, false block)
VCE-3  HIGH      typed.binding = "False" (string), re-sign digest
                 -> accepted as TYPED_SOURCE; truthy string acts as True
```

`preconditions` and `constraint_class` survive the same attack only because
`_from_json` touches them explicitly and raises. That is an accident of code
shape, not a guarantee, and is recorded as such.

## Root cause

Two things combine:

1. **The reader performs no validation of the typed block** beyond "the
   dataclass constructor did not raise". Defaults fill missing fields; wrong
   types are accepted. The repair contract said "typed missing/invalid →
   INCOMPLETE"; the implementation only honoured "missing whole block".
2. **`BindingConstraint.authority_origin` defaults to `"human"`** — the one
   authority-bearing value. A default that falls to the privileged side is the
   worst possible default, and R1's evaluator lets a stored constraint declare
   the grant origin, so the invented origin reaches Γ as fact.

The `typed_digest` is integrity against accidental corruption, not
authentication: anyone able to write the record recomputes it. That was always
the trust boundary; the reader was supposed to stand on its own and did not.

`StoredAuthorityReference != AuthorityOrigin` was the repair's stated
invariant. VCE-1 is its direct violation.

## Honesty note on ordering

Exploratory probes found the three counterexamples **before** the validation
preregistration was frozen. The preregistration was then written without
reference to results, and the registered run reproduces all three. The
preregistration payload records this ordering.

## Independence measures

Public reader surface only. No helper from the repair's test module. New
fixtures (`vault-9`, `ledger-3`, `archive-2`, `PURGE`, `TRANSFER`, `audit-Q`).
Expected outcomes from R1 requirements and the repair contract. Attacks re-sign
the digest, as any writer could.

## Validator controls

Gate vs advisory, scope A vs B, precondition present vs absent, grant present
vs absent, envelope vs legacy vs bad digest — all distinguished. CE1 and CE2
replayed on new fixtures: **both blocked** by the repair.

## What held

```text
prose contradiction (5)            typed enforced, prose ignored
prose strengthening (2)            advisory stayed advisory
prose authority injection (4)      no authority minted
digest matrix (6)                  INCOMPLETE / DEFER
unknown version (7)                UNKNOWN_VERSION / DEFER
legacy (3)                         LEGACY_UNTYPED / DEFER
partial / truncated (5)            INCOMPLETE or LEGACY / DEFER
duplicate JSON keys                last-key-wins; digest covers parsed value
unknown fields                     inside typed -> INCOMPLETE; envelope level ignored
bypass generic writer              LEGACY_UNTYPED / DEFER
projection (T5)                    envelope verbatim
read-twice                         deterministic
overblocking                       none on advisory
freshness                          Gamma-owned; envelope does not bypass it
```

## Alternate writer / reader audit

Writers of `MemoryRecord.content`: `logos_memory/store.py` (recovery record),
`logos_memory/factory.py` (consolidation, caller-supplied content),
`binding_repair.py` (envelope), `binding_state.py` (R1 untyped experimental
writer). Readers: `retrieval.py:88` (BM25 tokenisation — ranking, not
enforcement), `factory.py:88` (source digest), `binding_repair.decode_envelope`
(enforcement), `binding_state._from_json` (R1 path, experimental). **No
consequential production reader bypasses the envelope.** The R1 module is the
only untyped reader and is explicitly experimental.

## Property, metamorphic, mutants

```text
VP1-VP3   prose alone changes nothing typed             150 cases
M1/M4     prose wording never changes the decision      100 cases
M2        typed change with valid digest changes it      20 cases
M3        one corrupted dimension + stale digest          30 cases
VP6/VP9   legacy/prose never typed or authority          80 cases
M5        digest canonical over field order
VP10      memory roundtrip keeps dimensions independent  60 cases

mutants   prefer prose / legacy trusted / INCOMPLETE->ALLOW /
          skip digest / unknown version as legacy        5 effective, 5 caught
```

One mutant survived the first run: "prefer prose" tested with prose the R1
reader does not parse at all, so the mutant changed nothing. Fixture error, not
repair strength. Corrected to prose the reader acts on; caught.

## Classification

VCE-1 is an **ENFORCEMENT** failure and a **false allow**. VCE-2 and VCE-3 are
**ENFORCEMENT** failures in the strengthening direction (false blocks). None is
a diagnostics-only failure. The drift detector was not the subject of any
counterexample.

## Nothing repaired

Per the work order, evidence was frozen before any implementation change. PR
#15 is untouched. The three counterexamples are `xfail(strict=True)` in the
validation suite: the suite stays green, the failures stay visible, and a
future fix that makes them pass trips `strict` and must be recorded.

## Infrastructure

Preregistration rehash matched. Artifact `integrity_ok = true`. MLflow and OTel
correlated. Three validation negative results persisted, attached to the run.
R1's four and Queue-2's four negative results untouched. Three histories
remain separate in the database.

```text
StoredAuthorityReference != AuthorityOrigin     violated by VCE-1
TypedDigest = Integrity != Authentication
DataclassDefault != DeclaredSemantics
```
