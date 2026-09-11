"""INFRA-MATERIALIZATION-SMOKE-R1 — cross-system infrastructure smoke run.

**This is not a scientific experiment.** It exercises the materialized stack and
proves one thing: from a single canonical `experiment_id`, every external record
can be found again.

```text
TEST_FIXTURE   INFRASTRUCTURE_SMOKE   NON_SCIENTIFIC
```

No hypothesis is tested, no verdict is produced, and the run records
`scientific_verdict = None`. Any model interaction is a fake; no paid inference
is required.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .adapters import DatasetRevision, InfrastructureUnavailable
from .backends import backends_from_env
from .identity import ExperimentIdentity, environment_id
from .runner import ResearchRun, ResearchStack, resolve_from_experiment_id

EXPERIMENT_ID = "INFRA-MATERIALIZATION-SMOKE-R1"
TITLE = "Infrastructure materialization smoke run (NON_SCIENTIFIC)"

#: Marks every record this module writes, so an infrastructure fixture can never
#: be mistaken for scientific evidence.
FIXTURE_MARKERS = ("TEST_FIXTURE", "INFRASTRUCTURE_SMOKE", "NON_SCIENTIFIC")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_identity(git_sha: str = "", gamma_version: str = "v0.2") -> ExperimentIdentity:
    """Content-addressed preregistration for the fixture. Not a hypothesis."""
    prereg = {
        "markers": list(FIXTURE_MARKERS),
        "purpose": "verify cross-system correlation of the materialized stack",
        "scientific_claim": None,
    }
    digest = hashlib.sha256(
        json.dumps(prereg, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ExperimentIdentity(
        experiment_id=EXPERIMENT_ID,
        experiment_revision=1,
        preregistration_hash=digest,
        git_sha=git_sha,
        gamma_version=gamma_version,
        environment_id=environment_id({
            "python": "3.12", "postgres": "16.4-alpine", "mlflow": "2.16.2",
            "langfuse": "2.95.0", "otel_collector": "0.109.0",
            "minio": "RELEASE.2024-09-13T20-26-02Z", "schema_version": "1",
        }),
    )


def run(git_sha: str = "") -> dict[str, Any]:
    """Execute the smoke run against the materialized stack.

    Returns the correlation view reconstructed from the canonical id alone.
    """
    backends = backends_from_env()
    repo = backends["repository"].connect()
    repo.migrate()

    identity = build_identity(git_sha=git_sha)
    repo.ensure_experiment(EXPERIMENT_ID, TITLE)

    prereg_payload = {"markers": list(FIXTURE_MARKERS), "scientific_claim": None}
    repo.freeze_preregistration(identity, prereg_payload)

    stack = ResearchStack(
        repository=repo,
        artifacts=backends["artifacts"],
        lineage=_RepoLineage(repo),
        tracker=backends["tracker"],
        traces=backends["traces"],
        llm_traces=backends["llm_traces"],
    )

    # A fixed run id made the smoke run single-use: a second invocation collided
    # on runs_pkey. Each invocation is a new run of the same experiment, and the
    # canonical experiment identity is what stays stable.
    run_id = f"{EXPERIMENT_ID}-run-{uuid.uuid4().hex[:8]}"
    session = ResearchRun(stack, identity, run_id, clock=_now())
    session.start()

    # 5. system trace
    session.trace("infrastructure_smoke", {"marker": "INFRASTRUCTURE_SMOKE"})

    # 6. synthetic LLM trace. Fake model, and a deliberate secret to prove
    #    redaction happens before anything leaves the process.
    session.llm_generation({
        "name": "fake-generation",
        "model": "fake-model-0",
        "input": "synthetic infrastructure fixture",
        "output": "synthetic response",
        "api_key": "sk-THIS-MUST-NOT-LEAVE",
        "usage": {"input": 4, "output": 3},
    })

    # 7. dataset lineage: object identity and semantic identity are separate
    fixture = b'{"id":1,"v":"a"}\n{"id":2,"v":"b"}\n{"id":3,"v":"c"}\n'
    rows = [json.loads(line) for line in fixture.decode().splitlines() if line.strip()]
    session.record_dataset(DatasetRevision(
        dataset_name="smoke_dataset.jsonl",
        revision="dvc-1",
        object_hash=hashlib.sha256(fixture).hexdigest(),
        semantic_identity=hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        identity_kind="ordered_row_identity",
    ))

    # 8. artifact
    artifact = json.dumps({"markers": list(FIXTURE_MARKERS)}).encode()
    ref = session.put_artifact("smoke_artifact.json", artifact, "application/json")
    repo.record_artifact(ref)

    if stack.tracker is not None:
        try:
            stack.tracker.log_params(run_id, {"marker": "INFRASTRUCTURE_SMOKE"})
            stack.tracker.log_metrics(run_id, {"artifacts_written": 1.0})
        except InfrastructureUnavailable:
            pass

    # 10. close. No scientific verdict: this is not an experiment.
    record = session.finish(scientific_verdict=None, completed_at=_now())

    if hasattr(stack.traces, "flush"):
        stack.traces.flush()

    view = resolve_from_experiment_id(stack, EXPERIMENT_ID)
    view["artifact_ref"] = {
        "artifact_id": ref.artifact_id,
        "content_sha256": ref.content_sha256,
        "storage_location": ref.storage_location,
    }
    view["run_status"] = record.status
    view["scientific_verdict"] = record.scientific_verdict
    repo.close()
    return view


class _RepoLineage:
    """Routes dataset lineage into the canonical repository."""

    criticality = "CANONICAL"

    def __init__(self, repo) -> None:
        self._repo = repo

    def health(self):
        return self._repo.health()

    def record(self, revision: DatasetRevision) -> None:
        self._repo.record_dataset(revision)

    def get(self, dataset_name: str, revision: str) -> DatasetRevision:
        raise NotImplementedError("read datasets through the repository")
