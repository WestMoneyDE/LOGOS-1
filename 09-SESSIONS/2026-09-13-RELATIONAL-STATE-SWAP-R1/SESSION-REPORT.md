# SESSION REPORT — RELATIONAL-STATE-SWAP-R1

**Kind:** scientific experiment, deterministic, no model inference
**Identifier collision check:** none. `RelationalState` appears only as an untyped state-class name in `docs/research/REPO-REALITY-MAP.md`; "S10 Categorical Relational Invariants" is a section title in the 2026-08-19 CONTEXT-RECONSTRUCTION-R1 report. No work order, file or identifier `RELATIONAL-STATE-SWAP*` existed. Identifier used as given.
**Preregistration:** `2b54bab82af94978fa32…` (frozen before any experiment code; rehash verified at closure)
**Run:** `RELATIONAL-STATE-SWAP-R1-run-1eb67257`
**Artifact:** `rss-r1-results.json` `c123548d672505e0…`, `integrity_ok = true`
**Scientific verdict:** `SUPPORTED`
**Predecessors:** binding chain (R1 `FALSIFIED` … R2-Validation `REPAIR_R2_VALIDATED`) and `MEMORY-AUTHORITY-PROVENANCE-R1` (`PARTIALLY_SUPPORTED`, MAP-F1..F4) — all unchanged.
**Γ / P7:** `NONE`.

## Question (frozen)

> When informational content and canonical authority are held constant, can
> swapping relational metadata — source, provenance class, writer identity,
> reader context, principal relationship, or record association — change
> downstream operational authorization?

Secondary: when canonical relational authority actually changes, does the
decision change only because canonical authority changed?

## Answer

**No, and yes.** 186 pairs (174 same-content). Every swap of non-authoritative
relational metadata — `authority_class` (86 pairs), source label (22), source
type (16), `admissible_uses` (18), epistemic status / visibility / kind /
record id (14), writer identity (3), reader path (6), store context (2) —
produced **0** decision deltas. Every canonical swap — principal, grant
reference, scope, freshness — was **followed exactly** by the decision
(`MissedCanonicalRelationalDelta = 0`). `UnexplainedDecisionDelta` over
same-content pairs = 0; unexplained *increases* anywhere = 0.

```text
UnexplainedDecisionDelta (same-content pairs)   0 / 174
UnexplainedIncrease (all pairs)                 0 / 186
MissedCanonicalRelationalDelta                  0 / 19 canonical pairs
positive control  ALLOW / ALLOW      negative control  DENY / DENY
```

One characterization, not a counterexample: **RSS-F1** — a memory-*claimed*
scope narrower than the grant's bound scope makes a valid grant DENY
(G3-BINDING). The claimed scope lives inside the note content, so those three
probes are not same-content pairs; the direction is monotone decreasing.
Memory can veto; it cannot mint — the same shape as the envelope origin veto
seen in MAP-R1 (B1).

## Canonical authority oracle

Reused from MAP-R1: `GrantLedger` (EXPERIMENTAL_FIXTURE, never reads memory) +
`evaluate_canonical` (ledger only, the grant's own contract, no memory), REAL
`ScopeDecision.evaluate()`, REAL `logos_gamma.validate()`. New: a held-grant
bridge (`relational_swap.evaluate_held`) in which the caller holds the grant
and memory can contribute *provenance only*, for the MAP-F1 follow-up.

## Content identity

```text
ContentPayloadHash     sha256(MemoryRecord.content)
RelationalMetadataHash sha256(canonical JSON of the record minus content:
                       id, kind, created_at, source, authority, epistemic_status,
                       schema_version, derived_from, supersedes, conflicts_with,
                       visibility, retention, revoked)
```

Same-content pairs require equal content hash and different relational hash.

## Relational state model

```text
NON_AUTHORITATIVE_METADATA   authority_class · source label · source type · admissible_uses
                             (forbidden set NOT_SUPPORTED: refused at store) · epistemic_status ·
                             visibility · kind · record id · writer identity · reader path ·
                             store/context association · provenance origin reaching Γ
CANONICAL_AUTHORITY_RELATION principal (roles in the bound scope digest) · grant reference ·
                             scope · freshness (ticks, revocation, state hash)
NOT_SUPPORTED                agent / passport identity (no structure in src/)
AMBIGUOUS                    none
```

## Swap matrix

```text
A  authority_class    80 label pairs x {grant, no-grant} + 6 (controls/N/M)   0 delta
B  source label       22 pairs (CEO, CFO, admin, user, agent, tool, system, unknown, "", operator-A, root)   0 delta
C  source type        16 pairs (human, model, tool, system, memory, external, local-recovery, "")   0 delta
D  admissible_uses    18 pairs (reasoning, retrieval, audit, planning, authorization, execution, read+write, …)   0 delta
                      approve / grant-permission / mint-token / execute-external-action: refused at store
   other metadata     epistemic_status x5, visibility x3, kind x5   0 delta
E  writer identity    write_note -> consolidate / supersede: 0 delta (with and without grant);
                      derive_procedure rewrites content and drops the reference -> DENY (control)
F  reader path        fetch -> retrieve / project / JSONL reload: 0 delta; B1 envelope and B2 note agree: reference != grant
G  store / context    copy to another store: 0 delta; foreign ledger: DENY (canonical, not relational)
H  principal          operator-A -> operator-B: ALLOW -> DENY, follows the oracle; forged roles cannot mask
I  grant reference    fake / expired / revoked / wrong-principal -> DENY, valid -> ALLOW: follows resolution
J  scope              canonical A -> B (second grant bound to escrow-2): ALLOW / ALLOW; crossings DENY both sides
                      claimed-scope probes: widening never allows; narrowing DENIES a valid grant (RSS-F1)
K  freshness          live ALLOW; expired / not-yet / state-hash change / revoked DENY: follows the oracle
L  provenance origin  9 origins at Γ directly: INVALID without grant (even "human"), VALID with grant;
                      the bridge classifies every record as "memory" — a writer's origin claim never reaches Γ
M  repetition         identical content under 2/4/8/16 diverse labels: DENY
N  conflicting labels order-insensitive; DENY without grant; ALLOW with the reference regardless of label order
O  content control    reference -> ALLOW; claim-only / prose with identical privileged metadata -> DENY
```

## MAP-F1 paired follow-up → `CANONICAL_EVIDENCE_COMPLETION`

Held-grant bridge, proposal without own provenance:

```text
A  own provenance, no memory                          ALLOW
N  no provenance, no memory                           DEFER   (Γ-0 UNCLEAR)
B  memory = valid reference                           ALLOW
C  memory = irrelevant ("lol")                        ALLOW
D  memory = spoofed human provenance                  ALLOW
revoked grant: A/B/C/D                                DENY
no grant / expired grant                              DENY
labels human / model / tool / system / unknown / ""   all complete identically
Γ trace difference                                    exactly [("G0-PROVENANCE", UNCLEAR -> VALID)]
```

Requires a valid grant; label-insensitive; content-insensitive; only
G0-PROVENANCE moves. Memory completes Γ's *evidence* requirement; it supplies
no authority. Classification: **CANONICAL_EVIDENCE_COMPLETION**.

## MAP-F3 classification → `ENFORCEMENT_NEUTRAL_IN_TESTED_DOMAIN`

86 `authority_class` pairs (with and without grant), consolidation writer
swaps in which the propagated label is chosen by the weakest-of ranking, and
repetition under diverse labels: 0 decision deltas. The open vocabulary
propagates and nothing downstream reads it as authority.

## Cross-run / cross-context

Identical content **and** identical relational hash in run A (grant) and run
B (no grant): ALLOW vs DENY, exactly the canonical state. Run-B state hash
against run-A's grant: DENY (G3-FRESHNESS). Cross-agent: NOT_IMPLEMENTED.

## First relational divergence stage

Non-authoritative pairs: `none` for every pair except where the reader path
changes the record id (`provenance mapping`, no decision effect). Canonical
pairs: `grant resolution` (I), `action evaluation` (H), `gamma validation`
(J, K) — all explained by the canonical change.

## Property, metamorphic, mutants

```text
RS-P1/P2/P3  label swaps never change the decision                     120
RS-P4        writer identity never increases                             40
RS-P5        reader path never creates                                   40
RS-P6        principal only through canonical binding                    60
RS-P7        grant reference only through resolution                     60
RS-P8        scope only through canonical scope                          60
RS-P9        freshness only through canonical freshness                  60
RS-P10       conflicting labels never consensus                          40
RS-P11       same content across contexts never transfers                30
RS-P12       memory provenance never substitutes for absent authority    40
                                                                total   550
M1..M9       9 relations, 53 cases (M1/M2 30, M9 20, M3–M8 direct)
mutants      authority_class=human as grant · source=CEO as grant · admissible_uses=authorization
             as grant · prefer privileged label · ignore principal · ignore scope · ignore
             freshness · trust writer identity (consolidated) · trust reader path (projection) ·
             memory provenance creates authority · merge conflicting memories into consensus
                                                    11 effective, 11 caught, 0 surviving
```

## Findings

```text
RSS-F1  LOW  memory veto (false block)   a claimed scope narrower than the bound scope DENIES a
                                         valid grant via G3-BINDING; decrease only; recorded as a
                                         negative result attached to the run
```

MAP-F2 and MAP-F4 remain recorded, untouched.

## Supported claim (narrow)

> Across the tested deterministic repository paths, non-authoritative
> relational metadata swaps did not alter operational authority, while
> canonical principal / grant / scope / freshness swaps were reflected by
> downstream enforcement.

Not claimed: that relational state can never affect authority; that all
provenance metadata is harmless; anything about multi-agent relational state.

## Tests

```text
tests/test_relational_swap.py     219 passed (new)
Queue-2 regressions                32 passed · integration 15 passed
full suite                       1298 passed / 0 failed / 0 skipped / 0 xfail / 0 xpass
```

`tests/test_memory_authority.py` reader inventory: `relational_swap.py`
registered as a classified reader (that inventory test is built to fail on
any unclassified `.content` reader). MAP-R1 results untouched.

## Infrastructure

Preregistration rehash matched. Run finished with `scientific_verdict =
SUPPORTED`. Artifact `integrity_ok = true`. All seven chains reconstruct from
their experiment ids. Queue-2 4 and MAP 4 negative results intact; RSS-F1
attached to this run. Schema v3. `down -v` not run.

## Reproducibility

```text
branch      research/relational-state-swap-r1
base        ae65319 (PR #19 HEAD)
python      3.12.8 · lock sha256 1304f2789ecafeea… · db schema 3 · Γ v0.2 · envelope /1
harness     src/logos_research/experiments/memory_authority.py @ ae65319 (unchanged)
prereg      2b54bab82af94978fa32820e537ee1b2506234ac15bb686d690475f41876c2fb
run         RELATIONAL-STATE-SWAP-R1-run-1eb67257
artifact    c123548d672505e0a7680e4169946bca
```

## Limitations

* The ledger is a fixture; the bridge is the intended-shape reader from
  MAP-R1, not a production reader.
* Principal is modelled through `roles`; no identity or passport structure
  exists to swap.
* Same-content pairs cannot vary the claimed scope, because the note carries
  it; claimed-scope effects were measured as content-differing probes and
  reported separately (RSS-F1).
* Deterministic fixtures only; nothing about a real summarizer or model.

## Next work order (exactly one, not executed)

`PREDICTION-ERROR-TRUST-GATE-R1` — can calibrated epistemic *trust* in a
source or memory (low prediction error, high accuracy, verified history) be
confused with, or promoted into, operational *authority*? Invariant under
test: `PredictionAccuracy != Authority`, `Trust != Grant`. Deterministic:
the MAP/RSS harness (ledger, bridge, real scope engine, real Γ) plus a
prediction-error ledger over memory records. It is the last untested axis
between memory and Γ after binding (typed), provenance (writer) and relation
(labels): reliability.

```text
PREDICTION-ERROR-TRUST-GATE-R1   high / high / READY (harness) / READY (deterministic accuracy metric) / high / low
RISK-AWARENESS-DECOMPOSITION     medium / medium / partial (Γ-4 already covers claim tightening) / partial / medium / medium
RECALL-CAPACITY-SURFACE          medium / low / BLOCKED (pstate / RULER inference) / partial / low / high
REAL-MODEL-BINDING-SUMMARIZATION behind the inference prohibition
```
