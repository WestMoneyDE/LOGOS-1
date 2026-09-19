"""Worker processes controlled from the UI: host executor (Claude) as a detached subprocess of the API host; Docker worker via `docker compose` (never `down -v`).
Stop is graceful: a settings flag the daemon polls; after the grace period the process is terminated."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from . import governor

ROOT = Path(__file__).resolve().parents[3]
INFRA = ROOT / "infra"
HOST_ID = "host-claude-1"


def host_status(conn) -> dict:
    hb = next((w for w in governor.workers(conn) if w["worker_id"] == HOST_ID), None)
    st = governor.get_setting(conn, "host_daemon") or {}
    pid = st.get("pid"); alive = bool(hb and hb["alive"])
    return {"worker_id": HOST_ID, "alive": alive, "pid": pid, "last_seen": hb["last_seen"] if hb else None, "current_job": hb["current_job"] if hb else None, "stop_requested": bool(st.get("stop_requested")), "started_at": st.get("started_at"), "info": (hb or {}).get("info", {})}


def host_start(conn, actor: str) -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("only the founder starts the host executor")
    if host_status(conn)["alive"]:
        return {**host_status(conn), "note": "already running"}
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")}
    env["PYTHONPATH"] = str(ROOT / "src")
    log = ROOT / "apps" / "dashboard" / "e2e" / "results"; log.mkdir(parents=True, exist_ok=True)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0) if os.name == "nt" else 0
    with open(log / "host-daemon.log", "ab") as fh:
        p = subprocess.Popen([sys.executable, "-m", "logos_dashboard.control.host_daemon", "--loop", "--worker-id", HOST_ID], cwd=str(ROOT), env=env, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=flags, shell=False)
    governor.set_setting(conn, "host_daemon", {"pid": p.pid, "stop_requested": False, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "started_by": actor}, actor)
    return {**host_status(conn), "pid": p.pid, "note": "started"}


def host_stop(conn, actor: str, grace_s: float = 5.0) -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("only the founder stops the host executor")
    st = governor.get_setting(conn, "host_daemon") or {}
    governor.set_setting(conn, "host_daemon", {**st, "stop_requested": True}, actor)
    return {**host_status(conn), "note": "stop requested (graceful: the daemon finishes the current job and exits; a running Claude process is terminated by Stop on the job)"}


def host_should_stop(conn) -> bool:
    return bool((governor.get_setting(conn, "host_daemon") or {}).get("stop_requested"))


def host_exited(conn) -> None:
    st = governor.get_setting(conn, "host_daemon") or {}
    governor.set_setting(conn, "host_daemon", {**st, "pid": None, "stop_requested": False, "exited_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, "system")


def _compose(*args: str, timeout: float = 600.0) -> tuple[int, str]:
    cp = subprocess.run(["docker", "compose", "--profile", "ros", *args], cwd=str(INFRA), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, shell=False)
    return cp.returncode, (cp.stdout + cp.stderr)[-2000:]


_DOCKER_CACHE: dict = {"at": 0.0, "val": None}


def _compose_ps() -> tuple[bool, str]:
    """`docker compose ps` is slow (~1 s); cached 10 s. A missing docker binary is reported, never raised."""
    if time.time() - _DOCKER_CACHE["at"] < 10 and _DOCKER_CACHE["val"] is not None:
        return _DOCKER_CACHE["val"]
    try:
        code, out = _compose("ps", "--format", "json", "ros-worker", timeout=60)
        val = (code == 0 and '"running"' in out.lower(), out)
    except Exception as e:
        val = (False, f"docker unavailable: {type(e).__name__}")
    _DOCKER_CACHE.update(at=time.time(), val=val)
    return val


def docker_status(conn) -> dict:
    hb = next((w for w in governor.workers(conn) if w["worker_id"] == "ros-worker-docker-1"), None)
    running, out = _compose_ps()
    return {"worker_id": "ros-worker-docker-1", "container_running": running, "alive": bool(hb and hb["alive"]), "last_seen": hb["last_seen"] if hb else None, "current_job": hb["current_job"] if hb else None, "compose": out[-300:]}


def docker_start(conn, actor: str, build: bool = False) -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("only the founder starts the Docker worker")
    args = ["up", "-d"] + (["--build"] if build else []) + ["ros-worker"]
    env_sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), capture_output=True, text=True).stdout.strip()
    os.environ["LOGOS_REPO_SHA"] = env_sha
    code, out = _compose(*args); _DOCKER_CACHE["at"] = 0.0
    return {**docker_status(conn), "exit_code": code, "note": out[-300:]}


def docker_stop(conn, actor: str) -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("only the founder stops the Docker worker")
    code, out = _compose("stop", "ros-worker", timeout=120); _DOCKER_CACHE["at"] = 0.0          # stop, never `down -v`
    return {**docker_status(conn), "exit_code": code, "note": out[-300:]}
