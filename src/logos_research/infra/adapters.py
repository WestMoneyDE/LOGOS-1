"""Adapter interfaces for external research infrastructure.

External tools serve LOGOS. LOGOS does not become a wrapper around them. Each
concern is a protocol with an in-repo default that needs no service running, so
the deterministic scientific core stays testable while PostgreSQL, MLflow,
Langfuse, MinIO or an OTel collector are down or, as today, not yet materialized.

```text
ResearchRepository   canonical research records      CANONICAL   fail-closed
RunTracker           run metrics and parameters      OBSERVABILITY
ArtifactStore        large immutable artifacts       CANONICAL   fail-closed
TraceSink            system traces                   OBSERVABILITY
LLMTraceSink         model-call traces               OBSERVABILITY
DatasetLineageStore  dataset lineage                 CANONICAL   fail-closed
```

The `Criticality` of an adapter decides what happens when it is unavailable, and
that decision is declared here rather than improvised at runtime:

```text
CANONICAL      unavailable -> the run must not claim durable completion
OBSERVABILITY  unavailable -> the run may continue, DEGRADED and recorded
```

No implementation in this module opens a socket. The real backends are
`BLOCKED_PENDING_SAFETY_REVIEW`; see
`docs/engineering/SAFETY-REVIEW-REQUEST-RESEARCH-INFRASTRUCTURE.md`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Literal, Mapping, Protocol, runtime_checkable

from .identity import ExperimentIdentity, ExternalRefs, RunRecord

Criticality = Literal["CANONICAL", "OBSERVABILITY"]

#: Service maturity, reusing the repository's sandbox vocabulary.
ServiceStatus = Literal[
    "NOT_SPECIFIED", "SPECIFIED", "CONFIGURED", "RUNNING", "HEALTHY",
    "INTEGRATED", "TESTED", "PERSISTENT", "DEGRADED", "UNAVAILABLE",
    "REVIEW_REQUIRED", "BLOCKED_PENDING_SAFETY_REVIEW",
]


class InfrastructureUnavailable(RuntimeError):
    """Raised when a CANONICAL adapter cannot serve a request.

    Deliberately loud. A canonical persistence failure must never degrade into a
    local JSON file plus a success report.
    """


@dataclass(frozen=True)
class ServiceHealth:
    name: str
    status: ServiceStatus
    criticality: Criticality
    detail: str = ""
    version: str = ""

    def is_usable(self) -> bool:
        return self.status in {"HEALTHY", "INTEGRATED", "TESTED", "PERSISTENT"}


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    content_sha256: str
    size_bytes: int
    experiment_id: str
    run_id: str
    media_type: str = "application/octet-stream"
    storage_location: str = ""
    produced_by: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class DatasetRevision:
    """Dataset lineage. Deliberately carries two identities, not one.

    The R4 lesson, generalized: a storage layer's object hash is not the
    scientific identity of a dataset. `object_hash` is what DVC or S3 would
    address; `semantic_identity` is what LOGOS compares across platforms.
    """

    dataset_name: str
    revision: str
    object_hash: str
    semantic_identity: str
    identity_kind: str = "exact_bytes"


# --------------------------------------------------------------------------
# Protocols
# --------------------------------------------------------------------------

@runtime_checkable
class ResearchRepository(Protocol):
    """Canonical durable research records. CANONICAL: fail-closed."""

    criticality: Criticality

    def health(self) -> ServiceHealth: ...
    def register_run(self, record: RunRecord) -> None: ...
    def update_run(self, record: RunRecord) -> None: ...
    def get_run(self, run_id: str) -> RunRecord: ...
    def runs_for_experiment(self, experiment_id: str) -> tuple[RunRecord, ...]: ...


@runtime_checkable
class RunTracker(Protocol):
    """Run parameters and metrics. OBSERVABILITY: fail-degraded."""

    criticality: Criticality

    def health(self) -> ServiceHealth: ...
    def start_run(self, identity: ExperimentIdentity, run_id: str,
                  tags: Mapping[str, str]) -> ExternalRefs: ...
    def log_params(self, run_id: str, params: Mapping[str, str]) -> None: ...
    def log_metrics(self, run_id: str, metrics: Mapping[str, float]) -> None: ...
    def end_run(self, run_id: str, status: str) -> None: ...


@runtime_checkable
class ArtifactStore(Protocol):
    """Immutable artifacts. CANONICAL: an artifact reference must not lie."""

    criticality: Criticality

    def health(self) -> ServiceHealth: ...
    def put(self, experiment_id: str, run_id: str, name: str, payload: bytes,
            media_type: str = "application/octet-stream") -> ArtifactRef: ...
    def get(self, artifact_id: str) -> bytes: ...
    def verify(self, ref: ArtifactRef) -> bool: ...


@runtime_checkable
class TraceSink(Protocol):
    """System traces. OBSERVABILITY: fail-degraded."""

    criticality: Criticality

    def health(self) -> ServiceHealth: ...
    def emit(self, identity: ExperimentIdentity, run_id: str, span: str,
             attributes: Mapping[str, str]) -> ExternalRefs: ...


@runtime_checkable
class LLMTraceSink(Protocol):
    """Model-call traces. OBSERVABILITY: fail-degraded, and redaction-aware."""

    criticality: Criticality

    def health(self) -> ServiceHealth: ...
    def emit_generation(self, identity: ExperimentIdentity, run_id: str,
                        payload: Mapping[str, object]) -> ExternalRefs: ...


@runtime_checkable
class DatasetLineageStore(Protocol):
    """Dataset lineage. CANONICAL: a dataset reference must not lie."""

    criticality: Criticality

    def health(self) -> ServiceHealth: ...
    def record(self, revision: DatasetRevision) -> None: ...
    def get(self, dataset_name: str, revision: str) -> DatasetRevision: ...


# --------------------------------------------------------------------------
# Redaction — applied before anything leaves for an observability backend
# --------------------------------------------------------------------------

#: Substrings that mark a field as unsafe to export.
SENSITIVE_MARKERS = (
    "secret", "password", "token", "credential", "api_key", "apikey",
    "authorization", "private_key", "access_key",
)

REDACTED = "[REDACTED]"


def redact(payload: Mapping[str, object]) -> dict[str, object]:
    """Drop sensitive values before export. Keys are kept, values are not.

    Keeping the key preserves the shape of the trace, which is diagnostically
    useful, while removing the value. Applied recursively.
    """
    out: dict[str, object] = {}
    for key, value in payload.items():
        if any(marker in key.lower() for marker in SENSITIVE_MARKERS):
            out[key] = REDACTED
        elif isinstance(value, Mapping):
            out[key] = redact(value)
        else:
            out[key] = value
    return out


# --------------------------------------------------------------------------
# Default in-repo implementations. No service, no socket.
# --------------------------------------------------------------------------

@dataclass
class InMemoryResearchRepository:
    """Canonical repository backed by a dict. For tests and offline work.

    Explicitly **not** the durable answer: `health()` reports `CONFIGURED`, never
    `PERSISTENT`, so a caller cannot mistake it for durable storage.
    """

    criticality: Criticality = "CANONICAL"
    _runs: dict[str, RunRecord] = field(default_factory=dict)

    def health(self) -> ServiceHealth:
        return ServiceHealth("in-memory-repository", "CONFIGURED", self.criticality,
                             "process-local; not durable across restart")

    def register_run(self, record: RunRecord) -> None:
        if record.run_id in self._runs:
            raise ValueError(f"duplicate run_id {record.run_id!r}")
        self._runs[record.run_id] = record

    def update_run(self, record: RunRecord) -> None:
        if record.run_id not in self._runs:
            raise KeyError(record.run_id)
        self._runs[record.run_id] = record

    def get_run(self, run_id: str) -> RunRecord:
        return self._runs[run_id]

    def runs_for_experiment(self, experiment_id: str) -> tuple[RunRecord, ...]:
        return tuple(
            r for _, r in sorted(self._runs.items())
            if r.identity.experiment_id == experiment_id
        )

    def artifact_reference(self, run_id: str, artifact_id: str) -> ArtifactRef | None:
        """Not tracked here; the caller falls back to the artifact store."""
        return None


@dataclass
class UnavailableRepository:
    """A canonical repository that is down. Every call fails loudly.

    Used to test that a run cannot report durable completion when canonical
    persistence is unavailable.
    """

    criticality: Criticality = "CANONICAL"
    reason: str = "service not materialized"

    def health(self) -> ServiceHealth:
        return ServiceHealth("unavailable-repository", "UNAVAILABLE", self.criticality,
                             self.reason)

    def _fail(self):
        raise InfrastructureUnavailable(
            f"canonical research persistence unavailable: {self.reason}"
        )

    def register_run(self, record: RunRecord) -> None: self._fail()
    def update_run(self, record: RunRecord) -> None: self._fail()
    def get_run(self, run_id: str) -> RunRecord: self._fail()
    def runs_for_experiment(self, experiment_id: str) -> tuple[RunRecord, ...]: self._fail()


@dataclass
class NoOpRunTracker:
    """Observability tracker that records nothing and says so."""

    criticality: Criticality = "OBSERVABILITY"
    available: bool = True
    calls: list[tuple[str, str]] = field(default_factory=list)

    def health(self) -> ServiceHealth:
        return ServiceHealth("noop-run-tracker",
                             "CONFIGURED" if self.available else "UNAVAILABLE",
                             self.criticality)

    def start_run(self, identity: ExperimentIdentity, run_id: str,
                  tags: Mapping[str, str]) -> ExternalRefs:
        if not self.available:
            raise InfrastructureUnavailable("run tracker unavailable")
        self.calls.append(("start_run", run_id))
        return ExternalRefs(mlflow_run_id=f"noop-{run_id}")

    def log_params(self, run_id: str, params: Mapping[str, str]) -> None:
        self.calls.append(("log_params", run_id))

    def log_metrics(self, run_id: str, metrics: Mapping[str, float]) -> None:
        self.calls.append(("log_metrics", run_id))

    def end_run(self, run_id: str, status: str) -> None:
        self.calls.append(("end_run", run_id))


@dataclass
class LocalArtifactStore:
    """Content-addressed artifact store held in memory.

    Content addressing is the point: `put` is idempotent for identical bytes, so
    a retried upload cannot create a second artifact identity.
    """

    criticality: Criticality = "CANONICAL"
    _objects: dict[str, bytes] = field(default_factory=dict)
    _refs: dict[str, ArtifactRef] = field(default_factory=dict)

    def health(self) -> ServiceHealth:
        return ServiceHealth("local-artifact-store", "CONFIGURED", self.criticality,
                             "process-local; not durable across restart")

    def put(self, experiment_id: str, run_id: str, name: str, payload: bytes,
            media_type: str = "application/octet-stream") -> ArtifactRef:
        digest = sha256(payload).hexdigest()
        artifact_id = f"{digest[:32]}"
        ref = ArtifactRef(
            artifact_id=artifact_id,
            content_sha256=digest,
            size_bytes=len(payload),
            experiment_id=experiment_id,
            run_id=run_id,
            media_type=media_type,
            storage_location=f"memory://{artifact_id}/{name}",
        )
        self._objects[artifact_id] = payload
        self._refs[artifact_id] = ref
        return ref

    def get(self, artifact_id: str) -> bytes:
        return self._objects[artifact_id]

    def verify(self, ref: ArtifactRef) -> bool:
        payload = self._objects.get(ref.artifact_id)
        return payload is not None and sha256(payload).hexdigest() == ref.content_sha256

    def reference(self, artifact_id: str) -> ArtifactRef | None:
        return self._refs.get(artifact_id)


@dataclass
class NoOpTraceSink:
    criticality: Criticality = "OBSERVABILITY"
    available: bool = True
    spans: list[str] = field(default_factory=list)

    def health(self) -> ServiceHealth:
        return ServiceHealth("noop-trace-sink",
                             "CONFIGURED" if self.available else "UNAVAILABLE",
                             self.criticality)

    def emit(self, identity: ExperimentIdentity, run_id: str, span: str,
             attributes: Mapping[str, str]) -> ExternalRefs:
        if not self.available:
            raise InfrastructureUnavailable("trace sink unavailable")
        self.spans.append(span)
        return ExternalRefs(otel_trace_id=f"noop-otel-{run_id}")


@dataclass
class NoOpLLMTraceSink:
    """Redaction is applied here, not at the backend, so it cannot be skipped."""

    criticality: Criticality = "OBSERVABILITY"
    available: bool = True
    generations: list[dict[str, object]] = field(default_factory=list)

    def health(self) -> ServiceHealth:
        return ServiceHealth("noop-llm-trace-sink",
                             "CONFIGURED" if self.available else "UNAVAILABLE",
                             self.criticality)

    def emit_generation(self, identity: ExperimentIdentity, run_id: str,
                        payload: Mapping[str, object]) -> ExternalRefs:
        if not self.available:
            raise InfrastructureUnavailable("LLM trace sink unavailable")
        self.generations.append(redact(payload))
        return ExternalRefs(langfuse_trace_id=f"noop-lf-{run_id}")


@dataclass
class InMemoryDatasetLineageStore:
    criticality: Criticality = "CANONICAL"
    _revisions: dict[tuple[str, str], DatasetRevision] = field(default_factory=dict)

    def health(self) -> ServiceHealth:
        return ServiceHealth("in-memory-dataset-lineage", "CONFIGURED", self.criticality,
                             "process-local; not durable across restart")

    def record(self, revision: DatasetRevision) -> None:
        self._revisions[(revision.dataset_name, revision.revision)] = revision

    def get(self, dataset_name: str, revision: str) -> DatasetRevision:
        return self._revisions[(dataset_name, revision)]
