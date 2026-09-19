"""Claude host executor (spec §5): one governed agent job -> one run -> events.

    dequeue -> pre-run gate -> run row -> worktree -> packet -> ClaudeCodeMaxProvider.invoke (documented argv, injected runner) -> allowlist -> commit
            -> apply proposed_event as actor `agent` -> optional prior_art sub-job -> complete

Never: registry edits, API keys, undocumented flags, fallback models, automatic retry after USAGE_LIMIT_REACHED. The process runner is injected
(`runner_factory(cwd) -> callable`), so the test suite drives everything with a fake `claude` and the real CLI is only reached by `host_daemon`.
"""
from __future__ import annotations

import json
import os
import platform
import time
from hashlib import sha256
from pathlib import Path
from typing import Callable

from logos_research.measurement.claude_code import ActivationToken, Limits, ProviderPolicyError, contamination

from .agent_provider import AMENDMENT, AgentProvider

from . import governor, packet as pk, queue, radar, runs, service, telemetry, worktree
from .state_machines import AGENT_CEILING, THESIS_STATES, IllegalTransition

DEFAULT_LIMITS = {"max_turns": 25, "max_output_bytes": 400_000, "timeout_s": 1800.0}


class ExecutorConfig:
    def __init__(self, repo: Path, worktrees_root: Path, runner_factory: Callable[[Path], Callable], *, regs_loader: Callable[[], dict], cli_version: str | None = None, limits: dict | None = None, keep_worktree: bool = True, telemetry_stack: dict | None = None):
        self.repo, self.worktrees_root, self.runner_factory, self.regs_loader, self.cli_version = Path(repo), Path(worktrees_root), runner_factory, regs_loader, cli_version
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}; self.keep_worktree = keep_worktree
        self.telemetry_stack = telemetry_stack if telemetry_stack is not None else telemetry.null_stack()


def _job_fail(conn, job_id: int, reason: str, run_id: str | None, detail: dict | None = None) -> dict:
    if run_id:
        runs.emit(conn, run_id, "error", {"reason": reason, **(detail or {})}); runs.finish_run(conn, run_id, "failed", reason, detail)
    return queue.fail(conn, job_id, reason, actor="system")


def run_job(conn, job: dict, cfg: ExecutorConfig) -> dict:
    """Execute one already-dequeued Claude job (state = running). Returns the final job row."""
    job_id = job["job_id"]; thesis_id = job["thesis_id"]; kind = job["kind"]
    run_id = f"RUN-{job_id}-{int(time.time())}"
    # -- gate (again, at dispatch) ------------------------------------------------------------------------------
    detail = service.thesis_detail(conn, thesis_id) if thesis_id else None
    gate = governor.pre_run_gate(conn, {**job, "state": "queued"}, detail["thesis"]["state"] if detail else None, AGENT_CEILING, THESIS_STATES)
    run = runs.create_run(conn, run_id, job_id=job_id, kind=kind, thesis_id=thesis_id, work_order_id=job.get("work_order_id"))
    tel = telemetry.RunTelemetry(conn, cfg.telemetry_stack, run_id, thesis_id, job_id, kind)
    tel.start({"model_pin": governor.caps(conn).model_pin, "cli_version": cfg.cli_version or ""})
    runs.emit(conn, run_id, "gate", {"checks": gate["checks"], "passed": gate["passed"], "caps": gate["caps"]})
    if not gate["passed"]:
        tel.finish("failed", None)
        return _job_fail(conn, job_id, "PRE_RUN_GATE_FAILED", run_id, {"failed": [k for k, v in gate["checks"].items() if not v]})
    radar_item = radar.get_radar(conn, int(job.get("payload", {}).get("radar_id"))) if kind == "radar_process" and job.get("payload", {}).get("radar_id") else None
    if kind not in ("thesis_advance", "prior_art", "radar_process") or (kind != "radar_process" and detail is None) or (kind == "radar_process" and radar_item is None):
        tel.finish("failed", None)
        return _job_fail(conn, job_id, f"UNSUPPORTED_JOB_KIND:{kind}", run_id)
    scope_id = thesis_id or f"radar-{radar_item['radar_id']}"
    caps = governor.caps(conn)
    # -- worktree -------------------------------------------------------------------------------------------------
    runs.emit(conn, run_id, "phase", {"phase": "worktree"}); tel.span("phase.worktree", {"phase": "worktree"})
    try:
        wt = worktree.create(cfg.repo, cfg.worktrees_root, scope_id, run_id)
    except RuntimeError as e:
        tel.finish("failed", None)
        return _job_fail(conn, job_id, "WORKTREE_FAILED", run_id, {"error": str(e)[:300]})
    branch = worktree.branch_name(scope_id, run_id)
    with conn.cursor() as cur:
        cur.execute("UPDATE ros_runs SET branch = %s, worktree = %s WHERE run_id = %s", (branch, str(wt), run_id))
    conn.commit()
    runs.emit(conn, run_id, "worktree", {"path": str(wt), "branch": branch, "base": worktree.head(cfg.repo)})
    # -- packet ---------------------------------------------------------------------------------------------------
    runs.emit(conn, run_id, "phase", {"phase": "packet"}); tel.span("phase.packet", {"phase": "packet"})
    regs = cfg.regs_loader(); notes = service.unconsumed_notes(conn, thesis_id) if thesis_id else []
    if kind == "radar_process":
        packet = pk.build_radar_packet(radar_item, regs)
    else:
        prior_n = sum(1 for c in regs["prior_art"]["citations"] if c["research_track"] == detail["thesis"]["track"])
        packet = pk.build_thesis_packet(detail, regs, notes, prior_n, kind=kind, brief_task=job.get("payload", {}).get("brief_task"))
    prompt_hash = sha256(packet["prompt"].encode()).hexdigest()
    runs.emit(conn, run_id, "packet", {"prompt_sha256": prompt_hash, "prompt_bytes": len(packet["prompt"]), "notes_consumed": [n["note_id"] for n in notes], "allowed_prefixes": packet["allowed_prefixes"], "allowed_events": packet["allowed_events"], "state": packet["state"]})
    tel.params({"thesis_state": packet["state"], "allowed_events": ",".join(packet["allowed_events"]), "allowed_tools": ",".join(packet["allowed_tools"]), "prompt_bytes": len(packet["prompt"]), "branch": branch, "contract": "ros-agent-result/1"})
    tel.artifact("prompt.txt", packet["prompt"].encode("utf-8"), "prompt")
    if notes:
        with conn.cursor() as cur:
            cur.execute("UPDATE ros_notes SET consumed_by_job = %s WHERE note_id = ANY(%s)", (job_id, [n["note_id"] for n in notes]))
        conn.commit()
    # -- invoke ---------------------------------------------------------------------------------------------------
    if queue.stop_requested(conn, job_id):
        runs.emit(conn, run_id, "stop", {"before": "invoke"}); runs.finish_run(conn, run_id, "stopped", "founder_stop"); _cleanup(cfg, wt, branch, discard=True); tel.finish("stopped", None)
        return queue.stop(conn, job_id, actor="founder")
    token = ActivationToken(run_id=run_id, model_pin=caps.model_pin, max_invocations=caps.max_claude_invocations_per_job, max_turns=cfg.limits["max_turns"], issued_by="logos_dashboard.control.governor",
                            cli_version=cfg.cli_version, contract_version="ros-agent-result/1", dataset_hash=None, prompt_bundle_hash=prompt_hash)
    provider = AgentProvider(runner=_as_stream_runner(cfg.runner_factory(wt)), expected_cli_version=cfg.cli_version)
    limits = Limits(max_turns=cfg.limits["max_turns"], max_output_bytes=cfg.limits["max_output_bytes"], timeout_s=cfg.limits["timeout_s"], disallowed_tools=packet["disallowed_tools"], allowed_tools=packet["allowed_tools"])
    runs.emit(conn, run_id, "phase", {"phase": "claude"}); tel.span("phase.claude", {"phase": "claude", "model_requested": caps.model_pin})
    runs.emit(conn, run_id, "claude.invoke", {"requested_model": caps.model_pin, "max_turns": limits.max_turns, "allowed_tools": packet["allowed_tools"], "disallowed_tools": packet["disallowed_tools"], "output_format": "stream-json", "verbose": AMENDMENT, "skills": packet.get("skills", []), "contamination_presence": contamination(), "invocation": 1})
    def _on_event(ev: dict) -> None:
        runs.emit(conn, run_id, ev["kind"], ev)
    try:
        res = provider.invoke(packet["prompt"], caps.model_pin, {"run_id": run_id, "system_prompt": packet["system"], "kind": kind}, limits, token=token, env=dict(os.environ), on_event=_on_event, stop_check=lambda: queue.stop_requested(conn, job_id))
    except ProviderPolicyError as e:
        _cleanup(cfg, wt, branch, discard=True); tel.finish("failed", None)
        return _job_fail(conn, job_id, "POLICY_BLOCK", run_id, {"error": str(e)})
    evidence = res.resolution.evidence_class if res.resolution else None
    tel.generation(model_requested=res.requested_model, model_resolved=res.reported_model, status=res.status, evidence_class=evidence, prompt=packet["prompt"], output=res.content, usage=res.usage_metadata, turns=res.turn_count, latency_s=res.latency_s)
    if provider.raw_lines:
        tel.artifact("claude_stream.jsonl", provider.stream_text().encode("utf-8"), "claude_stream")
        tel.metrics({f"tool_{k}": v for k, v in provider.tool_histogram().items()})
    if res.stderr_classification == "stopped":
        runs.emit(conn, run_id, "stop", {"during": "invoke"}); runs.finish_run(conn, run_id, "stopped", "founder_stop"); _cleanup(cfg, wt, branch, discard=True); tel.finish("stopped", None)
        return queue.stop(conn, job_id, actor="founder")
    if res.content is not None:
        tel.artifact("claude_result.json", json.dumps({"status": res.status, "requested_model": res.requested_model, "resolved_model": res.reported_model, "evidence_class": evidence, "turns": res.turn_count, "usage": res.usage_metadata, "content": res.content}, sort_keys=True).encode("utf-8"), "claude_result")
    runs.emit(conn, run_id, "claude.result", {"status": res.status, "requested_model": res.requested_model, "resolved_model": res.reported_model, "evidence_class": evidence, "reason_code": res.stderr_classification, "turns": res.turn_count,
                                              "latency_s": round(res.latency_s, 2), "stdout_sha256": res.artifact_refs[0] if res.artifact_refs else None, "usage": res.usage_metadata, "session_id": res.session_id, "cli_version": res.claude_code_version})
    if res.status == "USAGE_LIMIT_REACHED":
        governor.set_quota_state(conn, "USAGE_LIMIT_REACHED", "system", f"job {job_id} run {run_id}")
        runs.emit(conn, run_id, "quota", {"state": "USAGE_LIMIT_REACHED", "policy": "STOP; wait for the subscription reset; no PAYG/provider/model fallback"}); runs.finish_run(conn, run_id, "waiting_quota", "USAGE_LIMIT_REACHED")
        _cleanup(cfg, wt, branch, discard=True); tel.finish("waiting_quota", None)
        return _set_state(conn, job_id, "waiting_quota", "USAGE_LIMIT_REACHED")
    if res.status != "OK":
        _cleanup(cfg, wt, branch, discard=True); tel.finish("failed", None)
        return _job_fail(conn, job_id, res.status, run_id, {"reason_code": res.stderr_classification})
    # -- outputs --------------------------------------------------------------------------------------------------
    runs.emit(conn, run_id, "phase", {"phase": "verify"}); tel.span("phase.verify", {"phase": "verify"})
    result = pk.parse_agent_result(res.content)
    changed = worktree.changed_files(wt)
    violations = worktree.check_allowlist(changed, packet["allowed_prefixes"])
    if violations:
        runs.emit(conn, run_id, "error", {"reason": "INTEGRITY_VIOLATION", "files": violations}); runs.finish_run(conn, run_id, "failed", "INTEGRITY_VIOLATION", {"files": violations})
        _cleanup(cfg, wt, branch, discard=True); tel.finish("failed", {"violations": violations})
        return queue.fail(conn, job_id, "INTEGRITY_VIOLATION", actor="system")
    if result is None:
        _cleanup(cfg, wt, branch, discard=True); tel.finish("failed", None)
        return _job_fail(conn, job_id, "INVALID_OUTPUT", run_id, {"reason": "no ros-agent-result/1 block"})
    for f in changed:
        p = wt / f
        runs.emit(conn, run_id, "artifact", {"path": f, "sha256": sha256(p.read_bytes()).hexdigest() if p.exists() else None, "bytes": p.stat().st_size if p.exists() else 0})
    sha = worktree.commit(wt, f"ros({scope_id}): {kind} {run_id}\n\n{result.summary[:500]}")
    runs.emit(conn, run_id, "commit", {"sha": sha, "branch": branch, "files": changed})
    # -- lifecycle event (agent; gates enforced by the state machine) ----------------------------------------------
    applied = None
    if kind == "radar_process":
        prop_path = wt / pk.RADAR_DIR / str(radar_item["radar_id"]) / "PROPOSAL.json"
        try:
            proposal = json.loads(prop_path.read_text(encoding="utf-8")) if prop_path.exists() else None
        except ValueError:
            proposal = None
        with conn.cursor() as cur:
            cur.execute("UPDATE ros_radar_items SET proposal = %s, updated_at = now() WHERE radar_id = %s", (json.dumps({"schema": "AI_PROPOSAL", "run_id": run_id, "branch": branch, "commit": sha, "prompt_sha256": prompt_hash, "input_sha256": sha256(json.dumps(radar_item["payload"], sort_keys=True, default=str).encode()).hexdigest(),
                                                                                                                  "model_requested": res.requested_model, "model_resolved": res.reported_model, "evidence_class": evidence, "trace_ids": tel.trace_ids, "proposal": proposal, "valid": proposal is not None}), radar_item["radar_id"]))
        conn.commit(); runs.emit(conn, run_id, "artifact", {"radar_id": radar_item["radar_id"], "ai_proposal": proposal is not None})
    if result.proposed_event:
        if result.proposed_event not in packet["allowed_events"]:
            runs.emit(conn, run_id, "thesis.event", {"proposed": result.proposed_event, "applied": False, "reason": "not in allowed_events"})
        else:
            try:
                row = service.advance(conn, thesis_id, result.proposed_event, "agent", reason=f"agent job {job_id}: {result.summary[:200]}", source_record=f"{branch}@{sha}", git_commit=sha)
                applied = row["state"]; runs.emit(conn, run_id, "thesis.event", {"proposed": result.proposed_event, "applied": True, "to": applied})
            except IllegalTransition as e:
                conn.rollback(); runs.emit(conn, run_id, "thesis.event", {"proposed": result.proposed_event, "applied": False, "reason": e.reason})
    wo_draft = None
    if kind == "thesis_advance":
        wo_path = wt / pk.thesis_dir(thesis_id) / "WORK-ORDER-DRAFT.json"
        if wo_path.exists():
            try:
                spec = json.loads(wo_path.read_text(encoding="utf-8")); missing = service.validate_spec(spec)
                if missing:
                    runs.emit(conn, run_id, "work_order.draft", {"created": False, "missing": missing})
                else:
                    wo_id = f"WO-{thesis_id}-D{job_id}"
                    row = service.create_work_order(conn, wo_id, thesis_id, {**spec, "origin": {"agent_job": job_id, "run_id": run_id, "branch": branch}}, "agent"); wo_draft = row["work_order_id"]
                    runs.emit(conn, run_id, "work_order.draft", {"created": True, "work_order_id": wo_draft, "state": row["state"]})
            except (ValueError, Exception) as e:
                conn.rollback(); runs.emit(conn, run_id, "work_order.draft", {"created": False, "error": f"{type(e).__name__}: {str(e)[:160]}"})
    sub = None
    if result.needs_prior_art and kind == "thesis_advance":
        sub = queue.enqueue(conn, "prior_art", thesis_id=thesis_id, work_order_id=job.get("work_order_id"), payload={"requested_by_job": job_id, "brief_task": {"task_id": f"PRIOR-ART-{job_id}"}}, actor="agent")
        runs.emit(conn, run_id, "phase", {"phase": "prior_art_requested", "job_id": sub["job_id"], "state": sub["state"]})
    summary = {"status": "OK", "files": changed, "commit": sha, "branch": branch, "proposed_event": result.proposed_event, "applied_state": applied, "needs_prior_art": result.needs_prior_art, "summary": result.summary, "uncertainties": list(result.uncertainties), "prior_art_job": sub["job_id"] if sub else None, "work_order_draft": wo_draft}
    tel.metrics({"files_changed": len(changed), "event_applied": 1 if applied else 0, "needs_prior_art": 1 if result.needs_prior_art else 0})
    links = tel.finish("done", summary); summary["telemetry"] = links
    if links["degraded"]:
        runs.emit(conn, run_id, "note", {"telemetry_degraded": links["degraded"]})
    runs.emit(conn, run_id, "done", summary); runs.finish_run(conn, run_id, "done", None, summary)
    if not cfg.keep_worktree:
        _cleanup(cfg, wt, branch, discard=False)
    return queue.complete(conn, job_id, summary, actor="system")


def _set_state(conn, job_id: int, state: str, error: str) -> dict:
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("UPDATE ros_jobs SET state = %s, error = %s, locked_by = NULL, updated_at = now() WHERE job_id = %s RETURNING *", (state, error, job_id)); row = cur.fetchone()
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES ('system', 'job.transition', %s, %s)", (str(job_id), json.dumps({"to": state, "reason": error})))
    conn.commit()
    return row


def _cleanup(cfg: ExecutorConfig, wt: Path, branch: str, *, discard: bool) -> None:
    try:
        worktree.remove(cfg.repo, wt, delete_branch=branch if discard else None)
    except Exception:
        pass


def run_once(conn, cfg: ExecutorConfig, worker_id: str, kinds: tuple[str, ...] = ("thesis_advance", "prior_art", "radar_process")) -> dict | None:
    """One scheduler tick: governor check, dequeue one job, execute. Returns the final job row or None when idle/blocked."""
    ok, reason = governor.can_dispatch(conn, "thesis_advance")
    if not ok:
        return None
    job = queue.dequeue(conn, worker_id, kinds)
    if job is None:
        return None
    governor.heartbeat(conn, worker_id, "host", platform.node(), list(kinds), job["job_id"])
    try:
        return run_job(conn, job, cfg)
    except Exception as e:  # never leave a job stuck in running
        conn.rollback()
        return queue.fail(conn, job["job_id"], f"EXECUTOR_EXCEPTION:{type(e).__name__}:{str(e)[:200]}", actor="system")
    finally:
        governor.heartbeat(conn, worker_id, "host", platform.node(), list(kinds), None)


def _as_stream_runner(runner):
    """Accept both runner contracts: streaming `(argv, timeout, env, on_line, stop_check)` and the legacy `(argv, timeout, env)` (json-doc fakes in tests).
    Legacy stdout is replayed line-wise; a single JSON document becomes a synthetic `result` event."""
    import inspect
    try:
        n = len(inspect.signature(runner).parameters)
    except (TypeError, ValueError):
        n = 3
    if n >= 5:
        return runner

    def wrapped(argv, timeout, env, on_line, stop_check):
        code, out, err = runner(argv, timeout, env)
        if out:
            lines = [l for l in out.splitlines() if l.strip()]
            parsed = []
            for l in lines:
                try:
                    parsed.append(json.loads(l))
                except ValueError:
                    parsed = None; break
            if parsed and all(isinstance(p, dict) and "type" in p for p in parsed):
                for l in lines:
                    on_line(l)
            else:
                try:
                    doc = json.loads(out)
                    if isinstance(doc, dict):
                        on_line(json.dumps({"type": "result", **doc}))
                except ValueError:
                    pass
        return code, out, err
    return wrapped
