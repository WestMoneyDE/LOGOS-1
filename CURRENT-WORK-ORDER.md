# CURRENT WORK ORDER

**Status:** READY_PERSISTENT_STATE_MATCHED_FAMILY_FREEZE  
**Task:** `05-WORK-ORDERS/NEXT-SESSION-PERSISTENT-STATE-MATCHED-FAMILY-ADAPTER-FREEZE-R2.md`

The Persistent-State Causality R1 source preflight is complete.

Resolved facts:

- public `pathwaycom/bdh@2b0d7a45b058d4309c84a10e0768d541fe18bdc2` is an official BDH baseline, but its exposed public API is not the BDH-CQ persistent cross-query state interface required for the planned state-swap test;
- `pathwaycom/arc-task-gen@20b2203064b09f60f7925a191d75c11d72277f35` exposes ARC task-generation/evaluation material, not a public BDH-CQ model/state adapter;
- MoNe arXiv `2608.17616` specifies reusable layer-wise fast-weight state but no official code repository was resolved from the primary record in this preflight;
- `state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa` exposes inference-cache state suitable for recurrent-state adapter work;
- `test-time-training/ttt-lm-pytorch@cd831db10c8c9a0f6340f02da5613316a8a92b67` exposes explicit test-time learned state through `cache_params`;
- `NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a` is a usable controlled long-context substrate, but it generates synthetic examples and therefore cannot by itself support EM2 promotion under LOGOS rules.

Primary design correction:

```text
RawCrossBackboneAccuracy != MemoryMechanismEffect
```

The next session freezes matched **within-family** causal interventions first:

```text
TOKEN_CONTEXT:
  full history vs truncation/substitution

RECURRENT_LATENT:
  carry vs reset vs state swap

FAST_WEIGHT_STATE:
  carry vs reset vs fast-weight swap

EXTERNAL_RETRIEVAL:
  relevant vs matched distractor vs no retrieval
```

The preserved D/O/C ladder remains:

```text
D(S) = Decodability
O(S) = Operational utility
C(S) = Causal intervention effect
```

Cross-family results may be synthesized through normalized within-family effect sizes and resource curves, not a raw four-model leaderboard.

RULER-controlled results have maximum evidence level `EM1`. A later public realistic/non-synthetic confirmatory substrate is required before EM2 promotion.

BDH-CQ and MoNe remain architecture anchors and are not claimed to be reproduced by Mamba or TTT.

Parked external dependencies remain parked without retry:

```text
MF_R1 = UNTESTED_RESOURCE_TRANSPORT
TCV_R2 = UNTESTED_RESOURCE_TRANSPORT
MF_R3_SKILLSBENCH = UNTESTED_RESOURCE_TRANSPORT
SCB_R2_PR = UNTESTED_RESOURCE_TRANSPORT
TANGLE = WAIT_OFFICIAL_RELEASE
```

`Γ-v0.3` remains `HOLD`.
