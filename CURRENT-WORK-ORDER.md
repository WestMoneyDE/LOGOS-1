# CURRENT WORK ORDER

**Status:** READY_PERSISTENT_STATE_ADAPTER_IMPLEMENTATION_R3  
**Task:** `05-WORK-ORDERS/NEXT-SESSION-PERSISTENT-STATE-RESOLVED-FAMILY-ADAPTER-IMPLEMENTATION-R3.md`

Persistent-State Matched-Family Adapter Freeze R2 is complete as a partial source/checkpoint freeze. No model benchmark execution was started.

Resolved/frozen:

```text
TOKEN_CONTEXT / RETRIEVAL DECODER
openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e

RECURRENT STATE
state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa
state-spaces/mamba-130m-hf@1e76775f628fbf1350fbe4dbb3d971ba64af25a1

FAST-WEIGHT SOURCES/CHECKPOINT
TTT PyTorch @ cd831db10c8c9a0f6340f02da5613316a8a92b67
TTT JAX     @ 6f529b124c7fb5879b33c06926408b15add1d82f
TTT 125M checkpoint @ b1a5f81bed7b70be067867b6b47a6e7047c5093e

CONTROLLED SUBSTRATE
NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a
```

R2 blocker:

```text
TTT_OFFICIAL_CHECKPOINT = RESOLVED
TTT_PYTORCH_CHECKPOINT_BRIDGE = UNRESOLVED
TTT_EXACT_TOKENIZER_BYTES = UNRESOLVED_GATED_RESOURCE
```

The official 125M TTT artifact is a JAX/streaming-train-state checkpoint; no community conversion is substituted. The next session must resolve or park that exact bridge once.

Frozen controlled task envelope:

```text
tasks = [niah_single_1, niah_multikey_1, niah_multiquery, vt]
max_seq_length = 1024
num_samples_per_task_per_seed = 32
seeds = [73000, 73001, 73002, 73003]
```

Generated-example hashes remain intentionally pending until exact family tokenizer resources are frozen. Model benchmark execution before the hash freeze is prohibited.

The next session implements deterministic Mamba complete-state clone/reset/swap, GPT-2 token-history controls and deterministic matched retrieval; it resolves or explicitly parks the official TTT bridge; then it materializes/hash-freezes RULER datasets. It is still an adapter session, not a scientific mechanism verdict.

Methodological boundaries remain:

```text
RawCrossBackboneAccuracy != MemoryMechanismEffect
RULER-controlled result <= EM1
PersistentState != Authority
CausalState != PhenomenalConsciousness
```

Repository maintenance included in the R2 checkpoint: `assets/logos-1-hero.svg` is replaced by the new Γ-centered architecture hero. The binary PNG transport failed checksum validation once and was not retried; the final vector asset is corruption-safe and Git-native.

`Γ-v0.3` remains `HOLD`.
