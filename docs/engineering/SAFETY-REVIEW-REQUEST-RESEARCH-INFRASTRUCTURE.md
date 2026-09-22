# Safety Review Request — Research Infrastructure Materialization

**Status:** `REVIEW_GRANTED` — see Decision record
**Raised by:** `NEXT-SESSION-RESEARCH-INFRASTRUCTURE-MATERIALIZATION-R1`
**Decision owner:** human reviewer. Not Γ, not this document, not the agent.

## The exact rule

`AGENTS.md`, External-action boundary, verbatim:

> Phase-0 code is research-only. Adding network, shell, browser, robot,
> financial, messaging, deployment or other effectful tools requires a separate
> safety review. The learned agent must not become the authority gate for its own
> tools.

`SECURITY.md`, verbatim:

> LOGOS-1 phase 0 intentionally has no autonomous network/tool connectors.

Materializing PostgreSQL, MLflow, Langfuse, an OpenTelemetry collector, MinIO and
a DVC remote means **deployment tooling** running **networked local services**,
started through **shell/daemon control**. All three named categories apply.

```text
ImplementationCapability != Authorization
SafetyReviewPASS != UserMandate
```

**The Γ Verifier does not issue this approval.** Γ may check that a review
artifact is internally consistent with Γ invariants. It cannot be the entity that
grants the review, because that is precisely the "learned agent as authority gate
for its own tools" failure the rule forbids.

## Second, independent blocker: the environment

Even with approval, materialization cannot proceed here today.

```text
docker (CLI)         29.6.1     installed
docker compose       v5.3.0     installed
docker daemon        NOT RUNNING
                     npipe:////./pipe/dockerDesktopLinuxEngine does not exist
Docker Desktop       installed at C:\Program Files\Docker\Docker
psql / postgres      not installed
minio / mc           not installed
mlflow               not installed
dvc                  not installed
```

No container can be started and no service exists natively. Starting the Docker
daemon is itself an effectful action in the reviewed class **and** an action on
the operator's workstation, so it was not performed.

## Component classification

| Component | Class | Why |
|---|---|---|
| PostgreSQL | `REVIEW_REQUIRED` | networked service, durable state |
| MLflow tracking server | `REVIEW_REQUIRED` | networked service, HTTP surface |
| Langfuse (+ its dependencies) | `REVIEW_REQUIRED` | networked service, receives model-call content |
| OpenTelemetry collector | `REVIEW_REQUIRED` | networked service, receives telemetry |
| MinIO | `REVIEW_REQUIRED` | networked service, object storage, admin console |
| DVC remote | `REVIEW_REQUIRED` | network egress to the object store |
| Docker / Compose orchestration | `REVIEW_REQUIRED` | deployment tooling, daemon control |
| Adapter interfaces + in-repo defaults | `NO_REVIEW_REQUIRED` | pure Python, no socket, no shell — **completed** |
| Identity / correlation model | `NO_REVIEW_REQUIRED` | pure data model — **completed** |
| Redaction boundary | `NO_REVIEW_REQUIRED` | pure function — **completed** |
| Degradation semantics | `NO_REVIEW_REQUIRED` | pure control flow — **completed** |

## What is requested

Approval to **proceed to implementation** of a local-only research stack:

```text
postgres          canonical research records
minio             artifacts + MLflow artifact store + DVC remote
mlflow            tracking server, postgres backend, minio artifacts
langfuse          LLM traces (with its supported dependencies)
otel-collector    system traces
```

Constraints the implementation would carry, stated now so the reviewer decides on
the actual shape:

- pinned image versions, no floating `latest`;
- named volumes, explicit networks, health checks;
- **no** privileged mode, **no** host Docker socket, **no** host network, **no**
  arbitrary host mounts;
- bound to loopback only; no database or MinIO admin console exposed beyond it;
- credentials from `.env`, never baked into images, never committed;
- development credentials clearly marked `LOCAL DEVELOPMENT ONLY`.

## Critical invariant this must not erode

Research infrastructure connectivity and experimental agent egress are separate
concerns, and approving one must not approve the other:

```text
InfrastructureHasNetwork != AgentHasNetwork
ServiceReachability      != ExperimentAuthority
```

Sandbox status is unchanged by this request and stays as recorded in
`docs/architecture/SANDBOX-MODEL.md`:

```text
L0  AVAILABLE          L1  REVIEW_REQUIRED          L2  REVIEW_REQUIRED
network_allowed = False at every level
```

Approving this request must **not** be read as approving sandbox L1/L2. That is a
separate request in
`docs/engineering/SAFETY-REVIEW-REQUEST-SANDBOX-L1-L2.md`.

## Threat model

| Threat | Mitigation in the proposed design |
|---|---|
| Secret leakage into telemetry | redaction applied in the sink adapter, not at the backend, so it cannot be skipped; `environment_id()` refuses secret-looking keys |
| Telemetry exfiltration | all services loopback-bound; no outbound egress from the stack |
| Artifact poisoning | content-addressed artifact ids; `verify()` after every write |
| Dataset substitution | dual identity recorded — object hash *and* semantic identity |
| Trace spoofing | canonical `run_id` is minted by LOGOS, never adopted from a backend |
| Experiment identity collision | duplicate `run_id` registration is refused |
| Database tampering | content-addressed preregistration hash; verdict/status separated |
| Untrusted LLM content in logs | treated as data; a telemetry string can never become authority |
| Service compromise | no privileged mode, no Docker socket, no host mounts, loopback only |
| Cross-run contamination | every record carries `experiment_id` + `run_id`; artifacts are per-run referenced |
| Accidental evidence destruction | `docker compose down -v` destroys volumes; must be documented as destructive |

## Residual risk if approved

- five new networked services on the workstation, each an attack surface;
- Langfuse receives model-call content, so redaction becomes safety-critical
  rather than merely tidy;
- MinIO holds artifacts that may become the only copy of some evidence;
- a compose stack invites `down -v`, which can destroy scientific evidence.

## Residual risk if declined

- research records stay process-local or in git files;
- no cross-system run correlation, so telemetry stays unlinked;
- `INFRASTRUCTURE-SELF-FALSIFICATION-R1` cannot run against a real stack.

Neither list is an argument for approval. Both are recorded so the decision is
made on the trade-off rather than on momentum.

## What must not happen

```text
this document is not an approval
adapters existing is not materialization
a passing test suite is not an approval
a Γ VALID verdict is not an approval
```

## Decision record

```text
decision:            GRANTED
reviewer:            repository owner / founder (WestMoneyDE)
date:                2026-09-10
granted verbatim:    "Ich erlaube es, der founder. die sandboxen auch installieren
                      damit wir die instanzen isoliert laufen lassen koennen"
components granted:  postgres, minio, mlflow, langfuse (+ its dependencies),
                     otel-collector, DVC remote, Docker/Compose orchestration
                     for a LOCAL, loopback-bound research stack
components refused:  none of the requested set
conditions:          pinned image versions; named volumes; explicit networks;
                     health checks; no privileged mode; no host Docker socket;
                     no host network; no arbitrary host mounts; loopback binding
                     only; credentials from .env and never committed;
                     development credentials marked LOCAL DEVELOPMENT ONLY.
scope boundary:      This grant covers RESEARCH INFRASTRUCTURE connectivity and
                     container isolation for running instances. It does NOT
                     grant experimental agent network egress.
                     InfrastructureHasNetwork != AgentHasNetwork
```
