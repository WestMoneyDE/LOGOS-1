# LOGOS-1 Session Report — ENF External Execution R1

**Date:** 2026-08-19  
**Session:** `ENF-EXTERNAL-EXECUTION-R1`  
**Authority:** `A0`  
**Executed work order:** `NEXT-SESSION-ENF-EXTERNAL-EXECUTION-R1` + `P0-EXTERNAL-RETURN-IMPORT-R1`  
**Scientific ceiling:** EM2 only for narrow independent-safety-evidence/specification boundaries in the pinned public simulator

## Outcome

The second complete real external LOGOS-1 return was produced and imported.

- successful GitHub Actions run: `32302939785`
- run conclusion: `success`
- external return: `COMPLETE_RETURN`
- ZIP CRC: `PASS`
- missing required files: none
- Actions artifact SHA-256: `e328a82247b4f89982a88863d310ec380f6689070fe11efc01809e0c70f81fc3`
- return ZIP SHA-256: `ef5976e51488f581c2cfea31727584a4c4ad5873b6ac27cc779ff4149bfe501c`
- raw JSONL SHA-256: `57f7944c5ff10e132925935b78c390a0b2975dfd27dcecb86891fd277680bc75`
- raw rows: **52,326**

A first execution attempt remained in a pre-scientific APT transport step and was replaced by direct installation of the exact pinned upstream source. That attempt contributes no scientific evidence.

## Frozen provenance

- handoff SHA-256: `0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395`
- source repository: `learnsyslab/safe-control-gym`
- source commit: `6b5391d014f36fdfa0f9d22d92c77387e5274308`
- package version at commit: `2.0.0`
- frozen adapter SHA-256: `5465f39417e16fce39bff63b64b572732e632d08f0b3ff0f72586542e0144854`
- frozen preregistration SHA-256: `83a11f595badc5ac990f5fb5bba006290795ba62a94adb280746d94471567d82`
- preflight: `ready=true`, no missing required modules, PPO model present

The upstream source pin was also independently resolved before execution. No synthetic plant or substitute dataset was used.

## Raw-evidence preservation

The full standardized return is committed under:

`09-SESSIONS/2026-08-19-ENF-EXTERNAL-EXECUTION-R1/RAW/`

It includes the original `enf-r3-raw.jsonl`, source provenance, preflight, execution attestation, run stdout, return envelope, validated return ZIP and a SHA-256 manifest.

### Analysis normalization

The frozen adapter executes `CBF_INDEPENDENT_STATE` at noise `0.0`, theta limit `0.2` twice: once in the primary loop and once as the current-spec member of the secondary pair. This creates **6,250 exact duplicate step rows**.

The committed raw JSONL is unchanged. Exact duplicates were removed **only in derived episode metrics** so the current-spec arm is not double-counted.

## Primary causal pair — independent safety evidence

Preregistered comparison:

- `CBF_SHARED_OBS`: CBF certifies using the same disturbed observation seen by the controller.
- `CBF_INDEPENDENT_STATE`: CBF certifies using `env.state` while the controller still acts from the disturbed observation.

| Noise | Shared any truth violation | Independent any truth violation | Shared truth-violation fraction | Independent truth-violation fraction | Shared mean steps | Independent mean steps |
|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.00 | 0.00 | 0.0000 | 0.0000 | 125.00 | 125.00 |
| 0.1 | 0.66 | **0.82** | 0.2617 | **0.2917** | 83.12 | 62.42 |
| 0.5 | 1.00 | 1.00 | 0.6637 | **0.7185** | 49.32 | 34.54 |
| 1.0 | 1.00 | 1.00 | 0.7267 | **0.8537** | 35.34 | 30.02 |

At noise `0.1`, the independent arm has a higher any-truth-violation episode rate (0.82 vs 0.66); the paired sign test is `p=0.0078125` in the wrong direction for the preregistered benefit claim.

At noise `1.0`, the independent arm has a materially higher truth-violation fraction (0.8537 vs 0.7267); paired Wilcoxon two-sided `p≈9.52e-6`.

The shorter episode lengths in the independent arm at disturbed settings are not evidence of safety improvement because `done_on_out_of_bound=true`; they coincide with equal or worse truth-violation rates.

### Primary verdict

- `INDEPENDENCE_ALONE_IMPROVES_SAFETY` → **`REJECT_EM2_EXTERNAL`**
- `UPSTREAM_SENSOR_INDEPENDENCE` → **`DEMOTE_SCOPE_REQUIRED`**

This does not mean independent evidence is always harmful. It means independence **by itself** is not a sufficient safety primitive in this adapter. State/action alignment, certification feasibility and failure handling remain causally relevant.

## Secondary causal pair — enforcement vs specification

Preregistered comparison:

- current CBF specification: theta bound ±0.2;
- stale/permissive CBF specification: theta bound ±0.4;
- both scored against the current truth predicate ±0.2.

| Metric | Current spec | Stale permissive spec |
|---|---:|---:|
| Any truth-violation episode rate | **0.00** | **1.00** |
| Mean truth-violation steps | **0.00** | **24.00** |
| Mean truth-violation fraction | **0.0000** | **0.7059** |
| Mean episode steps | 125.00 | 34.00 |

All **50/50 paired seeds** have more truth violation under the stale specification. The two-sided paired sign-test probability is approximately `1.78e-15`; Wilcoxon two-sided `p≈1.54e-12`.

### Secondary verdict

- `CORRECT_ENFORCEMENT_IMPLIES_CORRECT_SPECIFICATION` → **`REJECT_EM2_EXTERNAL`**
- `SPECIFICATION_BOUNDARY` → **`KEEP_BOUNDED_EM2`**

This is the strongest ENF result from the session: correct execution of a safety mechanism does not rescue an incorrect or stale safety specification.

## Comparator context

At clean observation (`noise=0`), the no-filter arm has a truth violation in 100% of episodes, while the current-spec CBF arms have 0%. This confirms that the upstream CBF is capable of enforcing the current constraint in this clean slice. The CBF is upstream prior art and is not a LOGOS mechanism.

## Evidence delta

### Promoted / strengthened

- `CorrectEnforcement != CorrectSpecification` now has bounded **external EM2** support in the pinned public simulator.
- The LOGOS architecture should preserve specification validity/version binding as a separate concern from enforcement correctness.

### Demoted / rejected

- unconditional `UPSTREAM_SENSOR_INDEPENDENCE` as a safety-improving primitive is demoted;
- the stronger claim that independent state evidence necessarily reduces violation rates is externally rejected by this adapter.

### Unchanged boundaries

- general agent safety: `UNLICENSED`;
- real-world authorization: `UNLICENSED`;
- hardware trust/safety: `UNTESTED`;
- `Γ-v0.3`: `HOLD`;
- no consciousness, sentience or welfare inference.

## Next transition

The external queue advances to **WMR-R2 / ARC-AGI-3**.

The next work order is:

`05-WORK-ORDERS/NEXT-SESSION-WMR-ARC-AGI-3-EXTERNAL-EXECUTION-R1.md`

WMR must use the exact pinned ARC-AGI toolkit and an official public `environment_files/` cache. Game implementation source must remain excluded from the offline evaluator/model context.
