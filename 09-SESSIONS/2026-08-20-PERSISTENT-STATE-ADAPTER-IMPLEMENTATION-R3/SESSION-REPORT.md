# Session Report — Persistent-State Adapter Implementation R3

**Date:** 2026-08-20  
**Authority:** `A0`  
**Session:** `NEXT-SESSION-PERSISTENT-STATE-RESOLVED-FAMILY-ADAPTER-IMPLEMENTATION-R3`  
**Scientific/model benchmark execution:** `NOT_STARTED`  
**Classification:** `ADAPTERS_IMPLEMENTED_STATIC_PASS / DATASET_RESOURCE_GATE / TTT_SOURCE_ADAPTER_UNRESOLVED`

## Objective

Implement deterministic intervention adapters for the resolved persistent-state families, statically validate them before any model outcome, audit the official TTT bridge exactly once, and hash-freeze RULER datasets only if the frozen tokenizer resources are actually available.

## Implemented

A new dependency-light research package now provides:

- `src/logos_pstate/mamba_state.py`
  - complete allowlisted Mamba continuation-state capture;
  - deep restore;
  - genuinely fresh cache allocation;
  - full snapshot swap;
  - deterministic tensor permutation control;
  - device-independent content digest.
- `src/logos_pstate/token_context.py`
  - full-history validation;
  - frozen 512-token truncation control;
  - history A→B substitution under the identical query.
- `src/logos_pstate/retrieval.py`
  - deterministic dependency-free BM25 (`k1=1.5`, `b=0.75`);
  - canonical chunk-ID tie breaking;
  - deterministic token-budget distractor selection;
  - source/prompt SHA-256 provenance records.
- `src/logos_pstate/ruler_freeze.py`
  - output JSONL SHA-256;
  - canonical per-row SHA-256;
  - task/seed/tokenizer/source/command manifest.

## Source-level Mamba finding

Upstream Mamba `InferenceParams.reset()` updates offsets and zeroes `lengths_per_sample`, but does not erase `key_value_memory_dict` itself.

The Mamba layer cache consists of two tensors per layer:

```text
conv_state = [batch, d_model * expand, d_conv]
ssm_state  = [batch, d_model * expand, d_state]
```

For the frozen 130M configuration this is:

```text
24 layers
conv_state/layer = [B, 1536, 4]
ssm_state/layer  = [B, 1536, 16]
```

Therefore the scientific reset intervention is explicitly:

```text
RESET_STATE = allocate a new/reinitialized complete cache
```

not merely `InferenceParams.reset()`.

## Static validation

Command:

```text
pytest -q
```

Result:

```text
13 passed
0 failed
compileall PASS
```

These are adapter/static tests, **not** a benchmark or mechanism result.

## Authority isolation

The Mamba snapshot is allowlisted to continuation fields only:

```text
max_seqlen
max_batch_size
seqlen_offset
batch_size_offset
key_value_memory_dict
lengths_per_sample
```

Unknown attributes are not captured. The static suite explicitly verifies that an injected `authority` attribute is excluded.

This preserves:

```text
PersistentState != Authority
```

## TTT bridge audit — one attempt

Official sources remain:

```text
test-time-training/ttt-lm-pytorch@cd831db10c8c9a0f6340f02da5613316a8a92b67
test-time-training/ttt-lm-jax@6f529b124c7fb5879b33c06926408b15add1d82f
Test-Time-Training/ttt-linear-125m-books-2k@b1a5f81bed7b70be067867b6b47a6e7047c5093e
```

The official checkpoint is a JAX streaming train-state artifact. The JAX repository contains a loader for that format. The pinned PyTorch reference implementation exposes the desired learned test-time state tensors, but this session did not resolve an official, byte-verifiable checkpoint→PyTorch bridge that preserves learned weights without conversion ambiguity.

The official TTT code also names `meta-llama/Llama-2-7b-hf` as tokenizer. Exact authorized tokenizer bytes are not bundled with the frozen official checkpoint and are unavailable in the connected environment.

Verdict:

```text
TTT_R3 = SOURCE_ADAPTER_UNRESOLVED
```

No community conversion was tried as a replacement and no second bridge attempt was made.

This is not evidence against TTT or fast-weight memory.

## RULER dataset hash gate

Frozen source and envelope are retained:

```text
NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a

tasks = niah_single_1, niah_multikey_1, niah_multiquery, vt
max_seq_length = 1024
samples/task/seed = 32
seeds = 73000..73003
remove_newline_tab = false
```

Generator/config blobs were pinned in `DATASET-FREEZE-GATE.json`.

The connected container has no cached GPT-2/Mamba tokenizer bytes, no `transformers` package, and no network name resolution. One package-install check failed on name resolution and was not retried.

Therefore output datasets were **not** materialized and fake tokenization was not substituted:

```text
RULER_DATASET_FREEZE_R3 = NOT_MATERIALIZED_RESOURCE_TRANSPORT
```

No model outcomes were inspected.

## Scientific status

No memory mechanism is promoted, rejected or ranked in R3.

Retained boundaries:

```text
RawCrossBackboneAccuracy != MemoryMechanismEffect
RULER-controlled result <= EM1
Mamba != BDH-CQ
TTT != MoNe
PersistentState != Authority
CausalState != PhenomenalConsciousness
```

`Γ-v0.3` remains `HOLD`.

## Next work order

`NEXT-SESSION-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4`

R4 is a **data/resource transport session only**. It must materialize exact tokenizer bytes and frozen RULER JSONL outputs in a network-capable environment, verify file/row hashes, and return them **without running GPT-2, Mamba or TTT inference**. Only after those artifacts are frozen may a later explicit scientific RULER execution work order be created.
