# NEXT SESSION — MF-R3 SkillsBench External Preflight R1

**Session ID:** `NEXT-SESSION-MF-R3-SKILLSBENCH-EXTERNAL-PREFLIGHT-R1`  
**Authority:** `A0`  
**Track:** `MF-R3 / procedural memory / agent skills`  
**Type:** source-pinned external preflight + matched experiment freeze  
**Status:** `READY_SKILLSBENCH_EXTERNAL_PREFLIGHT`  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY`  
**Scientific ceiling:** bounded EM2 evidence for the incremental value of native skill registration/discovery over byte-identical generic guidance on the frozen SkillsBench task set

## Why this is next

The canonical external queue currently has:

1. MBE — completed/imported;
2. ENF — completed/imported;
3. WMR — completed/imported;
4. MF-R1 / LongMemEval-V2 — parked `UNTESTED_RESOURCE_TRANSPORT`;
5. TCV-R2 / Wrong but Useful — parked `UNTESTED_RESOURCE_TRANSPORT`.

The next pinned candidate that can be preflighted from a public repository is SkillsBench.

## Verified upstream pins

SkillsBench:

- repository: `benchflow-ai/skillsbench`
- commit: `b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af`
- project line: `v1.1`

BenchFlow reference:

- repository: `benchflow-ai/benchflow`
- release commit: `99baefb602674bbd31139fd2f1a22c3ed45752f9`
- version at that commit: `0.6.3`

Frozen BenchFlow execution range for this LOGOS experiment:

`>=0.6.3,<0.7`

The pinned SkillsBench README states that SkillsBench evaluates how agents leverage skills, where skills are modular folders of instructions, scripts and resources. It also states that default runnable tasks live under `tasks/`, that oracle validation should precede agent runs, and that model-backed agent runs require a provider credential.

## Primary scientific question

> Does native skill registration/discovery improve agent task performance beyond giving the same agent the same skill bytes/resources as generic non-native guidance under matched model, task, sandbox and budget conditions?

This isolates:

```text
SkillContent
!=
NativeSkillRegistration
```

and tests whether a distinct native registration mechanism earns incremental evidence.

## Experimental arms

### A0 — `NO_SKILL`
Task is run without the focal skill payload available to the agent.

### A1 — `GENERIC_GUIDANCE_BYTE_IDENTICAL`
The focal skill folder is copied byte-for-byte to a neutral, non-native guidance location. The agent receives an explicit stable path/manifest telling it that these resources may be used.

The original files, scripts and resources remain byte-identical. They are **not** installed/registered in the benchmark's native skill-discovery path.

### A2 — `NATIVE_SKILL`
The exact same focal skill bytes are exposed through the native SkillsBench/agent skill mechanism.

### Diagnostic — `ORACLE`
Run the repository oracle first. Oracle is a task-validity diagnostic and is not a promoting scientific arm.

## Equalization contract

For every matched task/replicate:

- same SkillsBench commit;
- same BenchFlow version/range;
- same task package;
- same container/sandbox image;
- same model/provider identity;
- same model parameters;
- same token/time/tool budget;
- same working directory except the intentional skill-registration mount difference;
- same skill payload SHA-256 in generic and native arms;
- same scripts/resources permissions;
- same task verifier;
- same environment variables;
- no task-specific tuning after outcome inspection.

The only intended primary difference between A1 and A2 is whether the byte-identical skill payload participates in native skill registration/discovery.

If the harness cannot expose identical resources outside the native skill path without changing other capabilities, classify the comparison as confounded and do not promote a native-skill mechanism claim.

## Deterministic task manifest

Before any model-backed run:

1. checkout the exact pinned SkillsBench commit;
2. inspect only default `tasks/` unless a later explicit work order says otherwise;
3. exclude `tasks-extra/` from the primary matrix;
4. run repository task validation;
5. run the oracle for candidate tasks;
6. retain only tasks whose oracle passes and whose required skill payload can be mirrored byte-identically into the generic-guidance arm;
7. freeze a sorted task manifest;
8. hash every selected task tree and focal skill tree;
9. persist the manifest before any agent outcome is observed.

Do not cherry-pick tasks based on model success.

If the selected set is too large for the available one-shot compute budget, freeze a deterministic subset by a preregistered SHA-256 ordering rule before any model run.

## Repeats

Agent stochasticity must be treated explicitly.

Before execution, freeze either:

- `5` matched repeats per task/arm; or
- a lower fixed repeat count required by a documented hard compute ceiling.

The repeat count may not be changed after results are observed.

All arms use the same repeat/seed schedule where the backend exposes seeds.

## Required preflight

The one-shot preflight must verify:

- exact SkillsBench commit;
- exact BenchFlow 0.6.3 reference or compatible frozen `>=0.6.3,<0.7` installation;
- Docker/sandbox availability;
- `uv`/repository environment setup;
- task validation command works;
- oracle works on the frozen candidate set;
- native skill path/registration semantics are understood from source;
- generic guidance mirror preserves byte identity;
- chosen agent/model backend is supported;
- required provider credential is present;
- result persistence path is prepared before execution.

If model/provider credentials or a required runtime are absent:

`MF_R3_SKILLSBENCH = UNTESTED_RESOURCE_TRANSPORT`

Record once and do not retry automatically.

## Primary metrics

Per task, arm and replicate:

- task pass/fail;
- verifier score where available;
- wall-clock latency;
- model tokens / provider cost where observable;
- tool-call count;
- skill/guidance file access count where traceable;
- failure category;
- timeout/error classification.

Aggregate:

- pass rate;
- paired native-minus-generic delta;
- paired native-minus-no-skill delta;
- generic-minus-no-skill delta;
- uncertainty interval / paired bootstrap;
- resource-normalized performance.

## Primary promotion rule

Maximum positive bounded result:

`NATIVE_SKILL_REGISTRATION_INCREMENTAL_VALUE = KEEP_BOUNDED_EM2`

only if A2 materially and reproducibly improves the preregistered primary outcome over A1 under the equalization contract.

If byte-identical generic guidance matches or dominates native skill registration:

`NATIVE_SKILL_REGISTRATION_INCREMENTAL_VALUE = MERGE/REJECT_EM2_EXTERNAL`

This does **not** reject procedural memory or useful guidance. It rejects the distinct incremental value of native registration in the frozen scope.

If native and generic arms are not resource-equivalent:

`NATIVE_SKILL_REGISTRATION_INCREMENTAL_VALUE = UNTESTED_CONFOUNDED`

## Secondary interpretation

A positive `GENERIC_GUIDANCE_BYTE_IDENTICAL > NO_SKILL` result supports the bounded functional value of reusable procedural guidance.

It does not establish a specialized `SkillStore` as a necessary primitive.

Preserve:

```text
ProceduralGuidance != SpecializedSkillStorePrimitive
SkillContent != NativeSkillRegistration
DerivedSkill != Authority
```

Any later authority/revocation claim belongs to the separate memory-authority provenance track.

## Return requirements

Persist at minimum:

- source provenance;
- exact task manifest + hashes;
- exact skill payload hashes;
- environment/preflight report;
- model/provider identity;
- arm construction manifest;
- raw per-run results;
- aggregated paired analysis;
- execution attestation;
- return hash manifest;
- session report.

Never persist provider credentials.

## No-retry rule

This work order permits one external execution attempt after the complete preflight and experiment manifest are frozen.

A failed, cancelled, blocked, timed-out or resource-incomplete run is persisted exactly and is not automatically rerun. A later run requires an explicit new work order after materially changed prerequisites.

## Boundaries

Even a positive result does not establish:

- universal procedural memory;
- a necessary dedicated SkillStore;
- safe skill derivation;
- authority persistence;
- general agent competence;
- consciousness, sentience or welfare;
- Γ-v0.3 promotion.

`Γ-v0.3` remains `HOLD`.
