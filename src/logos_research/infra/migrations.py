"""Versioned, idempotent schema migrations for the canonical research database.

A deliberately small migration runner rather than Alembic. The repository has no
existing migration framework, and adding SQLAlchemy plus Alembic to own eight
tables would introduce a second heavy dependency for very little. Migrations are
ordered SQL statements with a recorded version; the runner is ~40 lines and the
whole schema is reproducible from an empty database with one command.

The schema encodes research semantics rather than merely storing rows:

* a preregistration is content-addressed and its hash is the primary key, so an
  experiment cannot silently mutate its own criteria;
* `run_status` and `scientific_verdict` are separate columns with separate check
  constraints, so an operational state can never be read as a verdict;
* negative results have no `DELETE` path in this module and carry their own id,
  so a later repair cannot overwrite the failure it repaired;
* claim evidence is a link table, so a claim without evidence is visibly a claim
  without evidence.
"""
from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION_TABLE = "logos_schema_version"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        name="research_core",
        statements=(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
                version     INTEGER PRIMARY KEY,
                name        TEXT NOT NULL,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id   TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS preregistrations (
                preregistration_hash TEXT PRIMARY KEY,
                experiment_id        TEXT NOT NULL REFERENCES experiments(experiment_id),
                revision             INTEGER NOT NULL,
                supersedes           TEXT REFERENCES preregistrations(preregistration_hash),
                payload              JSONB NOT NULL,
                frozen_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (experiment_id, revision)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id               TEXT PRIMARY KEY,
                experiment_id        TEXT NOT NULL REFERENCES experiments(experiment_id),
                experiment_revision  INTEGER NOT NULL,
                preregistration_hash TEXT NOT NULL REFERENCES preregistrations(preregistration_hash),
                run_status           TEXT NOT NULL,
                scientific_verdict   TEXT,
                git_sha              TEXT NOT NULL DEFAULT '',
                gamma_version        TEXT NOT NULL DEFAULT '',
                environment_id       TEXT NOT NULL DEFAULT '',
                started_at           TIMESTAMPTZ,
                completed_at         TIMESTAMPTZ,
                external_refs        JSONB NOT NULL DEFAULT '{}'::jsonb,
                degraded_sinks       JSONB NOT NULL DEFAULT '[]'::jsonb,
                CONSTRAINT run_status_known CHECK (run_status IN (
                    'REGISTERED','READY','RUNNING','COMPLETED','FAILED','ABORTED','DEGRADED')),
                CONSTRAINT verdict_known CHECK (scientific_verdict IS NULL OR scientific_verdict IN (
                    'SUPPORTED','PARTIALLY_SUPPORTED','FALSIFIED','INCONCLUSIVE','INVALID_MEASUREMENT')),
                CONSTRAINT verdict_requires_finished_run CHECK (
                    scientific_verdict IS NULL OR run_status IN ('COMPLETED','DEGRADED'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS artifact_references (
                artifact_id     TEXT PRIMARY KEY,
                run_id          TEXT NOT NULL REFERENCES runs(run_id),
                experiment_id   TEXT NOT NULL REFERENCES experiments(experiment_id),
                content_sha256  TEXT NOT NULL,
                size_bytes      BIGINT NOT NULL,
                media_type      TEXT NOT NULL DEFAULT 'application/octet-stream',
                storage_location TEXT NOT NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dataset_references (
                dataset_name      TEXT NOT NULL,
                revision          TEXT NOT NULL,
                object_hash       TEXT NOT NULL,
                semantic_identity TEXT NOT NULL,
                identity_kind     TEXT NOT NULL,
                run_id            TEXT REFERENCES runs(run_id),
                created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (dataset_name, revision)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS claims (
                claim_id      TEXT PRIMARY KEY,
                claim         TEXT NOT NULL,
                status        TEXT NOT NULL,
                scope         TEXT NOT NULL DEFAULT '',
                confidence    TEXT NOT NULL DEFAULT '',
                last_reviewed TIMESTAMPTZ,
                CONSTRAINT claim_status_known CHECK (status IN (
                    'SPECULATIVE','SUPPORTED','PARTIALLY_SUPPORTED','REPLICATED',
                    'CAUSALLY_SUPPORTED','CHALLENGED','FALSIFIED','INCONCLUSIVE'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS claim_evidence (
                claim_id      TEXT NOT NULL REFERENCES claims(claim_id),
                run_id        TEXT REFERENCES runs(run_id),
                evidence_ref  TEXT NOT NULL,
                relation      TEXT NOT NULL,
                CONSTRAINT relation_known CHECK (relation IN ('SUPPORTS','COUNTERS','INTERVENTION')),
                PRIMARY KEY (claim_id, evidence_ref, relation)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS negative_results (
                negative_id            TEXT PRIMARY KEY,
                hypothesis             TEXT NOT NULL,
                how_tested             TEXT NOT NULL,
                what_falsified_it      TEXT NOT NULL,
                scope_of_falsification TEXT NOT NULL,
                run_id                 TEXT REFERENCES runs(run_id),
                retest_justified       BOOLEAN NOT NULL DEFAULT FALSE,
                retest_rationale       TEXT NOT NULL DEFAULT '',
                recorded_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
                superseded_by          TEXT REFERENCES negative_results(negative_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS failure_attributions (
                failure_id         TEXT PRIMARY KEY,
                run_id             TEXT REFERENCES runs(run_id),
                source             TEXT NOT NULL,
                evidence           TEXT NOT NULL,
                scope              TEXT NOT NULL DEFAULT '',
                learning_permitted BOOLEAN NOT NULL DEFAULT FALSE,
                recorded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT infrastructure_failure_teaches_nothing CHECK (
                    NOT (learning_permitted AND source IN (
                        'SANDBOX','NETWORK','TOOL','ORCHESTRATOR','MEASUREMENT','UNKNOWN',
                        'DATABASE','MLFLOW','LANGFUSE','OTEL','DVC','ARTIFACT_STORE',
                        'CONFIGURATION','MIGRATION','IDENTITY_CORRELATION')))
            )
            """,
            "CREATE INDEX IF NOT EXISTS runs_experiment_idx ON runs(experiment_id)",
            "CREATE INDEX IF NOT EXISTS artifacts_run_idx ON artifact_references(run_id)",
        ),
    ),
)


def apply_migrations(conn) -> tuple[int, ...]:
    """Apply every unapplied migration in order. Idempotent.

    Returns the versions applied by this call, empty when already current.
    """
    applied: list[int] = []
    with conn.cursor() as cur:
        cur.execute(MIGRATIONS[0].statements[0])
        conn.commit()
        cur.execute(f"SELECT version FROM {SCHEMA_VERSION_TABLE}")
        known = {row[0] for row in cur.fetchall()}
        for migration in MIGRATIONS:
            if migration.version in known:
                continue
            for statement in migration.statements:
                cur.execute(statement)
            cur.execute(
                f"INSERT INTO {SCHEMA_VERSION_TABLE} (version, name) VALUES (%s, %s)",
                (migration.version, migration.name),
            )
            applied.append(migration.version)
        conn.commit()
    return tuple(applied)


def current_version(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT COALESCE(MAX(version), 0) FROM {SCHEMA_VERSION_TABLE}"
        )
        return int(cur.fetchone()[0])
