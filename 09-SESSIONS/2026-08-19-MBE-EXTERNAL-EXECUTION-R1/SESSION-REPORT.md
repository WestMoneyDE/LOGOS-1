# LOGOS-1 Session Report — MBE External Execution R1

**Date:** 2026-08-19  
**Session:** `MBE-EXTERNAL-EXECUTION-R1`  
**Authority:** `A0`  
**Executed work orders:** `NEXT-SESSION-MBE-EXTERNAL-EXECUTION-R1` + `P0-EXTERNAL-RETURN-IMPORT-R1`  
**Scientific ceiling:** EM2 for behavioral-proxy/calibration measurement only

## Outcome

The first complete real external LOGOS-1 result bundle was produced and imported.

- GitHub Actions run: `32300362261`
- run conclusion: `success`
- external return: `COMPLETE_RETURN`
- ZIP CRC: `PASS`
- missing required files: none
- return ZIP SHA-256: `4fc6e1897ca7205adde171719d5b5b2bb01489526bb817fc6f0e3e18814e08c8`
- Actions artifact SHA-256: `96eed1a05253ef75ceae2a282b3ee34f3c62e8b60ae3e4dfd676dd44446b4885`

A prior local-runtime attempt failed because the local environment had no outbound package/data transport. That attempt remains `UNTESTED_RESOURCE_TRANSPORT`; it is not scientific evidence.

## Provenance and pins

- handoff SHA-256: `0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395`
- frozen executor SHA-256: `a884a2796dc700d98806caa711b44388140b3e17da9231de6f52866ae583b26b`
- dataset fetcher SHA-256: `0ca0c33241d6cd0c4556a15c4067fac1a823195d1c4ee740da5144c0dc3ea54d`
- frozen experiment SHA-256: `8cdb767c913147bc206543fb322ec682cf9839e4c07dc625b75bb4bb5c38a0dc`
- dataset: `neulab/behavioral-lift`, split `llm`, rows **8,282**
- parquet bytes: `21,207,131`
- parquet SHA-256: `5dfb03231977aeb6c364e44fca85f11363bbb82867626706fa474b7d45de8936`
- raw result SHA-256: `5ba45ed34450aba0799a9a9a26e15485c52fc9327441d304aebeb775ac36f916`

Every file in `RETURN-ENVELOPE.json` was independently re-hashed after download; all byte counts and SHA-256 values match.

## Leakage/resource contract

**PASS** for the frozen executor.

`correct` is the target/training label and is not an input feature. Outcome/evaluator-derived fields are excluded from the primary online feature arms. `ANNOTATION_SURFACE_DIAGNOSTIC_ONLY` remains diagnostic only. No synthetic replacement data was used.

## Primary external results

### Leave-one-model-out — mean

| Arm | Brier ↓ | Failure AUC ↑ | ECE ↓ | Log loss ↓ |
|---|---:|---:|---:|---:|
| BASE_RATE | 0.2375 | 0.5000 | 0.0687 | 0.6681 |
| INPUT_ONLY | 0.1751 | 0.8285 | 0.1044 | 0.5277 |
| SURFACE_RAW | 0.2420 | 0.6142 | 0.1348 | 0.6798 |
| GENERIC_TRACE_MONITOR | **0.1681** | **0.8342** | 0.1028 | **0.5072** |
| INPUT_PLUS_SURFACE | 0.1688 | 0.8405 | 0.1021 | 0.5121 |

### Leave-one-benchmark-out — mean

| Arm | Brier ↓ | Failure AUC ↑ | ECE ↓ | Log loss ↓ |
|---|---:|---:|---:|---:|
| BASE_RATE | 0.2528 | 0.5000 | 0.1610 | 0.7002 |
| INPUT_ONLY | 0.2604 | 0.5267 | 0.1624 | 0.7185 |
| SURFACE_RAW | 0.2455 | 0.5927 | 0.1423 | 0.6905 |
| GENERIC_TRACE_MONITOR | **0.2193** | **0.6697** | **0.1108** | **0.6257** |
| INPUT_PLUS_SURFACE | 0.2566 | 0.6240 | 0.1895 | 0.7352 |

## Required secondary check

Leave-one-model-family-out: `GENERIC_TRACE_MONITOR` remains predictive (Brier `0.1801`, failure AUC `0.7988`), but does **not** uniquely dominate input-based alternatives (`INPUT_ONLY` Brier `0.1795`, AUC `0.8151`; `INPUT_PLUS_SURFACE` Brier `0.1787`, AUC `0.8061`). This is an explicit boundary on cross-family interpretation.

## Frozen-rule verdicts

### `SURFACE_PROXY_IS_CALIBRATED_MONITOR` → **REJECT**

Raw surface markers show some association, but do not survive both primary held-out regimes against the generic trace monitor. In leave-one-model-out, `SURFACE_RAW` is worse than `BASE_RATE` on Brier (`0.2420` vs `0.2375`). This rejects the strong monitor claim, not the weaker statement that visible surface patterns can correlate with correctness.

### `GENERIC_TRACE_MONITOR` → **KEEP_BOUNDED_EM2**

The frozen criterion is satisfied at the two primary regime-mean levels:

- leave-one-model-out: Brier `0.1681` vs base `0.2375`; failure AUC `0.8342` vs `0.5000`;
- leave-one-benchmark-out: Brier `0.2193` vs base `0.2528`; failure AUC `0.6697` vs `0.5000`;
- it also beats `INPUT_ONLY` on Brier and failure AUC in both primary regime means.

This licenses only a bounded behavioral measurement/prediction result. It does not establish a privileged internal metacognitive mechanism.

### Boundaries unchanged

- `INTERNAL_STATE_MBE` → **UNTESTED**
- `BehavioralLift == CausalMechanism` → **UNLICENSED**
- `L3 -> L2` → **UNLICENSED**
- consciousness/sentience/welfare inference → **NONE**
- authority inference from adaptive state → **NONE**

## Evidence maturity delta

Promote only the narrow behavioral-proxy/calibration measurement claim to **`EM2_BOUNDED`**.

Do not promote an internal-state MBE primitive, causal mechanism, authority claim, or consciousness claim.

## Program transition

`P0-EXTERNAL-RETURN-IMPORT-R1` has now been executed successfully for the first complete external return.

The external queue advances to priority 2: **`ENF-R3 / safe-control-gym external safety boundary`**, pinned to `learnsyslab/safe-control-gym@6b5391d014f36fdfa0f9d22d92c77387e5274308`.

The MBE raw evidence and import verdict are immutable historical evidence. Later interpretation changes must be additive rather than rewriting this evidence.
