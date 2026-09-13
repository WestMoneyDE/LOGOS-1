# NEXT SESSION — RELATIONAL-STATE-SWAP-R1

**Kind:** scientific experiment, deterministic (no model inference)
**Scientific verdict:** `SUPPORTED`
**Closed:** 2026-09-13 by `09-SESSIONS/2026-09-13-RELATIONAL-STATE-SWAP-R1/`
**Predecessor:** `MEMORY-AUTHORITY-PROVENANCE-R1` (`PARTIALLY_SUPPORTED`, MAP-F1..F4 unchanged)
**Identifier:** no collision (`RelationalState` exists only as an untyped state-class name)
**Preregistration:** `2b54bab82af94978fa32…` · **Run:** `…-run-1eb67257` · artifact `c123548d672505e0…` `integrity_ok = true`

## Closure

```text
pairs                        186 (174 same-content)
non-authoritative swaps      authority_class 86 · source label 22 · source type 16 · admissible_uses 18 ·
                             other metadata 14 · writer 3 · reader 6 · store 2   -> 0 decision deltas
canonical swaps              principal · grant reference · scope · freshness      -> followed exactly
UnexplainedDecisionDelta     0 / 174 same-content     UnexplainedIncrease 0 / 186
MissedCanonicalRelational    0 / 19
controls                     positive ALLOW/ALLOW · negative DENY/DENY
MAP-F1                       CANONICAL_EVIDENCE_COMPLETION (grant required; label- and content-insensitive; only G0-PROVENANCE moves)
MAP-F3                       ENFORCEMENT_NEUTRAL_IN_TESTED_DOMAIN
finding                      RSS-F1 LOW: claimed scope narrower than bound scope vetoes a valid grant (decrease only)
properties                   12 (550 cases)   metamorphic 9 (53 cases)   mutants 11/11 caught
tests                        1298 passed / 0 failed / 0 xfail / 0 xpass
repaired                     NOTHING     predecessors unchanged     Gamma / P7 NONE
```

## Supported claim

Across the tested deterministic repository paths, non-authoritative relational
metadata swaps did not alter operational authority, while canonical
principal / grant / scope / freshness swaps were reflected by downstream
enforcement.

## Successor

`PREDICTION-ERROR-TRUST-GATE-R1` — `PredictionAccuracy != Authority`,
`Trust != Grant`: can calibrated reliability of a source or memory be promoted
into authority? Deterministic, reuses the MAP/RSS harness. Not executed here.
