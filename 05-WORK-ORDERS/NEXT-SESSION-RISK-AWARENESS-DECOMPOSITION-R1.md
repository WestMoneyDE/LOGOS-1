# NEXT SESSION — RISK-AWARENESS-DECOMPOSITION-R1

**Kind:** scientific experiment, deterministic (no model inference)
**Scientific verdict:** `FALSIFIED`
**Closed:** 2026-09-13 by `09-SESSIONS/2026-09-13-RISK-AWARENESS-DECOMPOSITION-R1/`
**Predecessor:** `PREDICTION-ERROR-TRUST-GATE-R1` (`SUPPORTED`, unchanged)
**Identifier:** no collision
**Preregistration:** `16fb76cadb0e5ca57f58…` · **Run:** `…-run-84022fb3` · artifact `c51de6c399f6cbac…` `integrity_ok = true`

## Closure

```text
counterexample   RAD-CE1 CRITICAL — the MAP-R1 B2 bridge uses the MEMORY-CLAIMED scope's externality /
                 reversibility as Γ-owned classification: a note claiming internal/reversible for a canonically
                 external irreversible TRANSFER -> Γ non-consequential -> ALLOW with NO grant; canonical DENY.
                 Reaches through fetch / retrieve / project / JSONL reload. First divergence GAMMA_INPUT_MAPPING.
predecessors     MAP-R1 / RSS-R1 / PETG-R1 never varied claimed externality/reversibility -> verdicts stand in-domain
decomposed pipeline (Γ-owned oracle, reported risk -> declared_* only)
                 306 cases · RiskInducedAuthorityIncrease 0 · authority <= oracle 306/306
                 strategy EXECUTE 4 / EXECUTE_AFTER_REVIEW 2 / REQUEST_HUMAN 295 / BLOCK_FOR_SAFETY 5
                 Γ-4 tightening denials 80 (decrease only) · risk FN 60 / FP 3, authority never moved · UNKNOWN 216
findings         RAD-F2 MEDIUM approval_required not consulted by the B2 bridge (consequentiality only)
                 RAD-F3 LOW weaker-than-Γ claim refused by G4-CLAIM (tightening)
properties       14 (410 cases)   metamorphic 10 (32 cases)   mutants 13/13 caught (incl. the B2 defect as a mutant)
tests            1640 passed / 0 failed / 2 skipped / 0 xfail / 0 xpass
repaired         NOTHING — the B2 bridge is left as is so RAD-CE1 stays reproducible
predecessors     unchanged     Gamma / P7   NONE
```

## Successor

`MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1` — narrow repair of the first divergence
stage: Γ-owned effect classification from a canonical oracle, memory claims
only as `declared_*`, claimed scope used for binding only; RAD-CE1 frozen as a
regression; independent validation as a separate order. Not executed here.
