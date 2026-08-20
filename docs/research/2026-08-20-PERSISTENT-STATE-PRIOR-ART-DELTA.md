# Research Delta — Persistent State, Internal Readout, World Models

**Date:** 2026-08-20  
**Status:** verified prior-art update / no automatic mechanism promotion  
**Scope:** memory, latent state, metacognition, world models, epistemic exploration, governed execution

## Source verification

Primary-source verification was performed against the corresponding arXiv records.

### Verified papers

1. **MoNe: Modular Neural Memory for Efficient Long Context Inference** — arXiv:2608.17616, submitted 2026-08-18.
2. **Beyond the Trace: Coupling an Interpretable Reasoning-State Readout to Native MoE Routing** — arXiv:2608.17638, submitted 2026-08-18.
3. **A decodability criterion predicts when hidden-state selection beats majority voting in large language models** — arXiv:2608.17124, submitted 2026-08-17.
4. **Runtime Governance for Agentic AI: Action-Boundary Control with Trusted Provenance and Fail-Closed Execution** — arXiv:2608.16891, submitted 2026-05-17. This is relevant prior art for current LOGOS authority separation, but it is not a paper first appearing on 2026-08-19.
5. **Q-Learning With World Models** — arXiv:2608.17163, submitted 2026-08-17.
6. **Expected free energy as an information constraint on the Bethe Lagrangian** — arXiv:2608.17167, submitted 2026-08-17.
7. **RecurrentGPT: Expressive Depth through Recurrent Modulation in Transformers** — arXiv:2608.15062, submitted 2026-08-15.
8. **BDH-CQ: In-Context Learning with Recurrent Latent Reasoning** — arXiv:2608.09888, submitted 2026-08-10.

## 1. MoNe changes the memory-comparison baseline

MoNe attaches a lightweight neural memory to a frozen Transformer. Context is processed segment-wise and the fast-weight memory is updated at test time using localized gradient updates. At query time the original context tokens need not be replayed.

The authors report:

- O(N) context preprocessing with O(1) query cost with respect to context length;
- about 80% lower compute and peak GPU memory than ordinary in-context learning at 128K tokens;
- 6.4% parameter overhead;
- operation beyond the native context window on the reported long-context tests.

### LOGOS implication

The persistent-state comparison should no longer be framed only as recurrent state versus external retrieval.

Minimum comparison set:

```text
Static / Token Context
vs
Recurrent Latent State
vs
Fast-Weight State
vs
External Retrieval
```

Common abstraction:

```text
M_(t+1) = Update(M_t, o_t)
y_t     = Decode(q_t, M_t)
```

The mechanisms differ materially even if all compress history into a reusable state.

### Required causal test

State swap:

```text
M_A <-> M_B
```

under the same query. A systematic output shift toward the swapped history is stronger evidence of operational memory use than retention accuracy alone.

## 2. Internal-state claims need a three-level validation ladder

Beyond the Trace reports three increasingly strong forms of evidence for MoE internal reasoning state:

1. an interpretable internal readout is decodable;
2. it adds predictive utility beyond visible trace features and can guide test-time branch/stop decisions;
3. targeted router edits produce predicted behavioral shifts.

This motivates a stricter LOGOS distinction:

```text
DecodableState != OperationalState != CausalState
```

For any proposed state S:

```text
D(S) = decodability
O(S) = operational predictive / selection utility
C(S) = intervention-caused behavioral change
```

A strong mechanism claim should preferably survive C(S), not only D(S).

## 3. CASE strengthens leakage controls for metacognitive probes

CASE uses answer-token hidden state to select among sampled candidates. The paper shows that conventional probe performance can be inflated by question-identity leakage and uses grouped evaluation to remove this shortcut.

Reported held-out relationship:

```text
Decodability -> selection gain over majority vote
Pearson r = 0.75
```

The authors report gains of up to 19 percentage points on medium-difficulty questions and 16.8 points on hard questions in their evaluated settings.

### LOGOS implication

```text
VerbalConfidence != LatentErrorSignal
LatentErrorSignal != UniversalMetacognition
```

Any hidden-state correctness probe should use question-grouped or comparably leakage-resistant splits.

## 4. Aegis is relevant prior art for the authority boundary

Aegis treats model outputs as proposals and places a trusted runtime in the execution path. The reported sandbox evaluation contains 6,300 total rows; among 2,100 Aegis-governed rows the authors report zero governed risky side-effect completions.

The paper explicitly limits the conclusion to the evaluated sandbox and does not claim general agent safety.

### LOGOS implication

This strengthens prior art for the existing invariant:

```text
ModelProposal != ExecutionAuthority
Capability != Authority
```

It does not by itself promote Gamma or establish general mediation closure.

## 5. QWM sharpens the world-model epistemic boundary

QWM uses a world model for test-time search over imagined trajectories while training policy/value only on real transitions.

### LOGOS implication

The architecture should distinguish imagined search from grounded learning:

```text
ImaginedTransition != ObservedTransition
```

Candidate epistemic typing:

```text
S_t = (O_t, B_t, H_t, E_t)

O_t = observed / grounded state
B_t = believed / inferred state
H_t = hypothetical / counterfactual state
E_t = uncertainty / information demand
```

Candidate hard boundary for future testing:

```text
H_t -/-> O_t
```

without explicit validation or grounded evidence.

This is not yet promoted to a canonical Atomic Rule; it is a testable architecture candidate.

## 6. Information-constrained active inference suggests conditional exploration

The constrained Bethe formulation casts epistemic drive as an information constraint rather than only a fixed exploration bonus. The solved multiplier can be inactive, interior or saturated depending on information demand.

Candidate LOGOS principle:

```text
SeekInformation iff CurrentInformation < TaskRequiredInformation
```

This is a research hypothesis, not a canonical rule.

Future comparison:

```text
fixed exploration bonus
vs
risk/goal/uncertainty-conditioned information requirement
```

Metrics should include task success, information gain, redundant queries, exploration cost and unsafe action under uncertainty.

## 7. RecurrentGPT strengthens iterative latent compute as a separate axis

RecurrentGPT reuses a shared Transformer core across recurrent depth with gated modulation. The reported experiments show that recurrent computation can exchange architectural depth / parameter count for iterative compute.

### LOGOS implication

```text
ComputationalDepth != ArchitecturalDepth
```

This is adjacent support for the broader BDH-relevant hypothesis that reasoning capacity can arise from iterative latent computation, but it is not a BDH-CQ replication and does not demonstrate persistent lifelong state across tasks.

## Consolidated architecture delta

The strongest current abstraction is:

```text
Persistent / Iterative State
        -> World Simulation
        -> Information Need
        -> Proposal
        -> Gamma / Governance
        -> Action
        -> Real Observation
```

Two distinctions should be treated as mandatory evaluation axes going forward:

```text
TokenContext vs RecurrentLatent vs FastWeights vs ExternalRetrieval
```

and

```text
Readable -> Operational -> Causally Validated
```

## Metrics for the next cross-architecture memory study

- accuracy;
- retention;
- interference;
- path dependence;
- state capacity;
- adaptation latency;
- compute per query;
- peak memory;
- corruption sensitivity;
- corruption recovery;
- state convergence / fixed-point behavior where applicable;
- causal state utility.

## Consciousness / P7 boundary

None of the verified papers supplies evidence sufficient to move the LOGOS phenomenal-consciousness boundary.

The following implication remains invalid:

```text
PersistentLatentState
+ InternalCorrectnessSignal
+ CausalReasoningState
+ GlobalAccess
=> PhenomenalConsciousness
```

Functional internal-state evidence can support claims about memory, monitoring, routing, prediction or causal computation. It does not establish phenomenal experience.

## Evidence assessment

These are recent preprints. Several contain technically meaningful ablations, leakage controls, benchmark results or interventions, but independent reproduction is currently absent or limited. Therefore this document changes comparison baselines and future falsification requirements; it does not silently promote a LOGOS mechanism.