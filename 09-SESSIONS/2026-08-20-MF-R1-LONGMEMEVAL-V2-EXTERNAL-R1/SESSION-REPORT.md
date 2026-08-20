# Session Report — MF-R1 LongMemEval-V2 Resource Gate / TCV Advancement R1

**Date:** 2026-08-20  
**Authority:** A0  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY`  
**MF classification:** `UNTESTED_RESOURCE_TRANSPORT`  
**MF scientific verdict:** `UNTESTED`

## Objective

Take the canonical MF-R1 / LongMemEval-V2 Phase-3B track through its frozen prerequisite gate without model/data substitution or repeated GitHub execution, then advance the external queue if the exact resources are unavailable.

## MF frozen contract checked

The preserved Phase-3B package and its work order require:

- upstream `xiaowu0162/LongMemEval-V2@2cc8c540bdb87fe6761629b585e727e1c4704520`;
- official `trajectories.jsonl` SHA-256 `363cec9a8e87aa8d9101ce4e600aadbf7031d674056ebe4f969e8424abc5f3c6`;
- reader/controller `Qwen/Qwen3.5-9B`;
- embedding `Qwen/Qwen3-Embedding-8B`;
- judge `gpt-5.2`;
- strong-flat vs strong-associative equalization with 8 anchors, 8 final evidence items, 32768-token memory-context cap, one-hop `prev_state`/`next_state` expansion and decay `0.85`.

The frozen local executor/backend suite was validated before repository mutation: `18/18` tests passed.

## Resource gate outcome

The exact required model/judge endpoints and credentials are not available to the connected execution environment used for this session. Therefore the full LongMemEval external matrix was **not started**.

Classification:

`MF_R1 = UNTESTED_RESOURCE_TRANSPORT`

This means:

- no result against associative reconstruction;
- no result in favor of associative reconstruction;
- no EM2 promotion/demotion;
- no alternate reader/controller;
- no alternate embedding model;
- no alternate judge;
- no lexical substitute counted as the frozen experiment;
- no synthetic dataset counted as external evidence.

Per the project/user execution rule, the blocked run was **not retried**.

## No-retry repository rule added

`AGENTS.md` and `docs/engineering/PUSH-PROTOCOL.md` now require:

1. fully prepare and validate before repository mutation;
2. prefer one coherent content push;
3. do not automatically retry failed/cancelled/blocked external runs;
4. persist the exact first outcome;
5. only a separately authorized future work order after materially changed prerequisites may execute again.

## TCV-R2 primary-source verification

The next runnable track was checked against the primary paper:

`Wrong but Useful: Trajectory Value Beyond Answer Correctness in Multi-Agent Messages`, arXiv:2608.14375.

Verified protocol facts used for the next work order:

- a fixed cached pool of five independently generated messages;
- a separate integrator;
- matched replay with the target message available vs hidden;
- single-message and in-pool leave-one-out replay are distinct contexts;
- observed replay effect is distinct from expected/repeatable trajectory value;
- removal changes prompt length/absolute token positions and therefore does not by itself isolate semantic content;
- the paper states that verbatim templates and protocol configuration are packaged in `anc/reproducibility_artifact.zip`.

No result from this paper is imported as a LOGOS causal result merely from reading the publication.

## Queue decision

MF-R1 is parked as an unresolved exact-resource dependency, not rejected.

Next canonical task:

`NEXT-SESSION-TCV-R2-WRONG-BUT-USEFUL-EXTERNAL-PREFLIGHT-R1`

The next session must acquire and integrity-audit the official ancillary artifact before any replay interpretation. If the official artifact or exact replay resources are unavailable, classify once as `UNTESTED_RESOURCE_TRANSPORT` and advance without automatic retry.

## Boundaries

Unchanged:

- `AdaptiveState != Authority`
- `AgentMemory != AssuranceState`
- `OUTCOME_UNKNOWN != NOT_EXECUTED`
- `TrajectoryValue != IntrinsicMessageQuality`
- `ObservedReplayFlip != ExpectedTrajectoryValue`
- Γ-v0.3 remains `HOLD`
- no consciousness/sentience/welfare inference
