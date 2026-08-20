# Session Report — Persistent-State Matched-Family Adapter Freeze R2

**Date:** 2026-08-20  
**Authority:** A0  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY`  
**Classification:** `PARTIAL_ADAPTER_FREEZE_TTT_BRIDGE_AND_TOKENIZER_UNRESOLVED`  
**Scientific execution:** `NOT_STARTED`

## Objective

Freeze exact source/checkpoint/state contracts for the matched within-family persistent-state program before any model benchmark execution.

The conceptual classes remain:

```text
TOKEN_CONTEXT
RECURRENT_LATENT
FAST_WEIGHT_STATE
EXTERNAL_RETRIEVAL
```

The R1 methodological correction remains binding:

```text
RawCrossBackboneAccuracy != MemoryMechanismEffect
```

Causal estimands are therefore defined within source families first; cross-family synthesis is restricted to normalized within-family effect sizes and resource curves.

## Frozen source/checkpoint set

### Token context + retrieval decoder

`openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e`

Primary matched context ceiling: `1024` tokens.

Token interventions:

```text
FULL_TOKEN_HISTORY
TRUNCATED_HISTORY
HISTORY_A
HISTORY_B
```

Retrieval uses the same decoder with deterministic BM25-style ranking:

```text
k1 = 1.5
b = 0.75
stable tie-break = canonical chunk id ascending
```

Conditions:

```text
NO_RETRIEVAL
RELEVANT_RETRIEVAL
MATCHED_DISTRACTOR_RETRIEVAL
```

### Recurrent state — Mamba

Source:

`state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa`

Model/tokenizer:

`state-spaces/mamba-130m-hf@1e76775f628fbf1350fbe4dbb3d971ba64af25a1`

The complete continuation-state contract is the full `InferenceParams` object and tensor leaves:

```text
max_seqlen
max_batch_size
seqlen_offset
batch_size_offset
key_value_memory_dict
lengths_per_sample
```

Important finding:

```text
InferenceParams.reset() != proven clean-memory reset
```

The source reset method resets offsets/lengths but does not establish that continuation tensors are clean. Scientific `RESET_STATE` must therefore allocate/reinitialize the complete cache.

Frozen interventions:

```text
CARRY_STATE
RESET_STATE_FRESH_CACHE
SWAP_COMPLETE_STATE_A_TO_B
RANDOM_OR_PERMUTED_COMPLETE_STATE
```

### Fast-weight state — TTT

Official sources:

```text
test-time-training/ttt-lm-pytorch@cd831db10c8c9a0f6340f02da5613316a8a92b67
test-time-training/ttt-lm-jax@6f529b124c7fb5879b33c06926408b15add1d82f
```

Official small checkpoint candidate:

`Test-Time-Training/ttt-linear-125m-books-2k@b1a5f81bed7b70be067867b6b47a6e7047c5093e`

The official checkpoint is a JAX/streaming-train-state artifact rather than a native state dictionary for the pinned PyTorch tutorial implementation. The PyTorch source references the gated Llama-2 tokenizer.

Therefore:

```text
TTT_OFFICIAL_CHECKPOINT = RESOLVED
TTT_PYTORCH_CHECKPOINT_BRIDGE = UNRESOLVED
TTT_EXACT_TOKENIZER_BYTES = UNRESOLVED_GATED_RESOURCE
TTT_EXECUTION_ADAPTER = NOT_YET_FROZEN
```

No community conversion is substituted.

The source `TTTCache` includes:

```text
seqlen_offset
mini_batch_size
ttt_params_dict
conv_states_dic
```

For `TTTLinear`, mutable learned state includes at least `W1_states`, `b1_states`, `W1_grad`, and `b1_grad`; exact complete state remains checkpoint-configuration dependent.

## Controlled RULER freeze

Pinned source:

`NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a`

Frozen tasks:

```text
niah_single_1
niah_multikey_1
niah_multiquery
vt
```

Frozen generation envelope:

```text
max_seq_length = 1024
num_samples_per_task_per_seed = 32
seeds = [73000, 73001, 73002, 73003]
remove_newline_tab = false
```

Generated-example hashes remain pending because RULER generation is tokenizer-aware and the exact TTT tokenizer bridge is unresolved. No model outcome may be observed before dataset hashes are frozen.

Evidence ceiling:

```text
RULER-controlled result <= EM1
```

## Scientific status

No memory class is promoted or rejected. No benchmark model run occurred.

R2 state:

```text
GPT2_TOKEN_ADAPTER_SPEC = FROZEN
GPT2_RETRIEVAL_ADAPTER_SPEC = FROZEN
MAMBA_CHECKPOINT = FROZEN
MAMBA_STATE_CONTRACT = FROZEN
TTT_SOURCE_AND_CHECKPOINT = FROZEN
TTT_CHECKPOINT_TOKENIZER_BRIDGE = UNRESOLVED
RULER_TASKS_CONFIGS_SEEDS = FROZEN
RULER_EXAMPLE_HASHES = PENDING
```

## Hero correction co-delivered

The README hero is updated in the same final repository commit.

A direct binary upload of the approved raster hero failed Git-blob checksum validation once. Under the project's no-retry rule it was not retried. Instead, the old SVG is replaced at the same path with a newly rendered **Γ-centered vector architecture hero** preserving the intended visual/semantic structure:

- central `Γ — Governed Action Core`;
- Memory, World Models, Reasoning, Evaluation, Governance and External Evidence;
- `ADMISSIBLE ACTIONS ONLY` gate;
- Execution / World beneath the governance core;
- Safety Boundary;
- `Capability ≠ Authority` and `OUTCOME_UNKNOWN ≠ NOT_EXECUTED`.

Final hero path:

`assets/logos-1-hero.svg`

The SVG is a normal UTF-8 Git blob, so the binary corruption problem cannot recur for this asset. This maintenance change has no scientific-evidence effect.

## Next work order

`NEXT-SESSION-PERSISTENT-STATE-RESOLVED-FAMILY-ADAPTER-IMPLEMENTATION-R3`

R3 implements deterministic adapters for the resolved families, resolves or explicitly parks the official TTT bridge once, and materializes/hash-freezes the controlled datasets before any model benchmark run.

## Boundaries

```text
PersistentState != Authority
MemoryTruth != MemoryAuthority
CausalState != PhenomenalConsciousness
ControlledSyntheticEvidence != EM2
ArchitecturePerformance != MechanismIdentity
```

`Γ-v0.3` remains `HOLD`.
