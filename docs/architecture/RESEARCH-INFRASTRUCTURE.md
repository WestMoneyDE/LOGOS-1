# Research Infrastructure — ownership, identity, degradation

**Materialization status:** `BLOCKED_PENDING_SAFETY_REVIEW`.
See `docs/engineering/SAFETY-REVIEW-REQUEST-RESEARCH-INFRASTRUCTURE.md`.

This document describes the design and the adapter layer that exists today. It
does **not** describe a running system.

```text
Installed  != Integrated
Integrated != Validated
Mocked     != Materialized
```

## Canonical ownership

External tools serve LOGOS. LOGOS is not a wrapper around them.

| Concern | Canonical owner | Status |
|---|---|---|
| Hypothesis / verdict / claim semantics | `logos_research` | `EXISTS` |
| Γ invariants | `GAMMA.md` | `EXISTS` |
| Γ validation | `logos_gamma` | `EXISTS` |
| Authority origin | external human grant | `EXISTS` (specification) |
| Canonical experiment identity | `logos_research.infra.identity` | `EXISTS` |
| Structured durable research records | PostgreSQL | `BLOCKED` |
| Run metrics / parameters | MLflow | `BLOCKED` |
| LLM traces | Langfuse | `BLOCKED` |
| System traces | OpenTelemetry | `BLOCKED` |
| Dataset lineage | DVC | `BLOCKED` |
| Large immutable artifacts | MinIO / S3 | `BLOCKED` |
| Code version | Git | `EXISTS` |
| Dataset scientific identity | LOGOS manifest/hash rules | `EXISTS` |

Non-equivalences that the design must keep true:

```text
PostgreSQL     != scientific reasoning engine
MLflow         != scientific ground truth
Langfuse       != experiment registry
OpenTelemetry  != scientific evidence
DVC            != runtime state
MinIO          != metadata authority
observed trace != validated claim
Γ PASS         != execution authority
```

## Identity model

One canonical identity; external systems correlate to it, never the reverse.

```text
experiment_id
  -> experiment_revision
    -> preregistration_hash
      -> run_id
        -> mlflow_run_id / langfuse_trace_id / otel_trace_id /
           dvc_dataset_revs / artifact_ids
```

`correlation_tags()` produces the `logos.*` tags written onto external systems so
a run is findable from LOGOS identity. It carries identity fields only, never a
secret.

`resolve_from_experiment_id()` answers the acceptance question: given one
`experiment_id`, return every correlated record without searching six dashboards.
It works today against the in-repo adapters, and is the function the materialized
stack must satisfy unchanged.

## Operational status is not a scientific verdict

Two separate fields, enforced by `RunRecord.problems()`:

```text
RunStatus          REGISTERED READY RUNNING COMPLETED FAILED ABORTED DEGRADED
ScientificVerdict  SUPPORTED PARTIALLY_SUPPORTED FALSIFIED INCONCLUSIVE
                   INVALID_MEASUREMENT  (or none at all)
```

`run_status = COMPLETED` with `verdict = FALSIFIED` is valid and ordinary.
`run_status = FAILED` with no verdict is valid. A verdict on a `RUNNING` run is
flagged.

## Failure semantics — declared, not improvised

Each adapter declares a criticality, and that decides what happens when it is
unavailable:

| Adapter | Criticality | Unavailable behaviour |
|---|---|---|
| `ResearchRepository` | `CANONICAL` | `InfrastructureUnavailable`; the run must not claim durable completion |
| `ArtifactStore` | `CANONICAL` | write fails; no reference is recorded |
| `DatasetLineageStore` | `CANONICAL` | fails loudly |
| `RunTracker` | `OBSERVABILITY` | run continues, `DEGRADED`, loss recorded |
| `TraceSink` | `OBSERVABILITY` | as above |
| `LLMTraceSink` | `OBSERVABILITY` | as above |

The forbidden behaviour, tested explicitly:

```text
canonical persistence unavailable
  -> write a local JSON file
  -> report success            FORBIDDEN
```

`InMemoryResearchRepository.health()` reports `CONFIGURED`, never `PERSISTENT`,
so a caller can always tell a dict from durable storage.

### Observability of observability

A `DegradedSink` record makes these two distinguishable:

```text
no events occurred
events occurred but telemetry was unavailable
```

Without it a missing trace looks identical to a run that did nothing.

## Redaction

Applied inside the sink adapter, before anything leaves, so a caller cannot skip
it. Keys are preserved and values replaced, which keeps traces diagnostically
readable without exporting the value. Recursive.

`environment_id()` refuses inputs whose key looks like a credential, so the
environment hash cannot quietly become a place secrets live.

## Dataset identity — the R4 lesson generalized

`DatasetRevision` carries **two** identities on purpose:

```text
object_hash        what DVC or S3 would address
semantic_identity  what LOGOS compares across platforms
identity_kind      exact_bytes | normalized_content |
                   ordered_row_identity | structured_object_identity
```

R4 established that a CRLF and an LF serialization of the same rows have
different file hashes and identical row hashes. A storage layer's object hash is
therefore not the scientific identity of a dataset, and DVC must not become the
sole answer to "is this the same data".

## Adapter layer

```text
ResearchRepository   InMemoryResearchRepository | UnavailableRepository | (PostgresResearchRepository)
RunTracker           NoOpRunTracker                                     | (MLflowRunTracker)
ArtifactStore        LocalArtifactStore                                 | (S3ArtifactStore)
TraceSink            NoOpTraceSink                                      | (OpenTelemetryTraceSink)
LLMTraceSink         NoOpLLMTraceSink                                   | (LangfuseTraceSink)
DatasetLineageStore  InMemoryDatasetLineageStore                        | (DvcLineageStore)
```

Names in parentheses do not exist. They are the blocked implementations.

The deterministic scientific core is testable with the in-repo defaults, so an
MLflow outage cannot make Γ or the research semantics untestable.

## What exists today

```text
src/logos_research/infra/identity.py   canonical identity, correlation, run record
src/logos_research/infra/adapters.py   protocols, in-repo defaults, redaction
src/logos_research/infra/runner.py     orchestration, degradation, resolution
tests/test_infra_adapters.py           27 tests, no service required
```

## What does not exist

No PostgreSQL, MLflow, Langfuse, OpenTelemetry collector, MinIO or DVC remote is
configured, started, integrated or tested. No compose file exists. No dependency
was added. The environment has no Docker daemon running and none of these tools
installed natively.

Queue 1 is therefore **not** complete.
