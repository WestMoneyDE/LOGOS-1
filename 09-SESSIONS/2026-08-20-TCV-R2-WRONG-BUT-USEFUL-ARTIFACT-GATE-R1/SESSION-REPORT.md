# Session Report — TCV-R2 Wrong but Useful Artifact Transport Gate R1

**Date:** 2026-08-20  
**Authority:** A0  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY`  
**TCV classification:** `UNTESTED_RESOURCE_TRANSPORT`  
**Scientific verdict:** `UNTESTED`

## Objective

Execute the canonical TCV-R2 external artifact preflight against the primary `Wrong but Useful` release without reconstructing missing data, substituting artifacts, or retrying a failed transport path.

## Primary-source verification

Primary record:

- title: `Wrong but Useful: Trajectory Value Beyond Answer Correctness in Multi-Agent Messages`
- arXiv: `2608.14375`
- version: `v1`
- submitted: `2026-08-14`

The paper defines DHD around a fixed cached message pool and matched downstream replay. It distinguishes:

```text
ProposalCorrectness
ObservedReplayEffect
ExpectedTrajectoryValue
```

The paper also states that verbatim prompt templates and protocol configuration are included in its ancillary reproducibility artifact.

The primary arXiv release currently exposes that ancillary material as an expanded directory under:

`anonymous_reproducibility/`

The release page visibly lists, among other members:

- `ARTIFACT_MANIFEST.json`
- `SHA256SUMS`
- `README.md`
- `REPRODUCE.md`
- `ENVIRONMENT.md`
- paper/smoke configs
- derived analysis tables
- a smoke-pool fixture
- analysis/reproduction scripts

This confirms that a real author-supplied reproducibility artifact exists. It does not by itself establish integrity of any member until the bytes are acquired and hashed.

## One-shot transport attempt

The connected execution environment attempted to acquire the exact primary-source member:

`anonymous_reproducibility/ARTIFACT_MANIFEST.json`

from the arXiv v1 ancillary source path.

The byte transport failed in the connected download layer.

Per the project/user rule:

- no second download attempt was made;
- no alternate mirror was substituted;
- no reconstructed manifest was created;
- no community copy was treated as official evidence;
- no model replay was started.

Therefore the required SHA-256 / CRC / complete member audit could not be completed.

## Classification

`TCV_R2 = UNTESTED_RESOURCE_TRANSPORT`

This is a transport classification, **not negative scientific evidence** for trajectory value.

No LOGOS causal verdict is changed.

In particular, this session does not establish or reject:

- repeatable trajectory value;
- wrong-helpful causal prevalence;
- semantic-content mechanism;
- an intrinsic message-value primitive.

## Scientific boundaries retained

```text
TrajectoryValue != IntrinsicMessageQuality
ObservedReplayFlip != ExpectedTrajectoryValue
LOOAvailabilityEffect != SemanticContentEffect
Correlation != CausalValue
```

A future TCV rerun requires a new explicit work order after the official ancillary bytes become transportable or are provided directly. It must not silently use a mirror or reconstruction.

## Queue advancement

The next runnable pinned external-evidence candidate is:

`MF-R3 / SkillsBench native skill vs byte-identical generic guidance`

The source pin is verified at:

`benchflow-ai/skillsbench@b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af`

The pinned SkillsBench README describes skills as modular folders of instructions, scripts and resources and uses BenchFlow 0.6.x. LOGOS will isolate the incremental effect of **native skill registration/discovery** from the informational content of the skill itself.

Next canonical work order:

`NEXT-SESSION-MF-R3-SKILLSBENCH-EXTERNAL-PREFLIGHT-R1`

## Boundaries

Unchanged:

- `AdaptiveState != Authority`
- `AgentMemory != AssuranceState`
- `OUTCOME_UNKNOWN != NOT_EXECUTED`
- Γ-v0.3 remains `HOLD`
- no consciousness/sentience/welfare inference
