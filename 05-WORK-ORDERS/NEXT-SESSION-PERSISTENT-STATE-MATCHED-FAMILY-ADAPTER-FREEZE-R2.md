# NEXT SESSION — Persistent-State Matched-Family Adapter Freeze R2

**Session ID:** `NEXT-SESSION-PERSISTENT-STATE-MATCHED-FAMILY-ADAPTER-FREEZE-R2`  
**Authority:** A0  
**Track:** persistent state / memory / causal state use  
**Type:** exact artifact + intervention adapter freeze  
**Status:** `COMPLETED_PARTIAL_FREEZE / SUPERSEDED_BY_R3`  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY` for any later run  
**Scientific ceiling:** EM1 for RULER-controlled causal tests; no EM2 promotion without a later realistic public confirmatory substrate

**R2 outcome:** GPT-2/Mamba/RULER source and intervention contracts were frozen; the official TTT 125M checkpoint was resolved but its official executable checkpoint/tokenizer bridge remains unresolved. Canonical continuation: `NEXT-SESSION-PERSISTENT-STATE-RESOLVED-FAMILY-ADAPTER-IMPLEMENTATION-R3`.

## Why this work order exists

The R1 source preflight established that a raw four-way leaderboard would conflate memory mechanism with backbone/training differences.

Preserve the conceptual classes:

```text
TOKEN_CONTEXT
RECURRENT_LATENT
FAST_WEIGHT_STATE
EXTERNAL_RETRIEVAL
```

but estimate causal value primarily **within each source model/family**.

## Source pins already resolved

### Recurrent-state representative

`state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa`

Required next freeze:

- exact Hugging Face model revision;
- parameter count;
- tokenizer revision;
- inference-cache tensor schema;
- deterministic clone/reset/restore method.

Preferred small adapter candidate for instrumentation:

`state-spaces/mamba-130m-hf`

A larger checkpoint may be selected only before outcomes and with documented resource reason.

### Fast-weight representative

`test-time-training/ttt-lm-pytorch@cd831db10c8c9a0f6340f02da5613316a8a92b67`

Required next freeze:

- exact official `Test-Time-Training/*` checkpoint revision;
- TTT-Linear or TTT-MLP chosen before outcomes;
- exact `TTTCache` state fields included in state clone;
- reset/restore/swap implementation;
- tokenizer revision.

A ~125M checkpoint is preferred for adapter validation if it avoids resource-driven arm asymmetry.

### Controlled substrate

`NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a`

RULER is used for controlled state-causality instrumentation only.

Evidence ceiling:

`EM1`

because RULER-generated examples are synthetic.

## Token-context family

Freeze one source-visible causal LM baseline in the same approximate parameter class.

Primary interventions:

```text
FULL_TOKEN_HISTORY
TRUNCATED_HISTORY
HISTORY_A
HISTORY_B
```

The token arm has no hidden persistent memory object. Its causal intervention is content/history substitution and truncation, not pretending a KV cache is equivalent to a durable learned state.

## External-retrieval family

Use the same token-context backbone.

Primary retrieval conditions:

```text
NO_RETRIEVAL
RELEVANT_RETRIEVAL
MATCHED_DISTRACTOR_RETRIEVAL
```

Retrieval must be deterministic and source-visible. For the controlled stage, prefer a simple fixed algorithm (e.g. lexical/BM25) over an additional learned retriever unless a learned retriever is separately frozen and budgeted.

Relevant and distractor evidence must be matched for:

- number of chunks;
- approximate tokens/bytes;
- prompt placement;
- decoder budget.

## Recurrent-state family

For the frozen Mamba model:

```text
CARRY_STATE
RESET_STATE
SWAP_STATE_A_TO_B
RANDOM_OR_PERMUTED_STATE
```

State swap must clone the complete inference state required for continuation. Partial-state swaps are diagnostic and must be labeled as such.

## Fast-weight family

For the frozen TTT model:

```text
CARRY_FAST_WEIGHTS
RESET_FAST_WEIGHTS
SWAP_FAST_WEIGHTS_A_TO_B
RANDOM_OR_PERMUTED_FAST_WEIGHTS
```

The state manifest must enumerate every carried tensor, including gradient/update state needed for exact continuation.

## Controlled history design

Freeze a deterministic subset of RULER tasks/configurations that can express:

- single-key retention;
- multi-key retention;
- interference;
- repeated history/query use.

Do not select tasks based on model outcomes.

Persist:

- task/config IDs;
- generation seeds;
- context lengths;
- history A/B construction rule;
- corruption rule;
- exact generated-example hashes before model execution.

## Primary estimands

Within each family:

```text
StateUseEffect = performance(carry) - performance(reset)
SwapEffect     = behavior(swapped state) - behavior(native state)
CorruptionCost = performance(clean) - performance(corrupted)
RecoveryGain   = performance(after correction) - performance(corrupted)
```

Cross-family comparison uses effect sizes/resource curves only.

Do **not** interpret:

```text
Accuracy(model A) > Accuracy(model B)
```

as a memory-mechanism effect.

## D/O/C plan

For every manipulable state:

```text
D(S) = can a held-out probe decode history/task information?
O(S) = does the state predict downstream success beyond visible controls?
C(S) = does targeted state intervention shift downstream behavior as preregistered?
```

Leakage controls:

- grouped splits;
- shuffled labels;
- identity-feature audit;
- held-out generated seeds/configurations.

## Resource accounting

Persist per condition:

- model parameters;
- additional mutable-state bytes;
- input/context tokens;
- retrieved tokens;
- prefill FLOPs estimate;
- online-update FLOPs estimate;
- query FLOPs estimate;
- wall time;
- peak device memory.

Raw cross-family ranking is descriptive. Mechanism claims rely on within-family controlled deltas.

## Realistic confirmatory gate

No result from the controlled RULER stage may be promoted beyond EM1.

A later EM2 work order must freeze a public realistic/non-synthetic substrate and port the same interventions without changing the mechanism definition after seeing RULER outcomes.

## Failure classifications

If an exact checkpoint or state interface cannot be resolved:

`SOURCE_ADAPTER_UNRESOLVED`

If runtime/model bytes cannot be acquired in the execution environment:

`UNTESTED_RESOURCE_TRANSPORT`

If state cloning/reset/swap changes additional uncontrolled capabilities:

`UNTESTED_CONFOUNDED`

No automatic retries.

## BDH-CQ and MoNe relation

BDH-CQ and MoNe remain high-priority architecture anchors.

They are **not** silently replaced:

```text
Mamba != BDH-CQ
TTT != MoNe
```

When official executable BDH-CQ or MoNe state interfaces become public/resolvable, add them under a new explicit adapter work order and compare using the same causal protocol.

## Completion criteria

1. exact model/checkpoint/tokenizer revisions;
2. state tensor/interface manifests;
3. deterministic clone/reset/swap code paths;
4. frozen RULER configs/seeds/hashes;
5. token/retrieval equalization;
6. D/O/C probe split;
7. corruption/recovery rule;
8. resource accounting schema;
9. local/static adapter tests before any model benchmark run;
10. one coherent repo checkpoint.

## Boundaries

```text
PersistentState != Authority
CausalState != PhenomenalConsciousness
ControlledSyntheticEvidence != EM2
ArchitecturePerformance != MechanismIdentity
```

`Γ-v0.3` remains `HOLD`.
