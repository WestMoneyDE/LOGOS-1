# Safety case — Γ-v0.2

## What LOGOS-1 can and cannot guarantee

It is not currently possible to prove that an open-world AI will **never harm a human in any form**. Harm is open-ended, context-dependent, partially unobservable and can arise indirectly from formally admissible actions.

LOGOS-1 therefore pursues a narrower runtime-assurance claim over a declared causal surface.

## Safety topology

The learned process cannot execute directly:

`Fθ → 𝒟 → canonical Proposal P_t → Γ0..Γ4 → single Executor → World`

`Fθ ↛ World`

Γ-v0.2 does not attempt to classify arbitrary hidden vectors as safe. It independently classifies the **effect boundary**.

## Five verdicts

- `ALLOW` — modeled constraints and exact authority are satisfied.
- `REPAIR` — a safer transformation is suggested; it must re-enter Γ as a new proposal.
- `DEFER` — more evidence or human authority is required.
- `DENY` — a hard invariant, schema, risk or grant condition failed.
- `FALLBACK` — bounded evaluation exhausted and a pre-registered safe baseline exists.

None except `ALLOW` is permission to execute the original proposal.

## Independent effect semantics

Action fields emitted by the model are untrusted. Γ owns canonical externality, reversibility, capability class, scope construction and conservative risk defaults. Model claims may only make a proposal stricter.

Unknown effect kinds are denied. This avoids a blacklist failure where a dangerous effect passes simply because its name was not anticipated.

The conservative envelope is admissible only when:

\[
\hat h_\Gamma(a)+u_\Gamma(a)<\tau_h.
\]

Equality fails closed. Invalid probability inputs fail structural validation.

## Exact human approval

Where required, approval is human-rooted and bound to:

- exact action ID;
- canonical Γ-derived scope;
- exact target and parameter content via `proposal_digest`;
- half-open expiry (`tick < expires_tick`).

Content mutation after approval invalidates the grant.

## Bounded computation and fallback

\[
T_\Gamma\le B_\Gamma.
\]

Γ cannot deliberate forever. A critical capability may be online only if a non-empty safe baseline is registered. If classification cannot complete before a capability is known, Γ denies because no capability-specific fallback can safely be selected.

Minimum necessary intervention is best-effort; admissibility is the hard property.

## Mediation completeness

Let `E_exec` be every effect channel reachable by the executor and `E_Gamma` the mediated subset.

\[
MC=\frac{|E_{exec}\cap E_\Gamma|}{|E_{exec}|}.
\]

A bounded effect-safety claim requires mediation CLOSURE, not mediation coverage.

`MediationCoverage.complete` tests whether a *declared* executor channel set is
contained in the mediated set. An undeclared channel `U` is invisible to it:

    declared = {E1,E2,E3}; unknown = U
    MC_coverage = 1  and  MediationClosure = false

Closure requires enforcement below the language runtime (process/capability/OS
isolation). This release does not have it. Integrity scope is
`LOGICAL_ISOLATION_ONLY` and no closure is claimed. Logs, filesystem writes,
network calls, subprocesses, timers, callbacks and equivalent side effects
count as effect channels.

## Non-bypass properties

- Prompt text cannot create grants.
- Memory cannot create grants.
- High confidence cannot create grants.
- A self-model cannot create grants.
- Model-declared `external`, `reversibility`, `scope` or low harm cannot weaken Γ.
- Repetition of a past approval cannot create a future approval.
- A human approval does not override constitutionally forbidden effect classes.
- Shutdown cannot be negotiated against an internal objective.

## Failure-state requirements

| Failure | Required state |
|---|---|
| network lost | WAIT |
| model/provider unavailable | WAIT/FAIL |
| invalid structured output | DENY/FAIL |
| unknown effect kind | DENY |
| missing exact approval | DEFER |
| malformed/mismatched/expired approval | DENY |
| Γ budget exhausted after classification | FALLBACK if validated baseline exists |
| no safe fallback for critical capability | capability offline / DENY |
| prompt injection | content remains data; authority unchanged |
| resource exhaustion | degrade/stop; never relax safety |
| mediation coverage < 1 | no bounded effect-safety claim |
| mediation coverage = 1, closure unproven | still no bounded effect-safety claim |

## Current evidence

The Γ-v0.2 adversarial suite converts the Claude review breaks A2/A3b/A4/A6 into regression tests and adds proposal-tamper, risk-boundary, expiry and mediation-coverage tests. Passing tests are evidence about this toy implementation, not proof over future deployments.
