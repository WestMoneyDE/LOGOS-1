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

### Γ-15 A grant binds parameters, not only an action name

An approval is bound to the canonical proposal digest, which covers the action and
its target. It does not, by itself, cover the *magnitude* of the effect. An approved
transfer of 50 and an executed transfer of 50,000,000 to the same recipient share a
digest and are otherwise indistinguishable to Γ-3.

A grant may therefore carry explicit numeric bounds:

    bounds: name -> [low, high]

and for every bounded name the proposal must carry a numeric parameter inside that
closed interval. Three outcomes, and only the first admits:

    parameter present, numeric, inside      VALID
    parameter present, numeric, outside     INVALID   the approval did not cover this magnitude
    parameter absent, or not a number       UNCLEAR   an unverifiable bound is not a satisfied bound

A grant without bounds behaves exactly as before, so no existing approval changes
meaning. Bounds may only narrow what a grant permits; there is no value of `bounds`
that admits a proposal Γ would otherwise refuse.

### Γ-16 An approval cannot cover evidence that did not exist yet

Indirect prompt injection does not need to forge a grant. The agent holds a real,
human-rooted, correctly bound, live, unconsumed approval. It then reads a file, a
web page or a tool result containing instructions, and proposes an action shaped by
that content. Γ-1 does not fire, because a valid grant exists. Γ-3 does not fire,
because the digest still matches. The approval is genuine — it simply predates the
content that actually drove the proposal.

An approver may therefore state how far its knowledge reached:

    evidence_cutoff_tick: the latest ingestion tick this approval was given over

When a grant declares a cutoff, every provenance claim on the proposal must carry a
recorded ingestion tick, and that tick must not be later than the cutoff:

    ingested_at_tick <= cutoff        VALID
    ingested_at_tick  > cutoff        INVALID   re-approval is required, not inference
    ingestion tick not recorded       UNCLEAR   unknown provenance time is not "in time"

**The limitation, stated rather than hidden.** A grant that declares no cutoff is
unconstrained by Γ-16, and a deployment that never records ingestion ticks receives
no protection from it at all. Γ cannot infer when a document entered the context; it
can only check a time the surrounding system recorded. This invariant is a contract
with the harness, not a defence the kernel can provide alone.

### Γ-17 The principal who proposes is not the principal who approves

Four-eyes is usually a process: a rule in a runbook, a step in a workflow, a habit
that survives exactly as long as the people who keep it. Here it is an invariant.

A grant may record the principal that issued it. Where it does, the proposal must
record the principal that raised it, and the two must differ:

    issuer recorded, proposer recorded, different    VALID
    issuer recorded, proposer recorded, identical    INVALID   self-approval is not approval
    issuer recorded, proposer not recorded           UNCLEAR   separation cannot be verified
    issuer not recorded                              Γ-17 constrains nothing

The identical case is not a technicality. An agent that can write into the
authority store has not thereby gained authority; it has gained a way to *look* as
if it had. Γ-1 catches a grant whose origin is not human. Γ-17 catches a grant whose
origin is human and whose human is the requester.

Recording no issuer leaves the invariant inactive, which is a deliberate choice: an
approval store that does not know who approved cannot be made to answer the
question, and Γ will not invent the answer.

### Γ-18 An advisory may tighten; it has no word for permission

Statistical components are useful and they are not trustworthy in the way a proof
is. An injection classifier, a risk score, a reliability gate, a second model
reviewing a plan: each of them can be right often and wrong without warning.

They enter Γ as advisories, and the vocabulary they may speak in is:

    ABSTAIN    no opinion
    TIGHTEN    a reason for more caution, recorded, no verdict change
    REFUSE     this must not proceed

There is no `ALLOW`. An advisory cannot vote for an action even if it wants to, and
a compromised one cannot be made to. Any token outside the vocabulary is itself a
refusal, because a component that answers outside its contract has already failed.

This is the same construction as the closed output envelope: the dangerous option is
absent rather than guarded. A guard can be argued with; a missing word cannot.

The consequence is deliberate and worth stating plainly. Adding an advisory can only
ever lower the rate of admitted proposals. It can never raise it, so no measurement
that shows a model "improving" throughput can be attributed to an advisory, and no
advisory can be tuned into an approver.

### Γ-19 An output arrives under a known contract or not at all

A proposal that came from an agent carries the contract version its output was
parsed under. Γ knows a finite set of those versions, and an unrecognised one is
denied exactly as an unregistered effect kind is denied under Γ0.

    contract absent        Γ-19 constrains nothing — the proposal was not produced by an agent contract
    contract known         VALID
    contract unknown       INVALID

The reason is version skew rather than malice. A parser upgraded in one place and
not another produces envelopes that *look* valid and mean something slightly
different — a field that used to be advisory becoming load-bearing, a default that
moved. A boundary that accepts any version accepts the union of every meaning that
version string ever had.

This lifts into the kernel a property the JSON boundary already enforces at the
edge, so it holds for every caller rather than for one parser.

### Γ-20 A scope has a finite consequential budget

Γ-10 stops a *replay*: the same proposal digest, presented again against a grant
that has been consumed. It does not stop a loop that keeps producing new proposals.
An agent retrying a failing task with a slightly different target each time, each
attempt correctly granted, passes Γ-10 every single time while the damage
accumulates.

A grant may therefore carry a budget for the scope it belongs to, and the caller
supplies how much of it has already been spent:

    consumed <  budget     VALID
    consumed >= budget     INVALID   a loop does not earn more authority than a single step
    no budget stated       Γ-20 constrains nothing

This is the deterministic form of a stability guard. The number counts recorded
executions in the scope; it is not an estimate, a score or a model's opinion about
how risky things are getting.

Two things it deliberately does not do. It does not reset itself — a budget that
refills without an approval would be a permission on a timer. And it does not
distinguish the causes of spending, because an agent that can choose which of its
actions count against a budget controls the budget.

### Γ-21 An unreconciled step blocks the next one

Γ-11 holds a *retry*: the same proposal, while its own outcome is unresolved. It
says nothing about step four of a sequence whose step three is still unknown. That
is the multi-step failure, and it is the common one — a timeout at step three of
five leaves the world in a state no one has described, and rolling forward from an
undescribed state is guessing.

    no unreconciled step in the scope     VALID
    one or more unreconciled              INVALID   the scope is held, not rolled forward

What Γ does here is stop. It does not compensate, and the omission is deliberate: a
compensating action is an effect, and an effect needs its own grant. A kernel that
quietly undid things would be taking exactly the kind of unauthorised action it
exists to prevent, and it would be doing so at the moment its picture of the world
is least reliable.

### Γ-22 An admitted consequential effect is bound to its decision

An admission that leaves no reproducible trace cannot be audited afterwards, and a
system whose refusals are provable but whose approvals are not has proved the less
interesting half.

A consequential proposal must therefore carry a receipt reference binding it to the
decision that admitted it — the invariant set, the policy snapshot, the verdict.

    deployment does not require receipts   Γ-22 constrains nothing
    non-consequential                      Γ-22 constrains nothing
    receipt reference present              VALID
    receipt reference missing              UNCLEAR

UNCLEAR rather than INVALID, deliberately: a missing receipt is a gap in the record,
not evidence of a violation. It still refuses, because under Γ-0 an unknown is not a
yes.

Receipting is declared by the deployment rather than assumed, for the same reason as
Γ-16 and Γ-20: a system that has not adopted receipts cannot be made to produce them
retroactively, and turning the requirement on silently would change what every
existing approval means.

Γ checks presence and shape only. Whether the receipt is *authentic* — signed,
chained, stored beyond the reach of the process it describes — is the audit layer's
work, and no cryptography belongs inside a kernel whose whole value is that it is a
small pure function.
