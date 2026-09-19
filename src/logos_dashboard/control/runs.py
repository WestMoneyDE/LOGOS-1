"""ros_runs + ros_run_events: the append-only event stream behind the run console (spec §6)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from psycopg.rows import dict_row

EVENT_KINDS = ("phase", "gate", "worktree", "packet", "claude.invoke", "claude.result", "artifact", "commit", "thesis.event", "quota", "stop", "error", "note", "done", "agent.init", "agent.batch", "agent.result", "work_order.draft", "autopilot", "measure.item")
PRIVACY = ("public", "internal", "redacted")


def create_run(conn, run_id: str, *, job_id: int, kind: str, thesis_id: str | None, work_order_id: str | None, branch: str | None = None, worktree: str | None = None) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_runs (run_id, job_id, work_order_id, thesis_id, kind, state, branch, worktree, started) VALUES (%s, %s, %s, %s, %s, 'running', %s, %s, now()) RETURNING *",
                    (run_id, job_id, work_order_id, thesis_id, kind, branch, worktree)); row = cur.fetchone()
    conn.commit()
    return row


def emit(conn, run_id: str, kind: str, payload: dict | None = None, privacy: str = "internal") -> int:
    if kind not in EVENT_KINDS:
        raise ValueError(kind)
    if privacy not in PRIVACY:
        raise ValueError(privacy)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ros_run_events (run_id, kind, payload, privacy_class) VALUES (%s, %s, %s, %s) RETURNING seq", (run_id, kind, json.dumps(payload or {}, default=str), privacy)); seq = cur.fetchone()[0]
    conn.commit()
    return int(seq)


def finish_run(conn, run_id: str, state: str, stop_reason: str | None = None, summary: dict | None = None, **cols) -> dict:
    sets = ["state = %s", "finished = now()", "stop_reason = %s", "summary = %s"]; vals = [state, stop_reason, json.dumps(summary, default=str) if summary is not None else None]
    for k, v in cols.items():
        if k in ("branch", "worktree", "artifact_dir", "mlflow_parent_run", "trace_root"):
            sets.append(f"{k} = %s"); vals.append(v)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"UPDATE ros_runs SET {', '.join(sets)} WHERE run_id = %s RETURNING *", (*vals, run_id)); row = cur.fetchone()
    conn.commit()
    return row


def get_run(conn, run_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_runs WHERE run_id = %s", (run_id,)); return cur.fetchone()


def list_runs(conn, limit: int = 100, thesis_id: str | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if thesis_id:
            cur.execute("SELECT r.*, (SELECT count(*) FROM ros_run_events e WHERE e.run_id = r.run_id) AS n_events FROM ros_runs r WHERE thesis_id = %s ORDER BY created_at DESC LIMIT %s", (thesis_id, limit))
        else:
            cur.execute("SELECT r.*, (SELECT count(*) FROM ros_run_events e WHERE e.run_id = r.run_id) AS n_events FROM ros_runs r ORDER BY (state = 'running') DESC, created_at DESC LIMIT %s", (limit,))
        return cur.fetchall()


def events_after(conn, run_id: str, after: int = 0, limit: int = 500) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_run_events WHERE run_id = %s AND seq > %s ORDER BY seq LIMIT %s", (run_id, after, limit)); return cur.fetchall()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
