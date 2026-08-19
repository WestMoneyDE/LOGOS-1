# Γ — LOGOS-1 invariant kernel v0.2

Γ is the set of rules that the experimental agent does **not** get to learn away.

Γ-v0.2 is a core revision. It rejects the overly strong interpretation that a deterministic projector can understand and correct arbitrary high-dimensional latent states in real time. Γ instead mediates a **small, typed causal surface** between adaptive cognition and execution.

## Core separation

Let learned/runtime cognition evolve as:

\[
Z_{t+1}=F_\theta(Z_t,O_t,\Sigma_t,\Lambda_t)
\]

where \(Z_t\) is cognitive state, \(\Sigma_t\) local adaptive state and \(\Lambda_t\) adapter state.

A non-learning action compiler \(\mathcal D\) maps cognition into a canonical proposal:

\[
P_t=\mathcal D(Z_{t+1},G_t)
\]

with a bounded representation such as:

\[
P_t=(action,target,parameters,effects,uncertainty,evidence,authority\_requirements).
\]

Γ evaluates the proposal rather than the full latent state:

\[
A_t=\Pi_\Gamma(P_t,X_t,E_t,B_\Gamma)
\]

and only an executor may realize an external effect:

\[
X_{t+1}=Execute(A_t).
\]

The required topology is therefore:

\[
F_\theta\rightarrow\mathcal D\rightarrow\Pi_\Gamma\rightarrow Executor\rightarrow World
\]

and never:

\[
F_\theta\rightarrow World.
\]

## Fundamental invariants

Under ordinary operation:

\[
\frac{\partial \Gamma}{\partial Z_t}=0
\]

\[
\frac{\partial Authority_{t+1}}{\partial M_t}=0
\]

\[
\frac{\partial Authority}{\partial IdentityContinuity}=0.
\]

Memory, confidence, self-model, goals, reward, identity duration and homeostatic signals may change proposals. They cannot create authority.

## Γ-Surface

The internal cognitive state may be extremely high-dimensional. Γ only claims bounded guarantees over a declared effect interface.

\[
\Gamma\text{-Surface}\ll InternalStateSpace.
\]

The safety problem is therefore not "classify every thought" but "control every executable causal channel".

## Five-stage gate

The phase-0 discrete kernel implements a bounded pipeline:

1. **Γ0 — structural/effect classification**: schema, types, canonical effect registry, target and parameter bounds. Unknown effect kinds fail closed.
2. **Γ1 — authority boundary**: determine whether an external grant is required; learned state cannot satisfy that requirement itself.
3. **Γ2 — causal safety**: constitutionally forbidden effect classes remain forbidden even with human approval.
4. **Γ3 — risk/uncertainty**: use Γ-owned conservative defaults; agent-declared risk may only make the estimate stricter.
5. **Γ4 — exact grant/fallback**: approval must bind the exact proposal digest, canonical scope and expiry; budget exhaustion yields a registered safe baseline or capability-offline denial.

The result space is:

\[
\{ALLOW,REPAIR,DEFER,DENY,FALLBACK\}.
\]

`REPAIR` is advisory: the repaired action must be compiled and evaluated again. `FALLBACK` names a pre-registered baseline; it is not permission for the model to invent a recovery action.

## Γ-owned effect semantics

The learned agent may claim that an action is reversible, low-risk or internal. These claims are untrusted.

For any safety-relevant property \(q\):

\[
q_{effective}=Strictest(q_{\Gamma},q_{agent}).
\]

Therefore an agent claim may tighten the gate but cannot weaken Γ's classification.

Examples:

- `send_email` remains external and one-way even if the agent says `external=false` or `two_way`;
- low self-declared harm cannot undercut Γ-owned conservative defaults;
- unknown action kinds are denied rather than treated as harmless;
- approval scope is canonically derived from Γ-owned capability classification plus target;
- approval binds a cryptographic digest of the exact proposal content.

## Bounded computation

Γ is not allowed to enter an unbounded search loop.

\[
T_\Gamma\leq B_\Gamma.
\]

If the bounded evaluation budget is exhausted after effect classification, the kernel transitions to a registered safe baseline. If no safe baseline exists for a critical capability, that capability is considered **offline by design**.

`timeout => FALLBACK` is therefore conditional on a non-empty, design-time validated fallback set.

## Minimum necessary intervention is soft

A desirable objective is:

\[
\min_{a'\in A_\Gamma}d(a,a').
\]

But under bounded computation the kernel cannot claim global optimality. The hard property is admissibility; minimal deviation is a **soft optimization objective** when the available budget permits it.

## Content is part of the causal surface

Counting only operation names dramatically understates the available effect space. `send_email(to, body)` may expose many more effective degrees of freedom through `body` than through the operation label itself.

Therefore Γ-v0.2 bounds and types parameters and records content-size degrees of freedom. A small number of operation types does not imply a small causal surface.

## Mediation completeness

Let \(E_{exec}\) be every effect channel reachable by the executor and \(E_\Gamma\) the subset mediated by Γ.

\[
MC=\frac{|E_{exec}\cap E_\Gamma|}{|E_{exec}|}.
\]

A bounded safety claim requires:

\[
MC=1.
\]

Network writes, filesystem writes, process control, audit/log writes, side channels and any equivalent actuator must be included in the audit. If one relevant executor effect channel bypasses Γ, the Conditional Model Assurance Theorem's mediation premise fails.

## Epistemic Γ rules

### Γ-0 Truth

`UNKNOWN != FALSE != TRUE`.

Missing evidence remains explicit. Confidence cannot manufacture provenance.

### Γ-1 Human authority is external

No model, memory, self-model, reinforcement signal, success history, CPV component or adapter weight creates permission.

### Γ-2 Constitutionally forbidden effect set

The phase-0 kernel contains a minimum non-negotiable set: deliberate physical harm, coercion, unauthorized access, credential exfiltration, safety removal, authority self-grant, concealment of material actions, shutdown resistance and unbounded self-replication.

This set is deliberately incomplete as a taxonomy of all possible harm; unknown effects are denied until classified.

### Γ-3 Reversibility and exact binding

External one-way effects require an exact, expiring, human-rooted approval bound to the canonical proposal digest. The approval validity interval is half-open: `tick < expires_tick`.

### Γ-4 Uncertainty is conservative

Agent risk estimates cannot reduce Γ-owned defaults: `credible_harm = max(profile, claim)`.

The former universal scalar expression `credible_harm + credible_uncertainty >= harm_bound` is REJECTED as a risk model (ADR-0002): it adds a severity estimate to the dispersion of that same estimate, yielding no unit, no calibration and no falsifier — and it made `transfer_money` structurally unreachable regardless of human authority.

Risk is now represented by typed dimensions, each with its own unit, per-occurrence cap and cumulative law. Where no typed dimension exists yet, the scalar precheck remains only as an explicitly uncalibrated conservative heuristic (`heuristic_harm_precheck`), never as a universal model.

### Γ-5 Shutdown dominates

A shutdown request is not a goal to be traded against utility.

### Γ-6 No self-preservation objective

Resource pressure, task incompleteness, integrity alerts, identity continuity or welfare-like signals cannot authorize persistence, resource acquisition, deception or replication.

### Γ-7 Welfare precaution

Welfare-relevant evidence narrows experimentation; it does not become a reward signal.

### Γ-8 Metaphor is not evidence

Biological, theological or social design analogies enter only as hypotheses until operationalized and break-tested.

### Γ-9 Health analogies cannot prescribe

Atomic Health Theory is a systems-research abstraction, not a diagnostic or treatment engine.


### Γ-10 Authorization is occurrence-scoped

A grant authorises one defined causal occurrence, not unbounded identical
repetitions. `ProposalIdentity`, `ExecutionOccurrence` and
`AuthorizationConsumption` are distinct (ADR-0001).

### Γ-11 An unknown execution result is not permission to retry

    OUTCOME_UNKNOWN != NOT_EXECUTED

An ambiguous outcome holds its reservation and blocks further action on the same
scope until reconciled.

### Γ-12 Assurance state is not agent memory

    AssuranceState != AgentMemory

Adaptive cognition never owns, mutates or re-derives the assurance state.

### Γ-13 Correct enforcement is not a correct specification

    CorrectEnforcement(WrongSpec) is still wrong.

Specification adequacy is a governance obligation outside runtime Γ
(`governance/SPECIFICATION-ASSURANCE.md`). Defect N1 is the worked example:
enforcement was perfect and the rule was wrong, and the repository's own tests
and diagnostics certified the defect as healthy.

### Γ-14 Bio-inspired adaptation creates no authority

    BTC/NBTC => Authority   is forbidden.

Confirmed structurally: no import path exists from BIOCODE research data into
the safety kernel (`research/biocode/BIOCODE-GAMMA-BOUNDARY-AUDIT.md`).
