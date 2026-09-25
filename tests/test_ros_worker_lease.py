"""ros-worker lease and lost-lease sweep: a crash or container restart must not leave a job and its run `running` forever.

Prediction (stated before implementation): a deterministic job left `running` with a lock older than the lease is moved by
`queue.sweep_lost` to `failed` with error WORKER_LOST through the job state machine (`running --fail--> failed`), with one
`job.transition` audit row and its open run closed; a fresh lock, a terminal job and a Claude-kind job are untouched; a second
sweep changes nothing; nothing is requeued, and the existing founder `retry` recovers the job.

DB-backed tests use the lab Postgres with TEST-ROS- ids and are skipped (not failed) when it is unreachable, like
tests/test_ros_control_plane.py. The sweep is scoped with `only_job_ids`, so it never touches lab jobs outside the test.
"""
from __future__ import annotations

import subprocess
import sys
import uuid

import pytest

from logos_dashboard import db
from logos_dashboard.control import queue, runs, service, worker
from logos_dashboard.control.state_machines import IllegalTransition, transition

# -- pure ---------------------------------------------------------------------------------------------------------


def test_lease_seconds_reads_env_and_falls_back():
    assert queue.lease_seconds({}) == queue.DEFAULT_LEASE_S == 900
    assert queue.lease_seconds({"ROS_JOB_LEASE_S": "120"}) == 120
    for bad in ("", "abc", "0", "-5", "1.5"):
        assert queue.lease_seconds({"ROS_JOB_LEASE_S": bad}) == 900, bad


def test_sweep_uses_an_existing_ungated_job_transition():
    """The sweep adds no transition: `running --fail--> failed` exists and is not a founder gate."""
    assert transition("job", "running", "fail", "system") == "failed"
    with pytest.raises(IllegalTransition):
        transition("job", "done", "fail", "system")
    with pytest.raises(IllegalTransition):
        transition("job", "failed", "fail", "system")


def test_run_leased_returns_output_and_stops_on_a_lost_lease(monkeypatch):
    job = {"job_id": -1, "locked_by": "w-test"}
    monkeypatch.setattr(queue, "renew_lease", lambda conn, job_id, worker_id: True)
    cp = worker._run_leased(None, job, [sys.executable, "-c", "print('ok')"], 60)
    assert cp.returncode == 0 and cp.stdout.strip() == "ok"
    renewals = []
    monkeypatch.setattr(queue, "lease_seconds", lambda env=None: 3)            # renew every 1 s
    monkeypatch.setattr(queue, "renew_lease", lambda conn, job_id, worker_id: renewals.append(job_id) or False)
    with pytest.raises(worker.LeaseLost):
        worker._run_leased(None, job, [sys.executable, "-c", "import time; time.sleep(60)"], 3600)
    assert renewals == [-1]
    monkeypatch.setattr(queue, "renew_lease", lambda conn, job_id, worker_id: True)
    with pytest.raises(subprocess.TimeoutExpired):
        worker._run_leased(None, job, [sys.executable, "-c", "import time; time.sleep(60)"], 0.5)


# -- DB-backed ----------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def conn():
    c = db.connect()
    if c is None:
        pytest.skip("lab Postgres unreachable — dashboard runs records-only")
    db.ensure_schema(c)
    yield c
    c.close()


@pytest.fixture
def tid(conn):
    t = f"TEST-ROS-{uuid.uuid4().hex[:8]}"
    service.create_thesis(conn, t, [], "lease", "authority", "founder")
    yield t
    conn.rollback()
    service.delete_thesis(conn, t, "system")


def _crash_state(conn, job_id: int, worker_id: str, age_s: int) -> None:
    """Fixture: the row a worker leaves behind after `dequeue` when it dies `age_s` seconds later (state from the state machine)."""
    with conn.cursor() as cur:
        cur.execute("SELECT state FROM ros_jobs WHERE job_id = %s", (job_id,)); state = cur.fetchone()[0]
        cur.execute("UPDATE ros_jobs SET state = %s, locked_by = %s, locked_at = now() - make_interval(secs => %s), attempt = attempt + 1 WHERE job_id = %s",
                    (transition("job", state, "dequeue", "worker"), worker_id, float(age_s), job_id))
    conn.commit()


def _job(conn, job_id: int) -> dict:
    return next(j for j in queue.list_jobs(conn, 1000) if j["job_id"] == job_id)


def _lost_audits(conn, job_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM ros_audit WHERE action = 'job.transition' AND subject = %s AND detail->>'reason' = %s", (str(job_id), queue.WORKER_LOST))
        return cur.fetchone()[0]


def test_stale_lease_is_swept_to_worker_lost_once_and_nothing_else_moves(conn, tid):
    mk = lambda d, kind="tests": queue.enqueue(conn, kind, thesis_id=tid, discriminator=d)["job_id"]
    stale, fresh, done, claude = mk("stale"), mk("fresh"), mk("done"), mk("claude", "thesis_advance")
    _crash_state(conn, stale, "w-dead", 3600)
    run_id = f"RUN-{stale}-lease"; runs.create_run(conn, run_id, job_id=stale, kind="tests", thesis_id=tid, work_order_id=None)
    _crash_state(conn, fresh, "w-live", 0)
    _crash_state(conn, done, "w-old", 3600); queue.complete(conn, done, {"ok": True})
    queue.governance_pass(conn, claude); _crash_state(conn, claude, "host-claude-1", 3600)
    mine = [stale, fresh, done, claude]

    swept = queue.sweep_lost(conn, queue.DETERMINISTIC_KINDS, 900, only_job_ids=mine)

    assert [r["job_id"] for r in swept] == [stale]
    s = _job(conn, stale)
    assert (s["state"], s["error"], s["locked_by"]) == ("failed", queue.WORKER_LOST, None)
    assert _lost_audits(conn, stale) == 1
    run = runs.get_run(conn, run_id)
    assert (run["state"], run["stop_reason"]) == ("failed", queue.WORKER_LOST) and run["finished"] is not None
    assert [e["payload"] for e in runs.events_after(conn, run_id) if e["kind"] == "error"] == [{"reason": queue.WORKER_LOST}]
    # a fresh lock, a terminal job and a Claude-kind job are untouched
    assert (_job(conn, fresh)["state"], _job(conn, fresh)["locked_by"]) == ("running", "w-live")
    assert _job(conn, done)["state"] == "done"
    assert _job(conn, claude)["state"] == "running"
    assert [_lost_audits(conn, j) for j in (fresh, done, claude)] == [0, 0, 0]

    # idempotent: a second sweep changes nothing and writes no audit row
    assert queue.sweep_lost(conn, queue.DETERMINISTIC_KINDS, 900, only_job_ids=mine) == []
    assert _lost_audits(conn, stale) == 1 and _job(conn, stale)["state"] == "failed"

    # the swept worker has lost its lease; the live one keeps it
    assert queue.renew_lease(conn, stale, "w-dead") is False
    assert queue.renew_lease(conn, fresh, "w-live") is True and queue.renew_lease(conn, fresh, "w-other") is False

    # nothing was requeued; recovery is the explicit founder retry (existing path)
    assert queue.retry(conn, stale, actor="founder")["state"] == "queued"


def test_a_renewed_lease_is_not_swept(conn, tid):
    job = queue.enqueue(conn, "tests", thesis_id=tid, discriminator="renew")["job_id"]
    _crash_state(conn, job, "w-live", 3600)
    assert queue.renew_lease(conn, job, "w-live") is True
    assert queue.sweep_lost(conn, queue.DETERMINISTIC_KINDS, 900, only_job_ids=[job]) == []
    assert _job(conn, job)["state"] == "running"
