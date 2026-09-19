"""Deterministic worker (Docker `ros-worker` or host): `tests` (allowlisted pytest paths) and `snapshot` (registries snapshot). Other kinds fail closed until Phase 4/5.

    python -m logos_dashboard.control.worker --once | --loop
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

ROOT = Path(__file__).resolve().parents[3]
TEST_ALLOWLIST = ("tests/",)
NOT_IMPLEMENTED = {"dataset": "Phase 4", "dry_run": "Phase 4", "rescore": "Phase 4", "playwright_qa": "Phase 5", }


def handle(conn, job: dict) -> dict:
    run_id = f"RUN-{job['job_id']}-{int(time.time())}"
    runs.create_run(conn, run_id, job_id=job["job_id"], kind=job["kind"], thesis_id=job.get("thesis_id"), work_order_id=job.get("work_order_id"))
    if job["kind"] == "tests":
        path = str(job.get("payload", {}).get("path") or "tests/test_ros_control_plane.py").replace("\\", "/")
        if not path.startswith(TEST_ALLOWLIST) or ".." in path:
            runs.finish_run(conn, run_id, "failed", "PATH_NOT_ALLOWED"); return queue.fail(conn, job["job_id"], "PATH_NOT_ALLOWED")
        runs.emit(conn, run_id, "phase", {"phase": "pytest", "path": path})
        cp = subprocess.run([sys.executable, "-m", "pytest", path, "-q", "-p", "no:warnings", "--tb=short"], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
        tail = (cp.stdout or "")[-4000:]
        res = {"exit_code": cp.returncode, "tail": tail, "stdout_sha256": sha256((cp.stdout or "").encode()).hexdigest()}
        runs.emit(conn, run_id, "artifact", {"kind": "pytest", **res}); runs.finish_run(conn, run_id, "done" if cp.returncode == 0 else "failed", None if cp.returncode == 0 else "TESTS_FAILED", res)
        return queue.complete(conn, job["job_id"], res) if cp.returncode == 0 else queue.fail(conn, job["job_id"], "TESTS_FAILED")
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
        governor.heartbeat(conn, a.worker_id, "deterministic", platform.node(), list(queue.DETERMINISTIC_KINDS), None)
        ok, _ = governor.can_dispatch(conn, "tests")
        job = queue.dequeue(conn, a.worker_id, queue.DETERMINISTIC_KINDS) if ok else None
        if job:
            governor.heartbeat(conn, a.worker_id, "deterministic", platform.node(), list(queue.DETERMINISTIC_KINDS), job["job_id"])
            try:
                r = handle(conn, job); print(f"job {job['job_id']} -> {r['state']}")
            except Exception as e:
                conn.rollback(); queue.fail(conn, job["job_id"], f"WORKER_EXCEPTION:{type(e).__name__}")
        if a.once or not a.loop:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())
