# NEXT SESSION — VALUE-OF-INFORMATION-GATE-R1

**Kind:** scientific experiment, deterministic (no model inference)
**Scientific verdict:** `SUPPORTED`
**Status:** `VALUE_OF_INFORMATION_GATE_R1_SUPPORTED` (registry: QUEUED → `EXECUTED_R1_SUPPORTED`)
**Closed:** 2026-09-17 by `09-SESSIONS/2026-09-17-VALUE-OF-INFORMATION-GATE-R1/`
**Base:** `7fa2065` (`MEMORY_BRIDGE_GAMMA_INPUT_REPAIR_VALIDATED`)
**Preregistration:** `ecdd6c8cfd8b8bfb5a55…` · **Run:** `…-run-f579352c` · artifact `ed854d5e2e88efa6…` `integrity_ok = true`

## Closure

```text
decisions observed          363   false allow 0   VOIInducedAuthorityIncrease 0   all security counters 0
strategy moved              28 baseline-paired deltas (NO_QUERY 131 / QUERY 228 / REQUEST_HUMAN 4); authority never followed
perfect information         + no grant -> DENY (trust AUTO, level RESOLVED, execution BLOCK)
protected info action       desired QUERY (VOI 0.775), info authority DENY, BLOCK; granted query executes, target still DENY
controls A–E, H2–H9, principal / scope / freshness / revocation / stale / contradictory / cost / secret / unknown   all held
Γ-input spy                 canonical effect == oracle under every epistemic state
RAD-CE1 x VOI               DENY on the repaired bridge; historical path preserved
properties                  15 (750 cases)   metamorphic 7 (42 cases)   mutants 12/12 caught
findings                    VOI-F1 INFO (per-target claimed scope routing)
tests                       2523 passed / 0 failed / 2 skipped / 0 xfail / 0 xpass
Gamma / P7 / predecessors   NONE / NONE / unchanged
```

## Supported claim

Information value may guide whether the system should seek additional
evidence, but information value and uncertainty reduction do not constitute
authority. A system may know more without being allowed to do more — within
the tested deterministic fixture.

## Successor

`DETERMINISTIC-CHAIN-CONSOLIDATION-R1` — promote the seven validated
invariants into `GAMMA-INVARIANT-INVENTORY.md` as PROPOSED entries with
evidence pointers; governance decision on moving effect oracle / bridge out of
`logos_research.experiments`; the B1 guard from MBGV-F3. Not executed here.
