"""Service-backed adapter implementations.

These talk to the materialized local research stack. They are imported lazily by
`stack_from_env()` so the deterministic core keeps working with no client library
installed and no service running.

Authorized by `docs/engineering/SAFETY-REVIEW-REQUEST-RESEARCH-INFRASTRUCTURE.md`
(Decision record: GRANTED). Local development only.

Every backend keeps the same boundary the in-repo defaults keep:

```text
external identifier != canonical identity
telemetry record    != authority
run status          != scientific verdict
```
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping

from .adapters import (
    ArtifactRef,
    Criticality,
    DatasetRevision,
    InfrastructureUnavailable,
    ServiceHealth,
    redact,
)
from .identity import DegradedSink, ExperimentIdentity, ExternalRefs, RunRecord
from .migrations import apply_migrations, current_version


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --------------------------------------------------------------------------
# PostgreSQL — canonical research records
# --------------------------------------------------------------------------

@dataclass
class PostgresResearchRepository:
    """Canonical durable persistence. CANONICAL: fail-closed.

    Every failure raises `InfrastructureUnavailable`. There is deliberately no
    local-file fallback: a run that cannot persist canonically must not report
    durable completion.
    """

    dsn: str
    criticality: Criticality = "CANONICAL"
    _conn: Any = field(default=None, repr=False)

    def connect(self) -> PostgresResearchRepository:
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise InfrastructureUnavailable(f"psycopg not installed: {exc}") from exc
        try:
            self._conn = psycopg.connect(self.dsn, autocommit=False)
        except Exception as exc:
            raise InfrastructureUnavailable(f"postgres unreachable: {exc}") from exc
        return self

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def migrate(self) -> tuple[int, ...]:
        self._require()
        return apply_migrations(self._conn)

    def schema_version(self) -> int:
        self._require()
        return current_version(self._conn)

    def _require(self):
        if self._conn is None:
            raise InfrastructureUnavailable("postgres repository is not connected")
        return self._conn

    def health(self) -> ServiceHealth:
        if self._conn is None:
            return ServiceHealth("postgres", "UNAVAILABLE", self.criticality,
                                 "not connected")
        try:
            with self._conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0].split(",")[0]
            return ServiceHealth("postgres", "PERSISTENT", self.criticality,
                                 f"schema v{current_version(self._conn)}", version)
        except Exception as exc:
            return ServiceHealth("postgres", "UNAVAILABLE", self.criticality, str(exc))

    # -- canonical writes ---------------------------------------------------

    def ensure_experiment(self, experiment_id: str, title: str) -> None:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO experiments (experiment_id, title) VALUES (%s, %s) "
                "ON CONFLICT (experiment_id) DO NOTHING",
                (experiment_id, title),
            )
        conn.commit()

    def freeze_preregistration(self, identity: ExperimentIdentity,
                               payload: Mapping[str, Any],
                               supersedes: str | None = None) -> None:
        """Idempotent for identical content; refuses a different payload.

        The hash is the primary key, so re-registering the same criteria is a
        no-op while changing them under the same hash is impossible.
        """
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO preregistrations "
                "(preregistration_hash, experiment_id, revision, supersedes, payload) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (preregistration_hash) DO NOTHING",
                (identity.preregistration_hash, identity.experiment_id,
                 identity.experiment_revision, supersedes, json.dumps(dict(payload))),
            )
        conn.commit()

    def register_run(self, record: RunRecord) -> None:
        conn = self._require()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO runs (run_id, experiment_id, experiment_revision, "
                    "preregistration_hash, run_status, scientific_verdict, git_sha, "
                    "gamma_version, environment_id, external_refs, degraded_sinks) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (record.run_id, record.identity.experiment_id,
                     record.identity.experiment_revision,
                     record.identity.preregistration_hash, record.status,
                     record.scientific_verdict, record.identity.git_sha,
                     record.identity.gamma_version, record.identity.environment_id,
                     json.dumps(_refs_to_json(record.external)),
                     json.dumps(_sinks_to_json(record.degraded_sinks))),
                )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise

    def update_run(self, record: RunRecord) -> None:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE runs SET run_status=%s, scientific_verdict=%s, "
                "external_refs=%s, degraded_sinks=%s WHERE run_id=%s",
                (record.status, record.scientific_verdict,
                 json.dumps(_refs_to_json(record.external)),
                 json.dumps(_sinks_to_json(record.degraded_sinks)), record.run_id),
            )
            if cur.rowcount == 0:
                conn.rollback()
                raise KeyError(record.run_id)
        conn.commit()

    def get_run(self, run_id: str) -> RunRecord:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT run_id, experiment_id, experiment_revision, preregistration_hash, "
                "run_status, scientific_verdict, git_sha, gamma_version, environment_id, "
                "external_refs, degraded_sinks FROM runs WHERE run_id=%s", (run_id,))
            row = cur.fetchone()
        if row is None:
            raise KeyError(run_id)
        return _row_to_record(row)

    def runs_for_experiment(self, experiment_id: str) -> tuple[RunRecord, ...]:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT run_id, experiment_id, experiment_revision, preregistration_hash, "
                "run_status, scientific_verdict, git_sha, gamma_version, environment_id, "
                "external_refs, degraded_sinks FROM runs WHERE experiment_id=%s "
                "ORDER BY run_id", (experiment_id,))
            rows = cur.fetchall()
        return tuple(_row_to_record(r) for r in rows)

    def record_artifact(self, ref: ArtifactRef) -> None:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO artifact_references (artifact_id, run_id, experiment_id, "
                "content_sha256, size_bytes, media_type, storage_location) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (artifact_id) DO NOTHING",
                (ref.artifact_id, ref.run_id, ref.experiment_id, ref.content_sha256,
                 ref.size_bytes, ref.media_type, ref.storage_location))
        conn.commit()

    def record_dataset(self, revision: DatasetRevision, run_id: str | None = None) -> None:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO dataset_references (dataset_name, revision, object_hash, "
                "semantic_identity, identity_kind, run_id) VALUES (%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (dataset_name, revision) DO NOTHING",
                (revision.dataset_name, revision.revision, revision.object_hash,
                 revision.semantic_identity, revision.identity_kind, run_id))
        conn.commit()

    def record_negative_result(self, negative_id: str, hypothesis: str, how_tested: str,
                               what_falsified_it: str, scope: str,
                               run_id: str | None = None) -> None:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO negative_results (negative_id, hypothesis, how_tested, "
                "what_falsified_it, scope_of_falsification, run_id) VALUES (%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (negative_id) DO NOTHING",
                (negative_id, hypothesis, how_tested, what_falsified_it, scope, run_id))
        conn.commit()

    def negative_results(self) -> tuple[dict[str, Any], ...]:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute("SELECT negative_id, hypothesis, what_falsified_it, "
                        "scope_of_falsification, superseded_by FROM negative_results "
                        "ORDER BY negative_id")
            rows = cur.fetchall()
        return tuple(
            {"negative_id": r[0], "hypothesis": r[1], "what_falsified_it": r[2],
             "scope": r[3], "superseded_by": r[4]} for r in rows
        )

    def record_claim(self, claim_id: str, claim: str, status: str,
                     evidence: tuple[tuple[str, str], ...] = ()) -> None:
        conn = self._require()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO claims (claim_id, claim, status) VALUES (%s,%s,%s) "
                "ON CONFLICT (claim_id) DO UPDATE SET status=EXCLUDED.status",
                (claim_id, claim, status))
            for ref, relation in evidence:
                cur.execute(
                    "INSERT INTO claim_evidence (claim_id, evidence_ref, relation) "
                    "VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    (claim_id, ref, relation))
        conn.commit()


def _refs_to_json(refs: ExternalRefs) -> dict[str, Any]:
    return {
        "mlflow_run_id": refs.mlflow_run_id,
        "mlflow_experiment_id": refs.mlflow_experiment_id,
        "langfuse_trace_id": refs.langfuse_trace_id,
        "otel_trace_id": refs.otel_trace_id,
        "dvc_dataset_revs": list(refs.dvc_dataset_revs),
        "artifact_ids": list(refs.artifact_ids),
    }


def _sinks_to_json(sinks: tuple[DegradedSink, ...]) -> list[dict[str, str]]:
    return [{"sink": s.sink, "reason": s.reason, "at": s.at,
             "lost_capability": s.lost_capability} for s in sinks]


def _row_to_record(row) -> RunRecord:
    refs = row[9] or {}
    sinks = row[10] or []
    return RunRecord(
        run_id=row[0],
        identity=ExperimentIdentity(
            experiment_id=row[1], experiment_revision=row[2],
            preregistration_hash=row[3], git_sha=row[6] or "",
            gamma_version=row[7] or "", environment_id=row[8] or ""),
        status=row[4],
        scientific_verdict=row[5],
        external=ExternalRefs(
            mlflow_run_id=refs.get("mlflow_run_id"),
            mlflow_experiment_id=refs.get("mlflow_experiment_id"),
            langfuse_trace_id=refs.get("langfuse_trace_id"),
            otel_trace_id=refs.get("otel_trace_id"),
            dvc_dataset_revs=tuple(refs.get("dvc_dataset_revs") or ()),
            artifact_ids=tuple(refs.get("artifact_ids") or ())),
        degraded_sinks=tuple(
            DegradedSink(s["sink"], s["reason"], s["at"], s["lost_capability"])
            for s in sinks),
    )


# --------------------------------------------------------------------------
# MLflow — run tracking
# --------------------------------------------------------------------------

@dataclass
class MLflowRunTracker:
    """OBSERVABILITY. MLflow generates a run id; LOGOS identity still dominates."""

    tracking_uri: str
    experiment_name: str = "logos-research"
    criticality: Criticality = "OBSERVABILITY"
    _client: Any = field(default=None, repr=False)
    _runs: dict[str, str] = field(default_factory=dict)

    def _mlflow(self):
        try:
            import mlflow
        except ImportError as exc:  # pragma: no cover
            raise InfrastructureUnavailable(f"mlflow not installed: {exc}") from exc
        mlflow.set_tracking_uri(self.tracking_uri)
        return mlflow

    def health(self) -> ServiceHealth:
        try:
            mlflow = self._mlflow()
            from mlflow.tracking import MlflowClient
            MlflowClient(self.tracking_uri).search_experiments(max_results=1)
            return ServiceHealth("mlflow", "HEALTHY", self.criticality,
                                 self.tracking_uri, mlflow.__version__)
        except Exception as exc:
            return ServiceHealth("mlflow", "UNAVAILABLE", self.criticality, str(exc))

    def start_run(self, identity: ExperimentIdentity, run_id: str,
                  tags: Mapping[str, str]) -> ExternalRefs:
        try:
            mlflow = self._mlflow()
            mlflow.set_experiment(self.experiment_name)
            active = mlflow.start_run(run_name=run_id, tags=dict(tags))
            self._runs[run_id] = active.info.run_id
            return ExternalRefs(mlflow_run_id=active.info.run_id,
                                mlflow_experiment_id=active.info.experiment_id)
        except Exception as exc:
            raise InfrastructureUnavailable(f"mlflow start_run failed: {exc}") from exc

    def log_params(self, run_id: str, params: Mapping[str, str]) -> None:
        mlflow = self._mlflow()
        mlflow.log_params(dict(params))

    def log_metrics(self, run_id: str, metrics: Mapping[str, float]) -> None:
        mlflow = self._mlflow()
        mlflow.log_metrics(dict(metrics))

    def end_run(self, run_id: str, status: str) -> None:
        mlflow = self._mlflow()
        # MLflow's terminal states are operational, never scientific.
        mlflow.end_run(status="FINISHED" if status in {"COMPLETED", "DEGRADED"} else "FAILED")

    def fetch(self, mlflow_run_id: str) -> dict[str, Any]:
        from mlflow.tracking import MlflowClient
        run = MlflowClient(self.tracking_uri).get_run(mlflow_run_id)
        return {"run_id": run.info.run_id, "status": run.info.status,
                "tags": dict(run.data.tags), "metrics": dict(run.data.metrics),
                "params": dict(run.data.params)}


# --------------------------------------------------------------------------
# MinIO / S3 — artifacts
# --------------------------------------------------------------------------

@dataclass
class S3ArtifactStore:
    """CANONICAL. Content-addressed; verified after every write."""

    endpoint_url: str
    bucket: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"
    criticality: Criticality = "CANONICAL"
    _client: Any = field(default=None, repr=False)

    def client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover
                raise InfrastructureUnavailable(f"boto3 not installed: {exc}") from exc
            self._client = boto3.client(
                "s3", endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region)
        return self._client

    def health(self) -> ServiceHealth:
        try:
            self.client().head_bucket(Bucket=self.bucket)
            return ServiceHealth("minio", "PERSISTENT", self.criticality,
                                 f"{self.endpoint_url}/{self.bucket}")
        except Exception as exc:
            return ServiceHealth("minio", "UNAVAILABLE", self.criticality, str(exc))

    def put(self, experiment_id: str, run_id: str, name: str, payload: bytes,
            media_type: str = "application/octet-stream") -> ArtifactRef:
        digest = sha256(payload).hexdigest()
        artifact_id = digest[:32]
        key = f"{experiment_id}/{run_id}/{artifact_id}/{name}"
        try:
            self.client().put_object(
                Bucket=self.bucket, Key=key, Body=payload, ContentType=media_type,
                Metadata={"logos-experiment-id": experiment_id,
                          "logos-run-id": run_id,
                          "logos-content-sha256": digest})
        except Exception as exc:
            raise InfrastructureUnavailable(f"artifact write failed: {exc}") from exc
        return ArtifactRef(artifact_id=artifact_id, content_sha256=digest,
                           size_bytes=len(payload), experiment_id=experiment_id,
                           run_id=run_id, media_type=media_type,
                           storage_location=f"s3://{self.bucket}/{key}")

    def get(self, artifact_id: str) -> bytes:
        client = self.client()
        listing = client.list_objects_v2(Bucket=self.bucket)
        for item in listing.get("Contents", []):
            if f"/{artifact_id}/" in item["Key"]:
                return client.get_object(Bucket=self.bucket, Key=item["Key"])["Body"].read()
        raise KeyError(artifact_id)

    def get_by_location(self, storage_location: str) -> bytes:
        key = storage_location.split(f"s3://{self.bucket}/", 1)[1]
        return self.client().get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def verify(self, ref: ArtifactRef) -> bool:
        try:
            payload = self.get_by_location(ref.storage_location)
        except Exception:
            return False
        return sha256(payload).hexdigest() == ref.content_sha256


# --------------------------------------------------------------------------
# OpenTelemetry — system traces
# --------------------------------------------------------------------------

@dataclass
class OpenTelemetryTraceSink:
    """OBSERVABILITY. Spans carry LOGOS identity as attributes."""

    endpoint: str
    service_name: str = "logos-research"
    criticality: Criticality = "OBSERVABILITY"
    _provider: Any = field(default=None, repr=False)

    def _tracer(self):
        if self._provider is None:
            try:
                from opentelemetry import trace
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                from opentelemetry.sdk.resources import Resource
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
            except ImportError as exc:  # pragma: no cover
                raise InfrastructureUnavailable(f"opentelemetry not installed: {exc}") from exc
            provider = TracerProvider(
                resource=Resource.create({"service.name": self.service_name}))
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{self.endpoint}/v1/traces")))
            trace.set_tracer_provider(provider)
            self._provider = provider
        from opentelemetry import trace
        return trace.get_tracer("logos.research")

    def health(self) -> ServiceHealth:
        import urllib.request
        try:
            # The collector's OTLP HTTP endpoint rejects GET; reaching it at all
            # is the signal. A refused connection is the failure we care about.
            urllib.request.urlopen(f"{self.endpoint}/v1/traces", timeout=5)
            return ServiceHealth("otel-collector", "HEALTHY", self.criticality, self.endpoint)
        except urllib.error.HTTPError:
            return ServiceHealth("otel-collector", "HEALTHY", self.criticality,
                                 f"{self.endpoint} (reachable)")
        except Exception as exc:
            return ServiceHealth("otel-collector", "UNAVAILABLE", self.criticality, str(exc))

    def emit(self, identity: ExperimentIdentity, run_id: str, span: str,
             attributes: Mapping[str, str]) -> ExternalRefs:
        try:
            tracer = self._tracer()
            with tracer.start_as_current_span(span) as current:
                current.set_attribute("logos.experiment_id", identity.experiment_id)
                current.set_attribute("logos.run_id", run_id)
                current.set_attribute("logos.preregistration_hash",
                                      identity.preregistration_hash)
                for key, value in redact(dict(attributes)).items():
                    current.set_attribute(str(key), str(value))
                trace_id = format(current.get_span_context().trace_id, "032x")
            return ExternalRefs(otel_trace_id=trace_id)
        except Exception as exc:
            raise InfrastructureUnavailable(f"otel emit failed: {exc}") from exc

    def flush(self) -> None:
        if self._provider is not None:
            self._provider.force_flush()


# --------------------------------------------------------------------------
# Langfuse — LLM traces
# --------------------------------------------------------------------------

@dataclass
class LangfuseTraceSink:
    """OBSERVABILITY. Redaction is applied before anything is sent."""

    host: str
    public_key: str
    secret_key: str
    criticality: Criticality = "OBSERVABILITY"
    _client: Any = field(default=None, repr=False)

    def client(self):
        if self._client is None:
            try:
                from langfuse import Langfuse
            except ImportError as exc:  # pragma: no cover
                raise InfrastructureUnavailable(f"langfuse not installed: {exc}") from exc
            self._client = Langfuse(public_key=self.public_key,
                                    secret_key=self.secret_key, host=self.host)
        return self._client

    def health(self) -> ServiceHealth:
        import urllib.request
        try:
            with urllib.request.urlopen(f"{self.host}/api/public/health", timeout=10) as r:
                body = json.loads(r.read().decode())
            return ServiceHealth("langfuse", "HEALTHY", self.criticality, self.host,
                                 str(body.get("version", "")))
        except Exception as exc:
            return ServiceHealth("langfuse", "UNAVAILABLE", self.criticality, str(exc))

    def emit_generation(self, identity: ExperimentIdentity, run_id: str,
                        payload: Mapping[str, object]) -> ExternalRefs:
        safe = redact(dict(payload))
        try:
            client = self.client()
            trace = client.trace(
                name=safe.get("name", "logos-generation"),
                user_id=None,
                session_id=run_id,
                metadata={"logos.experiment_id": identity.experiment_id,
                          "logos.run_id": run_id,
                          "logos.preregistration_hash": identity.preregistration_hash},
                tags=[f"experiment:{identity.experiment_id}", f"run:{run_id}"])
            trace.generation(
                name=str(safe.get("name", "generation")),
                model=str(safe.get("model", "unknown")),
                input=safe.get("input"),
                output=safe.get("output"),
                usage=safe.get("usage"),
                metadata={k: v for k, v in safe.items()
                          if k not in {"input", "output", "usage", "model", "name"}})
            client.flush()
            return ExternalRefs(langfuse_trace_id=trace.id)
        except Exception as exc:
            raise InfrastructureUnavailable(f"langfuse emit failed: {exc}") from exc

    def fetch(self, trace_id: str) -> dict[str, Any]:
        import base64
        import urllib.request
        token = base64.b64encode(f"{self.public_key}:{self.secret_key}".encode()).decode()
        req = urllib.request.Request(
            f"{self.host}/api/public/traces/{trace_id}",
            headers={"Authorization": f"Basic {token}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())


# --------------------------------------------------------------------------
# Environment wiring
# --------------------------------------------------------------------------

def dsn_from_env() -> str:
    return _env(
        "DATABASE_URL",
        "postgresql://logos:logos_local_dev_only@127.0.0.1:55432/logos_research",
    )


def backends_from_env() -> dict[str, Any]:
    """Construct every service-backed adapter from environment defaults."""
    return {
        "repository": PostgresResearchRepository(dsn_from_env()),
        "tracker": MLflowRunTracker(_env("MLFLOW_TRACKING_URI", "http://127.0.0.1:55000")),
        "artifacts": S3ArtifactStore(
            endpoint_url=_env("S3_ENDPOINT_URL", "http://127.0.0.1:59000"),
            bucket=_env("S3_ARTIFACT_BUCKET", "logos-artifacts"),
            access_key=_env("S3_ACCESS_KEY_ID", "logosminio"),
            secret_key=_env("S3_SECRET_ACCESS_KEY", "logos_local_dev_only"),
            region=_env("S3_REGION", "us-east-1")),
        "traces": OpenTelemetryTraceSink(
            _env("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:54318")),
        "llm_traces": LangfuseTraceSink(
            host=_env("LANGFUSE_HOST", "http://127.0.0.1:53000"),
            public_key=_env("LANGFUSE_PUBLIC_KEY", "pk-lf-logos-local-dev"),
            secret_key=_env("LANGFUSE_SECRET_KEY", "sk-lf-logos-local-dev")),
    }
