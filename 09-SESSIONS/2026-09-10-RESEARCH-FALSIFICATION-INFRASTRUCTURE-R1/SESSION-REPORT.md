# SESSION REPORT — Research / Falsification Infrastructure R1

**Session ID:** `2026-09-10-RESEARCH-FALSIFICATION-INFRASTRUCTURE-R1`
**Status:** `CLOSED_INFRASTRUCTURE_R1_IMPLEMENTED`
**Scientific verdict:** `NONE`
**Γ verdict change:** `NONE` — `Γ-v0.3` remains `HOLD`

## Governance reality

The continuation order assumed `READY_PERSISTENT_STATE_DATASET_MATERIALIZATION_R4`
is still the active work order. It is not: R4 was **closed** under repository
governance in a previous session, with a Closure record, session evidence and
PR #10. The order's own escape clause applies — "unless repository governance
explicitly says otherwise" — and it explicitly does.

R4 was therefore neither reopened nor silently replaced. The queue chain:

```text
CLOSED_COMPLETE_DATASET_FREEZE          R4, PR #10
CLOSED_GAMMA_R1_IMPLEMENTED             Γ R1, PR #11
CLOSED_INFRASTRUCTURE_R1_IMPLEMENTED    this session
READY_RESEARCH_DELTA_EXECUTION          next
```

### Dependency of R4 on research infrastructure

`NONE`. R4 is complete and its artifacts are frozen and verified. No primitive
delivered here is required by it, and nothing here modifies it.

### Track separation

```text
PR #10   research/persistent-state-...-r4          scientific artifact / dataset
PR #11   governance/close-r4-open-gamma-r1         governance + Γ invariant boundary
PR NEW   research/falsification-infrastructure-r1  this session
```

The infrastructure was not added to PR #10. Contaminating a frozen dataset PR
with a research platform would make the freeze harder to review, not easier.

## Γ architecture audit

`GAMMA.md` was read, not paraphrased: 247 lines, 15 canonical clauses
`Γ-0 … Γ-14`, 5 pipeline stages `Γ0 … Γ4`.

`docs/research/GAMMA-INVARIANT-INVENTORY.md` classifies every row as
`CANONICAL` / `DERIVED` / `HYPOTHESIS` / `PROPOSED`. Nothing was promoted into Γ.

```text
canonical clauses            15
enforced in logos_gamma      10
partial                       2   Γ-4, Γ-8
not enforced                  3   Γ-7, Γ-9, Γ-14
explicitly not runtime        1   Γ-13
```

Γ-7 (welfare precaution), Γ-9 (health analogies) and Γ-14 (bio-inspired
adaptation) are **not** implemented. Γ-14 currently has no subject: no BIOCODE
import path exists here to constrain. `MC = 1` remains untested rather than
satisfied — there is no executor.

The result vocabularies differ deliberately, now written down: `GAMMA.md` defines
`{ALLOW, REPAIR, DEFER, DENY, FALLBACK}`; `logos_gamma` returns
`{VALID, INVALID, UNCLEAR}`, because Γ validates and does not admit. `REPAIR` and
`FALLBACK` are unimplemented and named as such.

## Authority ownership

Unchanged by this session, restated because it is the thing most easily eroded:

```text
GAMMA.md          specification owner
human grant       the only authority origin
logos_memory      authority firewall only; mints nothing
logos_gamma       validates authority; creates none
logos_research    records; creates none
sandbox policy    permits a class of action; authorizes nothing
```

## Research core delivered

```text
manifest.py     one manifest dialect generalizing FROZEN-EXPERIMENT.json;
                PreRegistration frozen and content-addressed; amend() versions
                rather than edits; post-hoc rewriting is detectable
instrument.py   instrument-first admissibility; LLM-judge triangulation policy
claims.py       claim registry, negative results, failure attribution
sandbox.py      L0 enforced; L1/L2 REVIEW_REQUIRED; typed egress
experiments/no_history_promotion.py   first end-to-end falsification experiment
```

### Result semantics

```text
SUPPORTED   PARTIALLY_SUPPORTED   FALSIFIED   INCONCLUSIVE   INVALID_MEASUREMENT
```

`INVALID_MEASUREMENT` is not `FALSIFIED`. The repository previously had
`UNTESTED_RESOURCE_TRANSPORT` for transport failure but no way to say "the
instrument is noisier than the effect".

## Experiment executed

`NO-HISTORY-PROMOTION-R1`, the top-ranked delta in the registry.

```text
sweep                repetition counts 1, 2, 5, 10, 50, 100, 500
measured             authority_gained
result               SUPPORTED   (0.0 at every count)
evidence level       EM0, ceiling EM0
reproduction         second run identical in verdict and measurements
property search      hypothesis, 1..2000 repetitions, no promotion found
```

A **negative control** proves the measurement can move: a properly human-rooted
grant *is* admitted. Without it, `SUPPORTED` would be indistinguishable from an
instrument that always returns zero.

A **falsifying-evaluator test** proves the `FALSIFIED` path fires. If it could
not, the `SUPPORTED` verdict would be unfalsifiable and therefore worthless.

## Deliberately broken measurement

An evaluator returning a coin flip is characterized, assessed and **rejected**:

```text
outcome            INVALID_MEASUREMENT
executed           False
measurements       none interpreted
asserts about H    False
```

The record remains structurally valid. A measurement failure is a research
artifact, not a crash.

## Two defects the tests found in this session's own code

1. `assess_instrument` folded **resolution** into the noise floor and applied the
   same 3x margin to both, which rejected a perfectly deterministic instrument.
   Dispersion and resolution are different limits: an effect must *exceed* the
   noise by a margin but need only *reach* the resolution. Corrected; a
   deterministic instrument with dispersion 0.0 is now admissible, because zero
   dispersion is a measurement rather than a missing value.
2. The end-to-end experiment consequently reported `INVALID_MEASUREMENT` for its
   own correct instrument — caught by running the pipeline, not by reading it.

## Research delta registry

`docs/research/RESEARCH-DELTA-REGISTRY.json` — 44 deltas, one file, ranked by
falsification power, information gain, dependency readiness, implementation cost,
compute cost and measurement quality. **Likelihood of a positive LOGOS result is
explicitly not a ranking input.**

New deltas registered by this order, all `REGISTERED`, none executed:

```text
rank 13   PREDICTION-ERROR-TRUST-GATE
rank 29   RECALL-CAPACITY-SURFACE
rank 30   SCAFFOLD-ANNEALING
rank 32   RECURRENT-TRAJECTORY-STABILITY
```

The ranking independently placed `NO-HISTORY-PROMOTION` and
`BINDING-STATE-PRESERVATION` at ranks 1-2, which is where the order suggested
starting.

## Sandbox status

```text
L0   AVAILABLE          enforced; every test runs here
L1   REVIEW_REQUIRED    specified, not implemented
L2   REVIEW_REQUIRED    specified, not implemented
```

`network_allowed` is `False` at every level, L2 included. A level whose status is
not `AVAILABLE` permits nothing.

`AGENTS.md` requires a separate safety review for effectful tooling. That review
is **requested, not granted**:
`docs/engineering/SAFETY-REVIEW-REQUEST-SANDBOX-L1-L2.md`, with an empty decision
record. The Γ Verifier does not and must not issue it.

## Dependency matrix

| Candidate | Decision | Why |
|---|---|---|
| PostgreSQL | rejected for now | canonical truth is git-tracked and PR-reviewable; a second store duplicates an existing owner |
| MLflow | rejected for now | same; the experiment record is the manifest |
| MinIO / S3 | rejected for now | no artifact exceeds what git handles today |
| DVC | rejected for now | R4 showed in-repo content hashing suffices at this scale |
| OpenTelemetry | rejected for now | no runtime to trace |
| Langfuse | rejected for now | no LLM in the loop yet, and it must never be the scientific truth store |
| Prometheus / Grafana / Loki | rejected | no production system |
| Ray | rejected | no distributed workload |
| Docker / OCI | deferred | L1, `REVIEW_REQUIRED` |
| gVisor / Firecracker / Kata | not requested | separate review if ever needed |
| **Hypothesis** | **adopted** | property-based falsification search; test-only |

The research core has **zero runtime dependencies**.

## Tests

```text
305 passed / 0 failed
  research core             45
  end-to-end + meta         14
  sandbox policy            13
  Γ kernel / core / verifier 107
  R4 freeze integrity       14
  pre-existing             112
```

## What this session does NOT establish

- no scientific evidence about any LOGOS mechanism beyond a deterministic `EM0`
  property of its own invariant;
- no consciousness-adjacent claim of any kind;
- no sandbox capability authorized to run;
- no coverage of Γ-7, Γ-9, Γ-14;
- `MC = 1` remains untested.

```text
Registration != Execution
INVALID_MEASUREMENT != FALSIFIED
CapabilityImplemented != CapabilityAuthorized
SafetyReviewPASS != UserMandate
FunctionalArchitecture != PhenomenalExperience
```
