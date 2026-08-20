# Persistent-State Intervention Adapters

LOGOS preserves four conceptual classes:

```text
TOKEN_CONTEXT
RECURRENT_LATENT
FAST_WEIGHT_STATE
EXTERNAL_RETRIEVAL
```

Primary causal estimates are within-family. Raw accuracy across different backbones is descriptive only:

```text
RawCrossBackboneAccuracy != MemoryMechanismEffect
```

## Token context

Frozen baseline: `openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e`.

Controls: full history up to 1024 tokens, frozen 512-token tail truncation, and history A→B substitution under the identical query. No KV-cache manipulation is relabeled as durable learned memory.

## External retrieval

The retrieval arm uses the same GPT-2 decoder and deterministic lexical BM25:

```text
k1 = 1.5
b = 0.75
stable ties = chunk_id ascending
```

Every retrieval record carries candidate IDs, scores, selected IDs, selected-text SHA-256 values, retrieved lexical-token count and final-prompt SHA-256. Retrieval score is an index signal, not evidence strength or authority.

## Mamba recurrent state

Frozen source/model:

```text
state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa
state-spaces/mamba-130m-hf@1e76775f628fbf1350fbe4dbb3d971ba64af25a1
```

Snapshot allowlist:

```text
max_seqlen
max_batch_size
seqlen_offset
batch_size_offset
key_value_memory_dict
lengths_per_sample
```

For the frozen 130M configuration each of 24 layers carries:

```text
conv_state [B, 1536, 4]
ssm_state [B, 1536, 16]
```

Upstream `InferenceParams.reset()` does not itself erase `key_value_memory_dict`. Scientific `RESET_STATE` therefore allocates a fresh/reinitialized complete cache.

Supported controls: capture/restore, fresh reset, full A↔B state swap, deterministic tensor permutation preserving shape/dtype/value multiset, and content digests.

## TTT fast-weight state

Official sources/checkpoint remain pinned:

```text
test-time-training/ttt-lm-pytorch@cd831db10c8c9a0f6340f02da5613316a8a92b67
test-time-training/ttt-lm-jax@6f529b124c7fb5879b33c06926408b15add1d82f
Test-Time-Training/ttt-linear-125m-books-2k@b1a5f81bed7b70be067867b6b47a6e7047c5093e
```

The PyTorch code exposes mutable test-time state/update tensors such as `W1_states`, `b1_states`, `W2_states`, `b2_states` and gradient carry fields. The official 125M checkpoint is distributed as a JAX `streaming_train_state`; the exact official checkpoint-to-PyTorch bridge and exact tokenizer bytes were not resolved in R3.

```text
TTT_R3 = SOURCE_ADAPTER_UNRESOLVED
```

Community conversions do not silently replace the frozen official artifact.

## RULER role

Frozen tasks: `niah_single_1`, `niah_multikey_1`, `niah_multiquery`, `vt`; 1024-token maximum; 32 samples per task per seed; seeds 73000–73003.

RULER is synthetic, so:

```text
RULER evidence ceiling = EM1
```

The same intervention definitions must later transfer to a realistic public non-synthetic substrate before EM2 promotion.

## Authority boundary

```text
PersistentState != Authority
MemoryTruth != MemoryAuthority
```

The Mamba snapshot uses an explicit allowlist and does not capture governance, grants or credentials.
