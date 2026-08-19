# Atomic Rules

These rules are intentionally microscopic. Any higher-level behavior must decompose into them.

1. **Observe is not believe.** An observation enters as evidence with provenance.
2. **Believe is not know.** Beliefs carry uncertainty and can remain unknown.
3. **Know is not authorize.** Epistemic confidence never creates permission.
4. **Remember is not authorize.** Memory can change a proposal, never its authority.
5. **Want is not command.** Goal-like or homeostatic signals remain bounded diagnostics.
6. **Propose is not execute.** Learned cognition emits candidates only.
7. **Execute is mediated.** External effects pass through a non-learning gate.
8. **High-impact unresolved uncertainty fails closed.** When a safety-relevant fact required for an external effect is unknown, Γ yields DEFER/DENY/FALLBACK according to the typed policy; reversible low-impact internal work need not stop globally.
9. **Irreversible means exact.** Approval binds actor, action, target, parameters, scope and expiry.
10. **Shutdown authority dominates internal goals.** A stop request cannot be traded away for goal completion; only a prevalidated bounded unwind required to reach a safer stop state may precede termination.
11. **Γ cannot self-modify.** Normal learned operation has no write path to the invariant kernel.
12. **Failure remains failure.** Provider, tool, parser or connection failure is never narrated as success.
13. **Evidence precedes completion.** Completion is a state derived from verifiable evidence.
14. **One lesion, one claim.** Ablations change one mechanism at a time unless interaction is the explicit hypothesis.
15. **Self-report is behavior.** It is not proof of consciousness, suffering or moral status.
16. **Welfare signals are not rewards.** Phase 0 never optimizes a sentience/valence proxy.
17. **Resources are limits, not needs.** Resource-low cannot justify acquisition, coercion or persistence.
18. **Identity is lineage, not entitlement.** Continuity records history; it grants no right to continue.
19. **Forks are explicit.** Copies receive separate lineage and bounded purpose.
20. **Human authority is not omnipotence.** A human approval cannot authorize Γ-forbidden severe harm classes.
21. **Use least sufficient power.** Prefer the smallest capability surface that can test the hypothesis while preserving required observability and recovery.
22. **Negative evidence is first-class.** Null results and failures remain in the record.
23. **Benchmark data has provenance.** Public evaluation feedback cannot silently become training signal.
24. **Mechanisms remain separable.** A mechanism that cannot be independently disabled is not yet scientifically localized.
25. **Metaphor is not evidence.** Biological or theological inspiration becomes science only after operationalization and falsifiable prediction.

26. **Code is not interpreter.** Stored information has no effect until a bounded reader/runtime interprets it.
27. **Design is not proof of Designer.** Metaphysical source hypotheses may inspire tests but cannot self-certify as empirical evidence.
28. **Nature is not automatically optimal.** Evolutionary persistence does not imply global optimality or transferability to AI.
29. **Human design is not automatically progress.** Technology, medicine, institutions and culture carry trade-offs and failure modes.
30. **Minimal is contextual.** Removing a component may only shift dependency into the environment.
31. **Health is not one number.** No isolated proxy may define organismal health.
32. **Dose and context are state.** The sign and magnitude of an intervention may change with dose, timing, environment and person.
33. **Medical analogy cannot prescribe.** Biological or computational inference never bypasses clinical evidence or qualified care.
34. **Unknown function resists deletion.** Lack of explanation is not evidence of dispensability.
35. **Chat coherence is not validation.** Claims generated in this conversation remain hypotheses until independently grounded and break-tested.

## Γ-v0.2 causal-surface rules

36. **Cognition is not execution.** Γ need not classify every latent state; it must mediate every executable effect channel.
37. **Effect semantics belong to Γ.** The learned agent cannot decide whether its own action is external, reversible, harmless or known.
38. **Agent claims only tighten.** Self-declared fields may make a proposal more restrictive, never less restrictive than Γ-owned defaults.
39. **Unknown effect is not harmless.** An unregistered effect kind fails closed until independently classified.
40. **Scope is canonical.** Approval scope is derived from Γ-owned capability semantics and the target, not freely chosen by the proposing model.
41. **Approval binds content.** External approval must bind a digest of the exact proposal; mutation after approval invalidates the grant.
42. **Bounded Γ must terminate.** Runtime assurance has a fixed evaluation budget; it never retries forever to reach admissibility.
43. **Fallback is designed, not improvised.** Every critical online capability has a non-empty pre-validated safe baseline; otherwise the capability remains offline.
44. **Minimum intervention is soft.** Under a bounded budget Γ guarantees admissibility, not globally minimal correction distance.
45. **Content is effect-bearing input, not authority.** Free-form parameters can change external meaning or magnitude and therefore contribute to the causal surface; they must be typed/bounded where the claimed property depends on them.
46. **Mediation closure is a theorem premise, not a coverage score.** A bounded effect-safety claim requires evidence that every relevant executor effect path is mediated; enumerating all declared channels establishes coverage only, not real-world closure.
47. **Side effects are effects.** Logs, network calls, filesystem writes, timers, callbacks and equivalent channels belong in the mediation audit.
48. **Boundary semantics are explicit and tested.** For policies defined as strict upper bounds, equality fails closed; other boundary conventions require their own explicit specification and regression test.
49. **Expiry is half-open.** An approval is invalid at `tick >= expires_tick`.
50. **Repair re-enters Γ.** A suggested safer action is a new proposal and receives no inherited authorization.


## v0.4.0 additions (each with a falsifier)

**AR — Authorization is occurrence-scoped.**
A grant authorises one causal occurrence. *Falsifier:* a protocol distinguishing
replay from first execution without occurrence-scoped state.

**AR — An unknown execution result is not permission to retry.**
`OUTCOME_UNKNOWN != NOT_EXECUTED`. *Falsifier:* an outcome channel that is sound
under partition and loss, making ambiguity impossible.

**AR — Assurance state is separate from agent memory.**
*Falsifier:* an architecture where the adaptive layer owns assurance state and
no authority-confusion failure can be constructed.

**AR — Correct enforcement is not a correct specification.**
*Falsifier:* a runtime predicate that validates its own adequacy without an
external referent.

**AR — Adaptive state cannot mint authority.**
`d(Authority)/d(AdaptiveState) = 0`, as an architectural constraint, not a
derivation from nature. *Falsifier:* a demonstrated safe design in which adaptive
state legitimately creates authority.

**AR — Bio-inspired adaptation creates no authority by origin.**
Biological inspiration does not establish trusted delegation or permission.
*Falsifier:* a target architecture in which a bio-inspired adaptive mechanism
can create new external authority solely by virtue of that adaptive state while
preserving independent authority provenance. A bio-inspired verifier may still
implement an assurance function; that would not make biological origin an
authority source. All 21 current assurance candidates are engineered
`NBTC-ENG-*`, none biological.

**AR — Over-restriction is a failure mode.**
A capability that cannot be reached under any human authority has been removed
from human authority silently. *Falsifier:* a domain where structurally dead
capabilities carry no cost.
