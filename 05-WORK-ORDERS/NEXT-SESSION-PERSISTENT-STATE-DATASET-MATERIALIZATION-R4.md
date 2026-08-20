# NEXT SESSION — Persistent-State Dataset Materialization R4

**Session ID:** `NEXT-SESSION-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4`  
**Authority:** `A0`  
**Track:** persistent state / controlled causal substrate  
**Type:** exact tokenizer/data materialization only  
**Status:** `READY_PERSISTENT_STATE_DATASET_MATERIALIZATION_R4`  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY`  
**Scientific/model execution:** `PROHIBITED_IN_THIS_WORK_ORDER`

## Objective

R3 implemented and statically validated the resolved-family intervention adapters, but the connected container could not materialize RULER data because exact tokenizer bytes and the tokenizer runtime were not locally available. R4 freezes those bytes and generated datasets before any model outcome.

## Frozen sources

```text
NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a
openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e
state-spaces/mamba-130m-hf@1e76775f628fbf1350fbe4dbb3d971ba64af25a1
```

TTT remains excluded until a separate work order resolves its official adapter/tokenizer bridge.

## Frozen RULER envelope

```text
tasks = [niah_single_1, niah_multikey_1, niah_multiquery, vt]
max_seq_length = 1024
num_samples_per_task_per_seed = 32
seeds = [73000, 73001, 73002, 73003]
remove_newline_tab = false
```

Generator/config Git blobs:

```text
scripts/synthetic.yaml = 29cfa5f60b49a7fa53f8dccbbd4f0c7c9e7834fa
scripts/data/synthetic/niah.py = 729eddc260ef5a9aa0473557cd249abca232764a
scripts/data/synthetic/variable_tracking.py = bc5dab381f38e810e5050340d8dae29ae1cfc82a
scripts/data/tokenizer.py = 5a2ddb504ce26da5b43c0f196629e152fca1460b
scripts/config_tasks.sh = 2948008000e0c1c95815029b87b9886a05b8f073
```

## One-shot resource gate

Before generation record exact GPT-2 and Mamba tokenizer files, SHA-256/byte sizes, exact `transformers`/`tokenizers` versions, RULER checkout SHA and environment fingerprint.

If any required tokenizer byte cannot be acquired:

```text
R4 = UNTESTED_RESOURCE_TRANSPORT
```

Do not retry in the same session and do not synthesize a tokenizer.

## Generation and return

Generate only the frozen task/seed combinations for GPT-2 and Mamba tokenizers. For every JSONL persist task, seed, exact command, row count 32, file SHA-256, canonical per-row SHA-256, token-length summary, generator hashes and tokenizer hashes.

Expected if both families succeed:

```text
2 tokenizer families × 4 tasks × 4 seeds = 32 JSONL files
32 rows/file = 1024 generated examples total
```

Return one artifact containing:

```text
TOKENIZER-MANIFEST.json
DATASET-MANIFEST.json
SHA256SUMS.txt
generated/*.jsonl
ENVIRONMENT.json
RETURN-ENVELOPE.json
```

Allowed return classifications: `COMPLETE_DATASET_FREEZE` or `UNTESTED_RESOURCE_TRANSPORT`.

## Isolation

This work order must not load GPT-2, Mamba or TTT model weights and must not execute any answer-producing LLM. Dataset materialization is not mechanism evidence.

Only `COMPLETE_DATASET_FREEZE` may create a later explicit RULER model-execution work order. Any later RULER result remains `<= EM1`.

## Boundaries

```text
DatasetAvailability != MechanismEvidence
RawCrossBackboneAccuracy != MemoryMechanismEffect
PersistentState != Authority
CausalState != PhenomenalConsciousness
```

`Γ-v0.3` remains `HOLD`.
