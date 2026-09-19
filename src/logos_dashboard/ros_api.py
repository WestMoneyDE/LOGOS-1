"""Control-plane endpoints (`/api/ros/*`). Localhost single-user: the actor comes from header `X-Logos-Actor` (default `founder`) and is written to the audit log.

Nothing here executes a job — enqueue/pause/stop only change queue state (Phase 3 adds the executor). 503 `records_only` when the lab DB is unreachable.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from . import db
from .control import dag, queue, service
from .control.state_machines import ACTORS_DOC, IllegalTransition

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
        return {"jobs": queue.list_jobs(c, limit, state), "stats": queue.stats(c), "executor": "NOT BUILT (Phase 3) — jobs are recorded, never run"}


@router.post("/queue/enqueue")
def enqueue(j: EnqueueIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return queue.enqueue(c, j.kind, work_order_id=j.work_order_id, run_id=j.run_id, thesis_id=j.thesis_id, payload=j.payload, attempt_group=j.attempt_group, actor=_actor(x_logos_actor))


@router.post("/queue/{job_id}/{action}")
def job_action(job_id: int, action: str, x_logos_actor: str | None = Header(default=None)):
    fn = {"pause": queue.pause, "resume": queue.resume, "stop": queue.stop, "retry": queue.retry}.get(action)
    if fn is None:
        raise HTTPException(400, f"unknown action {action}")
    with _conn() as c:
        return fn(c, job_id, _actor(x_logos_actor))


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
        return {"queued_work_orders": int(qwo), "running_agents": s["running"], "queued_jobs": s["queued"], "waiting_governance": s["waiting_governance"], "open_decisions": int(od), "theses": int(nt), "ros_records_only": False}
    finally:
        c.close()
