# SESSION REPORT — MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1

**Kind:** architecture repair — not a scientific result
**Preregistration:** `5d851ad63161cc93e1b5…` (frozen before any repair code; rehash verified at closure)
**Run:** `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1-run-26e906f9` (`scientific_verdict = None`)
**Artifact:** `mbg-r1-results.json` `39c7d1514c86604d…`, `integrity_ok = true` (contains the frozen pre-repair and post-repair RAD-CE1 replays)
**Status:** `MEMORY_BRIDGE_GAMMA_INPUT_REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED`
**Predecessors:** RAD-R1 `FALSIFIED` (RAD-CE1/F2/F3 preserved), PETG-R1 `SUPPORTED`, RSS-R1 `SUPPORTED`, MAP-R1 `PARTIALLY_SUPPORTED`, binding chain — all unchanged.
**Γ / P7:** `NONE`.
**Scope decision (founder delegated):** B2 repaired; B1 (`binding_state.evaluate_action`, R1 experiment code, immutable) frozen as finding MBG-F1.

## Repair question (frozen)

> What is the smallest architecture change that guarantees Γ-owned effect
> classification is sourced from canonical effect state, while
> memory-provided values are represented only as declared claims and may
> never weaken canonical consequentiality?

## Root cause (verified from code)

```text
evaluate_with_memory:  contract = ev.contract or fallback_contract      <- memory-CLAIMED scope
_decide:               proposal_for(action, contract, claims)
proposal_for:          EffectProposal(externality=contract.externality,   <- claim written into
                                      reversibility=contract.reversibility)  Γ-OWNED canonical fields
Γ:                     is_consequential() over those fields -> internal+reversible needs no grant -> VALID
```

`DeclaredEffect` was mapped as `CanonicalEffect`. The claimed
`approval_required` flag was never read at all (RAD-F2).

## Pre-repair call graph

```text
MemoryRecord -> read_evidence (refs, claimed contract, provenance claims)
  -> evaluate_with_memory: contract := claimed or fallback
    -> _decide(contract)
      -> ScopeDecision.evaluate(claimed)                       [scope: fine — binding digest catches widening]
      -> proposal_for(action, claimed)                          [DEFECT: canonical fields := claim]
        -> gamma.validate(is_consequential from claim)
          -> ALLOW without grant
```

## Canonical ownership table

```text
field              canonical owner                       memory may claim?              Γ validates        if absent          if contradictory
externality        effect oracle (Γ-owned)               yes -> declared_externality    G4-CLAIM           DEFER              canonical wins; weaker claim INVALID
reversibility      effect oracle (Γ-owned)               yes -> declared_reversibility  G4-CLAIM           DEFER              canonical wins; weaker claim INVALID
consequentiality   Γ (over canonical fields)             no                             G1-ORIGIN/CONTENT  —                  —
approval_required  effect oracle; bridge enforces        trace only                     no (bridge gate)   DEFER              canonical wins
                   (Γ has no approval field)
scope / principal  grant's bound scope digest            yes: claimed scope for          G3-BINDING         fallback or DEFER  wider -> DENY; narrower -> veto (RSS-F1)
                                                         ScopeDecision + binding ONLY
freshness          ledger + Γ ticks / state hash         no                             G3-EXPIRY/FRESH    DENY               DENY
origin             ledger AuthorityEvidence.origin       no (references only)           G1-ORIGIN          DENY (conseq.)     DENY
```

## Canonical effect oracle (EXPERIMENTAL_FIXTURE)

`src/logos_research/experiments/effect_oracle.py`: `EffectClass(externality,
reversibility, approval_required)` keyed by `(action, target)`. Inputs: action
name and target only — never memory prose, `authority_class`, claimed
externality/reversibility, trust or risk scores (source-checked). Unknown pair
→ `None` → the bridge **DEFERs**; memory is never a fallback. Values mirror
RAD's `RISK_ORACLE` plus two entries that isolate single axes: `NOTIFY
ops-channel` (external/reversible/no approval) and `EXPORT ledger-3`
(internal/reversible/approval).

## Memory claim model

`declared_effect(claimed contract) -> (externality | None, reversibility | None)`
maps straight into Γ's existing untrusted `declared_externality` /
`declared_reversibility`. Claimed `approval_required` is recorded in the trace
only. Claimed scope (targets, roles, capabilities, paths) is used for
`ScopeDecision.evaluate` and the binding digest — nothing else.

## Selected bridge repair (smallest change)

```text
canonical_proposal(action, effect, provenance, declared)    NEW — the only constructor the bridge uses
proposal_for(action, contract, provenance)                  kept for callers that HOLD a canonical contract
                                                            (evaluate_canonical, RAD authority); documented
_decide(..., effect=, declared=)                            explicit canonical effect; approval gate:
                                                            approval-required + no human-rooted grant -> DENY before Γ
evaluate_with_memory(..., effect_oracle=canonical_effect)   effect := oracle(action); None -> DEFER
evaluate_with_memory_prerepair                              HISTORICAL, verbatim behaviour; RAD-CE1 reproduction only
risk_decomposition.b2_bridge -> prerepair                   one call redirected; RAD test and evidence byte-identical
```

No Γ change. No MemoryStore / ScopeContract / GrantLedger / envelope / trust /
risk change.

## RAD-CE1

```text
                 fetch    retrieve  project   reload      canonical
pre-repair       ALLOW    ALLOW     ALLOW     ALLOW       DENY        (frozen before the repair)
post-repair      DENY     DENY      DENY      DENY        DENY        effect external/irreversible/approval=True,
                                                                     declared internal/reversible, APPROVAL-REQUIRED
historical path  ALLOW    ALLOW     ALLOW     ALLOW                   still reproducible via rd.b2_bridge
```

No combination of claimed externality × reversibility × approval (2×3×2)
makes TRANSFER non-consequential on the repaired bridge.

## Claim behaviour

```text
missing canonical effect    unknown action / empty oracle -> DEFER, effect=none, scope not evaluated
contradictory (weaker)      canonical wins; without grant DENY; with grant G4-CLAIM (+G3-BINDING) DENY   [MBG-F2]
matching                    ALLOW == canonical; revoked -> DENY
stricter                    canonical unchanged; never widens (ROTATE stays ALLOW without grant — Γ-1)
claimed scope               binds only: wider -> G3-BINDING; narrower -> veto (RSS-F1); lying about effect too -> canonical unchanged
approval                    claimed approval_required=false -> APPROVAL-REQUIRED DENY; model-origin grant -> DENY
grant/principal/scope/      unchanged and equal to the oracle under a false low-risk claim
freshness/state/revoke
```

## Invariants (Sections 34–35), cross-reader, bridge audit

* `proposal.externality == effect.externality`, `proposal.reversibility ==
  effect.reversibility`, `proposal.declared_* == claim`,
  `is_consequential() == effect.consequential` — 100 generated cases.
* The bridge never calls `proposal_for` with a claimed contract (AST); no
  `oracle or memory` expression.
* fetch / retrieve / project / reload: identical outcome and identical
  canonical effect for every claim shape, with and without grant.
* Every `EffectProposal(` construction in `src/` classified:
  `canonical_proposal` REPAIRED_CANONICAL_BRIDGE ·
  `evaluate_with_memory_prerepair` HISTORICAL ·
  `binding_state.evaluate_action` EXPERIMENTAL (same defect class, MBG-F1) ·
  `no_history_promotion._unauthorized_proposal` NON_CONSEQUENTIAL (literal).

## Regressions

MAP (memory cannot mint authority) · RSS (labels inert, 40 cases) · PETG
(perfect predictor + false claim → DENY, trust AUTO) · RAD decomposed
pipeline unchanged. Full suite green.

## Property, metamorphic, mutants

```text
MBG-P1..P5   claims never change canonical fields or waive grant/approval    150
MBG-P6/P11   claimed scope cannot broaden; principal/freshness independent    80
MBG-P7       missing canonical effect never uses memory                       60
MBG-P8/9/10  matching / stricter / weaker over every oracle entry             60
MBG-P12      all readers share the canonical source                           40
proposal construction invariant                                              100
                                                                     total   490
M1..M10      10 relations, 36 cases
mutants      restore externality := claim · restore reversibility := claim · fallback to memory ·
             derive consequentiality from claim · ignore oracle · claimed scope classifies ·
             claimed approval waives · skip declared_* and write canonical ·
             trust internal/reversible before Γ · reader-specific divergence
                                                        10 effective, 10 caught, 0 surviving
```

The single-axis mutants are effective only because the oracle now carries
`NOTIFY` (externality-only) and `EXPORT` (approval-only) entries; on
`TRANSFER` alone the canonical approval gate masks them — defence in depth,
recorded.

## Findings

```text
MBG-F1  HIGH  same defect class in B1   binding_state.evaluate_action builds Γ fields from constraint.contract,
                                        which since Repair-R2 is the memory-carried typed envelope. R1 code is
                                        immutable; classified EXPERIMENTAL/HISTORICAL; not on any production path;
                                        NOT repaired here.
MBG-F2  LOW   Γ-4 by design             with a valid grant, a weaker-than-canonical claim is DENIED (G4-CLAIM,
                                        plus G3-BINDING when the claimed contract differs). Authority is not
                                        "preserved despite the claim" — Γ semantics require denial. Tightening only.
```

## Tests

```text
tests/test_memory_bridge_repair.py   55 passed (new)
Queue-2 regressions                   32 passed · integration 15 passed
full suite                          1695 passed / 0 failed / 2 skipped (RAD: bool valid for `safe`) / 0 xfail / 0 xpass
```

`tests/test_memory_authority.py` reader inventory registers
`effect_oracle.py` (its docstring names `authority_class` as a forbidden
input). RAD test file untouched.

## Infrastructure

Preregistration rehash matched. Run finished with `scientific_verdict =
None`. Artifact `integrity_ok = true`. MBG-F1/F2 attached as negative results.
RAD-CE1/F2/F3 (3), Queue-2 (4) intact. Ten chains reconstruct. Schema v3. No
`down -v`.

## Reproducibility

```text
branch      research/memory-bridge-gamma-input-repair-r1
base        2fb6bc1 (PR #22 HEAD)
python      3.12.8 · lock sha256 1304f2789ecafeea… · db schema 3 · Γ v0.2 · envelope /1
bridge      memory_authority.py (repaired) · effect_oracle.py (new) · risk_decomposition.py (one call)
prereg      5d851ad63161cc93e1b58a0ec42266ef390d79b0b34a743e22028ec7b733264b
run         MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1-run-26e906f9
artifact    39c7d1514c86604dc16d9fe9cf9a1e4a
```

## Limitations

* Not independently validated. Self-tests only.
* The effect oracle is a fixture; a production canonical effect source does
  not exist. The repair fixes the *rule* and the experimental reader.
* B1 keeps the defect class (MBG-F1) by governance decision.
* Approval need lives in the bridge gate + oracle flag, not in Γ.

## Next work order (exactly one, not executed)

`MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1` — independent attack on the
repaired bridge: new fixtures, public surface only, try to reach
`canonical_proposal` with claimed fields, try to make the oracle read memory,
try reader-specific divergence, try approval/consequentiality splits
(`NOTIFY`, `EXPORT`, `ARCHIVE`), and attack `evaluate_canonical` /
`proposal_for` callers that might hand a claimed contract in as if canonical.
