"""Run orchestration with declared failure semantics.

The rule this module exists to enforce: an unavailable **canonical** service
aborts the run, while an unavailable **observability** service degrades it and
the loss is recorded. Neither is decided ad hoc at runtime.

```text
CANONICAL unavailable      -> InfrastructureUnavailable, no durable claim
OBSERVABILITY unavailable  -> RunStatus DEGRADED + DegradedSink recorded
```

The forbidden behaviour is silent fallback: canonical persistence fails, the run
writes a local file, and reports success. That is why `InMemoryResearchRepository`
reports `CONFIGURED` rather than `PERSISTENT` — a caller can tell the difference.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping

from .adapters import (
    ArtifactRef,
    ArtifactStore,
    DatasetLineageStore,
    DatasetRevision,
    InfrastructureUnavailable,
    LLMTraceSink,
    ResearchRepository,
    RunTracker,
    ServiceHealth,
    TraceSink,
)
from .identity import (
    DegradedSink,
    ExperimentIdentity,
    ExternalRefs,
    RunRecord,
    correlation_tags,
)


@dataclass
class ResearchStack:
    """The adapters one run uses. Observability members may be absent."""

    repository: ResearchRepository
    artifacts: ArtifactStore
    lineage: DatasetLineageStore
    tracker: RunTracker | None = None
    traces: TraceSink | None = None
    llm_traces: LLMTraceSink | None = None

    def health(self) -> tuple[ServiceHealth, ...]:
        members = [self.repository, self.artifacts, self.lineage,
                   self.tracker, self.traces, self.llm_traces]
        return tuple(m.health() for m in members if m is not None)

    def canonical_unusable(self) -> tuple[str, ...]:
        return tuple(
            h.name for h in self.health()
            if h.criticality == "CANONICAL" and h.status == "UNAVAILABLE"
        )


@dataclass
class ResearchRun:
    """One orchestrated run. Not a scientific experiment by itself."""

    stack: ResearchStack
    identity: ExperimentIdentity
    run_id: str
    clock: str = "1970-01-01T00:00:00+00:00"
    _record: RunRecord = field(init=False)

    def __post_init__(self) -> None:
        self._record = RunRecord(
            run_id=self.run_id, identity=self.identity, status="REGISTERED",
            started_at=self.clock,
        )

    @property
    def record(self) -> RunRecord:
        return self._record

    def _replace(self, **changes) -> RunRecord:
        return replace(self._record, **changes)

    def _degrade(self, sink: str, error: Exception, capability: str) -> None:
        self._record = self._record.degraded(
            DegradedSink(sink=sink, reason=str(error), at=self.clock,
                         lost_capability=capability)
        )

    def start(self) -> RunRecord:
        """Register canonically first. Observability is best effort."""
        self._record = self._replace(status="RUNNING")
        # Canonical: a failure here aborts. No silent local fallback.
        self.stack.repository.register_run(self._record)

        if self.stack.tracker is not None:
            try:
                refs = self.stack.tracker.start_run(
                    self.identity, self.run_id,
                    correlation_tags(self.identity, self.run_id),
                )
                self._record = self._record.with_external(refs)
            except InfrastructureUnavailable as exc:
                self._degrade("run_tracker", exc, "run metrics and parameters")

        self.stack.repository.update_run(self._record)
        return self._record

    def trace(self, span: str, attributes: Mapping[str, str] | None = None) -> None:
        if self.stack.traces is None:
            return
        try:
            refs = self.stack.traces.emit(
                self.identity, self.run_id, span, dict(attributes or {})
            )
            self._record = self._record.with_external(refs)
        except InfrastructureUnavailable as exc:
            self._degrade("trace_sink", exc, "system traces")

    def llm_generation(self, payload: Mapping[str, object]) -> None:
        if self.stack.llm_traces is None:
            return
        try:
            refs = self.stack.llm_traces.emit_generation(
                self.identity, self.run_id, payload
            )
            self._record = self._record.with_external(refs)
        except InfrastructureUnavailable as exc:
            self._degrade("llm_trace_sink", exc, "model-call traces")

    def put_artifact(self, name: str, payload: bytes,
                     media_type: str = "application/octet-stream") -> ArtifactRef:
        """Canonical. A reference is only recorded once the write succeeded."""
        ref = self.stack.artifacts.put(
            self.identity.experiment_id, self.run_id, name, payload, media_type
        )
        if not self.stack.artifacts.verify(ref):
            raise InfrastructureUnavailable(
                f"artifact {ref.artifact_id} failed verification after write"
            )
        self._record = self._record.with_external(
            ExternalRefs(artifact_ids=(ref.artifact_id,))
        )
        self.stack.repository.update_run(self._record)
        return ref

    def record_dataset(self, revision: DatasetRevision) -> None:
        self.stack.lineage.record(revision)
        self._record = self._record.with_external(
            ExternalRefs(dvc_dataset_revs=(revision.revision,))
        )
        self.stack.repository.update_run(self._record)

    def finish(self, scientific_verdict: str | None = None,
               completed_at: str = "") -> RunRecord:
        """Close the run. Operational status and verdict stay separate."""
        status = "DEGRADED" if self._record.degraded_sinks else "COMPLETED"
        self._record = self._replace(
            status=status,
            scientific_verdict=scientific_verdict,
            completed_at=completed_at or self.clock,
        )
        if self.stack.tracker is not None:
            try:
                self.stack.tracker.end_run(self.run_id, status)
            except InfrastructureUnavailable as exc:
                self._degrade("run_tracker", exc, "run closure")
                self._record = self._replace(status="DEGRADED")
        self.stack.repository.update_run(self._record)
        return self._record


def resolve_from_experiment_id(
    stack: ResearchStack, experiment_id: str, *, verify_artifacts: bool = True
) -> dict[str, object]:
    """The acceptance question: from one canonical id, find everything.

    Returns the correlation view a researcher would otherwise assemble by hand
    across several dashboards.

    INFRA-SF-DEFECT-2: this function used to list artifact ids without checking
    the bytes behind them, so a substituted artifact reconstructed as a complete,
    intact evidence chain. Integrity is now verified during reconstruction and
    reported per run in `artifact_integrity`, with `integrity_ok` on the view.
    Pass `verify_artifacts=False` only for a deliberately cheap listing.
    """
    runs = stack.repository.runs_for_experiment(experiment_id)

    def integrity(record) -> dict[str, str]:
        if not verify_artifacts:
            return {a: "NOT_VERIFIED" for a in record.external.artifact_ids}
        result: dict[str, str] = {}
        for artifact_id in record.external.artifact_ids:
            ref = None
            lookup = getattr(stack.repository, "artifact_reference", None)
            if lookup is not None:
                try:
                    ref = lookup(record.run_id, artifact_id)
                except Exception:
                    ref = None
            if ref is None:
                fallback = getattr(stack.artifacts, "reference", None)
                if fallback is not None:
                    ref = fallback(artifact_id)
            if ref is None:
                result[artifact_id] = "REFERENCE_MISSING"
            else:
                result[artifact_id] = "OK" if stack.artifacts.verify(ref) else "CORRUPT"
        return result

    checked = {r.run_id: integrity(r) for r in runs}
    view = {
        "experiment_id": experiment_id,
        "integrity_ok": all(
            state == "OK" for states in checked.values() for state in states.values()
        ),
        "runs": [
            {
                "run_id": r.run_id,
                "revision": r.identity.experiment_revision,
                "preregistration_hash": r.identity.preregistration_hash,
                "status": r.status,
                "scientific_verdict": r.scientific_verdict,
                "mlflow_run_id": r.external.mlflow_run_id,
                "langfuse_trace_id": r.external.langfuse_trace_id,
                "otel_trace_id": r.external.otel_trace_id,
                "dvc_dataset_revs": list(r.external.dvc_dataset_revs),
                "artifact_ids": list(r.external.artifact_ids),
                "degraded_sinks": [d.sink for d in r.degraded_sinks],
                "artifact_integrity": checked[r.run_id],
            }
            for r in runs
        ],
    }
    return view
