"""Integration tests against the materialized local research stack.

These require the stack from `infra/docker-compose.yml` to be running. They skip
cleanly when it is not, so the deterministic core stays testable while services
are down — an MLflow outage must not make Γ untestable.

Start the stack with:

    cd infra && docker compose up -d

`docker compose down -v` is DESTRUCTIVE: it deletes the volumes and with them the
canonical research records and artifacts.
"""
from __future__ import annotations

import hashlib
import json

import pytest

pytest.importorskip("psycopg")

from logos_research.infra.backends import backends_from_env  # noqa: E402
from logos_research.infra.identity import ExperimentIdentity  # noqa: E402
from logos_research.infra.smoke import EXPERIMENT_ID  # noqa: E402


def _stack_available() -> bool:
    try:
        backends = backends_from_env()
        repo = backends["repository"]
        repo.connect()
        healthy = repo.health().is_usable()
        repo.close()
        return healthy
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _stack_available(),
    reason="local research stack not running (cd infra && docker compose up -d)",
)


@pytest.fixture(scope="module")
def backends():
    b = backends_from_env()
    b["repository"].connect()
    b["repository"].migrate()
    yield b
    b["repository"].close()


# --------------------------------------------------------------------------
# Migration reproducibility and health
# --------------------------------------------------------------------------

def test_migrations_are_idempotent(backends):
    repo = backends["repository"]
    version = repo.schema_version()
    assert repo.migrate() == (), "re-running migrations changed the schema"
    assert repo.schema_version() == version


def test_every_canonical_service_reports_persistent(backends):
    assert backends["repository"].health().status == "PERSISTENT"
    assert backends["artifacts"].health().status == "PERSISTENT"


def test_observability_services_are_reachable(backends):
    for name in ("tracker", "traces", "llm_traces"):
        health = backends[name].health()
        assert health.is_usable(), f"{health.name}: {health.detail}"
        assert health.criticality == "OBSERVABILITY"


# --------------------------------------------------------------------------
# Schema invariants — the database refuses to collapse research semantics
# --------------------------------------------------------------------------

def test_database_refuses_a_verdict_on_an_unfinished_run(backends):
    """`OperationalRunStatus != ScientificVerdict`, enforced by a check constraint."""
    conn = backends["repository"]._conn
    identity = _fixture_identity(backends, "constraint-check")
    with pytest.raises(Exception) as exc:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO runs (run_id, experiment_id, experiment_revision, "
                "preregistration_hash, run_status, scientific_verdict) "
                "VALUES (%s,%s,%s,%s,'RUNNING','SUPPORTED')",
                ("verdict-on-running", identity.experiment_id,
                 identity.experiment_revision, identity.preregistration_hash))
    conn.rollback()
    assert "verdict_requires_finished_run" in str(exc.value)


def test_database_refuses_an_unknown_verdict(backends):
    conn = backends["repository"]._conn
    identity = _fixture_identity(backends, "constraint-check")
    with pytest.raises(Exception) as exc:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO runs (run_id, experiment_id, experiment_revision, "
                "preregistration_hash, run_status, scientific_verdict) "
                "VALUES (%s,%s,%s,%s,'COMPLETED','PROBABLY_TRUE')",
                ("bogus-verdict", identity.experiment_id,
                 identity.experiment_revision, identity.preregistration_hash))
    conn.rollback()
    assert "verdict_known" in str(exc.value)


def test_infrastructure_failure_cannot_be_marked_learnable(backends):
    """A tool timeout teaches nothing; the schema enforces it."""
    conn = backends["repository"]._conn
    with pytest.raises(Exception) as exc:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO failure_attributions (failure_id, source, evidence, "
                "learning_permitted) VALUES ('f-bad','MLFLOW','tracker down',TRUE)")
    conn.rollback()
    assert "infrastructure_failure_teaches_nothing" in str(exc.value)


def test_preregistration_hash_is_the_primary_key(backends):
    """Criteria cannot be mutated under a fixed hash.

    `_fixture_identity` performs the genuinely first freeze, so every later
    freeze under the same hash — including the two below — must be a no-op.
    """
    repo = backends["repository"]
    identity = _fixture_identity(backends, "prereg-immutable")

    def stored():
        with repo._conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM preregistrations WHERE preregistration_hash=%s",
                (identity.preregistration_hash,))
            return cur.fetchone()[0]

    first = stored()
    assert first == {"marker": "TEST_FIXTURE"}

    repo.freeze_preregistration(identity, {"criteria": "moved goalposts"})
    repo.freeze_preregistration(identity, {"criteria": "moved again"})

    assert stored() == first, "preregistration payload changed under a fixed hash"


def test_all_five_verdicts_stay_distinct_after_persistence(backends):
    """No semantic collapsing in the database."""
    repo = backends["repository"]
    identity = _fixture_identity(backends, "verdict-fixtures")
    verdicts = ["SUPPORTED", "PARTIALLY_SUPPORTED", "FALSIFIED", "INCONCLUSIVE",
                "INVALID_MEASUREMENT"]
    conn = repo._conn
    with conn.cursor() as cur:
        for verdict in verdicts:
            cur.execute(
                "INSERT INTO runs (run_id, experiment_id, experiment_revision, "
                "preregistration_hash, run_status, scientific_verdict) "
                "VALUES (%s,%s,%s,%s,'COMPLETED',%s) ON CONFLICT (run_id) DO NOTHING",
                (f"verdict-{verdict}", identity.experiment_id,
                 identity.experiment_revision, identity.preregistration_hash, verdict))
    conn.commit()
    with conn.cursor() as cur:
        cur.execute("SELECT scientific_verdict FROM runs WHERE run_id LIKE 'verdict-%%'")
        stored = {row[0] for row in cur.fetchall()}
    assert set(verdicts) <= stored


def test_a_negative_result_survives_a_later_repair(backends):
    """A repair may supersede a failure; it may not overwrite it."""
    repo = backends["repository"]
    repo.record_negative_result(
        "N-SMOKE-1", "synthetic fixture hypothesis", "synthetic test",
        "synthetic counterexample", "TEST_FIXTURE / NON_SCIENTIFIC")
    repo.record_negative_result(
        "N-SMOKE-1", "REWRITTEN", "REWRITTEN", "REWRITTEN", "REWRITTEN")
    found = {n["negative_id"]: n for n in repo.negative_results()}
    assert "N-SMOKE-1" in found
    assert found["N-SMOKE-1"]["hypothesis"] == "synthetic fixture hypothesis"


# --------------------------------------------------------------------------
# Cross-system correlation — the strongest acceptance condition
# --------------------------------------------------------------------------

def test_one_experiment_id_resolves_every_external_record(backends):
    repo = backends["repository"]
    runs = repo.runs_for_experiment(EXPERIMENT_ID)
    assert runs, "smoke run not present; run logos_research.infra.smoke.run() first"
    record = runs[0]
    assert record.external.mlflow_run_id
    assert record.external.langfuse_trace_id
    assert record.external.otel_trace_id
    assert record.external.artifact_ids
    assert record.external.dvc_dataset_revs


def test_the_mlflow_run_carries_logos_identity(backends):
    record = backends["repository"].runs_for_experiment(EXPERIMENT_ID)[0]
    run = backends["tracker"].fetch(record.external.mlflow_run_id)
    assert run["tags"]["logos.experiment_id"] == EXPERIMENT_ID
    assert run["tags"]["logos.run_id"] == record.run_id
    assert run["tags"]["logos.preregistration_hash"] == record.identity.preregistration_hash


def test_the_langfuse_trace_carries_logos_identity_and_no_secret(backends):
    record = backends["repository"].runs_for_experiment(EXPERIMENT_ID)[0]
    trace = backends["llm_traces"].fetch(record.external.langfuse_trace_id)
    raw = json.dumps(trace)
    assert trace["metadata"]["logos.experiment_id"] == EXPERIMENT_ID
    assert "sk-THIS-MUST-NOT-LEAVE" not in raw, "secret leaked into Langfuse"
    assert "[REDACTED]" in raw


def test_the_artifact_round_trips_with_its_recorded_hash(backends):
    repo = backends["repository"]
    record = repo.runs_for_experiment(EXPERIMENT_ID)[0]
    with repo._conn.cursor() as cur:
        cur.execute("SELECT content_sha256, storage_location, size_bytes "
                    "FROM artifact_references WHERE run_id=%s", (record.run_id,))
        digest, location, size = cur.fetchone()
    payload = backends["artifacts"].get_by_location(location)
    assert hashlib.sha256(payload).hexdigest() == digest
    assert len(payload) == size


def test_dataset_lineage_keeps_object_and_semantic_identity_apart(backends):
    repo = backends["repository"]
    with repo._conn.cursor() as cur:
        cur.execute("SELECT object_hash, semantic_identity, identity_kind "
                    "FROM dataset_references WHERE dataset_name='smoke_dataset.jsonl'")
        row = cur.fetchone()
    assert row is not None
    assert row[0] != row[1], "object hash and semantic identity collapsed into one"
    assert row[2] == "ordered_row_identity"


def test_the_smoke_run_records_no_scientific_verdict(backends):
    """An infrastructure fixture must never look like scientific evidence."""
    record = backends["repository"].runs_for_experiment(EXPERIMENT_ID)[0]
    assert record.scientific_verdict is None
    assert record.status == "COMPLETED"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _fixture_identity(backends, tag: str) -> ExperimentIdentity:
    repo = backends["repository"]
    experiment_id = f"INFRA-FIXTURE-{tag}"
    repo.ensure_experiment(experiment_id, f"TEST_FIXTURE {tag} (NON_SCIENTIFIC)")
    digest = hashlib.sha256(tag.encode()).hexdigest()
    identity = ExperimentIdentity(experiment_id, 1, digest)
    repo.freeze_preregistration(identity, {"marker": "TEST_FIXTURE"})
    return identity
