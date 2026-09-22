"""Autopilot (founder decision 2026-09-19): one switch per thesis + a master switch; the daemon tick enqueues and starts the next agent stage automatically
until the agent ceiling (PREREG_DRAFT). It never passes a founder gate: reaching the ceiling switches the thesis off and leaves an attention item.

Governance is unchanged: the pre-run gate is evaluated at every automatic start (auth evidence, quota, contamination, cap 1); a failed gate pauses the
thesis' autopilot with the reason instead of retrying blindly. Enabling autopilot for a thesis is the founder's Start for all its agent stages up to the ceiling
(audit `autopilot.enable` with the gate snapshot).
"""
from __future__ import annotations

import json

from psycopg.rows import dict_row

from . import governor, queue, service
from .state_machines import AGENT_CEILING, THESIS_STATES

OPEN_JOB_STATES = ("queued", "running", "paused", "waiting_quota", "waiting_dependency", "waiting_governance")


def master(conn) -> bool:
    return bool((governor.get_setting(conn, "autopilot_master") or {}).get("enabled"))


def set_master(conn, enabled: bool, actor: str) -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("only the founder switches research on or off")
    governor.set_setting(conn, "autopilot_master", {"enabled": bool(enabled)}, actor)
    return {"enabled": bool(enabled)}


def thesis_flags(conn) -> dict:
    return governor.get_setting(conn, "autopilot_theses") or {}


def set_thesis(conn, thesis_id: str, enabled: bool, actor: str, reason: str = "") -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("only the founder lets a thesis be worked on autonomously")
    d = service.thesis_detail(conn, thesis_id)
    if d is None:
        raise KeyError(thesis_id)
    flags = thesis_flags(conn)
    if enabled:
        gate = governor.pre_run_gate(conn, {"kind": "thesis_advance", "state": "waiting_governance", "thesis_id": thesis_id}, d["thesis"]["state"], AGENT_CEILING, THESIS_STATES)
        flags[thesis_id] = {"enabled": True, "paused": None, "gate_at_enable": gate["checks"], "reason": reason}
    else:
        flags[thesis_id] = {"enabled": False, "paused": None, "reason": reason}
    governor.set_setting(conn, "autopilot_theses", flags, actor)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, %s, %s, %s)", (actor, "autopilot.enable" if enabled else "autopilot.disable", thesis_id, json.dumps(flags[thesis_id], default=str)))
    conn.commit()
    return flags[thesis_id]


def _pause(conn, flags: dict, thesis_id: str, reason: str) -> None:
    flags[thesis_id] = {**flags.get(thesis_id, {}), "enabled": False, "paused": reason}
    governor.set_setting(conn, "autopilot_theses", flags, "system")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES ('system', 'autopilot.pause', %s, %s)", (thesis_id, json.dumps({"reason": reason})))
    conn.commit()


def tick(conn) -> list[dict]:
    """One scheduler pass. Returns the actions taken (for the daemon log / events). Cap 1 is enforced by the governor at dispatch; here we only keep one open job per thesis."""
    actions = []
    if not master(conn):
        return actions
    flags = thesis_flags(conn)
    for thesis_id, f in list(flags.items()):
        if not f.get("enabled"):
            continue
        d = service.thesis_detail(conn, thesis_id)
        if d is None:
            _pause(conn, flags, thesis_id, "thesis missing"); continue
        state = d["thesis"]["state"]
        if state not in THESIS_STATES or THESIS_STATES.index(state) >= THESIS_STATES.index(AGENT_CEILING):
            _pause(conn, flags, thesis_id, f"ceiling reached ({state}); founder gate next"); actions.append({"thesis_id": thesis_id, "action": "ceiling"}); continue
        if any(j["state"] in OPEN_JOB_STATES for j in d["jobs"] if j["kind"] in ("thesis_advance", "prior_art")):
            continue
        n = sum(1 for j in d["jobs"] if j["kind"] == "thesis_advance")
        job = queue.enqueue(conn, "thesis_advance", thesis_id=thesis_id, attempt_group=n, payload={"state_at_enqueue": state, "autopilot": True}, actor="system")
        if job.get("duplicate"):
            continue
        gate = governor.pre_run_gate(conn, job, state, AGENT_CEILING, THESIS_STATES)
        if not gate["passed"]:
            failed = [k for k, v in gate["checks"].items() if not v]
            queue.request_stop(conn, job["job_id"], "system"); _pause(conn, flags, thesis_id, f"gate failed: {failed}"); actions.append({"thesis_id": thesis_id, "action": "gate_failed", "failed": failed}); continue
        queue.start(conn, job["job_id"], "founder", {**gate, "autopilot": True, "enabled_by": "founder (autopilot.enable)"})
        actions.append({"thesis_id": thesis_id, "action": "started", "job_id": job["job_id"], "state": state})
    # prior_art sub-jobs requested by agents of autopilot theses: start them too
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_jobs WHERE state = 'waiting_governance' AND kind = 'prior_art' AND thesis_id = ANY(%s)", ([t for t, f in flags.items() if f.get("enabled")],))
        for job in cur.fetchall():
            gate = governor.pre_run_gate(conn, job, None, AGENT_CEILING, THESIS_STATES)
            if gate["passed"]:
                queue.start(conn, job["job_id"], "founder", {**gate, "autopilot": True}); actions.append({"thesis_id": job["thesis_id"], "action": "started_prior_art", "job_id": job["job_id"]})
    return actions


def status(conn) -> dict:
    flags = thesis_flags(conn)
    return {"master": master(conn), "theses": flags, "ceiling": AGENT_CEILING, "n_enabled": sum(1 for f in flags.values() if f.get("enabled")), "paused": {t: f["paused"] for t, f in flags.items() if f.get("paused")}}
