"""Deterministic worker (Docker `ros-worker` or host): `tests` (allowlisted pytest paths) and `snapshot` (registries snapshot). Other kinds fail closed until Phase 4/5.

    python -m logos_dashboard.control.worker --once | --loop

Lease: while a pytest subprocess runs, the worker renews the job's `locked_at` every lease/3 seconds (`ROS_JOB_LEASE_S`, default 900).
At startup and on every tick it sweeps deterministic jobs whose lease expired to `failed` / WORKER_LOST (`queue.sweep_lost`). A worker
whose lease was swept terminates its subprocess. Nothing is requeued; recovery is the explicit founder `retry`.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from .. import db, registries
from . import governor, queue, runs
from .state_machines import IllegalTransition

ROOT = Path(__file__).resolve().parents[3]
TEST_ALLOWLIST = ("tests/",)
NOT_IMPLEMENTED = {"dataset": "needs a governed experiment order (dataset builds are experiment-specific)", "dry_run": "needs a governed experiment order (dry runs are prereg-specific)", "rescore": "use POST /api/ros/runs/{id}/rescore (no worker job)", "playwright_qa": "run from apps/dashboard (pnpm e2e); results feed /system/qa"}


class LeaseLost(RuntimeError):
    """The job's lease was swept while this worker was still running it."""


def _run_leased(conn, job: dict, argv: list[str], timeout: float) -> subprocess.CompletedProcess:
    """`subprocess.run(argv, capture_output=True, text=True)` with lease renewal between waits. Timeout -> TimeoutExpired; lost lease -> LeaseLost."""
    every = max(1.0, queue.lease_seconds() / 3)
    proc = subprocess.Popen(argv, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    t0 = time.monotonic()
    while True:
        try:
            out, err = proc.communicate(timeout=every)
            return subprocess.CompletedProcess(argv, proc.returncode, out, err)
        except subprocess.TimeoutExpired:
            if time.monotonic() - t0 > timeout:
                proc.kill(); proc.communicate(); raise subprocess.TimeoutExpired(argv, timeout)
            if not queue.renew_lease(conn, job["job_id"], job["locked_by"]):
                proc.kill(); proc.communicate(); raise LeaseLost(job["job_id"])


def sweep(conn, lease_s: int | None = None) -> list[dict]:
    """Expired-lease deterministic jobs -> failed / WORKER_LOST. Claude kinds are left to the host executor."""
    return queue.sweep_lost(conn, queue.DETERMINISTIC_KINDS, queue.lease_seconds() if lease_s is None else lease_s, actor="system")


def handle(conn, job: dict) -> dict:
    run_id = f"RUN-{job['job_id']}-{int(time.time())}"
    runs.create_run(conn, run_id, job_id=job["job_id"], kind=job["kind"], thesis_id=job.get("thesis_id"), work_order_id=job.get("work_order_id"))
    if job["kind"] == "tests":
        path = str(job.get("payload", {}).get("path") or "tests/test_ros_control_plane.py").replace("\\", "/")
        if not path.startswith(TEST_ALLOWLIST) or ".." in path:
            runs.finish_run(conn, run_id, "failed", "PATH_NOT_ALLOWED"); return queue.fail(conn, job["job_id"], "PATH_NOT_ALLOWED")
        runs.emit(conn, run_id, "phase", {"phase": "pytest", "path": path})
        cp = _run_leased(conn, job, [sys.executable, "-m", "pytest", path, "-q", "-p", "no:warnings", "--tb=short"], 3600)
        tail = (cp.stdout or "")[-4000:]
        res = {"exit_code": cp.returncode, "tail": tail, "stdout_sha256": sha256((cp.stdout or "").encode()).hexdigest()}
        runs.emit(conn, run_id, "artifact", {"kind": "pytest", **res}); runs.finish_run(conn, run_id, "done" if cp.returncode == 0 else "failed", None if cp.returncode == 0 else "TESTS_FAILED", res)
        return queue.complete(conn, job["job_id"], res) if cp.returncode == 0 else queue.fail(conn, job["job_id"], "TESTS_FAILED")
    if job["kind"] == "benchmark":
        from .. import benchmarks as bm
        from . import benchlab
        suite = str(job.get("payload", {}).get("suite") or "")
        spec = bm.SUITES.get(suite)
        if spec is None:
            runs.finish_run(conn, run_id, "failed", "UNKNOWN_SUITE"); return queue.fail(conn, job["job_id"], "UNKNOWN_SUITE")
        runs.emit(conn, run_id, "phase", {"phase": "pytest", "suite": suite, "fixtures": spec["fixtures"]})
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            xml = Path(d) / "junit.xml"
            cp = _run_leased(conn, job, [sys.executable, "-m", "pytest", *spec["fixtures"], "-q", "-p", "no:warnings", "--tb=line", f"--junitxml={xml}"], 3600)
            parsed = bm.parse_junit(xml.read_text(encoding="utf-8")) if xml.exists() else {"tests": 0, "passed": 0, "failed": 0, "skipped": 0, "cases": []}
        ctx = {"repo_sha": os.environ.get("LOGOS_REPO_SHA", "host"), "fixtures": spec["fixtures"], "definition_sha256": bm.definitions()["sha256"], "python": sys.version.split()[0], "mode": "DETERMINISTIC", "tool_boundary": "pytest", "model_pin": None, "dataset_hash": None, "prompt_bundle_hash": None}
        row = benchlab.record_metric(conn, suite, "DETERMINISTIC", "fixture_regression", parsed["passed"], parsed["tests"], ctx, run_id, job["job_id"])
        res = {"suite": suite, "tests": parsed["tests"], "passed": parsed["passed"], "failed": parsed["failed"], "skipped": parsed["skipped"], "exit_code": cp.returncode, "result_id": row["result_id"], "value": row["value"], "ci": [row["ci_low"], row["ci_high"]], "failed_cases": [c["name"] for c in parsed["cases"] if not c["ok"]][:50]}
        runs.emit(conn, run_id, "artifact", {"kind": "junit", **{k: v for k, v in res.items() if k != "failed_cases"}}); runs.finish_run(conn, run_id, "done", None, res)
        return queue.complete(conn, job["job_id"], res)
    if job["kind"] == "snapshot":
        regs = registries.load_all(); blob = json.dumps(regs, sort_keys=True, default=str).encode(); h = sha256(blob).hexdigest()
        out = ROOT / "docs" / "research" / "dashboard" / "snapshots"; out.mkdir(exist_ok=True)
        p = out / f"registries-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{h[:12]}.json"; p.write_bytes(blob)
        res = {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": h, "bytes": len(blob)}
        runs.emit(conn, run_id, "artifact", res); runs.finish_run(conn, run_id, "done", None, res); return queue.complete(conn, job["job_id"], res)
    reason = f"NOT_IMPLEMENTED:{NOT_IMPLEMENTED.get(job['kind'], 'unknown')}"
    runs.finish_run(conn, run_id, "failed", reason); return queue.fail(conn, job["job_id"], reason)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--once", action="store_true"); ap.add_argument("--loop", action="store_true"); ap.add_argument("--interval", type=float, default=3.0); ap.add_argument("--worker-id", default=os.environ.get("ROS_WORKER_ID", f"det-{platform.node()}"))
    a = ap.parse_args(argv)
    conn = db.connect()
    if conn is None:
        print("lab Postgres unreachable"); return 2
    db.ensure_schema(conn)
    while True:
        for lost in sweep(conn):
            print(f"job {lost['job_id']} -> failed {queue.WORKER_LOST}")
        governor.heartbeat(conn, a.worker_id, "deterministic", platform.node(), list(queue.DETERMINISTIC_KINDS), None)
        ok, _ = governor.can_dispatch(conn, "tests")
        job = queue.dequeue(conn, a.worker_id, queue.DETERMINISTIC_KINDS) if ok else None
        if job:
            governor.heartbeat(conn, a.worker_id, "deterministic", platform.node(), list(queue.DETERMINISTIC_KINDS), job["job_id"])
            try:
                r = handle(conn, job); print(f"job {job['job_id']} -> {r['state']}")
            except Exception as e:
                conn.rollback()
                try:
                    queue.fail(conn, job["job_id"], f"WORKER_EXCEPTION:{type(e).__name__}")
                    queue.close_open_runs(conn, job["job_id"], f"WORKER_EXCEPTION:{type(e).__name__}")
                except IllegalTransition:      # already terminal: the lease was swept (LeaseLost) or the job was stopped
                    conn.rollback()
        if a.once or not a.loop:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())
