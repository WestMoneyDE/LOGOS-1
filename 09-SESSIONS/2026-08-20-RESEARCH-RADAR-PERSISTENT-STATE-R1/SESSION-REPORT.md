# Session Report — Research Radar: Persistent State R1

**Date:** 2026-08-20  
**Type:** external research review / prior-art reconciliation  
**Scientific verdict delta:** comparison-baseline and falsification-method delta only; no automatic LOGOS mechanism promotion  
**Pull request:** `#5` — `research: add persistent-state prior-art delta and causal work order`  
**Merge commit:** `073af4134314cbde5d82c190eac3c450efc16b51`

## Input

New research notes were reviewed covering:

- MoNe fast-weight test-time memory;
- Beyond the Trace internal MoE reasoning-state readouts and interventions;
- CASE hidden-state correctness selection with leakage-resistant decodability;
- Aegis trusted runtime governance;
- QWM world-model search with real-transition-only learning;
- information-constrained active inference;
- RecurrentGPT recurrent depth;
- comparison to BDH-CQ recurrent latent reasoning.

## Verification outcome

The main technical claims were confirmed against primary arXiv records.

Date corrections:

- MoNe: submitted 2026-08-18;
- Beyond the Trace: submitted 2026-08-18;
- CASE: submitted 2026-08-17;
- QWM: submitted 2026-08-17;
- Expected free energy as an information constraint on the Bethe Lagrangian: submitted 2026-08-17;
- RecurrentGPT: submitted 2026-08-15;
- BDH-CQ: submitted 2026-08-10;
- Aegis runtime-governance paper: submitted 2026-05-17, therefore relevant prior art but not a new 2026-08-19 paper.

## What materially changes for LOGOS-1

### A. Persistent-memory baseline expands

Future persistent-state comparisons should include at least:

```text
Token Context
vs Recurrent Latent State
vs Fast-Weight State
vs External Retrieval
```

MoNe makes test-time fast weights a serious direct alternative to BDH-like recurrent state for history compression / reuse.

### B. Functional-state evidence is split into three levels

New evaluation vocabulary:

```text
DecodableState != OperationalState != CausalState
```

For a proposed state S, evaluate D(S), O(S), and C(S) separately.

Beyond the Trace is important because it reaches intervention evidence rather than stopping at probe decodability.

### C. Hidden-state metacognition requires stronger leakage controls

CASE shows that ordinary probe accuracy can be inflated by question identity. Question-grouped / leakage-resistant evaluation is now a minimum methodological requirement for future LOGOS correctness-state probes.

### D. Ground truth, belief and simulation should be typed separately

QWM supports a strong engineering distinction between imagined trajectories used for search and real transitions used for learning.

Candidate state classes:

```text
O_t = observed / grounded
B_t = believed / inferred
H_t = hypothetical / counterfactual
E_t = epistemic uncertainty / information demand
```

Candidate boundary:

```text
H_t -/-> O_t without validation
```

This is recorded as a hypothesis to test, not a promoted Atomic Rule.

### E. Epistemic exploration may be demand-conditioned

The constrained-Bethe active-inference result motivates testing dynamic information requirements instead of a permanently active exploration bonus.

Candidate:

```text
SeekInformation iff CurrentInformation < TaskRequiredInformation
```

Again: research hypothesis, not canonical rule.

### F. Recurrent compute is a distinct architecture axis

RecurrentGPT strengthens the distinction:

```text
ComputationalDepth != ArchitecturalDepth
```

It is adjacent support for BDH-like iterative latent computation, not a BDH replication and not evidence of lifelong persistent state.

### G. Authority separation receives additional prior art

Aegis independently supports the pattern:

```text
ModelProposal != ExecutionAuthority
```

but only within the evaluated sandbox scope. It does not establish general agent safety or mediation closure.

## Consciousness / P7

No reviewed paper justifies a change to the phenomenal-consciousness boundary.

Functional evidence for persistent state, hidden correctness signals, routing interventions, world models or recurrent compute does not imply phenomenal experience.

P7 remains unchanged.

## New durable artifacts

1. `docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md`
2. `05-WORK-ORDERS/QUEUED-PERSISTENT-STATE-CAUSALITY-R1.md`

## Canonical-queue boundary

`CURRENT-WORK-ORDER.md` remains WMR / ARC-AGI-3. This session does not reorder the active external-validation queue.

The new persistent-state causality work order is explicitly queued for later execution.

## Validation

- all reviewed technical claims were checked against primary arXiv records;
- date mismatches were corrected rather than copied forward;
- the branch diff contained only the prior-art delta, queued work order and this session report;
- `CURRENT-WORK-ORDER.md` was not modified;
- PR #5 was merged to `main` successfully.

## Next step

Continue the active WMR external execution. When the canonical queue reaches the persistent-state study, freeze the four-arm memory comparison with matched-resource curves, state-swap interventions, corruption/recovery, leakage-resistant hidden-state probes and grounded-vs-hypothetical contamination tests.