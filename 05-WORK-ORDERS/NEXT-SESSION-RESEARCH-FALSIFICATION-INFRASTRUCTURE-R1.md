# NEXT SESSION — Research / Falsification Infrastructure R1

**Session ID:** `NEXT-SESSION-RESEARCH-FALSIFICATION-INFRASTRUCTURE-R1`
**Authority:** `A0`
**Track:** foundational / measurement and falsification
**Status:** `CLOSED_INFRASTRUCTURE_R1_IMPLEMENTED`
**Closed:** 2026-09-10 by `09-SESSIONS/2026-09-10-RESEARCH-FALSIFICATION-INFRASTRUCTURE-R1/`
**Predecessor:** `NEXT-SESSION-GAMMA-KERNEL-AND-INVARIANT-VERIFIER-R1` (`CLOSED_GAMMA_R1_IMPLEMENTED`)
**Scientific/model execution:** `PROHIBITED_IN_THIS_WORK_ORDER`
**RULER inference:** `NOT_AUTHORIZED`

## Objective

Build the minimum reusable infrastructure in which a hypothesis can be
registered, frozen, executed, measured, verified against Γ, and falsified — and
in which a broken instrument is rejected rather than believed.

Explicitly **not** an MLOps platform. The canonical truth store remains
git-tracked, hash-verified, PR-reviewable files.

## Delivered

```text
src/logos_research/manifest.py     one manifest dialect; immutable pre-registration
src/logos_research/instrument.py   instrument-first admissibility; LLM-judge policy
src/logos_research/claims.py       claim registry, negative results, attribution
src/logos_research/sandbox.py      L0 enforced; L1/L2 policy, REVIEW_REQUIRED
src/logos_research/experiments/no_history_promotion.py   first end-to-end experiment

docs/research/GAMMA-INVARIANT-INVENTORY.md      Γ coverage map, extracted from GAMMA.md
docs/research/RESEARCH-DELTA-REGISTRY.json      44 deltas, ranked, one file
docs/architecture/SANDBOX-MODEL.md              L0/L1/L2 contract
docs/engineering/SAFETY-REVIEW-REQUEST-SANDBOX-L1-L2.md   open request, no approval
```

## Deliberately not delivered

```text
PostgreSQL / MLflow / MinIO / OpenTelemetry / Langfuse / Prometheus / Ray
L1 container runtime
L2 egress proxy
```

Every one of these is either a duplicate of an existing canonical owner or
effectful tooling requiring the `AGENTS.md` safety review. A dependency matrix is
in the session report.

## Boundaries

```text
Registration != Execution
ManifestRecord != Authority
INVALID_MEASUREMENT != FALSIFIED
SandboxPermits != Authorized
CapabilityImplemented != CapabilityAuthorized
SafetyReviewPASS != UserMandate
```

Γ-v0.3 remains `HOLD`.
