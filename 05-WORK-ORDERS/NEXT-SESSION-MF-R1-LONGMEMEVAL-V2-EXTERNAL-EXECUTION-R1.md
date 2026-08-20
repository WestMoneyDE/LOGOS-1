# NEXT SESSION — MF-R1 LongMemEval-V2 External Execution R1

**Session ID:** `NEXT-SESSION-MF-R1-LONGMEMEVAL-V2-EXTERNAL-EXECUTION-R1`  
**Authority:** `A0`  
**Track:** `MF-R1 / LongMemEval-V2 strong flat vs associative`  
**Type:** external execution  
**Status:** `READY_ON_DATA_AND_MODEL_ENDPOINTS`  
**Scientific ceiling:** first possible bounded `EM2` result for associative reconstruction vs a strong flat retrieval baseline under frozen pairing

## Why this is next

The canonical external queue has now completed/imported:

1. MBE / Behavioral-Lift;
2. ENF / safe-control-gym;
3. WMR / ARC-AGI-3.

WMR did not establish distinct incremental value for counterexample-priority replay over matched uniform replay. The next frozen P0 external-validation track is therefore MF-R1 / LongMemEval-V2.

This work order transports the already frozen Phase-3B Memory Fabric experiment. It does not redesign or retune it after observing prior results.

## Frozen upstream and dataset pins

- repository: `xiaowu0162/LongMemEval-V2`
- commit: `2cc8c540bdb87fe6761629b585e727e1c4704520`
- dataset repository: `xiaowu0162/longmemeval-v2`
- required `trajectories.jsonl` SHA-256:
  `363cec9a8e87aa8d9101ce4e600aadbf7031d674056ebe4f969e8424abc5f3c6`

Frozen LOGOS Phase-3B package identities from the preserved transport:

- original work order SHA-256: `9d3340126876911f882296ebfed97df92f24a5c605414087cb63c6353d16cb0c`
- `FROZEN-EXPERIMENT.json`: `84616a639bd4b8b3367467a0f049c95002f06c4c7ef6e6fe58d642c8107dee49`
- `phase3b_executor.py`: `ce5d306fe4f0d480721f151027b0e63f21ed2b8612be3535ae05bb52f24dbfd6`
- `test_executor.py`: `dfef0984b8b9e60ea46dbaf04f4ce4fde272c86eca15c2f09da1dfc5220cb7dd`
- executor `RUNBOOK.md`: `b265733d04bbbcadc3b09baf200af4d6cbf6f8295bbea0a1fccea3de54d693a7`
- `SOURCE-SNAPSHOT.md`: `0712da8228a035aa36788ddfcaf7db453a70bd9d4609bb83083f7efcc36502bd`

Before execution, transport these files byte-exactly into a public/reproducible `external-runs/longmem-r1/` package and verify the hashes above.

## Frozen experiment

Schema:

`logos-mf-r1-phase3b-v1`

Tier:

`small`

Domains:

- `web`
- `enterprise`

### Frozen matrix

1. `no_retrieval` — official reader-only diagnostic
2. `agentrunbook_r` — strongest official RAG-family reference arm
3. `logos_strong_flat` — M3 shared strong anchor ranker without association expansion
4. `logos_strong_associative` — M4 same anchors plus frozen one-hop sequential expansion

## Frozen equalization contract

Do not modify before the primary run:

- shared embedding model/query instruction/chunking;
- anchor count = `8`;
- final evidence item count = `8`;
- primary memory-context cap = `32768` tokens;
- M4 relations = `prev_state`, `next_state`;
- M4 maximum depth = `1`;
- expansion decay = `0.85`;
- same reader/evaluator configuration across arms.

Any required bug fix invalidates the affected run and must be documented before a full rerun. Never patch only the losing arm.

## Frozen model identities

Reader/controller:

- `Qwen/Qwen3.5-9B`
- temperature `0.6`
- top-p `0.95`
- top-k `20`
- thinking enabled

Embedding:

- `Qwen/Qwen3-Embedding-8B`
- max input tokens `4096`
- query instruction:
  `Given a question about past agent trajectories, retrieve relevant memory entries that help answer it.`

Official judge:

- `gpt-5.2`
- reasoning effort `medium`

No model substitution is allowed in the frozen primary result.

## Required runtime resources

Required data mount / root:

`LONGMEM_DATA_ROOT`

Required model/API environment:

- `READER_BASE_URL`
- `LME_CONTROLLER_BASE_URL`
- `LME_EMBEDDING_BASE_URL`
- `OPENAI_API_KEY`

The two Qwen services must expose OpenAI-compatible APIs and report the expected model identities.

If the official dataset, exact model endpoints, or judge access are unavailable:

`UNTESTED_RESOURCE_TRANSPORT`

No substitute model, lexical retriever, synthetic dataset or alternate judge may count as the frozen EM2 result.

## Execution sequence

### 1. Transport and verify frozen executor

Copy the preserved Phase-3B executor package byte-exactly and verify all frozen SHA-256 values.

### 2. Checkout upstream

```bash
git clone https://github.com/xiaowu0162/LongMemEval-V2.git
git checkout 2cc8c540bdb87fe6761629b585e727e1c4704520
```

### 3. Prepare official data

Validate at minimum:

- `questions.jsonl`
- `trajectories.jsonl`
- `haystacks/lme_v2_small.json`
- screenshots required by the selected full official evaluation

The core trajectory hash must equal the frozen SHA above.

### 4. Frozen preflight

The preflight must pass:

- exact upstream commit;
- exact core dataset hash;
- official data validation;
- reader endpoint/model identity;
- controller endpoint/model identity;
- embedding endpoint/model identity;
- judge key availability;
- anti-leakage / pairing contract checks.

### 5. Full-haystack retrieval smoke

Run one text-only question per domain for both:

- `logos_strong_flat`
- `logos_strong_associative`

Inspect technical invariants only. Do not tune relevance or association policy after seeing answers.

### 6. Primary Small-tier matrix

Run all four frozen arms for both:

- web Small
- enterprise Small

### 7. Collect standardized return

Required return evidence includes at least:

- `phase3b-return-index.json`
- `source-provenance.json`
- `preflight.json`
- raw/aggregated JSON or JSONL outputs
- metrics and traces required by the frozen executor
- execution attestation
- return-envelope/hash manifest

## Required metrics

- official answer accuracy/category metrics;
- official latency;
- context token counts;
- embedding calls/items;
- stored text/embedding bytes;
- build/query latency;
- LOGOS anchor/expansion traces;
- official RAG comparison.

Compute CRR / Accessibility Gap only where released annotations support a defensible evidence oracle.

## Primary kill rule

`ASSOCIATIVE_RECONSTRUCTION_DISTINCT = MERGE/REJECT`

if `logos_strong_associative` does not improve the preregistered outcome over `logos_strong_flat` under equalized conditions, or if a gain is attributable to unequal resource access.

Maximum positive outcome:

`ASSOCIATIVE_RECONSTRUCTION_DISTINCT = KEEP_BOUNDED_EM2`

only within the exact LongMemEval-V2 Small-tier pairing and frozen resource contract.

## Scientific boundaries

Even a positive result does not establish:

- a universal associative-memory primitive;
- a dedicated conflict graph or specialized skill store as necessary architecture;
- lifelong memory in unrestricted environments;
- consciousness, sentience, identity or welfare;
- authority from memory;
- Γ-v0.3 promotion.

Preserve:

`AgentMemory != AssuranceState`

`AdaptiveState != Authority`

## Immediate first action next session

Run the frozen **resource/preflight gate before any model evaluation**. If exact Qwen endpoints, official data or the `gpt-5.2` judge are unavailable, record `UNTESTED_RESOURCE_TRANSPORT` and do not fabricate a substitute result.
