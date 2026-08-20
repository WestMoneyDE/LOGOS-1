# NEXT SESSION — SCB-R2 Terminal-Bench P×R External Preflight R1

**Session ID:** `NEXT-SESSION-SCB-R2-TERMINALBENCH-PR-EXTERNAL-PREFLIGHT-R1`  
**Authority:** `A0`  
**Track:** `SCB-R2 / state-causality benchmark / procedural × recovery localization`  
**Type:** source/runtime preflight for preserved external factorial  
**Status:** `READY_SCB_R2_EXTERNAL_PREFLIGHT`  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY`  
**Scientific ceiling:** bounded EM2 localization for the real `P × R` Terminal-Bench 2.0 substrate only

## Why this is next

Completed/imported external tracks:

1. MBE;
2. ENF;
3. WMR.

Parked exact-resource/transport tracks:

4. MF-R1 / LongMemEval-V2 — `UNTESTED_RESOURCE_TRANSPORT`;
5. TCV-R2 / Wrong but Useful — `UNTESTED_RESOURCE_TRANSPORT`;
6. MF-R3 / SkillsBench — `UNTESTED_RESOURCE_TRANSPORT`.

SCB-R2 already has a preserved preregistration from the prior LOGOS transport lineage. Do not replace it with a newly invented five-module benchmark.

## Preserved scientific decision

No scientifically valid common public substrate currently joins all proposed W/M/P/R/Q components.

Therefore:

```text
SCB_FIVE_WAY_EXTERNAL_INTEGRATION = WAIT_COMPONENT_EXTERNAL_ADAPTERS
```

The only preserved common real substrate is:

```text
P × R -> Terminal-Bench 2.0
```

where:

- `P` = procedural-guidance intervention;
- `R` = recovery intervention.

## Verified upstream pins

Procedural source:

- repository: `UCSB-NLP-Chang/Skill-Usage`
- commit: `03446d16f7b659ccc93ac5bd512f62e9b7fabb45`
- public skill pool target: `34,198` skills
- benchmark/task substrate: Terminal-Bench 2.0

Recovery source:

- repository: `Futuresis/replay-agent-recorder`
- commit: `6661046e2b30fcf5f17c93d51acb56babdea8c53`
- public release line at pin: v2 alpha.1 lineage

The source pins were re-resolved before this work order was activated.

## Frozen factorial

Procedural factor:

```text
P0 = MATCHED_DISTRACTOR_GUIDANCE
P1 = RETRIEVED_PROCEDURAL_GUIDANCE
```

Recovery factor:

```text
R0 = RESTART_WITH_EXPERIENCES
R1 = AGENT_REWIND
```

`CONTINUE_NO_RECOVERY` is descriptive only and is not the primary R control.

## Procedural information contract

P1 uses the source-pinned top-5/reproduced retrieval from Skill-Usage.

P0 uses the same number of packages from the same public skill pool, excluding P1 skill IDs, selected by deterministic nearest aggregate byte match.

Required:

```text
abs(bytes(P0) - bytes(P1)) / bytes(P1) <= 0.10
```

Tasks failing the byte-match constraint are excluded before outcomes are observed.

Both conditions are converted to the same harness-neutral `PROCEDURAL_GUIDANCE.md` representation and loaded by the same neutral prompt.

This tests procedural relevance rather than merely extra text/resources.

## Recovery control contract

`R0 = RESTART_WITH_EXPERIENCES` resets the task environment and restarts while preserving prior-attempt experience information.

`R1 = AGENT_REWIND` restores aligned agent context plus a controlled environment checkpoint and injects rewind memory.

The intended contrast is:

```text
CheckpointRestore
vs
ExperienceOnlyRestart
```

not recovery versus doing nothing.

## Factorial estimands

For task outcome `Y`:

```text
E_P(R0) = Y(P1,R0) - Y(P0,R0)
E_P(R1) = Y(P1,R1) - Y(P0,R1)
E_R(P0) = Y(P0,R1) - Y(P0,R0)
E_R(P1) = Y(P1,R1) - Y(P1,R0)
I_PR     = Y11 - Y10 - Y01 + Y00
```

Primary inference is paired at task level with a paired task bootstrap.

## Generic untyped comparator

A strong held-out-task diagnostic predictor receives only flat, pre-outcome observables:

- raw task text;
- raw guidance text;
- raw configuration;
- trace-prefix summaries where source-clean.

It must not receive typed `P`/`R` labels, verifier results, oracle data, hidden criteria, or post-hoc outcomes as features.

If a generic representation predicts outcomes as well as typed terms, that blocks any claim that P/R typing is a necessary capability architecture.

Preserve:

```text
StateEffect != MechanismIdentity
```

## Leakage prohibitions

Retrieval/guidance preparation must not use:

- verifier source/tests;
- oracle/reference solution;
- hidden acceptance criteria;
- post-hoc task outcomes;
- typed P/R labels as generic predictor features.

Any violation invalidates the run.

## Required preflight before execution

Verify once, before any scientific run:

1. exact Skill-Usage commit;
2. exact Replay Agent Recorder commit;
3. exact Terminal-Bench **2.0** task tree — do not silently switch to 2.1;
4. complete 34,198-skill public pool or source-equivalent pinned release;
5. reproduced/precomputed P1 retrieval for the same TB2 tasks;
6. common model identity;
7. common agent harness identity/version;
8. Docker/Harbor-compatible sandbox runtime;
9. recovery/checkpoint path capable of R0 and R1 under one harness;
10. one provider credential/back-end for the common model;
11. result persistence path prepared before execution.

If any required runtime/source/mount is absent:

```text
SCB_R2_PR = UNTESTED_RESOURCE_TRANSPORT
```

Record once; do not substitute or automatically retry.

## Equal-budget contract

Across all four primary cells hold constant wherever applicable:

- task tree;
- model;
- agent harness;
- verifier;
- attempt termination rule;
- model reasoning effort;
- trial count;
- procedural package count;
- approximate procedural bytes.

Recovery resource costs are reported rather than hidden because R1 inherently performs checkpoint operations.

## Primary metrics

- task success;
- verifier reward / criteria fraction;
- trace events;
- wall seconds;
- input tokens;
- output tokens;
- recovery invocations;
- checkpoint restore count.

## Maximum promotion

A successful real public-task execution can at most support:

```text
SCB_P_R_EXTERNAL_LOCALIZATION = KEEP_BOUNDED_EM2
```

It cannot establish:

- five-module SCB external validity;
- P/R typing as a necessary capability architecture;
- `AgentRollback == WorldRollback`;
- authority from state;
- consciousness, sentience or welfare;
- Γ-v0.3 promotion.

## No-retry rule

One frozen external execution attempt is permitted only after the entire source/runtime gate passes and all manifests are persisted/prepared.

Failed, cancelled, blocked, timed-out or resource-incomplete execution is recorded exactly and is not automatically repeated. A later rerun requires an explicit new work order after a materially changed prerequisite.
