# Session Report — SCB-R2 Terminal-Bench P×R External Preflight R1

**Date:** 2026-08-20  
**Authority:** A0  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY`  
**Classification:** `UNTESTED_RESOURCE_TRANSPORT`  
**Scientific verdict:** `UNTESTED`

## Objective

Take the preserved SCB-R2 `P × R` Terminal-Bench 2.0 localization through its complete source/mount/runtime gate before any scientific agent execution.

The frozen factorial remains:

```text
P0 = MATCHED_DISTRACTOR_GUIDANCE
P1 = RETRIEVED_PROCEDURAL_GUIDANCE

R0 = RESTART_WITH_EXPERIENCES
R1 = AGENT_REWIND
```

The session does not construct a synthetic five-way W/M/P/R/Q benchmark.

## Source verification

The pinned sources resolve:

- `UCSB-NLP-Chang/Skill-Usage@03446d16f7b659ccc93ac5bd512f62e9b7fabb45`;
- `Futuresis/replay-agent-recorder@6661046e2b30fcf5f17c93d51acb56babdea8c53`.

The pinned Skill-Usage README confirms:

- evaluation on Terminal-Bench 2.0;
- a cleaned public collection of 34,198 real-world skills;
- a Terminal-Bench `retrieved` setting using top-5 skills from the 34k pool;
- Docker as an execution requirement;
- Harbor-based agent evaluation.

The pinned Replay Agent Recorder commit resolves to the v2 alpha.1 public-release lineage and exposes checkpoint/sandbox/replay functionality relevant to the preserved `R1` intervention.

These observations establish source availability only. They do not establish that the two projects are already integrated into a single valid SCB experimental harness.

## Runtime and mount gate

The connected execution environment was inspected before any trial.

Observed:

```text
Python = 3.13.5
uv = AVAILABLE
Docker = UNAVAILABLE
Podman = UNAVAILABLE
Harbor = UNAVAILABLE
SCB_SKILL_POOL_ROOT = ABSENT
SCB_RETRIEVED_TB2_ROOT = ABSENT
SCB_COMMON_MODEL = ABSENT
SCB_COMMON_HARNESS = ABSENT
OPENAI_API_KEY = ABSENT
ANTHROPIC_API_KEY = ABSENT
GEMINI_API_KEY = ABSENT
GOOGLE_API_KEY = ABSENT
```

The preserved work order requires all of the following before execution:

1. exact TB2 task tree;
2. complete 34,198-skill pool or source-equivalent release;
3. P1 retrieval for the same TB2 tasks;
4. common model identity;
5. common harness identity;
6. Docker/Harbor-compatible sandbox;
7. R0/R1 recovery path in the same harness;
8. one supported model backend/credential.

Several hard prerequisites are absent. Therefore no scientific run was started.

## Classification

```text
SCB_R2_PR = UNTESTED_RESOURCE_TRANSPORT
```

This is not negative evidence for procedural guidance, AgentRewind, P×R interaction, or SCB localization.

No verdict is produced for:

```text
SCB_P_R_EXTERNAL_LOCALIZATION
```

No substitute task tree, synthetic recovery layer, alternate benchmark, local toy agent, provider, or inferred retrieval output was used.

## One-shot discipline

- preflight/resource inspection: completed once;
- scientific execution attempts: `0`;
- Terminal-Bench trials: `0`;
- retries: `0`;
- GitHub Actions scientific runs: `0`.

A future SCB-R2 execution requires a new explicit work order after the missing mounts/runtime/backend are materially available.

## External queue state

The external handoff queue is now exhausted except for blocked dependencies:

- MF-R1 / LongMemEval-V2 — parked transport/resource dependency;
- TCV-R2 — parked official-artifact transport dependency;
- MF-R3 / SkillsBench — parked Docker/provider dependency;
- SCB-R2 — parked mounts/runtime/provider dependency;
- TANGLE — paper exists, but no author-linked public benchmark/code release was resolved in this preflight; keep `WAIT_OFFICIAL_RELEASE`.

The TANGLE paper remains directly relevant to LOGOS conflict-preserving memory, but publication alone is not an executable external artifact.

## Queue advancement

With the current external queue blocked, the next canonical research session activates the already-existing queued work order:

`PERSISTENT-STATE-CAUSALITY-PREFLIGHT-R1`

This track compares:

```text
TOKEN_CONTEXT
RECURRENT_LATENT
FAST_WEIGHT_STATE
EXTERNAL_RETRIEVAL
```

under matched information/compute/parameter accounting and requires separate `D(S)`, `O(S)`, and `C(S)` evidence plus state-swap/corruption controls.

The next session is a **preflight/freeze**, not automatic mechanism promotion. It must resolve source implementations, a common task substrate, equalization rules and causal interventions before any execution.

## Boundaries

Unchanged:

```text
StateEffect != MechanismIdentity
Capability != Authority
AdaptiveState != Authority
AgentMemory != AssuranceState
FunctionalStateEvidence != PhenomenalConsciousness
```

`Γ-v0.3` remains `HOLD`.
