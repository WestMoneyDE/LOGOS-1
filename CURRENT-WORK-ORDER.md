# CURRENT WORK ORDER

**Status:** `READY_PERSISTENT_STATE_DATASET_MATERIALIZATION_R4`  
**Task:** `05-WORK-ORDERS/NEXT-SESSION-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4.md`

Persistent-State Adapter Implementation R3 is complete as an engineering/static-validation session. No GPT-2, Mamba, TTT or RULER benchmark model execution was started.

## R3 result

Implemented and statically tested:

```text
TOKEN_CONTEXT
  full history / 512-token truncation / A→B substitution

EXTERNAL_RETRIEVAL
  deterministic BM25 k1=1.5, b=0.75
  stable chunk-id ties + retrieval/prompt hashes

RECURRENT_LATENT representative
  Mamba complete state capture / restore / fresh / swap / permute / digest

RULER freeze utility
  file SHA-256 + canonical per-row SHA-256 manifests
```

Validation:

```text
pytest: 13 passed / 0 failed
compileall: PASS
scientific model execution: NOT_STARTED
```

Mamba reset boundary:

```text
InferenceParams.reset() != demonstrated memory erasure
RESET_STATE = fresh/reinitialized complete cache
```

TTT official bridge:

```text
TTT_R3 = SOURCE_ADAPTER_UNRESOLVED
```

The official JAX checkpoint format is resolved, but an exact official checkpoint→pinned-PyTorch bridge plus exact authorized tokenizer bytes was not available. No community conversion was substituted and no retry was performed.

RULER output datasets were not faked. The current container lacks cached tokenizer bytes / `transformers`, and network name resolution is unavailable:

```text
RULER_DATASET_FREEZE_R3 = NOT_MATERIALIZED_RESOURCE_TRANSPORT
```

This is not negative evidence for any memory family.

## R4 objective

Materialize and hash the exact GPT-2 and Mamba tokenizer-dependent RULER datasets in a network-capable environment **without loading any model weights**.

Frozen envelope:

```text
tasks = niah_single_1, niah_multikey_1, niah_multiquery, vt
max_seq_length = 1024
samples/task/seed = 32
seeds = 73000..73003
```

Only a byte-verified `COMPLETE_DATASET_FREEZE` may authorize a later RULER model-execution work order.

```text
RawCrossBackboneAccuracy != MemoryMechanismEffect
RULER-controlled evidence <= EM1
PersistentState != Authority
CausalState != PhenomenalConsciousness
```

`Γ-v0.3` remains `HOLD`.
