"""`ros_*` schema. Own version table so the lab's research-core migrations (`logos_schema_version`) stay untouched. Idempotent."""
from __future__ import annotations

from dataclasses import dataclass

VERSION_TABLE = "ros_schema_version"
ROS_TABLES = ["ros_theses", "ros_thesis_events", "ros_work_orders", "ros_work_order_deps", "ros_runs", "ros_run_events", "ros_jobs", "ros_decisions",
              "ros_inbox_items", "ros_radar_items", "ros_notes", "ros_artifacts", "ros_trace_links", "ros_audit"]


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "ros_control_plane", (
        f"CREATE TABLE IF NOT EXISTS {VERSION_TABLE} (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())",
        """CREATE TABLE IF NOT EXISTS ros_theses (
            thesis_id TEXT PRIMARY KEY, claim_ids TEXT[] NOT NULL DEFAULT '{}', title TEXT NOT NULL, track TEXT NOT NULL, state TEXT NOT NULL,
            owner TEXT NOT NULL DEFAULT 'founder', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_thesis_events (
            event_id BIGSERIAL PRIMARY KEY, thesis_id TEXT NOT NULL REFERENCES ros_theses(thesis_id) ON DELETE CASCADE, from_state TEXT, to_state TEXT NOT NULL,
            event TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', source_record TEXT, git_commit TEXT, at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_work_orders (
            work_order_id TEXT PRIMARY KEY, thesis_id TEXT REFERENCES ros_theses(thesis_id) ON DELETE CASCADE, state TEXT NOT NULL, spec JSONB NOT NULL,
            prereg_hash TEXT, approved_by TEXT, approved_at TIMESTAMPTZ, created_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_work_order_deps (
            child TEXT NOT NULL REFERENCES ros_work_orders(work_order_id) ON DELETE CASCADE, parent TEXT NOT NULL REFERENCES ros_work_orders(work_order_id) ON DELETE CASCADE,
            mandatory BOOLEAN NOT NULL DEFAULT TRUE, PRIMARY KEY (child, parent))""",
        """CREATE TABLE IF NOT EXISTS ros_runs (
            run_id TEXT PRIMARY KEY, work_order_id TEXT REFERENCES ros_work_orders(work_order_id) ON DELETE SET NULL, thesis_id TEXT REFERENCES ros_theses(thesis_id) ON DELETE SET NULL,
            kind TEXT NOT NULL, state TEXT NOT NULL, branch TEXT, worktree TEXT, artifact_dir TEXT, mlflow_parent_run TEXT, trace_root TEXT,
            started TIMESTAMPTZ, finished TIMESTAMPTZ, stop_reason TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_run_events (
            seq BIGSERIAL PRIMARY KEY, run_id TEXT NOT NULL REFERENCES ros_runs(run_id) ON DELETE CASCADE, at TIMESTAMPTZ NOT NULL DEFAULT now(),
            kind TEXT NOT NULL, payload JSONB NOT NULL DEFAULT '{}', privacy_class TEXT NOT NULL DEFAULT 'internal')""",
        "CREATE INDEX IF NOT EXISTS ros_run_events_run_idx ON ros_run_events (run_id, seq)",
        """CREATE TABLE IF NOT EXISTS ros_jobs (
            job_id BIGSERIAL PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, run_id TEXT, work_order_id TEXT, thesis_id TEXT,
            state TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0, attempt_group INTEGER NOT NULL DEFAULT 0, locked_by TEXT, locked_at TIMESTAMPTZ,
            payload JSONB NOT NULL DEFAULT '{}', result JSONB, error TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        "CREATE INDEX IF NOT EXISTS ros_jobs_state_idx ON ros_jobs (state, kind, job_id)",
        """CREATE TABLE IF NOT EXISTS ros_decisions (
            decision_id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject_ref TEXT NOT NULL, state TEXT NOT NULL, why TEXT NOT NULL, impact TEXT NOT NULL DEFAULT '',
            if_approved TEXT NOT NULL DEFAULT '', if_rejected TEXT NOT NULL DEFAULT '', blocks TEXT[] NOT NULL DEFAULT '{}', decided_by TEXT, decided_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_inbox_items (
            item_id BIGSERIAL PRIMARY KEY, kind TEXT NOT NULL, text TEXT NOT NULL, source TEXT, state TEXT NOT NULL DEFAULT 'UNTRIAGED', created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_radar_items (
            radar_id BIGSERIAL PRIMARY KEY, inbox_item_id BIGINT REFERENCES ros_inbox_items(item_id) ON DELETE SET NULL, state TEXT NOT NULL DEFAULT 'RAW',
            payload JSONB NOT NULL DEFAULT '{}', proposal JSONB, decided_by TEXT, decided_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_notes (
            note_id BIGSERIAL PRIMARY KEY, thesis_id TEXT REFERENCES ros_theses(thesis_id) ON DELETE CASCADE, run_id TEXT, author TEXT NOT NULL, text TEXT NOT NULL,
            decision_flag BOOLEAN NOT NULL DEFAULT FALSE, consumed_by_job BIGINT, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_artifacts (
            artifact_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, uri TEXT NOT NULL, kind TEXT NOT NULL, run_id TEXT REFERENCES ros_runs(run_id) ON DELETE SET NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_trace_links (
            link_id BIGSERIAL PRIMARY KEY, run_id TEXT NOT NULL REFERENCES ros_runs(run_id) ON DELETE CASCADE, mlflow_run_id TEXT, trace_id TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS ros_audit (
            audit_id BIGSERIAL PRIMARY KEY, at TIMESTAMPTZ NOT NULL DEFAULT now(), actor TEXT NOT NULL, action TEXT NOT NULL, subject TEXT NOT NULL, detail JSONB NOT NULL DEFAULT '{}')""",
    )),
)


def ensure_schema(conn) -> int:
    """Apply unapplied migrations in order; returns the current version. Safe to call on every request."""
    with conn.cursor() as cur:
        cur.execute(MIGRATIONS[0].statements[0]); conn.commit()
        cur.execute(f"SELECT version FROM {VERSION_TABLE}"); known = {r[0] for r in cur.fetchall()}
        for m in MIGRATIONS:
            if m.version in known:
                continue
            for s in m.statements:
                cur.execute(s)
            cur.execute(f"INSERT INTO {VERSION_TABLE} (version, name) VALUES (%s, %s)", (m.version, m.name))
        conn.commit()
        cur.execute(f"SELECT COALESCE(MAX(version), 0) FROM {VERSION_TABLE}")
        return int(cur.fetchone()[0])
