"""Postgres job queue (spec §5). Idempotency key = (work_order_id, run_id, kind, attempt_group): a restart never duplicates a job.

`claude` jobs enter as `waiting_governance` — Phase 3 (executor + ConcurrencyGovernor) lifts them; nothing in this module runs anything.
"""
from __future__ import annotations

import json
import os

from psycopg.rows import dict_row

from .service import _audit
from .state_machines import IllegalTransition, JOB_STATES, transition

DETERMINISTIC_KINDS = ("tests", "dataset", "dry_run", "rescore", "playwright_qa", "snapshot", "benchmark")
AGENT_KINDS = ("thesis_advance", "prior_art", "radar_process")          # R3: agent cap 3 (amendment), measurement cap 1 (governance record)
MEASUREMENT_KINDS = ("measurement",)
CLAUDE_KINDS = ("claude",) + AGENT_KINDS + MEASUREMENT_KINDS   # prior_art needs the deep-research skill (Claude + web tools) -> host job, not Docker (recorded deviation from spec §5)
KINDS = DETERMINISTIC_KINDS + CLAUDE_KINDS
LEASE_ENV = "ROS_JOB_LEASE_S"      # job lease: a running job whose locked_at is older than this is treated as lost (see sweep_lost)
DEFAULT_LEASE_S = 900
WORKER_LOST = "WORKER_LOST"


def idempotency_key(kind: str, work_order_id: str | None, run_id: str | None, attempt_group: int, thesis_id: str | None = None,
                    discriminator: str | None = None) -> str:
    """(work_order_id, run_id, thesis_id, kind, attempt_group[, discriminator]).

    `thesis_id` was added in R2 so that agent jobs of different theses never collide.
    `discriminator` was added by LOGOS1-EXECUTABLE-BOUNDARY-DEMO-R1 for jobs whose
    subject lives only in the payload: a `radar_process` job carries no work order,
    no run and no thesis, so every radar item produced the same key and the second
    item was silently handed the first item's job. The segment is appended only when
    present, so every key issued before this change is unchanged.
    """
    base = f"{work_order_id or '-'}|{run_id or '-'}|{thesis_id or '-'}|{kind}|{attempt_group}"
    return base if discriminator is None else f"{base}|{discriminator}"


def enqueue(conn, kind: str, *, work_order_id: str | None = None, run_id: str | None = None, thesis_id: str | None = None, payload: dict | None = None, attempt_group: int = 0, actor: str = "system",
            discriminator: str | None = None) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown job kind {kind!r}; expected one of {KINDS}")
    key = idempotency_key(kind, work_order_id, run_id, attempt_group, thesis_id, discriminator)
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


def request_stop(conn, job_id: int, actor: str = "founder") -> dict:
    """Graceful stop: the executor checks the flag before every invocation and terminates the current process; the job state moves via `stop`."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("UPDATE ros_jobs SET stop_requested = TRUE, updated_at = now() WHERE job_id = %s RETURNING *", (job_id,)); row = cur.fetchone()
        if row is None:
            raise KeyError(job_id)
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'job.stop_requested', %s, '{}')", (actor, str(job_id)))
    conn.commit()
    if row["state"] in ("queued", "waiting_quota", "waiting_dependency", "waiting_governance", "paused"):
        return _apply(conn, job_id, "stop", actor)
    return row


def stop_requested(conn, job_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT stop_requested FROM ros_jobs WHERE job_id = %s", (job_id,)); r = cur.fetchone()
    return bool(r and r[0])


def start(conn, job_id: int, actor: str, gate: dict) -> dict:
    """Founder Start for a Claude job: waiting_governance -> queued, only with a passed pre-run gate (recorded in the audit row)."""
    if actor != "founder":
        raise IllegalTransition("job", "waiting_governance", "governance_pass", actor, "founder gate")
    if not gate.get("passed"):
        raise ValueError(f"pre-run gate failed: {[k for k, v in gate.get('checks', {}).items() if not v]}")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_jobs WHERE job_id = %s FOR UPDATE", (job_id,)); job = cur.fetchone()
        if job is None:
            raise KeyError(job_id)
        nxt = transition("job", job["state"], "governance_pass", "system")
        cur.execute("UPDATE ros_jobs SET state = %s, started_by = %s, updated_at = now() WHERE job_id = %s RETURNING *", (nxt, actor, job_id)); row = cur.fetchone()
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'job.start', %s, %s)", (actor, str(job_id), json.dumps({"gate": gate})))
    conn.commit()
    return row


def lease_seconds(env: dict | None = None) -> int:
    """The job lease from `ROS_JOB_LEASE_S`; a missing, non-integer or non-positive value falls back to DEFAULT_LEASE_S."""
    raw = (os.environ if env is None else env).get(LEASE_ENV, "")
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LEASE_S
    return value if value > 0 else DEFAULT_LEASE_S


def renew_lease(conn, job_id: int, worker_id: str) -> bool:
    """Refresh `locked_at` of a job this worker still holds. False = the lease is gone (swept, stopped or re-locked): the caller must stop working on it."""
    with conn.cursor() as cur:
        cur.execute("UPDATE ros_jobs SET locked_at = now() WHERE job_id = %s AND locked_by = %s AND state = 'running'", (job_id, worker_id)); held = cur.rowcount == 1
    conn.commit()
    return held


def _close_open_runs(cur, job_id: int, reason: str) -> list[str]:
    """Runs of `job_id` still marked running -> failed with `reason`, plus one `error` event each. Same transaction as the caller."""
    cur.execute("UPDATE ros_runs SET state = 'failed', finished = now(), stop_reason = %s WHERE job_id = %s AND state = 'running' RETURNING run_id", (reason, job_id))
    run_ids = [r["run_id"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
    for run_id in run_ids:
        cur.execute("INSERT INTO ros_run_events (run_id, kind, payload, privacy_class) VALUES (%s, 'error', %s, 'internal')", (run_id, json.dumps({"reason": reason})))
    return run_ids


def close_open_runs(conn, job_id: int, reason: str) -> list[str]:
    with conn.cursor() as cur:
        run_ids = _close_open_runs(cur, job_id, reason)
    conn.commit()
    return run_ids


def sweep_lost(conn, kinds: tuple[str, ...] | list[str], lease_s: int, *, actor: str = "system", only_job_ids: list[int] | None = None) -> list[dict]:
    """Move running jobs of `kinds` whose lease expired (`locked_at` older than `lease_s`) to `failed` with error WORKER_LOST.

    Each move goes through the job state machine (`running --fail--> failed`) and writes one `job.transition` audit row; the job's
    open runs are closed in the same transaction. A job with a fresh lock or a NULL lock is not touched; a terminal job is never
    selected, so a second sweep changes nothing. Nothing is requeued: recovery is the explicit founder `retry`.
    `only_job_ids` restricts the sweep (test isolation and targeted repair).
    """
    sql = "SELECT * FROM ros_jobs WHERE state = 'running' AND kind = ANY(%s) AND locked_at < now() - make_interval(secs => %s)"
    args: list = [list(kinds), float(lease_s)]
    if only_job_ids is not None:
        sql += " AND job_id = ANY(%s)"; args.append(list(only_job_ids))
    swept = []
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql + " ORDER BY job_id FOR UPDATE SKIP LOCKED", args)
        for job in cur.fetchall():
            nxt = transition("job", job["state"], "fail", actor)
            cur.execute("UPDATE ros_jobs SET state = %s, error = %s, locked_by = NULL, updated_at = now() WHERE job_id = %s RETURNING *", (nxt, WORKER_LOST, job["job_id"])); row = cur.fetchone()
            run_ids = _close_open_runs(cur, job["job_id"], WORKER_LOST)
            _audit(cur, actor, "job.transition", str(job["job_id"]), {"event": "fail", "from": job["state"], "to": nxt, "reason": WORKER_LOST, "locked_by": job["locked_by"],
                                                                       "locked_at": job["locked_at"], "lease_s": lease_s, "runs_closed": run_ids})
            swept.append(row)
    conn.commit()
    return swept


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
