"""Control-plane endpoints (`/api/ros/*`). Localhost single-user: the actor comes from header `X-Logos-Actor` (default `founder`) and is written to the audit log.

Nothing here invokes Claude: Start only lifts a job to `queued` after the §75 gate; the host daemon executes. 503 `records_only` when the lab DB is unreachable.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import json
import time

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from logos_research.governance import GovernanceError

from . import db
from .control import dag, governor, queue, runs, service
from .control.state_machines import ACTORS_DOC, AGENT_CEILING, THESIS_STATES, IllegalTransition

router = APIRouter(prefix="/api/ros")


@contextmanager
def _conn():
    c = db.connect()
    if c is None:
        raise HTTPException(503, {"records_only": True, "detail": "lab Postgres unreachable"})
    try:
        db.ensure_schema(c)
        yield c
    except IllegalTransition as e:
        c.rollback(); raise HTTPException(409, {"illegal_transition": str(e), "reason": e.reason, "state": e.state, "event": e.event, "actor": e.actor})
    except GovernanceError as e:
        c.rollback(); raise HTTPException(403, {"governance": str(e)})
    except (ValueError, dag.CycleError) as e:
        c.rollback(); raise HTTPException(400, str(e))
    except KeyError as e:
        c.rollback(); raise HTTPException(404, f"not found: {e}")
    finally:
        c.close()


def _actor(x_logos_actor: str | None) -> str:
    a = (x_logos_actor or "founder").strip().lower()
    if a not in service.ACTORS:
        raise HTTPException(400, f"unknown actor {a!r}")
    return a


class ThesisIn(BaseModel):
    thesis_id: str
    claim_ids: list[str] = []
    title: str
    track: str
    reason: str = ""


class EventIn(BaseModel):
    event: str
    reason: str = ""
    source_record: str | None = None
    git_commit: str | None = None
    prereg_hash: str | None = None


class WorkOrderIn(BaseModel):
    work_order_id: str
    thesis_id: str | None = None
    spec: dict[str, Any]


class DepIn(BaseModel):
    child: str
    parent: str
    mandatory: bool = True


class DecisionIn(BaseModel):
    decision_id: str
    kind: str
    subject_ref: str
    why: str
    impact: str = ""
    if_approved: str = ""
    if_rejected: str = ""
    blocks: list[str] = []


class EnqueueIn(BaseModel):
    kind: str
    work_order_id: str | None = None
    run_id: str | None = None
    thesis_id: str | None = None
    payload: dict[str, Any] = {}
    attempt_group: int = 0


class NoteIn(BaseModel):
    thesis_id: str | None = None
    run_id: str | None = None
    text: str
    decision_flag: bool = False


@router.get("/status")
def status():
    return {**db.status(), "actors": ACTORS_DOC, "job_kinds": list(queue.KINDS), "claude_kinds": list(queue.CLAUDE_KINDS)}


@router.get("/theses")
def theses():
    with _conn() as c:
        return {"theses": service.list_theses(c)}


@router.post("/theses")
def create_thesis(t: ThesisIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        try:
            return service.create_thesis(c, t.thesis_id, t.claim_ids, t.title, t.track, _actor(x_logos_actor), t.reason)
        except Exception as e:  # unique violation etc.
            if "duplicate key" in str(e):
                c.rollback(); raise HTTPException(409, f"thesis {t.thesis_id} exists")
            raise


@router.get("/theses/{thesis_id}")
def thesis(thesis_id: str):
    with _conn() as c:
        d = service.thesis_detail(c, thesis_id)
        if d is None:
            raise HTTPException(404, thesis_id)
        return d


@router.post("/theses/{thesis_id}/advance")
def advance(thesis_id: str, e: EventIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return service.advance(c, thesis_id, e.event, _actor(x_logos_actor), e.reason, e.source_record, e.git_commit)


@router.delete("/theses/{thesis_id}")
def delete_thesis(thesis_id: str, x_logos_actor: str | None = Header(default=None)):
    """Test hygiene only (TEST-ROS-* ids)."""
    with _conn() as c:
        return {"deleted": service.delete_thesis(c, thesis_id, _actor(x_logos_actor))}


@router.get("/work-orders")
def work_orders():
    with _conn() as c:
        return {"work_orders": service.list_work_orders(c), "ready": dag.ready_ids(c), "blocked": dag.blocked(c), "required_fields": list(service.WORK_ORDER_REQUIRED)}


@router.post("/work-orders")
def create_work_order(w: WorkOrderIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return service.create_work_order(c, w.work_order_id, w.thesis_id, w.spec, _actor(x_logos_actor))


@router.post("/work-orders/{work_order_id}/transition")
def wo_transition(work_order_id: str, e: EventIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return service.wo_transition(c, work_order_id, e.event, _actor(x_logos_actor), e.reason, e.prereg_hash)


@router.post("/work-orders/deps")
def add_dep(d: DepIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return dag.add_dependency(c, d.child, d.parent, d.mandatory, _actor(x_logos_actor))


@router.get("/dag")
def graph():
    with _conn() as c:
        return dag.graph(c)


@router.get("/decisions")
def decisions(state: str | None = None):
    with _conn() as c:
        return {"decisions": service.list_decisions(c, state)}


@router.post("/decisions")
def open_decision(d: DecisionIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return service.open_decision(c, d.decision_id, d.kind, d.subject_ref, d.why, d.impact, d.if_approved, d.if_rejected, d.blocks, _actor(x_logos_actor))


@router.post("/decisions/{decision_id}/decide")
def decide(decision_id: str, e: EventIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return service.decide(c, decision_id, e.event, _actor(x_logos_actor), e.reason)


@router.get("/queue")
def queue_list(state: str | None = None, limit: int = 200):
    with _conn() as c:
        return {"jobs": queue.list_jobs(c, limit, state), "stats": queue.stats(c), "executor": "host daemon (claude jobs, founder Start) + deterministic worker; see /system/workers"}


@router.post("/queue/enqueue")
def enqueue(j: EnqueueIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return queue.enqueue(c, j.kind, work_order_id=j.work_order_id, run_id=j.run_id, thesis_id=j.thesis_id, payload=j.payload, attempt_group=j.attempt_group, actor=_actor(x_logos_actor))


def _gate_for(c, job: dict) -> dict:
    th = service.thesis_detail(c, job["thesis_id"]) if job.get("thesis_id") else None
    return governor.pre_run_gate(c, job, th["thesis"]["state"] if th else None, AGENT_CEILING, THESIS_STATES)


@router.get("/queue/{job_id}/gate")
def job_gate(job_id: int):
    """§75 pre-run integrity gate preview for a Claude job (what Start would check)."""
    with _conn() as c:
        job = next((j for j in queue.list_jobs(c, 10000) if j["job_id"] == job_id), None)
        if job is None:
            raise HTTPException(404, str(job_id))
        return _gate_for(c, job)


@router.post("/queue/{job_id}/{action}")
def job_action(job_id: int, action: str, x_logos_actor: str | None = Header(default=None)):
    actor = _actor(x_logos_actor)
    with _conn() as c:
        if action == "start":                       # founder Start: gate evaluated now and recorded in the audit row
            job = next((j for j in queue.list_jobs(c, 10000) if j["job_id"] == job_id), None)
            if job is None:
                raise HTTPException(404, str(job_id))
            return queue.start(c, job_id, actor, _gate_for(c, job))
        if action == "stop":
            return queue.request_stop(c, job_id, actor)
        fn = {"pause": queue.pause, "resume": queue.resume, "retry": queue.retry}.get(action)
        if fn is None:
            raise HTTPException(400, f"unknown action {action}")
        return fn(c, job_id, actor)


@router.post("/theses/{thesis_id}/agent-job")
def agent_job(thesis_id: str, x_logos_actor: str | None = Header(default=None)):
    """Enqueue a `thesis_advance` job (waiting_governance). Founder Start is a separate click."""
    with _conn() as c:
        d = service.thesis_detail(c, thesis_id)
        if d is None:
            raise HTTPException(404, thesis_id)
        n = sum(1 for j in d["jobs"] if j["kind"] == "thesis_advance")
        return queue.enqueue(c, "thesis_advance", thesis_id=thesis_id, attempt_group=n, payload={"state_at_enqueue": d["thesis"]["state"]}, actor=_actor(x_logos_actor))


# -- runs + console -------------------------------------------------------------------------------------------------


@router.get("/runs")
def runs_list(thesis_id: str | None = None, limit: int = 100):
    with _conn() as c:
        return {"runs": runs.list_runs(c, limit, thesis_id)}


@router.get("/runs/{run_id}")
def run_get(run_id: str):
    with _conn() as c:
        r = runs.get_run(c, run_id)
        if r is None:
            raise HTTPException(404, run_id)
        job = next((j for j in queue.list_jobs(c, 10000) if j["job_id"] == r.get("job_id")), None)
        return {"run": r, "job": job, "events": runs.events_after(c, run_id, 0, 1000)}


@router.get("/runs/{run_id}/events")
def run_events(run_id: str, after: int = 0, limit: int = 500):
    with _conn() as c:
        return {"events": runs.events_after(c, run_id, after, limit)}


@router.get("/runs/{run_id}/stream")
def run_stream(run_id: str, after: int = 0):
    """SSE: replays events after `after`, then polls the append-only table until the run leaves `running` (max 1 h)."""
    def gen():
        last = after; started = time.time()
        while time.time() - started < 3600:
            c = db.connect()
            if c is None:
                yield "event: error\ndata: {\"records_only\": true}\n\n"; return
            try:
                r = runs.get_run(c, run_id)
                if r is None:
                    yield f"event: error\ndata: {json.dumps({'missing': run_id})}\n\n"; return
                for e in runs.events_after(c, run_id, last, 200):
                    last = e["seq"]; yield f"id: {e['seq']}\nevent: {e['kind']}\ndata: {json.dumps(e, default=str)}\n\n"
                yield f"event: state\ndata: {json.dumps({'state': r['state'], 'finished': r['finished']}, default=str)}\n\n"
                if r["state"] != "running":
                    return
            finally:
                c.close()
            time.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/runs/{run_id}/stop")
def run_stop(run_id: str, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        r = runs.get_run(c, run_id)
        if r is None or not r.get("job_id"):
            raise HTTPException(404, run_id)
        runs.emit(c, run_id, "stop", {"requested_by": _actor(x_logos_actor)})
        return queue.request_stop(c, int(r["job_id"]), _actor(x_logos_actor))


# -- governor / auth evidence / workers -------------------------------------------------------------------------------


@router.get("/governor")
def governor_state():
    with _conn() as c:
        st = governor.state(c)
        return {**st, "model_pin_source": governor.FOUNDER_MODEL_PIN_SOURCE, "can_dispatch": {"claude": governor.can_dispatch(c, "thesis_advance"), "deterministic": governor.can_dispatch(c, "tests")}, "attestation_ttl_h": governor.ATTESTATION_TTL_H}


@router.post("/governor/preflight")
def governor_preflight(x_logos_actor: str | None = Header(default=None)):
    """Runs the documented zero-inference commands (`claude --version`, `claude auth status --json`) and records class-level evidence. Founder only."""
    actor = _actor(x_logos_actor)
    ev = governor.preflight_evidence()
    with _conn() as c:
        rec = governor.record_attestation(c, ev, actor)
        return {"evidence": ev, "recorded": rec, "attestation": governor.attestation(c)}


class QuotaIn(BaseModel):
    state: str = "OK"
    detail: str = ""


@router.post("/governor/quota")
def governor_quota(q: QuotaIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return governor.set_quota_state(c, q.state, _actor(x_logos_actor), q.detail)


class SettingIn(BaseModel):
    key: str
    value: int


@router.post("/governor/settings")
def governor_setting(sv: SettingIn, x_logos_actor: str | None = Header(default=None)):
    if sv.key not in ("max_active_theses", "max_parallel_deterministic_jobs", "max_claude_invocations_per_job"):
        raise HTTPException(403, {"governance": f"{sv.key} is not an operator setting"})
    with _conn() as c:
        governor.set_setting(c, sv.key, int(sv.value), _actor(x_logos_actor)); return governor.state(c)


@router.get("/workers")
def workers_list():
    with _conn() as c:
        return {"workers": governor.workers(c)}


@router.get("/events")
def events(thesis_id: str | None = None, limit: int = 200):
    with _conn() as c:
        return {"events": service.events(c, thesis_id, limit)}


@router.get("/audit")
def audit(limit: int = 100):
    with _conn() as c:
        return {"audit": service.audit_tail(c, limit)}


@router.post("/notes")
def add_note(n: NoteIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return service.add_note(c, n.thesis_id, n.run_id, _actor(x_logos_actor), n.text, n.decision_flag)


def command_center_stats() -> dict:
    """Live counts for the command center; zeros + records_only flag when the DB is down."""
    c = db.connect()
    if c is None:
        return {"queued_work_orders": 0, "running_agents": 0, "ros_records_only": True, "open_decisions": 0, "theses": 0}
    try:
        db.ensure_schema(c)
        s = queue.stats(c)
        with c.cursor() as cur:
            cur.execute("SELECT count(*) FROM ros_work_orders WHERE state IN ('APPROVED','READY')"); qwo = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM ros_decisions WHERE state = 'WAITING'"); od = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM ros_theses"); nt = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM ros_jobs WHERE state = 'running' AND kind = ANY(%s)", (list(queue.CLAUDE_KINDS),)); ra = cur.fetchone()[0]
        return {"queued_work_orders": int(qwo), "running_agents": int(ra), "running_jobs": s["running"], "queued_jobs": s["queued"], "waiting_governance": s["waiting_governance"], "waiting_quota": s["waiting_quota"], "open_decisions": int(od), "theses": int(nt),
                "quota": governor.quota_state(c).get("state"), "ros_records_only": False}
    finally:
        c.close()


# -- test hook (TEST-ROS-* only): a synthetic run with events so the console can be exercised without any Claude invocation ------


@router.post("/test/fake-run/{thesis_id}")
def fake_run(thesis_id: str):
    if not thesis_id.startswith("TEST-ROS-"):
        raise HTTPException(400, "TEST-ROS-* ids only")
    with _conn() as c:
        j = queue.enqueue(c, "thesis_advance", thesis_id=thesis_id, attempt_group=int(time.time()) % 100000, payload={"fake": True}, actor="system")
        run_id = f"RUN-{j['job_id']}-fake"
        runs.create_run(c, run_id, job_id=j["job_id"], kind="thesis_advance", thesis_id=thesis_id, work_order_id=None, branch=f"ros/{thesis_id}/{run_id}")
        runs.emit(c, run_id, "gate", {"checks": {"db_ok": True}, "passed": True}); runs.emit(c, run_id, "phase", {"phase": "packet"})
        runs.emit(c, run_id, "claude.invoke", {"requested_model": "claude-opus-5", "max_turns": 25, "invocation": 1})
        runs.emit(c, run_id, "claude.result", {"status": "OK", "requested_model": "claude-opus-5", "resolved_model": "claude-opus-5", "evidence_class": "TIER3_PIN_CONTAINMENT", "turns": 3, "latency_s": 1.5})
        runs.emit(c, run_id, "done", {"status": "OK", "files": [], "summary": "fake"}); runs.finish_run(c, run_id, "done", None, {"fake": True})
        with c.cursor() as cur:
            cur.execute("UPDATE ros_jobs SET state = 'done', updated_at = now() WHERE job_id = %s", (j["job_id"],))
        c.commit()
        return {"run_id": run_id, "job_id": j["job_id"]}
