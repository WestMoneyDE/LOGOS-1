# Session Report — Persistent-State Causality Preflight R1

**Date:** 2026-08-20  
**Authority:** A0  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY` for any later scientific run  
**Classification:** `PARTIAL_SOURCE_RESOLUTION_FOUR_WAY_NOT_EXECUTION_READY`  
**Scientific execution:** `NOT_STARTED`

## Objective

Resolve whether the proposed four memory/state classes can participate in one scientifically fair causal comparison:

```text
TOKEN_CONTEXT
RECURRENT_LATENT
FAST_WEIGHT_STATE
EXTERNAL_RETRIEVAL
```

The preflight was required to reject an attractive but confounded four-way benchmark if source implementations, backbone equivalence or state intervention semantics did not support causal attribution.

## Primary-source resolution

### BDH / BDH-CQ

The official public BDH repository resolves at:

`pathwaycom/bdh@2b0d7a45b058d4309c84a10e0768d541fe18bdc2`

The public implementation is valuable architectural prior art, but its exposed `BDH.forward(idx, ...)` computes over the supplied sequence and does not expose a durable cross-query state object that can be independently serialized, reset, swapped and resumed.

Therefore:

```text
PUBLIC_BDH_BASELINE != PUBLIC_BDH_CQ_PERSISTENT_STATE_ADAPTER
```

The Pathway ARC companion repository resolves at:

`pathwaycom/arc-task-gen@20b2203064b09f60f7925a191d75c11d72277f35`

It documents BDH-CQ and provides ARC-style task-generation/evaluation material. It does not expose the BDH-CQ model implementation, weights or a manipulable recurrent-memory API.

Verdict:

`BDH_CQ_SOURCE_ADAPTER = UNRESOLVED`

This does not reject BDH-CQ. It blocks use of the public repositories as if they were an executable state-swap reproduction.

### MoNe

Primary paper:

`MoNe: Modular Neural Memory for Efficient Long Context Inference`, arXiv `2608.17616`.

The paper defines a layer-local fast-weight memory state `W_S^(l)`, supports reuse across multiple queries and incremental extension, and is conceptually well suited to state swap/reset/corruption.

However, this preflight did not resolve an official implementation/repository from the primary arXiv record.

Verdict:

`MONE_EXACT_SOURCE_ADAPTER = UNRESOLVED`

No unofficial reimplementation is promoted as MoNe evidence.

## Resolved operational representatives

### Recurrent latent/state family — Mamba

Pinned source:

`state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa`

The model exposes `allocate_inference_cache(...)` and accepts `inference_params` in forward execution. This provides an explicit engineering surface for clone/reset/swap instrumentation, subject to adapter tests.

This is a **recurrent-state representative**, not a BDH-CQ reproduction.

### Fast-weight/test-time-learning family — TTT

Pinned source:

`test-time-training/ttt-lm-pytorch@cd831db10c8c9a0f6340f02da5613316a8a92b67`

The implementation explicitly passes `cache_params`, stores per-layer learned `W*_states` and gradient/update state, and updates those states during sequence processing.

This gives a strong source-level basis for targeted reset/swap/corruption tests.

This is a **fast-weight representative**, not a MoNe reproduction.

### Controlled task substrate — RULER

Pinned source:

`NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a`

RULER supports configurable long-context tasks and is directly relevant to retention/interference/long-context access.

But RULER generates synthetic examples. Under the existing LOGOS evidence rules:

```text
RULER causal/adaptor test -> max EM1
```

It may be used to establish adapter correctness, state-swap sensitivity, reset controls and resource curves. It may not by itself promote a persistent-state mechanism to EM2.

## Key methodological finding

A direct raw four-way leaderboard is not currently a valid mechanism test.

The candidate implementations differ in:

- architecture;
- pretraining objective/data;
- parameterization;
- context window;
- state semantics;
- training requirements;
- query/readout path.

Matching parameter count or FLOPs alone does not remove those confounds.

Therefore the preflight changes the primary analysis from:

```text
Which arm has highest raw Accuracy?
```

to:

```text
Within each architecture family:
  carry/use state
  vs reset
  vs targeted swap
  vs matched corruption
```

and then compares **within-family causal effect sizes and resource curves** across families.

Raw cross-backbone accuracy is descriptive only.

This preserves the four conceptual classes while preventing:

```text
ArchitectureQuality -> falsely labeled as MemoryMechanismEffect
```

## State-evidence ladder retained

For every state `S`:

```text
D(S) = Decodability
O(S) = Operational utility
C(S) = Causal intervention effect
```

A state cannot be promoted because it is merely readable.

Minimum intervention family:

```text
history A -> M_A
history B -> M_B
same query q
swap M_A <-> M_B
```

with same-history, random-state, norm/statistics-preserving and reset controls where technically possible.

## Evidence plan

### Stage 1 — controlled adapter validation

Use source-pinned RULER tasks only to test:

- state carry/reset;
- exact state cloning;
- state swap;
- matched corruption;
- state recovery;
- retention/interference;
- compute/query and peak memory.

Evidence ceiling: `EM1`.

### Stage 2 — realistic confirmatory substrate

Before any EM2 promotion, the same intervention logic must be transferred to a public realistic/non-synthetic task or trajectory substrate with frozen IDs/splits and outcome-independent selection.

The existing LongMemEval-V2 track remains a possible candidate after its resource dependencies are separately resolved, but this session does not silently reuse or alter that parked work order.

## Scientific verdict

No memory class is promoted or rejected.

The result is a **design correction**:

```text
DIRECT_FOUR_WAY_MECHANISM_WINNER = UNLICENSED
MATCHED_WITHIN_FAMILY_CAUSAL_TESTING = REQUIRED
```

This is material because it prevents backbone quality from being misreported as evidence for a memory mechanism.

## Next work order

`NEXT-SESSION-PERSISTENT-STATE-MATCHED-FAMILY-ADAPTER-FREEZE-R2`

The next session will freeze exact model artifacts and adapters for:

- token-context carry/truncation;
- recurrent-state carry/reset/swap;
- fast-weight carry/reset/swap;
- external retrieval relevant/distractor/no-retrieval;

first on a controlled RULER subset at EM1, with an explicit later realistic confirmatory gate.

## Boundaries

Unchanged:

```text
PersistentState != Authority
MemoryTruth != MemoryAuthority
CausalState != PhenomenalConsciousness
ArchitecturePerformance != MechanismIdentity
```

`Γ-v0.3` remains `HOLD`.
