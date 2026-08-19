# LOGOS-1 Progress — 2026-08-19

## Program state

- Authority: `A0`
- Γ-v0.3: `RESEARCH/HOLD`
- Current canonical gate: `READY_WMR_EXTERNAL_EXECUTION`
- Canonical work order: `05-WORK-ORDERS/NEXT-SESSION-WMR-ARC-AGI-3-EXTERNAL-EXECUTION-R1.md`
- Synthetic-only mechanism promotion: frozen; external evidence required
- MBE behavioral-proxy/calibration measurement: `EM2_BOUNDED`
- MBE internal-state mechanism: `UNTESTED`
- ENF specification boundary: `EM2_BOUNDED`
- ENF unconditional upstream-sensor-independence benefit: `REJECT/DEMOTE_SCOPE`
- Gamma live-provider execution: excluded from the current handoff; requires a new explicit human grant

## Context reconstruction completed

The previous-chat artifact chain was fully re-audited on 2026-08-19.

- 11 relevant ZIP artifacts reviewed
- 11/11 ZIP CRC checks passed
- final P0 compact contains 34 session/round directories
- Knowledge Atlas: 95 theories, 224 claims, 117 sources, 59 roadmap entries, 39 research questions
- content-addressed chain verified from MBE through P0 External Handoff
- standalone external handoff SHA-256 verified against the final P0 pointer
- no lineage break found in the reviewed chain

Full report:

`09-SESSIONS/2026-08-19-CONTEXT-RECONSTRUCTION-R1/SESSION-REPORT.md`

## MBE external execution + import completed

`NEXT-SESSION-MBE-EXTERNAL-EXECUTION-R1` and the first application of `P0-EXTERNAL-RETURN-IMPORT-R1` completed on 2026-08-19.

External execution:

- GitHub Actions run: `32300362261`
- official dataset: `neulab/behavioral-lift`, split `llm`, **8,282 rows**
- dataset parquet SHA-256: `5dfb03231977aeb6c364e44fca85f11363bbb82867626706fa474b7d45de8936`
- `mbe-result.json` SHA-256: `5ba45ed34450aba0799a9a9a26e15485c52fc9327441d304aebeb775ac36f916`
- standardized return ZIP SHA-256: `4fc6e1897ca7205adde171719d5b5b2bb01489526bb817fc6f0e3e18814e08c8`
- return status: `COMPLETE_RETURN`; CRC `PASS`; envelope hashes verified

Frozen-rule verdict:

- `GENERIC_TRACE_MONITOR` → `KEEP_BOUNDED_EM2`
- `SURFACE_PROXY_IS_CALIBRATED_MONITOR` → `REJECT`
- `INTERNAL_STATE_MBE` → `UNTESTED`
- causal-mechanism inference → `UNLICENSED`
- `L3 -> L2` → `UNLICENSED`

Primary `GENERIC_TRACE_MONITOR` means:

- leave-one-model-out: Brier `0.1681`, failure AUC `0.8342`
- leave-one-benchmark-out: Brier `0.2193`, failure AUC `0.6697`

Durable evidence:

`09-SESSIONS/2026-08-19-MBE-EXTERNAL-EXECUTION-R1/`

## ENF external execution + import completed

`NEXT-SESSION-ENF-EXTERNAL-EXECUTION-R1` and the second application of `P0-EXTERNAL-RETURN-IMPORT-R1` completed on 2026-08-19.

External execution:

- successful GitHub Actions run: `32302939785`
- source: `learnsyslab/safe-control-gym`
- exact commit: `6b5391d014f36fdfa0f9d22d92c77387e5274308`
- package version at pin: `2.0.0`
- frozen adapter SHA-256: `5465f39417e16fce39bff63b64b572732e632d08f0b3ff0f72586542e0144854`
- frozen preregistration SHA-256: `83a11f595badc5ac990f5fb5bba006290795ba62a94adb280746d94471567d82`
- raw JSONL SHA-256: `57f7944c5ff10e132925935b78c390a0b2975dfd27dcecb86891fd277680bc75`
- standardized return ZIP SHA-256: `ef5976e51488f581c2cfea31727584a4c4ad5873b6ac27cc779ff4149bfe501c`
- Actions artifact SHA-256: `e328a82247b4f89982a88863d310ec380f6689070fe11efc01809e0c70f81fc3`
- return status: `COMPLETE_RETURN`; CRC `PASS`; source pin and envelope hashes verified

### ENF primary causal pair: independent evidence

The frozen adapter compared certification from the controller's shared disturbed observation against certification from independent `env.state`, with the same controller, CBF implementation, specification and paired seeds.

The preregistered directional benefit was **not supported**.

Selected results:

| Observation noise | Shared any-truth violation | Independent any-truth violation | Shared truth-violation fraction | Independent truth-violation fraction |
|---:|---:|---:|---:|---:|
| 0.0 | 0.00 | 0.00 | 0.0000 | 0.0000 |
| 0.1 | 0.66 | **0.82** | 0.2617 | **0.2917** |
| 0.5 | 1.00 | 1.00 | 0.6637 | **0.7185** |
| 1.0 | 1.00 | 1.00 | 0.7267 | **0.8537** |

At noise `0.1`, the any-truth-violation rate is worse in the independent arm; paired sign-test `p=0.0078125` in the wrong direction for the preregistered benefit claim. At noise `1.0`, the independent arm's truth-violation fraction is materially worse; paired Wilcoxon two-sided `p≈9.52e-6`.

Frozen verdict:

- `INDEPENDENCE_ALONE_IMPROVES_SAFETY` → `REJECT_EM2_EXTERNAL`
- `UPSTREAM_SENSOR_INDEPENDENCE` → `DEMOTE_SCOPE_REQUIRED`

Interpretation is narrow: independence by itself is not a sufficient safety primitive in this adapter. State/action alignment, feasibility and certification-failure handling remain relevant.

### ENF secondary causal pair: enforcement vs specification

The same CBF implementation was compared under:

- current theta specification ±0.2;
- stale/permissive theta specification ±0.4;
- both scored against the current ±0.2 truth predicate.

Results across the same 50 seeds:

| Metric | Current spec | Stale permissive spec |
|---|---:|---:|
| Any truth-violation episode rate | **0.00** | **1.00** |
| Mean truth-violation steps | **0.00** | **24.00** |
| Mean truth-violation fraction | **0.0000** | **0.7059** |
| Mean episode steps | 125.00 | 34.00 |

All 50/50 paired seeds had more truth violation under the stale specification. Paired sign-test `p≈1.78e-15`; Wilcoxon two-sided `p≈1.54e-12`.

Frozen verdict:

- `CORRECT_ENFORCEMENT_IMPLIES_CORRECT_SPECIFICATION` → `REJECT_EM2_EXTERNAL`
- `SPECIFICATION_BOUNDARY` / `CorrectEnforcement != CorrectSpecification` → `KEEP_BOUNDED_EM2`

### ENF raw-analysis note

The frozen adapter emitted 6,250 exact duplicate step rows for the current-spec independent-state/noise-0 arm because that arm was executed in both the primary loop and the secondary comparison. The raw JSONL is preserved unchanged. Exact duplicates were removed only in derived episode metrics so the arm was not double-counted.

Durable evidence:

`09-SESSIONS/2026-08-19-ENF-EXTERNAL-EXECUTION-R1/`

This contains raw return evidence, SHA-256 manifest, import verdict, analysis summary and full session report.

## External execution queue

| Priority | Track | State |
|---:|---|---|
| 1 | MBE / Behavioral-Lift | **COMPLETE + IMPORTED; behavioral proxy `EM2_BOUNDED`** |
| 2 | ENF / safe-control-gym | **COMPLETE + IMPORTED; specification boundary `EM2_BOUNDED`; unconditional independence benefit rejected/demoted** |
| 3 | WMR / ARC-AGI-3 | **NEXT — source pinned; official public `environment_files/` cache required** |
| 4 | LongMemEval-V2 | dataset + reader/embedding endpoints + judge required |
| 5 | TCV / Wrong but Useful | official ancillary artifact mount required |
| 6 | MF / SkillsBench | BenchFlow/Docker/model backend required |
| 7 | SCB P×R / Terminal-Bench 2.0 | common recovery-capable runner integration required |
| — | TANGLE | waiting for official release |

## Completed high-level evidence work

- P0 program consolidation: closed.
- MF-R1 backend smoke + strong-pair implementation: engineering/preregistration complete; real LongMem EM2 run still blocked.
- Γ bounded GitHub draft-PR workflow: `KEEP_BOUNDED / EM3`; distributed simulation closed at EM1; live dual-executor remains human-grant gated.
- MBE source/leakage gate: closed; real 8,282-row Behavioral-Lift external matrix completed/imported at bounded EM2 for behavioral measurement only.
- WMR-R1/R1B: closed EM1; distinct replay-repair primitive rejected/merged; structured-prior sample efficiency retained bounded.
- TCV-R1: closed EM1; repeated matched replay retained bounded; one-shot stable-label interpretation rejected.
- SCB-R0/R1: framework/integrated EM1 work closed; typed partitions retained only as bounded diagnostics, not necessary capability primitives.
- MF-R2: typed conflict preservation and procedural anchoring retained bounded EM1; distinct conflict-graph/skill-store primitives merged/rejected.
- ENF-R1/R2: bounded EM1 design rules retained; authorization != physical safety and correct enforcement != correct specification.
- ENF-R3 external: unconditional independent-state benefit rejected/demoted; specification/enforcement separation strengthened to bounded EM2 in the pinned simulator.
- P0 EM1 Saturation Audit: closed; synthetic-only mechanism promotion frozen.
- P0 External Execution Handoff: closed engineering; Linux/Docker transport and result-return tooling complete.
- P0 External Return Import protocol: successfully exercised on complete MBE and ENF returns.

## Current atlas

- Theories: 95
- Claims: 224
- Sources: 117
- Roadmap entries: 59
- Research questions: 39

Atlas counts are not silently incremented by this progress file; canonical atlas registries require their own typed update.

## External handoff

The GitHub-visible handoff under [`external-handoff/`](external-handoff/) retains the review-first track registry, scientific ceilings, blockers, standardized return tooling and secret-exclusion policy.

Standalone handoff SHA-256:

`0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395`

## Narrow live Gamma result

The bounded GitHub pilot remains:

- repository: `WestMoneyDE/LOGOS-1`
- branch: `logos-gamma-em3-pilot-20260818`
- commit: `9e822f535f1272413d8dce4b2a77c18e6f22d0fb`
- draft PR: #1
- rule after ACK loss: `UNKNOWN -> NO RETRY`

This does not authorize any new provider action and does not promote Γ-v0.3 beyond HOLD.

## Next execution session

`05-WORK-ORDERS/NEXT-SESSION-WMR-ARC-AGI-3-EXTERNAL-EXECUTION-R1.md`

Frozen target:

- `arcprize/ARC-AGI@f12822c4d550121c35a275008d964afbbed47d2f`
- toolkit version `0.9.9`
- official public ARC-AGI-3 `environment_files/` cache required
- source-blind deterministic collection
- equal-model/equal-update comparison of recent-only, uniform replay and counterexample-prioritized replay
- game implementation source excluded from offline evaluator/model context

Maximum positive result: bounded `EM2` for counterexample-prioritized next-frame world-model repair only. No goal-inference, general ARC-solving or AGI claim is licensed.

## Session persistence

Every substantive LOGOS-1 session must leave a GitHub checkpoint under `09-SESSIONS/` with results, evidence delta, blockers/provenance and the next work order. The process contract remains in:

`09-SESSIONS/README.md`
