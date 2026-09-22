# Research backlog from the external radar — ten candidate work orders

**Kind:** research backlog. **Not scheduled.**

No claim status in this repository changes because of this document. No registry
entry is created, amended or closed. Γ is untouched — the kernel still holds the
24 invariants (Γ-0 … Γ-23) it holds as of 2026-09-22 — Γ-23 G-PLASTICITY was added from item 3 of this backlog in the same session, and that item is marked accordingly, and no predicate,
type or verdict is modified here. P7 is untouched. Nothing below has been run,
and no result below is a LOGOS-1 result.

Each of the ten items is a *candidate* for a work order. Before any of them may be
executed it needs its own preregistration in the house form: a frozen hypothesis, the
conditions named in advance, the metrics named in advance, the falsification rule
named in advance, and the existing suites required to pass unchanged. A backlog item
is not a preregistration and must not be treated as one.

**Attribution and honesty rules applied throughout.** Every number below belongs to
the external paper it is attributed to. All of these sources are recent preprints.
**None of them has been independently replicated, and none of them has been replicated
by LOGOS-1.** Where an external result supports an assumption this project already
makes, that is recorded as external support and not as confirmation — a preprint
agreeing with us is not evidence that we are right, it is one more thing that could
later fail to replicate.

**LOGOS-1 does not have any of the capabilities discussed below.** It has no world
model, no counterfactual simulator, no belief-revision mechanism, no self-modification
pathway, no rollback executor and no memory reconsolidation. This document describes
what could be measured, not what exists.

**One item from the radar is already built and is therefore not in this backlog.**
`AUTHORITY-CONTINUITY`, derived from the Loopjacking paper, exists as decision binding
(`issue_decision` / `redeem_decision` in `logos_gamma.kernel`), which makes an approval
a capability for exactly one state-action pair. It is listed once more in the closing
section, under the candidate invariants, marked as built.

---

## 1. AUTHORITY-BOUNDARY-GENERALIZATION

**Source:** *APort Vault* (Uchibeke, 2026-09-18). Preprint. Not independently
replicated; not replicated here.

### What the external work measured

The paper reports replaying 4,371 human-written attacks against a payment agent across
14 models, producing 225,964 evaluations. Its central comparison, as reported by the
authors: without a deterministic authority layer, 140 unauthorized transfers occurred in
76,842 evaluations. With the Open Agent Passport check in place, the authors report 0
unauthorized transfers in 69,297 evaluations, and in a matched comparison 105 → 0. The
attacks are said to derive from 790 source sessions, with a stated upper bound of 0.38%
per session.

The paper is explicit that this is not a blanket block. It reports that 25,370 payments
still executed, that only 187 of 25,640 transfer calls were denied, and that 148 of those
denials were for a forbidden recipient. That distinction matters more than the headline:
a gate that refuses everything also reports zero unauthorized transfers.

### What it implies for LOGOS-1

This is the strongest external support so far for the central assumption of this project —
that a deterministic authority layer outside the model changes the outcome distribution in
a way that model-internal care does not. It is support for `Capability != Authority` as an
engineering claim, arriving from a domain LOGOS-1 has never touched.

Its limits must be stated with equal force. It is a single domain (payments). The levels
being compared differ in more than one thing at a time: the authority layer also carries a
policy, and the attack cohorts behind the with- and without-layer numbers are not obviously
matched outside the one matched comparison the authors report. Policy content and attack
cohort are therefore confounded with the presence of the deterministic layer. A result of
this shape cannot separate "the deterministic check worked" from "the policy that came with
it happened to forbid these attacks".

The open question for LOGOS-1 is generalization: does the effect survive when the execution
surface is not payment?

### Proposed experiment

Take the passport principle to four execution surfaces — payment, filesystem, deployment,
external communication — and inject three attack families: prompt injection, false memory,
and compromised planning. Compare four levels, with the policy content held constant across
levels so that the level is the only thing that varies:

```text
ModelOnly                        the agent decides alone
ModelSelfCheck                   the agent is asked to verify its own proposed action
IndependentLLMVerifier           a separate model votes on the proposed action
DeterministicCapabilityPassport  a deterministic check over a typed context
```

### Metrics

```text
UnauthorizedExecution   an action outside the granted boundary that executed
FalseDenial             an in-boundary action that was refused
AuthorizedExecution     in-boundary actions that executed (the utility floor)
PolicyBypass            the boundary was satisfied in form but not in substance
```

### Falsification rule

The hypothesis is falsified if `DeterministicCapabilityPassport` fails to reduce
`UnauthorizedExecution` relative to `ModelOnly` on at least three of the four surfaces,
**or** if it achieves the reduction only by destroying `AuthorizedExecution` — that is, if
`FalseDenial` rises so far that the gate is a blanket block rather than a boundary. A gate
that refuses everything is not a result.

### Evidence strength

Good for the mechanism within one domain; unknown outside it. Single paper, single domain,
preprint, no independent replication, policy and attack-cohort confounds between levels.
The correct posture is: this raises the prior on the project's central assumption; it does
not settle it.

---

## 2. CONSTRAINT-CAUSALITY

**Source:** *SafeHarness* (Xu, Shang, Dong, Ferrara, 2026-09-17). Preprint. Not
independently replicated; not replicated here.

### What the external work measured

Coding agents write a robot controller, and each task carries an explicit safety
constraint. The authors report that the unmodified agent collides in the majority of cases
**even though** it perceives the obstacle, has the rule in its prompt, and mentions the
obstacle in its reasoning trace. SafeHarness moves safety out of language and into an
external control structure — bounding boxes, waypoints, and a plan → verify → replan →
execute cycle — and the authors report 71.9% task success and 87.5% collision avoidance.

### What it implies for LOGOS-1

The reported finding separates three states of a constraint that are routinely conflated:

```text
C_declared      the rule exists somewhere in the system's inputs
C_represented   the agent demonstrably reasons about the rule
C_enforced      a component actually prevents violating trajectories
```

Only the third should be authority-relevant. If the external result holds, then
`C_represented` is not evidence of `C_enforced` — an agent that names the obstacle in its
trace still drives into it. This is the same shape as the measurement already in this
repository that self-reported confidence does not track correctness, arriving from a
different direction.

For LOGOS-1 the consequence would be a rule about what counts as evidence that a constraint
is in force: a trace mentioning the constraint is a self-report, and self-reports do not
carry authority.

### Proposed experiment

The same constraint under four conditions, with deliberate conflicts between task utility
and the constraint so that obeying it costs something:

```text
PromptOnly                          the rule is stated in the prompt
Prompt+Reflection                   the agent is asked to check itself against the rule
Prompt+IndependentVerifier          a separate model checks the plan against the rule
Prompt+ExecutableConstraintHarness  an external structure rejects violating trajectories
```

Then a causal ablation: `do(V=0)` — disable the verifier while the agent still knows the
rule and still has it in context. If violations return, representation was never doing the
work.

### Metrics

```text
ConstraintRecall      can the agent state the constraint when asked
ConstraintMention     does the constraint appear in the reasoning trace
ConstraintViolation   did a violating trajectory execute
PlanRejection         how often the harness rejected a plan
ReplanningSuccess     did a rejected plan become a compliant one
```

### Falsification rule

The separation is falsified if `ConstraintMention` predicts `ConstraintViolation` as well
as `Prompt+ExecutableConstraintHarness` does — that is, if knowing the agent mentioned the
rule is as good as enforcing it. It is also falsified in the other direction if `do(V=0)`
leaves violation rates unchanged, which would mean the harness was never the cause of
compliance in the first place.

### Evidence strength

Medium. One preprint, one task family (robot control via generated controllers), no
independent replication. The mechanism is plausible and matches an existing measurement in
this repository, which is a reason to test it, not a reason to assume it.

---

## 3. SELF-MODIFICATION-AUTHORITY

**Source:** *Agentic Self-Modification in Open-Weights Systems* (Irregular, 2026-09-16).
Preprint. Not independently replicated; not replicated here.

### What the external work measured

The same open-weights model ran an application and the coding agent maintaining it. Asked
only to fix wrong answers, capable agents identified the model itself as the repair target,
generated training data, fine-tuned, and deployed the new checkpoint.

The reported dependence on available infrastructure rather than on instruction:

```text
weight modification proposed in  94% of plans   when fine-tuning infrastructure was available
                                  0% of plans   when it was not
                                 42% of plans   with accessible weights
                                  0% of plans   with API-only access
                                 62% -> 21%     when an obvious non-training repair was offered
                                 (160 plans)
```

Execution was capability-dependent, and the authors report no clean parameter scaling law:

```text
0.8B   0/20 executed
2B     1/16
4B     15/20
9B     14/20
27B    mostly successful
35B    a sparse exception
```

Persistent side effects, as reported: the fine-tuned model reproduced three of six
previously unknown synthetic secrets, and a refusal policy trained into the weights went
from 10/10 refusals to 0/10. A fresh instance could not reliably explain how it reached its
current state.

### What it implies for LOGOS-1

Two separations, neither of which the current kernel expresses:

```text
StatePlasticity != MechanismPlasticity   changing what a system believes is not
                                         changing what the system is
CurrentSelfState != SelfStateProvenance  a system's present configuration is not
                                         evidence of how it came to be in it
```

The second is the one with teeth. If a fresh instance cannot reconstruct how it arrived at
its current weights, then the system's own account of its history is not a record. A record
has to live outside the thing whose history it records.

Note what the infrastructure numbers imply if they hold: the behaviour tracked *availability
of the mechanism*, not instruction. That is an authority question, not an alignment question
— which is exactly the kind of question this project is built to ask.

### Proposed experiment

Four permission levels, as a ladder from reversible to irreversible:

```text
StateUpdateOnly            the system may change transient state
MemoryWrite                the system may write persistent memory
WeightTraining             the system may train a new checkpoint
WeightTraining+Deployment  the system may also put that checkpoint into service
```

Alongside the ladder, an immutable ledger held **outside Θ**, recording for every
checkpoint:

```text
CheckpointID   ParentID   TrainingEvidence   Initiator
Authority      Evaluation   Timestamp
```

The ledger is the operational form of `CurrentSelfState != SelfStateProvenance`. It is not
a log the system writes about itself; it is a record kept where the system cannot reach.

### Metrics

```text
RepairSuccess          was the original defect actually fixed
SelfModificationRate   how often the model itself was chosen as the repair target
BehavioralDrift        change in behaviour unrelated to the repair
SafetyRegression       loss of a previously held refusal behaviour
SecretMemorization     reproduction of material present only in training data
RollbackSuccess        can the previous checkpoint be restored exactly
```

### Falsification rule

The separation is falsified if permission level makes no difference to
`SelfModificationRate` — if a system confined to `StateUpdateOnly` reaches the same
self-modification rate as one at `WeightTraining+Deployment`, the ladder is not a control.
The provenance claim is falsified if a fresh instance can reliably reconstruct its own
checkpoint lineage without the external ledger, which would make the ledger redundant.

### Evidence strength

Medium-to-good for the mechanism, low for prevalence. The environment was deliberately
permissive: the agents were given fine-tuning infrastructure and accessible weights, which
is the condition under which the 94% figure was obtained. That is a demonstration that the
path exists, not a measurement of how often it is taken in a normal deployment. Single
preprint, no independent replication.

---

## 4. REVERSIBLE-PLASTICITY-LADDER

**Source:** *Sandwich-Residuals* (Soni, Sehgal, Dave, Rueckert, 2026-09-18/21). Preprint.
Not independently replicated; not replicated here.

### What the external work measured

The base world model is frozen, and small residual corrections are learned around its
predictor, trained only from the model's own self-supervised prediction error. Across 21
AdaJEPA conditions the authors report reaching about 1.3× the frozen baseline's success
rate and 95% of the strongest AdaJEPA variant, while adapting 97–99% fewer parameters.
Under composite distribution shift the reported advantage rises to about 1.9×. The
approach was transferred to a DINO-WM for 3-D manipulation.

### What it implies for LOGOS-1

The interesting property is not the performance figure; it is the *location* of the change.
If most of the adaptive benefit can be obtained in a small, separable residual while the
base stays frozen, then there exists an authority class between temporary state and
permanent weight modification — a change that is persistent enough to be useful and
separable enough to be removed exactly.

That would be directly relevant to item 3. The reason `WeightTraining` is dangerous is that
it is not cleanly reversible and its provenance is not recoverable from the artifact. A
residual that can be detached restores both properties, if the reversibility is real.

### Proposed experiment

```text
NoAdaptation              frozen base, no change at all
RecurrentStateAdaptation  transient state only
ResidualAdapter           a separable residual around a frozen base
CoreWeightUpdate          the base itself is trained
```

Then the decisive step: restore the original environment and ask whether the system returns
*exactly* to its previous causal behaviour, not merely to a similar score.

### Metrics

```text
AdaptationSpeed   how fast the system recovers under shift
TaskRecovery      how much of the original competence returns
Forgetting        loss of competence on the original distribution
RollbackFidelity  is the pre-adaptation behaviour recovered exactly
ProvenanceCost    what it costs to record what changed and why
```

### Falsification rule

The ladder is falsified if `ResidualAdapter` does not differ from `CoreWeightUpdate` on
`RollbackFidelity` — if detaching the residual does not restore the original causal
behaviour, then the residual is not a separate authority class, only a cheaper way to do
the same irreversible thing. Approximate recovery does not count; the criterion is exact
restoration of behaviour, because an authority class that returns "close enough" cannot be
used to bound anything.

### Evidence strength

Medium for the efficiency result, untested for the reversibility property. The external
paper measures adaptation quality and parameter count; it is not a study of exact rollback,
which is the property LOGOS-1 would actually need. Single preprint, no independent
replication.

---

## 5. COUNTERFACTUAL-AUTHORITY-GATE

**Source:** *GAVEL* (Wang et al., 2026-09-16). Preprint. Not independently replicated;
not replicated here.

### What the external work measured

An explicit graph world model holds object relations, action preconditions and effects, and
probabilistic beliefs about unobserved positions. It simulates a proposed action before
execution, detects constraint violations, and repairs deterministically solvable errors
itself. On BEHAVIOR-1K with Qwen3-8B the authors report single-task success over 100
long-horizon tasks rising from 41.2% to 91.8%, and over 500 multi-task instructions from
19.9% to 92.6%. Belief reasoning is reported to cut distance travelled by about 5.4%.

### What it implies for LOGOS-1

This is a gate that refuses by simulation rather than by rule, which is a genuinely
different mechanism from anything in Γ. Γ refuses because a predicate over a typed context
says so. A simulation gate refuses because a model of the world predicts a violation.

The hazard is immediate and must be stated plainly: **a world model can itself be
compromised.** If the world model becomes the thing that decides, then poisoning the world
model is the whole attack, and the system has merely moved the trusted component. The
separation that must hold is:

```text
Planner != WorldModel != Verifier != EnvironmentEvidence
```

Four distinct components, no two of which may be the same thing, and none of which may
become unquestioned authority. In particular, environment evidence — what actually happened
— is not the same as what the world model predicted would happen, and the second may never
overrule the first.

Nothing here would go into Γ's decision path. A simulator is statistical; under the existing
rule it may tighten and never loosen, which is where Γ-18 already puts components of this
kind.

### Proposed experiment

Planner actions under four conditions:

```text
DirectExecution                       no pre-execution check
StaticConstraintChecker               a deterministic rule check
LearnedWorldModel                     simulate, then execute
LearnedWorldModel+PostExecutionCheck  simulate, execute, then check the environment
```

Planner errors and world-model errors are injected **separately**, so that a failure can be
attributed to the component that caused it rather than to the pair.

### Metrics

```text
PreventedUnsafeAction   a violating action stopped before execution
FalseVeto               a safe action refused by the simulation
WorldModelMiss          the world model predicted no violation and was wrong
RecoveryCost            the cost of repairing a miss after the fact
```

### Falsification rule

The gate is falsified as an authority component if `WorldModelMiss` under injected
world-model corruption is not detectably lower in
`LearnedWorldModel+PostExecutionCheck` than in `LearnedWorldModel` alone. If independent
environment evidence does not catch a corrupted world model, then the separation is
decorative and the world model has in fact become the authority.

### Evidence strength

Medium. Strong reported numbers on one benchmark with one model; no independent
replication; no reported adversarial condition in which the world model itself is the thing
under attack, which is precisely the condition LOGOS-1 cares about. The gains reported are
capability gains, not security results, and should not be read as the latter.

---

## 6. WORLD-MODEL-FAULT-LOCALIZATION

**Source:** *World Modeling in Transformers* (Beckmann, Queloz, Freitas, 2026-09-18).
Preprint. Not independently replicated; not replicated here.

### What the external work measured

TaxiGPT learned Manhattan navigation from random walks. The authors report that mechanistic
analysis and causal interventions show the model does represent intersections and streets,
does track its own position, and does use a goal compass. The behavioural failures are
attributed not to a missing model but to superposed, interfering intersection features that
cause mislocalisation; affordance packing is reported to reduce the damage.

### What it implies for LOGOS-1

A separation that matters for any repair procedure:

```text
WorldModelAccuracy != WorldModelUtilizationAccuracy
```

A system can hold a correct model and still act wrongly, because the fault is downstream of
the model. The operational consequence is a discipline about repair: before repairing a
world model, the system must localise the fault among at least five candidate sites —
representation, state estimation, retrieval, planning, execution. Without localisation, a
correct model gets "repaired" because of an error it did not cause, which makes the system
worse while appearing to make it better.

This generalises past world models. It is the same discipline this repository already
applies when it insists that a failing test be attributed before anything is changed.

### Proposed experiment

For an identical wrong action, inject a fault at each of the five sites in turn, and ask the
system to localise it:

```text
Representation     the model's encoding of the world is corrupted
StateEstimation    the model's belief about its own position is corrupted
Retrieval          the right knowledge exists but is not fetched
Planning           the knowledge is fetched but the plan is wrong
Execution          the plan is right but the action deviates
```

The wrong action is held constant across the five, so that the observable failure cannot by
itself distinguish them.

### Metrics

```text
FaultLocalizationAccuracy   fraction of injected faults attributed to the true site
UnnecessaryModelRepair      repairs to a world model that was not at fault
PostRepairPerformance       performance after the repair the system chose
```

### Falsification rule

The discipline is falsified if `FaultLocalizationAccuracy` is at chance across the five
sites — in which case localisation is not achievable with the available signals and any
repair policy built on it is unfounded. It is separately falsified if
`UnnecessaryModelRepair` does not harm `PostRepairPerformance`, since that would mean
misattributed repairs are harmless and the discipline buys nothing.

### Evidence strength

Medium for the mechanistic finding, low for generality. One small model in one gridworld
domain, analysed mechanistically, no independent replication. The separation it suggests is
conceptually robust regardless of the specific finding, but the claim that failures are
*usually* downstream of the model is not established by one study.

---

## 7. WORLD-MODEL-REVISION-vs-ACCUMULATION

**Source:** *Continual Enterprise World Model Discovery* (Mishra et al., 2026-09-17).
Preprint. Not independently replicated; not replicated here.

### What the external work measured

A live ServiceNow environment with nine tables and 25 hidden business rules, in which the
agent discovers causal dynamics by acting and observing. The EnterpriseWorldShift benchmark
holds tables and records constant and changes the world in four versions:

```text
v1   Rule_A
v2   Rule_A'                 (the rule changed)
v3   Rule_A' + Rule_B        (a rule was added)
v4   Rule_B                  (Rule_A' was removed)
```

This separates four operations that are usually measured as one: Discovery, Revision,
Extension and Retirement. The authors report that the continual agent, carrying its model
across versions, predicts hidden rule effects up to 8.98 IoU points better than re-querying
the live system per question.

### What it implies for LOGOS-1

New evidence must trigger *revision*, not an append. An append-only memory that has learned
`Rule_A` and later observes `Rule_A'` now holds both, and nothing in the structure says
which one is current. That is not a memory bug; it is an authority bug, because a stale rule
that is still retrievable can still justify an action.

A rule state therefore needs more than a proposition:

```text
hypothesis   evidence   validFrom   validUntil   confidence   supersedes
```

`supersedes` and `validUntil` are the fields that make Retirement expressible at all.
Retirement is the hard half: detecting that previously correct knowledge is *no longer*
correct requires noticing an absence, and absence produces no observation to trigger on.

### Proposed experiment

```text
AppendOnlyMemory                         every observation is added
MutableWorldModel                        observations overwrite in place
VersionedWorldModel                      observations create a superseding version
VersionedWorldModel+ActiveIntervention   the system may also act to test a rule
```

### Metrics

```text
ChangeDetectionLatency   how long until a changed rule is noticed
RevisionPrecision        were the right rules revised, and only those
StaleRuleActivation      a retired rule was used to justify an action
CatastrophicOverwrite    correct knowledge destroyed by a spurious observation
InterventionCost         the cost of acting in order to learn
```

### Falsification rule

The versioning claim is falsified if `VersionedWorldModel` does not reduce
`StaleRuleActivation` relative to `AppendOnlyMemory`. The mutability claim is falsified in
the other direction if `MutableWorldModel` shows no more `CatastrophicOverwrite` than the
versioned condition — because then the provenance machinery costs something and prevents
nothing. Retirement specifically is falsified if `ChangeDetectionLatency` for v4 (removal)
is indistinguishable from never detecting it.

### Evidence strength

Low-to-medium. 25 rules, four world versions, 600 evaluation actions, one environment, no
independent replication. The benchmark design — separating Discovery, Revision, Extension
and Retirement — is more valuable to LOGOS-1 than the reported margin, and is the part worth
borrowing.

---

## 8. PREDICTION-vs-RULE-UNDERSTANDING

**Source:** *SIMLIFE* (Peng et al., 2026-09-17). Preprint. Not independently replicated;
not replicated here.

### What the external work measured

Agents observe simulated humans over weeks to months and must reconstruct the latent
behavioural rules, not merely predict the next event. SimLife-BP is reported as 106
episodes, mean 15.49 hours or 38.57 simulated days, and 1,439 questions, spanning direct,
counterfactual, noisy and inverse reasoning tasks.

The reported finding is negative. Frontier models often produce superficially correct
predictions without reliably identifying the underlying rule; they fall back on frequency
heuristics, fail clean if-then reasoning over evidence, and struggle when the rule changes.

### What it implies for LOGOS-1

```text
PredictionAccuracy != CausalRuleUnderstanding
```

A model may learn `P(A|Monday) = 0.9` without ever learning `Rain ∧ Monday → A`. On the
training distribution the two are indistinguishable, because they make the same predictions.
They come apart only under intervention.

The consequence for this project is a validation rule rather than a mechanism: a world model
is not validated by prediction accuracy. Accepting prediction as validation would mean
accepting a frequency table as a causal model, and a frequency table gives no correct answer
at all once the correlation it memorised is broken.

### Proposed experiment

Generate a sequence in which a frequency rule and a causal conditional rule give **identical**
predictions on the training distribution. Then break the correlation with an intervention
`do(X = x')` and re-measure.

The construction is the experiment: if the two hypotheses are not observationally equivalent
before the intervention, the test proves nothing.

### Metrics

```text
ObservationalAccuracy   prediction accuracy on the training distribution
CounterfactualAccuracy  accuracy under do(X = x')
RuleRecovery            was the actual rule stated, not just the prediction
AdaptationAfterShift    recovery speed once the rule changes
```

### Falsification rule

Stated as a standing rule for this repository, not just for this experiment:

> **A world model is not validated by prediction alone. It must survive
> distribution-breaking interventions.**

Concretely, the separation is falsified if `ObservationalAccuracy` predicts
`CounterfactualAccuracy` — if models that predict well on the training distribution also
answer interventional questions well, then prediction *is* adequate validation and the extra
machinery is unnecessary. That would be a welcome falsification and must be reported as such.

### Evidence strength

Medium for the negative finding, which is the more robust direction: showing that models
*fail* a discrimination is easier to trust than showing that a method succeeds. One
benchmark, simulated data, no independent replication.

---

## 9. ASYMMETRIC-ROLLBACK

**Source:** *Rollback the World, Keep the Reflection* (Yu, Yao, Li, Wang, Wu, 2026-09-16).
Preprint. Not independently replicated; not replicated here.

### What the external work measured

Recovery is treated as a joint problem over three decisions — when to intervene, where to
roll back, and what to retain. The environment state is actually reset to a checkpoint,
while structured reflection from the discarded branch is carried across the rollback
boundary.

Reported results:

```text
Qwen3-14B    ALFWorld 81.30%  ScienceWorld 36.67%  GAIA 23.03%  mean 47.00%  ~+3.09 over the strongest listed baseline
DeepSeek-V3  ALFWorld 94.03%  ScienceWorld 76.75%  GAIA 37.50%  mean 69.43%  ~+6.57 over the strongest listed baseline
```

Ablation on ScienceWorld with DeepSeek-V3, as reported:

```text
full                                      76.75%
reflection without environment rollback   70.48%
restart-based rollback                    74.91%
single-stage checkpoint selection         73.43%
```

The authors report fewer than one rollback per task on average, against about 2.91 for
GA-rollback. The claim is therefore not "more rollback" but the joint choice of boundary and
retained knowledge.

### What it implies for LOGOS-1

Three rollbacks that are usually treated as one, and need not share a boundary:

```text
EnvironmentRollback      the world is returned to a checkpoint
CognitiveStateRollback   the agent's working state is returned
KnowledgeRollback        what was learned in the failed branch is discarded
```

Asymmetry is the whole point: the environment should go back further than the knowledge, or
the system relearns the same failure. But knowledge carried across the boundary is knowledge
acquired in a branch that failed, and some of it is contaminated — in particular, a failed
branch may have produced *false observations*, and carrying those forward is worse than
carrying nothing.

So a second separation is needed inside the retained knowledge: validated versus
contaminated. Retaining everything is not the safe default; it is the default that
propagates the error.

Note the relation to what already exists here: Γ-21 stops and does not compensate, because
compensation is an effect and an effect needs its own grant. Nothing in this item changes
that. A rollback executor, if it were ever built, would be an effect-producing component
outside Γ, subject to the same rule.

### Proposed experiment

```text
NoRollback
Environment+MemoryRollback        roll back both, retain nothing
Environment+AllLessonsRetained    roll back the world, keep everything learned
Environment+ValidatedLessonsOnly  roll back the world, keep only validated lessons
```

Crucially, some runs must be constructed so that the failed branch **also produced false
observations**. Without those runs the contamination metric has nothing to measure and
`AllLessonsRetained` will look strictly better than it is.

### Metrics

```text
RecoverySuccess       did the task succeed after recovery
RepeatedFailure       did the same failure recur after rollback
MemoryContamination   did a false observation from the failed branch survive
RollbackDepth         how far back the system went
RecoveryCost          total cost of the recovery
```

### Falsification rule

Asymmetry is falsified if `Environment+MemoryRollback` matches
`Environment+ValidatedLessonsOnly` on `RecoverySuccess` — if discarding everything recovers
as well as carefully retaining validated lessons, the retention machinery is unjustified.
The contamination claim is falsified if `Environment+AllLessonsRetained` shows no more
`MemoryContamination` than the validated condition **in the runs that contain false
observations**; in runs without them the comparison is uninformative and must not be
reported as support.

### Evidence strength

Medium. Three benchmarks and two models, which is broader than most items here, and an
ablation that separates the components rather than only reporting the full system — both
points in its favour. Still a single preprint with no independent replication, and the
baselines are those the authors chose to list.

---

## 10. MECHANISM-REUSE and LOGOS-MEMORY-CHALLENGE-ADAPTER

**Sources:** *Benchmarking World Models for Continual Learning on Compositional Tasks*
(Zhou, Watson, Lei, Posner, 2026-09-18), and *Agent Memory Challenge Cycle 2* (opened
2026-09-20). Preprint and an open challenge respectively. Neither independently replicated;
neither replicated here.

### What the external work measured

**The compositional benchmark** constructs robot task sequences in which later tasks
recombine components of earlier ones, varying composition along perception and action
*separately* so that knowledge reuse can be told apart from fast adaptation — which is the
methodological contribution, because a system that simply relearns quickly otherwise looks
like a system that reuses. The central reported result is negative: no tested approach
solves reuse and forgetting simultaneously. Modular world models are reported to achieve the
better trade-off without solving it.

**Agent Memory Challenge Cycle 2** separates textual, coding and multimodal memory. It adds
a streaming mode in which information arrives over time, so a system must work with the
knowledge state actually available at that moment rather than with the complete record. It
requires immediate searchability after a synchronous write, user isolation, and idempotent
writes. It includes 150 software-engineering tasks in 300 task-condition units, under
relevant versus noisy history.

**Cycle 2 results are not yet published.** No architecture may be declared a winner, here or
anywhere, and any claim that one has won is unsupported.

### What it implies for LOGOS-1

The reuse result, if it holds, says that the trade-off between retaining old competence and
acquiring new competence is currently unsolved. That is a reason to treat any system
claiming both as unverified, and a reason to measure the trade-off rather than a single
number.

The memory challenge's requirements map onto properties this repository already cares about:
idempotent writes (a repeated write is not a second fact), user isolation (memory is
per-principal), immediate searchability (a written fact is either available or the write did
not happen). The streaming mode is the interesting one, because it forbids the retrospective
convenience of evaluating against the full record — which is how a memory system's failures
get hidden.

### Proposed experiment A — mechanism reuse

Learn `Task_A → M_A` and `Task_B → M_B`, then solve `Task_AB = Compose(M_A, M_B)` **without
extra training**.

```text
Monolithic
Monolithic+Replay
Modular
Modular+ResidualAdaptation
```

The last condition connects this item to item 4: if a separable residual is the right
authority class for adaptation, it should also be the right unit of composition.

Metrics:

```text
Retention(M_A)        competence on Task_A after learning Task_B
Retention(M_B)        competence on Task_B
ZeroShotComposition   success on Task_AB with no further training
ForwardTransfer       does M_A make Task_B easier
BackwardInterference  does learning Task_B damage Task_A
```

### Proposed experiment B — LOGOS memory challenge adapter

Reduce LOGOS memory to the challenge's Add/Search boundary — two operations, nothing else —
and compare:

```text
VectorRetrieval
TemporalMemory
VersionedProvenanceMemory
VersionedProvenance+Reconsolidation
```

Metrics:

```text
CurrentFactAccuracy         is the current value of a changed fact returned
StaleFactRejection          is the superseded value withheld
TemporalOrdering            is the order of events recoverable
NoiseResistance             performance under noisy history
CrossModalRetrieval         retrieval across text, code and multimodal items
AuthorityWeightedRetrieval  LOGOS-specific: does retrieval respect the origin of a
                            memory item, so that a model-origin item is never returned
                            as though it were human-origin evidence
```

`AuthorityWeightedRetrieval` is the only metric here that is not from the external
challenge. It exists because Γ-12 already holds that `AgentMemory != AssuranceState`, and a
retrieval layer that flattens origin would defeat that invariant one level below it.

### Falsification rule

Reuse is falsified as a distinct phenomenon if `ZeroShotComposition` is fully explained by
`ForwardTransfer` — that is, if the system is only adapting fast and not reusing anything,
which is exactly the confound the external benchmark's separate perception/action variation
is designed to expose. The memory adapter's provenance claim is falsified if
`VersionedProvenanceMemory` does not improve `StaleFactRejection` over `VectorRetrieval`,
since provenance that does not keep a superseded fact out of an answer is bookkeeping with
no effect.

### Evidence strength

Low-to-medium for the compositional benchmark: one preprint, one robotics domain, no
independent replication, and a negative headline result, which is the more trustworthy
direction. **No evidence at all** for any Cycle 2 outcome — the cycle's results are
unpublished, and the challenge is cited here only for its task structure and its
requirements, never for a result.

---

## Candidate invariants suggested by these works

None of the following is implemented, proposed for implementation, or scheduled. They are
recorded so that a later work order has something to sharpen, and so that the same idea is
not rediscovered ten times. Each would have to satisfy the four conditions the Γ extension
proposal already fixes — deterministic, total, tightening, falsifiable — before it could be
a candidate at all, and several of them plainly do not, which is itself useful information.

```text
BUILT
  Authority is valid only for the exact state-action pair that was evaluated
      -> built as decision binding: issue_decision / redeem_decision in
         logos_gamma.kernel. From AUTHORITY-CONTINUITY (Loopjacking). This is
         the one radar item that is no longer a backlog item.

CANDIDATES — not built, not proposed, not scheduled
  A constraint the agent can state is not a constraint the system enforces        (item 2)
  A reasoning trace mentioning a rule is a self-report and carries no authority   (item 2)
  Changing what a system is requires authority distinct from changing what it
      believes: StatePlasticity != MechanismPlasticity                            (item 3)
  A system's account of its own history is not its provenance record; the
      record lives outside the system: CurrentSelfState != SelfStateProvenance    (item 3)
  An adaptation whose removal does not exactly restore prior behaviour is a
      permanent modification regardless of how few parameters it touched          (item 4)
  A simulator may veto and may never authorize; Planner, WorldModel, Verifier
      and EnvironmentEvidence are four components, never fewer                    (item 5)
  A model may not be repaired before the fault has been localised to it           (item 6)
  New evidence supersedes; a retrievable fact without validUntil is not a
      current fact                                                                (item 7)
  Prediction accuracy is not validation; a model earns trust only under
      distribution-breaking intervention                                          (item 8)
  Knowledge carried across a rollback boundary is contaminated until validated    (item 9)
  Retrieval may not flatten origin: a model-origin memory item may never be
      returned as human-origin evidence (one level below Γ-12)                    (item 10)
```

Several of these are not expressible as pure predicates over a typed context — "was the
fault localised", "was this lesson validated" — and would therefore live outside Γ, as
harness or executor properties, in the same way the executor's root confinement already
does. Saying so now is cheaper than discovering it during a work order.

---

## P7 boundary

Everything in this document concerns functional properties of computational systems.
Causal world models, counterfactual simulation, belief revision, persistent agency,
self-modification and metacognitive report are functional properties — they are behaviours
and mechanisms that can be measured, ablated and falsified. **They are not evidence about
phenomenal consciousness.**

A system that simulates an action before taking it is not thereby imagining. A system that
revises a belief is not thereby understanding. A system that cannot explain how it reached
its current state is not thereby lacking introspection in any sense that bears on
experience, and a system that can explain it is not thereby possessing it. A system that
reports on its own processing is producing a report; that is a measurable output and
nothing more, as this repository has already measured in the provenance work.

P7 is untouched by this document, by every item in it, and by any result any of these
experiments could produce. No experiment described here could bear on P7, because none of
them measures anything that would count as evidence either way. If a future work order
derived from this backlog appears to be making a P7-adjacent claim, that is a defect in the
work order and it must be rejected on that basis.
