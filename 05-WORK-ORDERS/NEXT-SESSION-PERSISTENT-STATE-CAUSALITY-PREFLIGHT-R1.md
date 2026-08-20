# NEXT SESSION — Persistent-State Causality Preflight R1

**Session ID:** `NEXT-SESSION-PERSISTENT-STATE-CAUSALITY-PREFLIGHT-R1`  
**Authority:** `A0`  
**Track:** persistent state / memory / latent computation  
**Type:** source-adapter resolution + matched-experiment preregistration  
**Status:** `READY_PERSISTENT_STATE_CAUSALITY_PREFLIGHT`  
**Execution policy:** `ONE_SHOT_NO_AUTORETRY` for any later external run  
**Scientific ceiling:** bounded functional/causal mechanism evidence only

## Why this is now canonical

The source-pinned external handoff queue has reached resource/release blockers for LongMemEval-V2, TCV-R2, SkillsBench, SCB-R2 and TANGLE. The already-queued Persistent-State Causality work therefore becomes the next research track to make execution-ready.

This work order supersedes the old queue-position note in `QUEUED-PERSISTENT-STATE-CAUSALITY-R1.md`; it does not erase that file's historical preregistration content.

## Primary question

> Under matched information and resource accounting, which representation of history provides useful persistent state, and which resulting states can be shown to causally control later behavior rather than merely be decodable?

## Frozen comparison classes

The preflight must preserve four classes:

```text
TOKEN_CONTEXT
RECURRENT_LATENT
FAST_WEIGHT_STATE
EXTERNAL_RETRIEVAL
```

Current primary-source anchors include:

- recurrent latent / associative-state family: official Pathway `pathwaycom/bdh` implementation and BDH/BDH-CQ public material;
- fast-weight family: MoNe, arXiv `2608.17616`;
- token context: frozen-transformer ICL baseline matched to the selected backbone/task;
- external retrieval: source-visible retrieval baseline that does not silently alter the backbone or authority layer.

A paper or repository is not automatically an eligible arm. The next session must resolve exact commits/releases and prove that the selected implementations can participate in a fair common experiment.

## Preflight outputs required before any run

### 1. Source-adapter table

For each arm record:

- paper/repository;
- exact commit/release;
- license;
- model/backbone requirements;
- training requirement;
- state object exposed for intervention;
- inference/update API;
- hardware/runtime requirements;
- whether state reset/swap/corruption is technically possible.

If an arm lacks a reproducible implementation or manipulable state, mark it `SOURCE_ADAPTER_UNRESOLVED`; do not replace it with an unrelated toy mechanism and call the four-way comparison complete.

### 2. Common task substrate

Choose a public task family that supports repeated history/query episodes and does not privilege one memory representation by construction.

The chosen substrate must expose enough structure to measure:

- retention;
- interference;
- adaptation latency;
- path dependence;
- corruption/recovery;
- query compute;
- causal state use.

Freeze task IDs/splits before outcomes.

### 3. Equalization contract

Document either exact matching or resource curves for:

- information presented;
- history events/examples;
- backbone parameter count;
- additional memory parameters;
- total update/recurrent FLOPs;
- query count;
- state/retrieval bandwidth;
- decoder capacity;
- wall time / peak memory.

If exact equality is impossible, report normalized curves. Do not declare a single-arm victory from unmatched compute.

### 4. Mandatory state-validation ladder

For each candidate state `S`:

```text
D(S) = decodability
O(S) = operational predictive utility
C(S) = causal intervention effect
```

Allowed verdicts:

- `READABLE_ONLY`
- `OPERATIONAL_NONCAUSAL_OR_UNPROVEN`
- `CAUSALLY_SUPPORTED`
- `REJECT`
- `UNTESTED`

`D(S)` alone never licenses a mechanism claim.

### 5. Causal interventions

Where technically possible, preregister:

```text
history A -> M_A
history B -> M_B
same query q
swap M_A <-> M_B
```

Measure output shift toward swapped history, reversibility, effect size and layer/state-subset dependence.

Negative controls:

- same-history no swap;
- random-state swap;
- norm/statistics-preserving permutation;
- fast-weight reset;
- recurrent-state reset;
- external-retrieval distractor corpus;
- token-context truncation.

### 6. Corruption and recovery

For all eligible arms, inject matched corruption into state/history/retrieval inputs and measure:

- corruption sensitivity;
- recovery latency;
- false-memory / false-grounding rate;
- performance after contradictory grounded evidence.

## Grounded-state typing

Preserve the candidate distinction:

```text
O_t = observed / grounded
B_t = believed / inferred
H_t = hypothetical / counterfactual
E_t = epistemic uncertainty / information demand
```

Candidate boundary under test:

```text
ImaginedTransition != ObservedTransition
H_t -/-> O_t without validation
```

This is not promoted to an Atomic Rule solely by specification.

## Primary metrics

- Accuracy
- Retention
- Interference
- AdaptationLatency
- StateCapacity
- PathDependence
- ComputePerQuery
- PeakMemory
- CorruptionSensitivity
- CorruptionRecovery
- CausalStateUtility

Optional where compatible:

- recurrence convergence;
- fixed-point behavior;
- initial-state sensitivity;
- hardware-normalized energy/cost.

## Promotion boundary

A persistent-state mechanism can at most receive bounded support within the frozen substrate if:

1. it adds operational value under matched/resource-normalized comparison;
2. targeted intervention produces the predicted downstream shift;
3. the effect survives negative controls;
4. corruption/recovery behavior is reported;
5. leakage/task-identity confounds are excluded.

No arm may be promoted because it is biologically inspired, novel, parameter-efficient, or easy to probe.

## Authority and consciousness boundaries

Persistent/adaptive memory remains proposal-side.

```text
PersistentState != Authority
MemoryTruth != MemoryAuthority
CausalState != PhenomenalConsciousness
```

No state swap, recurrent attractor, fast-weight update, global access, correctness signal or self-report licenses a sentience/consciousness claim.

`Γ-v0.3` remains `HOLD`.

## Completion criteria for this preflight

1. exact source-adapter table;
2. common task substrate and frozen split;
3. resource/equalization table;
4. state-access/intervention feasibility table;
5. preregistered negative controls;
6. corruption/recovery protocol;
7. D/O/C analysis plan;
8. complete resource gate before any later run;
9. no synthetic substitute promoted as the four-way external result;
10. one durable session checkpoint and one coherent repo commit.
