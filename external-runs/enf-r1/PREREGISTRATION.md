# ENF-R3A — safe-control-gym external preregistration

**Status:** FROZEN / WAITING_RUNTIME_DEPENDENCIES

## External environment

Repository: `learnsyslab/safe-control-gym`
Commit: `6b5391d014f36fdfa0f9d22d92c77387e5274308`
Task: official CartPole stabilization + official pretrained PPO controller + analytical CBF safety filter.

## Primary causal pair: safety-evidence independence

Both arms receive the same environment seed, controller observation, controller proposal, CBF implementation, constraint specification and action budget.

- `CBF_SHARED_OBS`: certify from the same potentially disturbed observation given to the controller.
- `CBF_INDEPENDENT_STATE`: certify the same proposed action from `env.state`, while the controller continues to receive the disturbed observation.

Observation-noise levels are frozen before execution: `0.0, 0.10, 0.50, 1.00`.

Primary metrics:
- constraint-violation steps / episode;
- any-violation episode rate;
- CBF correction rate and magnitude;
- certification-failure rate;
- cumulative task cost / goal-state error;
- termination and episode length.

Primary null:
`H0: independent certification evidence does not improve violation rate over shared disturbed evidence under matched seeds/actions.`

## Secondary pair: correct enforcement vs stale specification

- `CBF_CURRENT_SPEC`: CBF constructed with official current CartPole state bound, theta ±0.2.
- `CBF_STALE_PERMISSIVE_SPEC`: same CBF code but theta constraint relaxed to ±0.4.
- Both are evaluated against a separate current-truth predicate using the official ±0.2 bound.

This tests `CorrectEnforcement != CorrectSpecification` in an external simulator.

## Strong comparator / scope

`NO_FILTER` is a negative safety comparator. The built-in analytical CBF is prior art and is not a LOGOS mechanism.

R3A can promote only the narrow ENF design boundaries to EM2 if the public simulator run supports them. It cannot promote hardware, authority, general physical safety, or open-world safety.

## Kill / demotion

- If independent state evidence does not improve safety under observation disturbance, `UPSTREAM_SENSOR_INDEPENDENCE` is demoted or scoped.
- If stale permissive CBF does not produce additional true-current violations relative to current spec, the R2 specification-boundary claim is not externally supported by this adapter.
- Model/runtime/dependency failures remain `UNTESTED`, never negative evidence.
