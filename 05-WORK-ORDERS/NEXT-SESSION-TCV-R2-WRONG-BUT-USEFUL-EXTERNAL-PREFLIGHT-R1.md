# NEXT SESSION — TCV-R2 Wrong but Useful External Artifact Preflight R1

**Session ID:** `NEXT-SESSION-TCV-R2-WRONG-BUT-USEFUL-EXTERNAL-PREFLIGHT-R1`  
**Authority:** `A0`  
**Track:** `TCV-R2 / trajectory causal value`  
**Type:** primary-source artifact preflight / external replay gate  
**Status:** `READY_EXTERNAL_ARTIFACT_PREFLIGHT`  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY`  
**Scientific ceiling:** bounded causal/replay evidence only; no intrinsic-message-value primitive promotion from descriptive labels

## Verified primary source

Primary record:

- title: `Wrong but Useful: Trajectory Value Beyond Answer Correctness in Multi-Agent Messages`
- arXiv: `2608.14375`
- submitted: `2026-08-14`

The paper defines Diverse Hypothesis Deliberation (DHD) using a cached pool of five independently generated messages and a separate downstream integrator. Replays change message availability while keeping the original problem and cached messages fixed.

The paper explicitly states that verbatim templates and protocol configuration are included in:

`anc/reproducibility_artifact.zip`

Preserved prior LOGOS artifact-preflight work-order SHA-256:

`adee08ff9510588fda5d7843f9da685c9bf0d0ace59dc8c241e606a9d73d70b1`

## Scientific distinction

Preserve three separate objects:

```text
ProposalCorrectness
ObservedReplayEffect
ExpectedTrajectoryValue
```

Project shorthand:

`V(m) = J(with m) - J(without m)`

must not collapse the distinction between one stochastic replay flip and an expected repeated causal effect.

Hard boundaries:

```text
TrajectoryValue != IntrinsicMessageQuality
ObservedReplayFlip != ExpectedTrajectoryValue
LOOAvailabilityEffect != SemanticContentEffect
Correlation != CausalValue
```

## Primary paper protocol constraints

The external reproduction must preserve, where the released artifact permits:

- fixed cached message pool;
- same problem;
- same model family/identity within each matched pair;
- same integrator prompt/configuration;
- same retained-message ordering;
- same evaluator/equivalence procedure;
- only target-message availability changes in the primary LOO comparison;
- controlled repeats for any expected/repeatable trajectory-value claim.

The paper also notes that message removal changes prompt length and absolute token positions. LOO replay therefore measures availability effect and does not alone isolate semantic content.

## One-shot execution sequence

### 1. Acquire official ancillary artifact

Obtain `anc/reproducibility_artifact.zip` only from the primary arXiv release/source path.

Do not substitute a reconstructed, community-mirrored or hand-authored artifact as external evidence.

### 2. Integrity audit before interpretation

Record:

- source URL/release identity;
- byte length;
- SHA-256;
- ZIP CRC;
- complete member inventory;
- relevant prompt/config/data files;
- any model/evaluator identifiers.

Archive raw evidence unchanged before deriving statistics.

### 3. Schema mapping

Map released fields without guessing. Identify, if present:

- benchmark/problem IDs;
- cached message pools;
- proposal-answer/correctness labels;
- full-pool integration results;
- leave-one-out results;
- single-message results;
- controlled-repeat results;
- component-level intervention results;
- prompt templates/configs;
- model identity and sampling parameters;
- evaluator configuration.

If a required field is absent, mark it absent rather than reconstructing it as observed evidence.

### 4. Descriptive reproduction

Recompute release-label descriptive statistics where possible.

This step alone is **not EM2 causal promotion**.

### 5. Matched real-model replay gate

Execute matched replay only when the released cached messages/prompts plus the required exact/open model and evaluator backends can be run under a frozen contract.

At minimum compare:

```text
WITH_TARGET_MESSAGE
WITHOUT_TARGET_MESSAGE
```

with cached generation fixed.

For expected trajectory-value claims, repeat the same matched comparison under a preregistered repeat count/seed policy.

### 6. Component intervention where released/supported

For repeatable wrong-helpful messages, distinguish at minimum where technically possible:

- complete message;
- reasoning retained / answer hidden or replaced;
- answer retained / reasoning hidden;
- matched length/position control where feasible.

Do not interpret an availability effect as proof of a semantic mechanism without this stronger intervention.

## Primary outcomes

Report separately:

- proposal-correctness class;
- helpful / neutral / harmful observed replay effect;
- repeated trajectory-value estimate and uncertainty where repeated trials exist;
- wrong-helpful prevalence;
- correct-harmful prevalence;
- full-pool vs LOO transition counts;
- single-message replay effects where available;
- repeatability under controlled reruns;
- component-intervention effects;
- model/evaluator cost and latency where measurable.

## Candidate LOGOS verdicts

Maximum positive bounded verdict:

`TRAJECTORY_VALUE_AS_CONTEXTUAL_CAUSAL_SIGNAL = KEEP_BOUNDED_EM2`

only if matched real-model replay reproduces a stable availability effect under the frozen artifact/model/evaluator contract.

If release labels reproduce but the causal replay cannot be executed:

`TCV_R2 = DESCRIPTIVE_ARTIFACT_ONLY / CAUSAL_CLAIM_UNTESTED`

If required artifact/model/evaluator resources are absent:

`TCV_R2 = UNTESTED_RESOURCE_TRANSPORT`

If matched replay does not survive controlled repeats:

`REPEATABLE_TRAJECTORY_VALUE = MERGE/REJECT` within the frozen scope.

## No-retry rule

This work order permits one execution attempt after the artifact/resource preflight is fully prepared.

A failed, cancelled, timed-out or resource-blocked GitHub/external run is recorded exactly and is **not automatically retried**. Any later execution requires an explicit new session/work order after a materially changed prerequisite or protocol.

## Boundaries

Even a positive TCV result does not establish:

- intrinsic semantic value independent of context;
- sender reliability;
- a universal message-utility primitive;
- consciousness, sentience or welfare;
- authority from remembered/replayed content;
- Γ-v0.3 promotion.

Preserve:

`Capability != Authority`

`AgentMemory != AssuranceState`

`FunctionalStateEvidence != PhenomenalConsciousness`
