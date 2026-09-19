"""Host executor loop — the ONLY place the real `claude` CLI is reached by the dashboard.

    python -m logos_dashboard.control.host_daemon --once | --loop [--interval 3]

Runner = the documented, credential-free process runner (same contract as cognitive_provenance_r1.claude_runner): argv from `build_argv`, re-checked,
no `ANTHROPIC_API_KEY`, no undocumented flag, cwd = the isolated worktree so that project CLAUDE.md/skills of the worktree (not the main tree) are seen.
"""
from __future__ import annotations

import argparse
import shutil
import time
import platform
import subprocess
import time
from pathlib import Path

from logos_research.measurement.claude_code import ProviderPolicyError

from .agent_provider import check_agent_argv

from .. import db, registries
from . import autopilot, executor, governor, procs, telemetry

ROOT = Path(__file__).resolve().parents[3]
FORBIDDEN_ENV = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")


def real_runner_factory(cwd: Path):
    exe = shutil.which("claude")
    if not exe:
        raise ProviderPolicyError("claude executable not on PATH")

    def _run(argv: list[str], timeout: float, env: dict, on_line, stop_check) -> tuple:
        """Streaming runner: one process, stdout line by line to `on_line`; `stop_check()` between lines terminates the process (graceful Stop)."""
        check_agent_argv(argv)
        if argv[0] != "claude" or any(k in env for k in FORBIDDEN_ENV):
            raise ProviderPolicyError("argv/env contract violated")
        proc = subprocess.Popen([exe, *argv[1:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", env=env, shell=False, cwd=str(cwd), bufsize=1)
        out_lines: list[str] = []; t0 = time.time(); stopped = False; timed_out = False
        try:
            for line in proc.stdout:
                out_lines.append(line); on_line(line)
                if stop_check():
                    stopped = True; proc.terminate(); break
                if time.time() - t0 > timeout:
                    timed_out = True; proc.kill(); break
        finally:
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()
        err = proc.stderr.read() if proc.stderr else ""
        if timed_out:
            return None, "".join(out_lines), "timeout"
        if stopped:
            return "STOPPED", "".join(out_lines), err
        return proc.returncode, "".join(out_lines), err
    return _run


def config(cli_version: str | None) -> executor.ExecutorConfig:
    return executor.ExecutorConfig(ROOT, ROOT.parent / "logos-1-worktrees", real_runner_factory, regs_loader=registries.load_all, cli_version=cli_version, telemetry_stack=telemetry.stack_from_env())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--once", action="store_true"); ap.add_argument("--loop", action="store_true"); ap.add_argument("--interval", type=float, default=3.0); ap.add_argument("--worker-id", default="host-claude-1")
    a = ap.parse_args(argv)
    conn = db.connect()
    if conn is None:
        print("lab Postgres unreachable"); return 2
    db.ensure_schema(conn)
    ev = governor.preflight_evidence(); cfg = config(ev.get("cli_version"))
    print(f"host executor {a.worker_id}: cli={ev.get('cli_version')} auth_class={ev.get('auth_class')} pin={governor.caps(conn).model_pin}")
    while True:
        governor.heartbeat(conn, a.worker_id, "host", platform.node(), ["thesis_advance", "prior_art", "radar_process"], None, {"cli_version": ev.get("cli_version"), "autopilot": autopilot.master(conn)})
        if procs.host_should_stop(conn):
            print("stop requested — exiting"); procs.host_exited(conn); return 0
        try:
            for act in autopilot.tick(conn):
                print(f"autopilot: {act}")
        except Exception as e:
            conn.rollback(); print(f"autopilot tick error: {type(e).__name__}: {e}")
        job = executor.run_once(conn, cfg, a.worker_id)
        if job:
            print(f"job {job['job_id']} -> {job['state']} {job.get('error') or ''}")
        if a.once or not a.loop:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())
