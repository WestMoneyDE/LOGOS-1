"""Postgres job queue (spec §5). Idempotency key = (work_order_id, run_id, kind, attempt_group): a restart never duplicates a job.

`claude` jobs enter as `waiting_governance` — Phase 3 (executor + ConcurrencyGovernor) lifts them; nothing in this module runs anything.
"""
from __future__ import annotations

import json

from psycopg.rows import dict_row

from .state_machines import JOB_STATES, transition

DETERMINISTIC_KINDS = ("prior_art", "tests", "dataset", "dry_run", "rescore", "playwright_qa", "snapshot")
CLAUDE_KINDS = ("claude", "thesis_advance", "radar_process")
KINDS = DETERMINISTIC_KINDS + CLAUDE_KINDS


def idempotency_key(kind: str, work_order_id: str | None, run_id: str | None, attempt_group: int) -> str:
    return f"{work_order_id or '-'}|{run_id or '-'}|{kind}|{attempt_group}"


def enqueue(conn, kind: str, *, work_order_id: str | None = None, run_id: str | None = None, thesis_id: str | None = None, payload: dict | None = None, attempt_group: int = 0, actor: str = "system") -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown job kind {kind!r}; expected one of {KINDS}")
    key = idempotency_key(kind, work_order_id, run_id, attempt_group)
    initial = "waiting_governance" if kind in CLAUDE_KINDS else "queued"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_jobs WHERE idempotency_key = %s", (key,)); existing = cur.fetchone()
        if existing:
            conn.commit(); return {**existing, "duplicate": True}
        cur.execute("INSERT INTO ros_jobs (idempotency_key, kind, run_id, work_order_id, thesis_id, state, attempt_group, payload) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
                    (key, kind, run_id, work_order_id, thesis_id, initial, attempt_group, json.dumps(payload or {})))
        row = cur.fetchone()
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'job.enqueue', %s, %s)", (actor, str(row["job_id"]), json.dumps({"kind": kind, "state": initial, "key": key})))
    conn.commit()
    return {**row, "duplicate": False}


def dequeue(conn, worker_id: str, kinds: tuple[str, ...] | list[str]) -> dict | None:
    """Claim the oldest queued job of the given kinds. FOR UPDATE SKIP LOCKED — two workers never get the same job."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_jobs WHERE state = 'queued' AND kind = ANY(%s) ORDER BY job_id FOR UPDATE SKIP LOCKED LIMIT 1", (list(kinds),)); job = cur.fetchone()
        if job is None:
            conn.commit(); return None
        nxt = transition("job", job["state"], "dequeue", "worker")
        cur.execute("UPDATE ros_jobs SET state = %s, locked_by = %s, locked_at = now(), attempt = attempt + 1, updated_at = now() WHERE job_id = %s RETURNING *", (nxt, worker_id, job["job_id"])); row = cur.fetchone()
    conn.commit()
    return row


def _apply(conn, job_id: int, event: str, actor: str, *, result: dict | None = None, error: str | None = None) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_jobs WHERE job_id = %s FOR UPDATE", (job_id,)); job = cur.fetchone()
        if job is None:
            raise KeyError(job_id)
        nxt = transition("job", job["state"], event, actor)
        cur.execute("UPDATE ros_jobs SET state = %s, result = COALESCE(%s, result), error = COALESCE(%s, error), locked_by = CASE WHEN %s IN ('done','failed','stopped','paused','queued') THEN NULL ELSE locked_by END, updated_at = now() WHERE job_id = %s RETURNING *",
                    (nxt, json.dumps(result) if result is not None else None, error, nxt, job_id)); row = cur.fetchone()
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'job.transition', %s, %s)", (actor, str(job_id), json.dumps({"event": event, "from": job["state"], "to": nxt})))
    conn.commit()
    return row


def complete(conn, job_id: int, result: dict, actor: str = "worker") -> dict: return _apply(conn, job_id, "complete", actor, result=result)
def fail(conn, job_id: int, error: str, actor: str = "worker") -> dict: return _apply(conn, job_id, "fail", actor, error=error)
def pause(conn, job_id: int, actor: str = "founder") -> dict: return _apply(conn, job_id, "pause", actor)
def resume(conn, job_id: int, actor: str = "founder") -> dict: return _apply(conn, job_id, "resume", actor)
def stop(conn, job_id: int, actor: str = "founder") -> dict: return _apply(conn, job_id, "stop", actor)
def retry(conn, job_id: int, actor: str = "founder") -> dict: return _apply(conn, job_id, "retry", actor)
def governance_pass(conn, job_id: int, actor: str = "system") -> dict: return _apply(conn, job_id, "governance_pass", actor)


def stats(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT state, count(*) FROM ros_jobs GROUP BY state"); got = dict(cur.fetchall())
    return {s: int(got.get(s, 0)) for s in JOB_STATES}


def list_jobs(conn, limit: int = 200, state: str | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if state:
            cur.execute("SELECT * FROM ros_jobs WHERE state = %s ORDER BY job_id DESC LIMIT %s", (state, limit))
        else:
            cur.execute("SELECT * FROM ros_jobs ORDER BY (state IN ('running','queued')) DESC, job_id DESC LIMIT %s", (limit,))
        return cur.fetchall()
