# NEXT SESSION — Persistent-State Resolved-Family Adapter Implementation R3

**Session ID:** `NEXT-SESSION-PERSISTENT-STATE-RESOLVED-FAMILY-ADAPTER-IMPLEMENTATION-R3`  
**Authority:** A0  
**Track:** persistent state / memory / causal state use  
**Type:** deterministic adapter implementation + dataset hash freeze  
**Status:** `READY_PERSISTENT_STATE_ADAPTER_IMPLEMENTATION_R3`  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY` for any scientific/model run  
**Scientific ceiling:** no scientific mechanism verdict in this adapter session; later RULER run <= EM1

## R2 state entering this work order

Frozen/resolved:

```text
TOKEN_CONTEXT:
  openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e

RECURRENT_LATENT representative:
  state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa
  state-spaces/mamba-130m-hf@1e76775f628fbf1350fbe4dbb3d971ba64af25a1

EXTERNAL_RETRIEVAL decoder:
  openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e

FAST_WEIGHT source/checkpoint:
  test-time-training/ttt-lm-pytorch@cd831db10c8c9a0f6340f02da5613316a8a92b67
  test-time-training/ttt-lm-jax@6f529b124c7fb5879b33c06926408b15add1d82f
  Test-Time-Training/ttt-linear-125m-books-2k@b1a5f81bed7b70be067867b6b47a6e7047c5093e
```

Unresolved:

```text
TTT official checkpoint -> executable adapter bridge
TTT exact tokenizer bytes / gated Llama-2 tokenizer resource
```

No community conversion may silently replace the official TTT checkpoint.

## Objective

Produce deterministic, statically tested adapters for all currently resolved families and either resolve the official TTT bridge or persist it as an explicit blocked adapter.

No benchmark model outcome may be inspected until dataset hashes and adapter tests are frozen.

## A. Mamba complete-state adapter

Implement a typed state snapshot containing every continuation-relevant `InferenceParams` field:

```text
max_seqlen
max_batch_size
seqlen_offset
batch_size_offset
key_value_memory_dict (deep tensor clone)
lengths_per_sample (deep tensor clone or null)
```

Required functions:

```text
capture_state()
restore_state(snapshot)
fresh_state()
swap_state(snapshot_A, snapshot_B)
permute_state(snapshot, seed)
state_digest(snapshot)
```

`fresh_state()` must allocate/reinitialize the full cache; calling `InferenceParams.reset()` alone is insufficient for the scientific `RESET_STATE` intervention unless an explicit tensor-zeroing proof is added.

Static/deterministic tests before any RULER benchmark:

1. capture -> restore is byte/tensor identical;
2. two captures from identical history have identical digests under deterministic execution;
3. fresh state does not reuse mutated cache tensors;
4. swap exchanges complete state objects without changing model weights;
5. random/permuted control preserves declared shape/dtype invariants;
6. no state object contains or modifies Γ/authority data.

## B. Token-context adapter

Frozen model/revision:

`openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e`

Implement deterministic transforms:

```text
FULL_TOKEN_HISTORY
TRUNCATED_HISTORY
HISTORY_SUBSTITUTION_A_TO_B
```

Freeze truncation by token count before outcomes. The primary controlled context is 1024 tokens maximum.

No KV-cache swap is interpreted as persistent-memory evidence in this family.

## C. External-retrieval adapter

Use the exact same GPT-2 model/revision as the token-context family.

Implement deterministic BM25-style lexical ranking:

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

Persist per example:

- candidate chunk IDs;
- scores;
- selected chunk IDs;
- selected text SHA-256;
- retrieved token count;
- final prompt SHA-256.

Relevant/distractor conditions must be matched in chunk count and approximate token budget.

## D. TTT official bridge gate

First attempt must use the official sources/checkpoint already frozen.

Required questions before execution:

1. Can `streaming_train_state` at the frozen 125M checkpoint revision be loaded by the pinned JAX code without modifying learned weights?
2. Can the exact inference hidden/test-time state be serialized, cloned, restored and swapped?
3. Which checkpoint metadata fields determine `share_qk`, `pre_conv`, mini-batch size and exact TTT state schema?
4. Can the exact tokenizer used for the checkpoint be byte-pinned under an authorized resource path?

If yes, freeze:

- checkpoint loader;
- tokenizer hash/revision;
- complete mutable state tree;
- reset/restore/swap functions;
- state digest.

If no:

```text
TTT_R3 = SOURCE_ADAPTER_UNRESOLVED
```

Do not retry alternative unofficial conversions within the same session.

## E. RULER dataset materialization and hash freeze

Pinned source:

`NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a`

Frozen tasks:

```text
niah_single_1
niah_multikey_1
niah_multiquery
vt
```

Frozen envelope:

```text
max_seq_length = 1024
num_samples_per_task_per_seed = 32
seeds = [73000, 73001, 73002, 73003]
remove_newline_tab = false
```

Generate family-specific token-length-fitted datasets only after the corresponding tokenizer is frozen.

Before any model benchmark execution persist:

- generator source hashes;
- tokenizer revision/hash;
- exact command/config;
- output JSONL SHA-256;
- per-row canonical SHA-256;
- row count;
- task/seed/context metadata.

If TTT remains unresolved, do not invent a TTT dataset. Resolved-family datasets may still be frozen for adapter verification but a complete four-family result remains unavailable.

## F. Scientific-run gate

No RULER model run in this session unless a subsequent explicit work order is created after all selected family datasets/adapters are frozen.

The later controlled run must retain:

```text
D(S) = Decodability
O(S) = Operational utility
C(S) = Causal intervention effect
```

and the within-family estimands:

```text
StateUseEffect
SwapEffect
CorruptionCost
RecoveryGain
```

## G. Evidence boundaries

```text
RULER-controlled result <= EM1
RawCrossBackboneAccuracy != MemoryMechanismEffect
Mamba != BDH-CQ
TTT != MoNe
PersistentState != Authority
CausalState != PhenomenalConsciousness
```

A later public realistic/non-synthetic confirmatory substrate is mandatory before EM2 promotion.

`Γ-v0.3` remains `HOLD`.

## Completion criteria

1. Mamba complete-state adapter implemented and deterministic static tests pass;
2. GPT-2 token-history transforms implemented and hashed;
3. deterministic retrieval adapter implemented and hashed;
4. TTT official bridge resolved or explicitly parked once;
5. exact tokenizer resources frozen for every runnable family;
6. RULER generated datasets hashed before any model outcome;
7. no scientific benchmark run hidden inside adapter validation;
8. one durable session checkpoint;
9. one coherent repo commit only.
