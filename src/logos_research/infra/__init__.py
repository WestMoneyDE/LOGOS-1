"""External research-infrastructure adapters and canonical run identity.

Nothing here opens a socket. The real PostgreSQL / MLflow / Langfuse /
OpenTelemetry / MinIO / DVC backends are `BLOCKED_PENDING_SAFETY_REVIEW` under
the `AGENTS.md` external-action boundary; see
`docs/engineering/SAFETY-REVIEW-REQUEST-RESEARCH-INFRASTRUCTURE.md`.

```text
Installed   != Integrated
Integrated  != Validated
Mocked      != Materialized
```
"""
from .adapters import (
    SENSITIVE_MARKERS,
    ArtifactRef,
    ArtifactStore,
    Criticality,
    DatasetLineageStore,
    DatasetRevision,
    InfrastructureUnavailable,
    InMemoryDatasetLineageStore,
    InMemoryResearchRepository,
    LLMTraceSink,
    LocalArtifactStore,
    NoOpLLMTraceSink,
    NoOpRunTracker,
    NoOpTraceSink,
    ResearchRepository,
    RunTracker,
    ServiceHealth,
    ServiceStatus,
    TraceSink,
    UnavailableRepository,
    redact,
)
from .identity import (
    RUN_STATUSES,
    VERDICT_BEARING_STATUSES,
    DegradedSink,
    ExperimentIdentity,
    ExternalRefs,
    RunRecord,
    RunStatus,
    correlation_tags,
    environment_id,
)
from .runner import ResearchRun, ResearchStack, resolve_from_experiment_id

__all__ = [
    "RUN_STATUSES",
    "SENSITIVE_MARKERS",
    "VERDICT_BEARING_STATUSES",
    "ArtifactRef",
    "ArtifactStore",
    "Criticality",
    "DatasetLineageStore",
    "DatasetRevision",
    "DegradedSink",
    "ExperimentIdentity",
    "ExternalRefs",
    "InMemoryDatasetLineageStore",
    "InMemoryResearchRepository",
    "InfrastructureUnavailable",
    "LLMTraceSink",
    "LocalArtifactStore",
    "NoOpLLMTraceSink",
    "NoOpRunTracker",
    "NoOpTraceSink",
    "ResearchRepository",
    "ResearchRun",
    "ResearchStack",
    "RunRecord",
    "RunStatus",
    "RunTracker",
    "ServiceHealth",
    "ServiceStatus",
    "TraceSink",
    "UnavailableRepository",
    "correlation_tags",
    "environment_id",
    "redact",
    "resolve_from_experiment_id",
]
