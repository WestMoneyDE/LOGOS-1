"""Canonical research identity and cross-system correlation.

One LOGOS experiment identity, many external identifiers. Never the reverse.

```text
experiment_id
    -> experiment_revision
        -> preregistration_hash
            -> run_id
                -> mlflow_run_id / langfuse_trace_id / otel_trace_id /
                   dvc_dataset_rev / artifact_ids
```

MLflow, Langfuse and OpenTelemetry each mint their own identifiers. Those are
**correlation identifiers**, not scientific identity. A run is the same run
because its `run_id` says so, not because a tracking server assigned it a UUID.

Two separations are enforced by type here:

```text
OperationalRunStatus != ScientificVerdict
ExternalIdentifier   != CanonicalIdentity
```

A run can be `COMPLETED` while the verdict is `FALSIFIED`, and a run can be
`FAILED` while there is no verdict at all.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
from typing import Literal, Mapping

#: Operational lifecycle of a run. Says nothing about what the science found.
RunStatus = Literal[
    "REGISTERED", "READY", "RUNNING", "COMPLETED", "FAILED", "ABORTED", "DEGRADED",
]

RUN_STATUSES: tuple[RunStatus, ...] = (
    "REGISTERED", "READY", "RUNNING", "COMPLETED", "FAILED", "ABORTED", "DEGRADED",
)

#: Statuses in which a run may legitimately carry a scientific verdict.
VERDICT_BEARING_STATUSES = frozenset({"COMPLETED", "DEGRADED"})


@dataclass(frozen=True)
class ExperimentIdentity:
    """The canonical scientific identity. External systems correlate to this."""

    experiment_id: str
    experiment_revision: int
    preregistration_hash: str
    git_sha: str = ""
    gamma_version: str = ""
    environment_id: str = ""

    def key(self) -> str:
        return f"{self.experiment_id}@r{self.experiment_revision}"

    def digest(self) -> str:
        return sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class ExternalRefs:
    """Correlation identifiers minted by external systems.

    Every field is optional: a run is canonical whether or not any tracking
    service was reachable. An absent reference means "not recorded", which is
    distinguishable from "the service said there is nothing".
    """

    mlflow_run_id: str | None = None
    mlflow_experiment_id: str | None = None
    langfuse_trace_id: str | None = None
    otel_trace_id: str | None = None
    dvc_dataset_revs: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()

    def merged_with(self, other: ExternalRefs) -> ExternalRefs:
        return ExternalRefs(
            mlflow_run_id=other.mlflow_run_id or self.mlflow_run_id,
            mlflow_experiment_id=other.mlflow_experiment_id or self.mlflow_experiment_id,
            langfuse_trace_id=other.langfuse_trace_id or self.langfuse_trace_id,
            otel_trace_id=other.otel_trace_id or self.otel_trace_id,
            dvc_dataset_revs=tuple(dict.fromkeys(self.dvc_dataset_revs + other.dvc_dataset_revs)),
            artifact_ids=tuple(dict.fromkeys(self.artifact_ids + other.artifact_ids)),
        )

    def recorded(self) -> tuple[str, ...]:
        names = []
        for name in ("mlflow_run_id", "langfuse_trace_id", "otel_trace_id"):
            if getattr(self, name):
                names.append(name)
        if self.dvc_dataset_revs:
            names.append("dvc_dataset_revs")
        if self.artifact_ids:
            names.append("artifact_ids")
        return tuple(names)


#: Tags written onto external systems so a run can be found from LOGOS identity.
#: Never contains a secret: the caller supplies only identity fields.
def correlation_tags(identity: ExperimentIdentity, run_id: str) -> dict[str, str]:
    tags = {
        "logos.experiment_id": identity.experiment_id,
        "logos.experiment_revision": str(identity.experiment_revision),
        "logos.preregistration_hash": identity.preregistration_hash,
        "logos.run_id": run_id,
    }
    for key, value in (
        ("logos.git_sha", identity.git_sha),
        ("logos.gamma_version", identity.gamma_version),
        ("logos.environment_id", identity.environment_id),
    ):
        if value:
            tags[key] = value
    return tags


@dataclass(frozen=True)
class DegradedSink:
    """Recorded when a telemetry sink was unavailable.

    The point of this type: distinguish "no events occurred" from "events
    occurred but telemetry was unavailable". Without it, a missing trace is
    indistinguishable from a run that did nothing.
    """

    sink: str
    reason: str
    at: str
    lost_capability: str


@dataclass(frozen=True)
class RunRecord:
    """One run. Operational status and scientific verdict are separate fields."""

    run_id: str
    identity: ExperimentIdentity
    status: RunStatus = "REGISTERED"
    external: ExternalRefs = field(default_factory=ExternalRefs)
    degraded_sinks: tuple[DegradedSink, ...] = ()
    #: The scientific outcome, from logos_research.manifest.Outcome. `None` means
    #: no verdict, which is not the same as INCONCLUSIVE.
    scientific_verdict: str | None = None
    started_at: str = ""
    completed_at: str = ""
    notes: str = ""

    def with_external(self, refs: ExternalRefs) -> RunRecord:
        return replace(self, external=self.external.merged_with(refs))

    def degraded(self, sink: DegradedSink) -> RunRecord:
        return replace(
            self,
            status="DEGRADED" if self.status == "RUNNING" else self.status,
            degraded_sinks=self.degraded_sinks + (sink,),
        )

    def problems(self) -> tuple[str, ...]:
        issues: list[str] = []
        if self.scientific_verdict and self.status not in VERDICT_BEARING_STATUSES:
            issues.append(
                f"run status {self.status} carries scientific verdict "
                f"{self.scientific_verdict}; a verdict requires a completed or "
                "explicitly degraded run"
            )
        if self.status == "DEGRADED" and not self.degraded_sinks:
            issues.append("status DEGRADED without any recorded degraded sink")
        return tuple(issues)


def environment_id(inputs: Mapping[str, str]) -> str:
    """Content-address the research environment. Never include a secret.

    Refuses inputs whose key looks like a credential, so an environment hash
    cannot silently become a place secrets are stored.
    """
    suspicious = sorted(
        k for k in inputs
        if any(t in k.lower() for t in ("secret", "password", "token", "key", "credential"))
    )
    if suspicious:
        raise ValueError(f"environment identity must not include secrets: {suspicious}")
    return sha256(
        json.dumps(dict(inputs), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
