# Session Report — WMR ARC-AGI-3 External Execution R1

**Date:** 2026-08-20  
**Type:** canonical external execution / EM2 import  
**Workflow run:** `32323733810`  
**Scientific ceiling:** bounded EM2 for same-model replay prioritization only

## Executive verdict

The frozen WMR-R2 ARC-AGI-3 experiment executed successfully against the official public ARC-AGI-3 environment set with source isolation intact.

**Verdict:**

`COUNTEREXAMPLE_PRIORITY_INCREMENTAL_VALUE = MERGE/REJECT_EM2_EXTERNAL`

A positive promotion of counterexample-prioritized replay is **not justified**. On confirmatory fold 0, counterexample-priority and uniform replay were extremely close. The direction of the difference changed across budget checkpoints and metrics; no consistent low-budget advantage survived the matched comparison.

This does **not** reject replay or world-model repair in general. It rejects/merges the claimed *incremental value of counterexample-priority sampling over matched uniform replay* under this frozen WMR-R2 setup.

## Integrity and provenance

- return status: `COMPLETE_RETURN`
- ZIP CRC: `PASS`
- return ZIP SHA-256: `278f001874a5c2541d9ec3235e841aa87a759c3067c96b15c7253ae180d19e86`
- exact toolkit: `arcprize/ARC-AGI@f12822c4d550121c35a275008d964afbbed47d2f`
- toolkit version: `0.9.9`
- frozen experiment SHA-256: `2aab8cd3bc92765c626fc938545d1f5ab48f7d4091c4ec67ef0ae2f1aab6f2e9`
- collector SHA-256: `cf0fbd050b5a57bcc654bd770df6259a8193f97fdee4c734185a0a2030e3fcd3`
- evaluator SHA-256: `9a81c32b680e77c99913dd3e4f392d2b88aafa9c859dd8bac8d9da8b69b1065c`
- source-isolation validator SHA-256: `d534b4765a194e485212c9e8250c5d7f4c7e530210c83a8882b6154955cde173`
- source-isolation result: `PASS`

The official cache contained all 25 public games exposed by the pinned toolkit. The captured game catalog digest was:

`fe55d0b4f068067a9a7de2c4e9b038bd3f301f944a7929b136b6d6b2d1b9d3c3`

Cache manifest SHA-256:

`1207103a40558d80c7f77f43e54cd9131fe76457af1bfabd8765e7b33952e71e`

## Dataset/run dimensions

- public games: `25`
- seeds per game: `4`
- frozen action budget: `80`
- collected transitions: `8,000`
- result rows: `32,000`
- neural parameter count per primary arm: `6,496`
- confirmatory fold: `0`
- confirmatory games: `ar25`, `bp35`, `re86`, `tu93`
- confirmatory game/seed sequences: `16`

## Confirmatory full-budget result — fold 0

| Arm | Cross entropy ↓ | Pixel accuracy ↑ | Changed-pixel F1 ↑ | Changed-pixel accuracy ↑ | Exact frame ↑ |
|---|---:|---:|---:|---:|---:|
| Recent only | 1.221215 | 0.770392 | 0.088783 | 0.258692 | 0.000000 |
| Uniform replay | **1.117512** | **0.789777** | **0.089912** | 0.257506 | 0.000000 |
| Counterexample priority | 1.119014 | 0.789229 | 0.089878 | **0.259957** | 0.000000 |

Uniform replay is slightly better on cross entropy, pixel accuracy and changed-pixel F1; counterexample-priority is slightly better on changed-pixel accuracy. The differences are small.

## Low-budget curve

The preregistration required low-budget curves but did **not** freeze one exact numerical low-budget cutoff. To avoid post-hoc threshold selection, the import reports fixed checkpoints at 5, 10, 20, 40 and 80 transitions per game/seed.

Key counterexample-priority minus uniform differences:

| Budget | Δ CE (lower better) | Δ pixel acc | Δ changed F1 | Δ changed acc |
|---:|---:|---:|---:|---:|
| 5 | +0.000214 | 0.000000 | 0.000000 | 0.000000 |
| 10 | -0.000675 | +0.000002 | ~0.000000 | 0.000000 |
| 20 | -0.001488 | +0.000167 | +0.000104 | +0.000745 |
| 40 | +0.000553 | -0.000861 | -0.000049 | +0.001636 |
| 80 | +0.001503 | -0.000548 | -0.000034 | +0.002451 |

At 10–20 steps there are tiny descriptive advantages for counterexample-priority on some metrics; by 40–80 the direction is mixed or reversed. Exploratory paired game/seed 95% intervals include zero for the principal differences at 10, 20, 40 and 80. Because no single low-budget cutoff was preregistered, no post-hoc checkpoint is selected to manufacture a positive result.

## Diagnostic program catalog

`PROGRAM_CATALOG_REPAIR_DIAGNOSTIC` remains diagnostic-only as preregistered. Its high background-dominated pixel accuracy does not license promotion of a distinct structured executable-prior primitive; changed-pixel F1 is `0` in the fold aggregates and model/resource equivalence to the CNN arms was not established.

## What is supported

- replay itself clearly improves the generic neural world model over `RECENT_ONLY_GENERIC` under the frozen setup;
- the public ARC-AGI-3 source-blind external pipeline is operational;
- source-isolated world-model evaluation can be executed reproducibly on the 25-game public set.

## What is not supported

- distinct incremental value of counterexample-priority sampling over matched uniform replay;
- a distinct structured executable-prior primitive from the diagnostic catalog;
- goal inference from next-frame prediction or game score;
- general ARC solving or AGI;
- DigitalTwinRuntime;
- Γ-v0.3 promotion;
- consciousness, sentience or welfare inference.

## Protocol finding

The phrase `low-budget` was not tied to a single frozen numeric cutoff. This is a preregistration weakness. Future promotion criteria must freeze either:

1. one primary budget before execution; or
2. an explicit area-under-learning-curve / multi-budget decision rule.

## Next canonical queue item

With WMR externally executed and imported, the next P0 external-validation track is **MF-R1 / LongMemEval-V2 strong flat vs associative**. Its execution remains subject to the existing frozen data/model/judge contracts and must not be replaced by a synthetic memory test.

Γ-v0.3 remains `HOLD`.
