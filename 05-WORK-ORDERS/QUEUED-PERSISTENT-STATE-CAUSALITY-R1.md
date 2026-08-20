# QUEUED WORK ORDER — Persistent-State Causality R1

**Status:** QUEUED / DOES_NOT_REPLACE_CURRENT_WMR_WORK_ORDER  
**Authority:** A0  
**Track:** persistent state / memory / latent computation / metacognitive readout  
**Scientific ceiling:** bounded mechanism evidence only

## Why this exists

Recent prior art adds two important comparison dimensions for LOGOS-1:

1. persistent history can be represented through token context, recurrent latent state, fast-weight test-time memory, or external retrieval;
2. an internal state may be decodable without being operationally useful or causally necessary.

The active canonical scientific queue remains WMR / ARC-AGI-3. This work order is queued for later execution and must not silently replace `CURRENT-WORK-ORDER.md`.

## Primary question

> Under matched information, compute and parameter budgets, which history representation provides the best retention/adaptation trade-off, and which internal states can be shown to causally control later behavior rather than merely correlate with it?

## Primary memory arms

1. `TOKEN_CONTEXT`
2. `RECURRENT_LATENT`
3. `FAST_WEIGHT_STATE`
4. `EXTERNAL_RETRIEVAL`

## Required equalization contract

The comparison must document and, where technically possible, match:

- information presented;
- number of demonstrations / history events;
- total parameter budget;
- total update / recurrent compute budget;
- query count;
- retrieval or state-read bandwidth;
- output decoder capacity.

Where exact matching is impossible, the mismatch must be reported and a normalized resource curve must be produced instead of claiming a single-arm victory.

## Primary metrics

- `Accuracy`
- `Retention`
- `Interference`
- `AdaptationLatency`
- `StateCapacity`
- `PathDependence`
- `ComputePerQuery`
- `PeakMemory`
- `CorruptionSensitivity`
- `CorruptionRecovery`
- `CausalStateUtility`

Optional where applicable:

- recurrent convergence;
- fixed-point behavior;
- sensitivity to initial state;
- energy estimate / hardware-normalized cost.

## Mandatory state-validation ladder

For each proposed functional state `S`, measure separately:

```text
D(S) = Decodability
O(S) = Operational utility
C(S) = Causal intervention effect
```

Verdict classes:

- `READABLE_ONLY`
- `OPERATIONAL_NONCAUSAL_OR_UNPROVEN`
- `CAUSALLY_SUPPORTED`
- `REJECT`
- `UNTESTED`

A mechanism claim may not be promoted solely because a probe can decode `S`.

## State-swap intervention

Minimum causal intervention:

```text
same query q
history A -> state M_A
history B -> state M_B
swap M_A <-> M_B
```

Required observation:

- whether outputs move toward the swapped history;
- effect size;
- reversibility;
- dependence on layer / state subset;
- negative control with random or matched-energy state perturbation.

If state swapping cannot be implemented for an arm, document the reason and use the strongest available targeted intervention without treating it as equivalent.

## Hidden-state leakage controls

Any correctness / metacognition probe must use leakage-resistant splits.

Minimum:

- question-grouped evaluation;
- held-out task/domain where feasible;
- shuffled-label control;
- identity-feature audit;
- probe capacity control.

Compare:

```text
c_verbal
c_hidden
c_behavioral
```

and report calibration error / ranking utility separately.

## Grounded-vs-hypothetical state test

Candidate state typing:

```text
O_t = observed / grounded
B_t = believed / inferred
H_t = hypothetical / counterfactual
E_t = epistemic uncertainty / information demand
```

Test whether hypothetical transitions can contaminate grounded episodic/semantic memory.

Required conditions:

1. `REAL_ONLY`
2. `IMAGINED_TRAINING`
3. `IMAGINED_SEARCH_REAL_TRAINING`

Then deliberately corrupt the world model and measure:

- policy drift;
- model-bias propagation;
- recovery after real contradictory evidence;
- false-memory / false-grounding rate;
- real-world or benchmark performance.

Candidate rule under test:

```text
ImaginedTransition != ObservedTransition
H_t -/-> O_t without validation
```

Do not promote this to a canonical Atomic Rule until the falsifier is passed.

## Epistemic-drive comparison

Compare:

1. fixed exploration bonus;
2. dynamic information requirement `I_min = f(goal, uncertainty, risk)`.

Measure:

- information gain;
- redundant queries;
- exploration cost;
- task success;
- unsafe or premature action under uncertainty.

This experiment must remain proposal-side. Information demand does not mint execution authority.

## Recurrent-depth control

Where the recurrent-latent arm supports repeated compute, compare:

```text
DenseDepth
vs
RecurrentDepth
vs
PersistentLatentRecurrence
```

under iso-parameter and iso-FLOP curves where feasible.

Measure performance against recurrence count `R`, state convergence and initial-state sensitivity.

## Negative controls

At minimum:

- random state swap;
- same-history no-swap;
- state permutation preserving norm/statistics;
- retrieval with distractor-matched corpus;
- fast-weight reset;
- recurrent-state reset;
- token-context truncation;
- shuffled probe labels;
- corrupted world-model control.

## Consciousness boundary

This work order may produce evidence for functional memory, monitoring, internal access or causal computation.

It must not infer phenomenal consciousness, sentience or welfare relevance from:

- persistence;
- decodability;
- self-report;
- correctness prediction;
- recurrent convergence;
- global accessibility;
- causal effect alone.

P7 remains unchanged unless a separate consciousness-specific evidence framework produces a discriminating result.

## Completion criteria

1. preregistered hypotheses and falsifiers;
2. frozen datasets/tasks and seeds;
3. matched-budget table;
4. negative controls;
5. state-swap or strongest equivalent causal intervention;
6. leakage-resistant probe evaluation;
7. grounded-vs-hypothetical contamination test;
8. full result table with uncertainty;
9. explicit evidence ceiling;
10. session report and durable raw evidence;
11. no change to `CURRENT-WORK-ORDER.md` unless the canonical queue is intentionally advanced.

## Highest-information first experiment

If only one experiment is affordable, run the four-arm memory comparison with a state-swap intervention and corruption/recovery phase. It directly tests both persistent-state usefulness and causal dependence while exposing interference and robustness trade-offs.