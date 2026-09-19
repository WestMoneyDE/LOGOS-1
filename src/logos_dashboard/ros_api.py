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



# -- Phase 4: trace explorer ---------------------------------------------------------------------------------------------

import hashlib  # noqa: E402
import os  # noqa: E402

from .control import telemetry as _tel  # noqa: E402

MLFLOW_UI = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:55000")


@router.get("/traces")
def traces(limit: int = 100):
    with _conn() as c:
        rs = runs.list_runs(c, limit)
        with c.cursor() as cur:
            cur.execute("SELECT run_id, mlflow_run_id, trace_id FROM ros_trace_links"); links: dict[str, dict] = {}
            for run_id, ml, tr in cur.fetchall():
                d = links.setdefault(run_id, {"mlflow_run_id": None, "otel_trace_ids": []}); d["mlflow_run_id"] = d["mlflow_run_id"] or ml
                if tr:
                    d["otel_trace_ids"].append(tr)
        for r in rs:
            r["links"] = links.get(r["run_id"], {"mlflow_run_id": None, "otel_trace_ids": []})
            tl = (r.get("summary") or {}).get("telemetry") or {}
            r["mlflow_ui"] = _tel.mlflow_ui_url(MLFLOW_UI, tl.get("mlflow_experiment_id"), r["links"]["mlflow_run_id"])
            r["telemetry_degraded"] = tl.get("degraded", [])
        return {"runs": rs, "mlflow_ui": MLFLOW_UI, "experiment": _tel.MLFLOW_EXPERIMENT}


@router.get("/runs/{run_id}/trace")
def run_trace(run_id: str, fetch_mlflow: bool = False):
    with _conn() as c:
        r = runs.get_run(c, run_id)
        if r is None:
            raise HTTPException(404, run_id)
        ev = runs.events_after(c, run_id, 0, 2000)
        links = _tel.trace_links(c, run_id); arts = _tel.artifacts(c, run_id)
        tl = (r.get("summary") or {}).get("telemetry") or {}
        inv = [e["payload"] for e in ev if e["kind"] == "claude.invoke"]; res = [e["payload"] for e in ev if e["kind"] == "claude.result"]
        ml = None
        if fetch_mlflow and links and links[0]["mlflow_run_id"] and not str(links[0]["mlflow_run_id"]).startswith("null-"):
            try:
                ml = _tel.stack_from_env()["tracker"].fetch(links[0]["mlflow_run_id"])
            except Exception as e:
                ml = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        return {"run": r, "waterfall": _tel.waterfall(ev), "links": links, "artifacts": arts, "invocations": [{"invoke": i, "result": rr} for i, rr in zip(inv, res)], "mlflow": ml,
                "mlflow_ui": _tel.mlflow_ui_url(MLFLOW_UI, tl.get("mlflow_experiment_id"), links[0]["mlflow_run_id"] if links else None), "telemetry": tl, "n_events": len(ev)}


@router.post("/runs/{run_id}/rescore")
def run_rescore(run_id: str):
    """Re-parse the stored agent result (claude_result.json artifact in MLflow) against the current contract. Never invokes Claude."""
    from .control import packet as _pk
    with _conn() as c:
        arts = _tel.artifacts(c, run_id); a = next((x for x in arts if x["kind"] == "claude_result"), None)
        if a is None:
            raise HTTPException(404, "no claude_result artifact for this run")
        links = _tel.trace_links(c, run_id)
        if not links or not links[0]["mlflow_run_id"] or str(links[0]["mlflow_run_id"]).startswith("null-"):
            raise HTTPException(409, "artifact not retrievable (telemetry stack was null for this run)")
        try:
            from mlflow.tracking import MlflowClient
            path = MlflowClient(MLFLOW_UI).download_artifacts(links[0]["mlflow_run_id"], "claude_result.json")
            doc = json.loads(open(path, encoding="utf-8").read())
        except Exception as e:
            raise HTTPException(502, f"mlflow: {type(e).__name__}: {str(e)[:200]}")
        parsed = _pk.parse_agent_result(doc.get("content") or "")
        return {"run_id": run_id, "artifact_sha256": a["sha256"], "content_sha256": hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest(), "contract": _pk.RESULT_SCHEMA, "valid": parsed is not None,
                "parsed": parsed.raw if parsed else None, "status": doc.get("status"), "resolved_model": doc.get("resolved_model"), "evidence_class": doc.get("evidence_class"), "inference": "none (re-score only)"}



# -- Phase 5: benchmark lab, statistics, snapshots, monthly progress -----------------------------------------------------

from . import benchmarks as _bm, readers as _readers, registries as _registries, stats as _stats  # noqa: E402
from .control import benchlab as _bl  # noqa: E402


@router.get("/benchmarks")
def benchmarks_get():
    with _conn() as c:
        suites = _bl.sync_definitions(c)
        sc = _bl.scorecard(c)
        return {**sc, "suite_rows": suites, "snapshots": _bl.snapshots(c)[:50], "mom": {sid: _bl.month_over_month(c, sid, "DETERMINISTIC") for sid in _bm.SUITES}}


@router.post("/benchmarks/{suite_id}/approve")
def benchmarks_approve(suite_id: str, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        _bl.sync_definitions(c); return _bl.approve_definition(c, suite_id, _actor(x_logos_actor))


@router.post("/benchmarks/{suite_id}/run")
def benchmarks_run(suite_id: str, x_logos_actor: str | None = Header(default=None)):
    """Enqueue the deterministic fixture run for a suite (worker job `benchmark`). Never an inference."""
    if suite_id not in _bm.SUITES:
        raise HTTPException(404, suite_id)
    with _conn() as c:
        n = sum(1 for j in queue.list_jobs(c, 10000) if j["kind"] == "benchmark" and (j.get("payload") or {}).get("suite") == suite_id)
        return queue.enqueue(c, "benchmark", payload={"suite": suite_id}, attempt_group=n, actor=_actor(x_logos_actor))


class SnapshotIn(BaseModel):
    mode: str = "DETERMINISTIC"
    month: str | None = None


@router.post("/benchmarks/{suite_id}/snapshot")
def benchmarks_snapshot(suite_id: str, s: SnapshotIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return _bl.freeze_snapshot(c, suite_id, s.mode, _actor(x_logos_actor), month=s.month)


class StatsIn(BaseModel):
    method: str
    args: dict[str, Any] = {}


@router.post("/statistics/compute")
def statistics_compute(s: StatsIn):
    fn = {"wilson": _stats.wilson, "newcombe": _stats.newcombe, "bootstrap_mean": _stats.bootstrap_mean, "cohens_h": _stats.cohens_h, "pp_delta": _stats.pp_delta, "relative_change": _stats.relative_change,
          "error_reduction": _stats.error_reduction, "efficiency": _stats.efficiency, "confusion": _stats.confusion, "calibration": _stats.calibration, "mcnemar_exact": _stats.mcnemar_exact}.get(s.method)
    if fn is None:
        raise HTTPException(400, f"unknown method {s.method}")
    try:
        return fn(**s.args)
    except (TypeError, ValueError) as e:
        raise HTTPException(400, str(e))


@router.get("/statistics/methods")
def statistics_methods():
    return {"version": _stats.VERSION, "methods": {"wilson": ["k", "n"], "newcombe": ["k1", "n1", "k2", "n2"], "bootstrap_mean": ["xs", "reps", "seed"], "cohens_h": ["p1", "p2"], "pp_delta": ["p_new", "p_old"], "relative_change": ["new", "old"], "error_reduction": ["err_new", "err_old"], "efficiency": ["successes", "cost"], "confusion": ["tp", "fp", "fn", "tn"], "calibration": ["pairs", "bins"], "mcnemar_exact": ["b", "c"]},
            "rule": "every result carries method, assumptions, n, missingness, version; zero denominators -> NOT_DEFINED"}


@router.get("/progress")
def progress(month: str | None = None):
    with _conn() as c:
        cl = _readers.closures(); regs = _registries.load_all()
        cur = _bl.monthly_progress(c, cl, regs, month)
        months = sorted({(x.get("closed") or "")[:7] for x in cl if x.get("closed")})
        series = [_bl.monthly_progress(c, cl, regs, m) for m in months]
        return {"current": cur, "series": series, "frozen": _bl.months(c), "comparability": "MoM deltas only between frozen months with identical definitions; otherwise NOT_COMPARABLE"}


@router.post("/progress/freeze")
def progress_freeze(month: str | None = None, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        payload = _bl.monthly_progress(c, _readers.closures(), _registries.load_all(), month)
        try:
            return _bl.freeze_month(c, payload, _actor(x_logos_actor))
        except Exception as e:
            if "duplicate key" in str(e):
                c.rollback(); raise HTTPException(409, f"month {payload['month']} already frozen (immutable)")
            raise



# -- Phase 6: inbox, radar, attention queue -------------------------------------------------------------------------------

from .control import radar as _radar  # noqa: E402


class InboxIn(BaseModel):
    kind: str
    text: str
    source_ref: str | None = None      # origin of the capture (paper, review, note); named `source_ref` so it is not mistaken for a memory-authority reader
    process: bool = True


@router.get("/inbox")
def inbox_list():
    with _conn() as c:
        return {"items": _radar.list_inbox(c), "kinds": list(_radar.INBOX_KINDS)}


@router.post("/inbox")
def inbox_add(i: InboxIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        row = _radar.add_inbox(c, i.kind, i.text, i.source_ref, _actor(x_logos_actor))
        if i.process:
            _radar.process(c, row["radar_id"], _registries.load_all(), "system")
        return {**row, "radar": _radar.get_radar(c, row["radar_id"])}


@router.get("/radar")
def radar_list(state: str | None = None):
    with _conn() as c:
        return {"items": _radar.list_radar(c, state), "pipeline": list(_radar.PIPELINE), "terminal": list(_radar.TERMINAL), "delta_kinds": list(_radar.DELTA_KINDS)}


@router.get("/radar/{radar_id}")
def radar_get(radar_id: int):
    with _conn() as c:
        r = _radar.get_radar(c, radar_id)
        if r is None:
            raise HTTPException(404, str(radar_id))
        return r


@router.post("/radar/{radar_id}/process")
def radar_process(radar_id: int, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return _radar.process(c, radar_id, _registries.load_all(), _actor(x_logos_actor))


class ReviewIn(BaseModel):
    verdict: str
    reason: str = ""


@router.post("/radar/{radar_id}/review")
def radar_review(radar_id: int, r: ReviewIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return _radar.review(c, radar_id, r.verdict, _actor(x_logos_actor), r.reason)


@router.post("/radar/{radar_id}/ai-proposal")
def radar_ai(radar_id: int, x_logos_actor: str | None = Header(default=None)):
    """Enqueue the optional AI_PROPOSAL Claude job (waits for founder Start like every Claude job)."""
    with _conn() as c:
        if _radar.get_radar(c, radar_id) is None:
            raise HTTPException(404, str(radar_id))
        n = sum(1 for j in queue.list_jobs(c, 10000) if j["kind"] == "radar_process" and (j.get("payload") or {}).get("radar_id") == radar_id)
        return queue.enqueue(c, "radar_process", payload={"radar_id": radar_id}, attempt_group=n, actor=_actor(x_logos_actor))


@router.delete("/radar/test-items")
def radar_delete_test():
    with _conn() as c:
        return {"deleted": _radar.delete_test_items(c)}


@router.get("/attention")
def attention():
    with _conn() as c:
        items = _radar.attention(c)
        a = governor.attestation(c)
        if not a["fresh"]:
            items.append({"kind": "auth_evidence", "id": "claude_auth", "text": "Claude-Auth-Nachweis fehlt oder ist älter als 24 h — Preflight ausführen", "href": "/system/claude"})
        return {"items": items, "n": len(items)}


@router.get("/notes")
def notes_list(limit: int = 200):
    with _conn() as c:
        with c.cursor(row_factory=__import__("psycopg.rows", fromlist=["dict_row"]).dict_row) as cur:
            cur.execute("SELECT * FROM ros_notes ORDER BY note_id DESC LIMIT %s", (limit,)); return {"notes": cur.fetchall()}



# -- Phase 7: evidence debt, paper readiness, monthly report ----------------------------------------------------------

from . import reports as _reports  # noqa: E402

REPORTS_DIR = _registries.DASH / "reports"


@router.get("/evidence-debt")
def evidence_debt():
    return _reports.evidence_debt(_registries.load_all(), _readers.closures())


@router.get("/paper-readiness")
def paper_readiness():
    return {"papers": _reports.paper_readiness(_registries.load_all())}


@router.get("/reports")
def reports_list():
    files = sorted(REPORTS_DIR.glob("*.md")) if REPORTS_DIR.exists() else []
    with _conn() as c:
        frozen = {m["month"]: m for m in _bl.months(c)}
    return {"reports": [{"month": f.stem, "path": str(f.relative_to(_registries.DASH.parents[2])).replace("\\", "/"), "frozen": f.stem in frozen, "sha256": (frozen.get(f.stem) or {}).get("sha256")} for f in files], "frozen_months": list(frozen)}


@router.get("/reports/{month}")
def report_get(month: str):
    with _conn() as c:
        regs = _registries.load_all(); cl = _readers.closures()
        doc = _reports.monthly_report(c, regs, cl, _bl.monthly_progress(c, cl, regs, month), month)
        return {"doc": doc, "markdown": _reports.render_markdown(doc), "frozen": month in {m["month"] for m in _bl.months(c)}}


@router.post("/reports/{month}/freeze")
def report_freeze(month: str, x_logos_actor: str | None = Header(default=None)):
    """Founder: write docs/research/dashboard/reports/<month>.md + .json and freeze the month (immutable ros_monthly_snapshots row carrying the report sha)."""
    actor = _actor(x_logos_actor)
    if actor != "founder":
        raise HTTPException(403, {"governance": "only the founder freezes a monthly report"})
    if month.startswith("TEST-ROS"):
        raise HTTPException(400, "test months are not frozen")
    with _conn() as c:
        regs = _registries.load_all(); cl = _readers.closures()
        progress = _bl.monthly_progress(c, cl, regs, month)
        doc = _reports.monthly_report(c, regs, cl, progress, month); md = _reports.render_markdown(doc)
        REPORTS_DIR.mkdir(exist_ok=True)
        (REPORTS_DIR / f"{month}.md").write_text(md, encoding="utf-8"); (REPORTS_DIR / f"{month}.json").write_text(json.dumps(doc, indent=2, default=str, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            row = _bl.freeze_month(c, {**progress, "report_sha256": doc["sha256"], "report_path": f"docs/research/dashboard/reports/{month}.md"}, actor)
        except Exception as e:
            if "duplicate key" in str(e):
                c.rollback(); raise HTTPException(409, f"month {month} already frozen (immutable); report files rewritten? no — remove is not allowed")
            raise
        return {"month": month, "sha256": doc["sha256"], "path": f"docs/research/dashboard/reports/{month}.md", "snapshot": row}



# -- R2: autopilot, worker control, repository orders, leitstand ---------------------------------------------------------

from .control import autopilot as _ap, procs as _procs, repo_orders as _ro  # noqa: E402


class SwitchIn(BaseModel):
    enabled: bool
    reason: str = ""


@router.get("/autopilot")
def autopilot_status():
    with _conn() as c:
        return _ap.status(c)


@router.post("/autopilot/master")
def autopilot_master(s: SwitchIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return {**_ap.set_master(c, s.enabled, _actor(x_logos_actor)), "status": _ap.status(c)}


@router.post("/autopilot/theses/{thesis_id}")
def autopilot_thesis(thesis_id: str, s: SwitchIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return {"thesis_id": thesis_id, "flag": _ap.set_thesis(c, thesis_id, s.enabled, _actor(x_logos_actor), s.reason), "status": _ap.status(c)}


@router.post("/autopilot/tick")
def autopilot_tick(x_logos_actor: str | None = Header(default=None)):
    """Manual scheduler pass (the host daemon does this every few seconds). Founder only."""
    if _actor(x_logos_actor) != "founder":
        raise HTTPException(403, {"governance": "founder only"})
    with _conn() as c:
        return {"actions": _ap.tick(c)}


@router.get("/workers/control")
def workers_control():
    with _conn() as c:
        return {"host": _procs.host_status(c), "docker": _procs.docker_status(c), "autopilot": _ap.status(c)}


@router.post("/workers/{which}/{action}")
def workers_action(which: str, action: str, build: bool = False, x_logos_actor: str | None = Header(default=None)):
    actor = _actor(x_logos_actor)
    fn = {("host", "start"): lambda c: _procs.host_start(c, actor), ("host", "stop"): lambda c: _procs.host_stop(c, actor), ("docker", "start"): lambda c: _procs.docker_start(c, actor, build), ("docker", "stop"): lambda c: _procs.docker_stop(c, actor)}.get((which, action))
    if fn is None:
        raise HTTPException(400, f"unknown {which}/{action}")
    with _conn() as c:
        return fn(c)


@router.post("/repo-orders/import")
def repo_orders_import(x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return _ro.import_orders(c, _actor(x_logos_actor))


@router.get("/repo-orders")
def repo_orders_list():
    with _conn() as c:
        return {"orders": _ro.chain(c), "documents": _ro.parse_documents()}


@router.get("/leitstand")
def leitstand():
    """Everything the home page needs in one call: workers, autopilot, theses with progress, attention, latest live events."""
    with _conn() as c:
        theses = service.list_theses(c); flags = _ap.thesis_flags(c)
        rs = runs.list_runs(c, 5)
        live = []
        for r in rs:
            if r["state"] == "running":
                live = [e for e in runs.events_after(c, r["run_id"], 0, 2000)][-8:]; live_run = r; break
        else:
            live_run = rs[0] if rs else None
        att = _radar.attention(c); a = governor.attestation(c)
        if not a["fresh"]:
            att.append({"kind": "auth_evidence", "id": "claude_auth", "text": "Claude-Auth-Nachweis fehlt oder ist älter als 24 h — Preflight ausführen", "href": "/system/claude"})
        for t in theses:
            t["autopilot"] = flags.get(t["thesis_id"], {"enabled": False}); t["stage_index"] = THESIS_STATES.index(t["state"]) if t["state"] in THESIS_STATES else -1
            t["open_jobs"] = [j for j in queue.list_jobs(c, 500) if j["thesis_id"] == t["thesis_id"] and j["state"] in _ap.OPEN_JOB_STATES]
        return {"host": _procs.host_status(c), "docker": _procs.docker_status(c), "autopilot": _ap.status(c), "theses": theses, "attention": att, "live_run": live_run, "live_events": live, "governor": governor.state(c), "ceiling": AGENT_CEILING, "states": list(THESIS_STATES),
                "first_steps": {"auth": a["fresh"], "thesis": len(theses) > 0, "host_running": _procs.host_status(c)["alive"], "autopilot": _ap.master(c)}}



# -- R2: trace statistics (bars, not lists) ----------------------------------------------------------------------------


@router.get("/traces/stats")
def traces_stats(limit: int = 300):
    """Aggregates over the last `limit` runs: per day × state, tokens per run, mean phase durations, tool calls, per thesis. Counts only; n shown everywhere."""
    with _conn() as c:
        rs = runs.list_runs(c, limit)
        per_day: dict[str, dict] = {}; tokens = []; phase_tot: dict[str, list[float]] = {}; tools: dict[str, int] = {}; per_thesis: dict[str, dict] = {}; latencies = []
        for r in rs:
            day = str(r["created_at"])[:10]; d = per_day.setdefault(day, {"day": day, "done": 0, "failed": 0, "stopped": 0, "running": 0, "waiting_quota": 0})
            d[r["state"] if r["state"] in d else "failed"] = d.get(r["state"], 0) + 1
            th = per_thesis.setdefault(r["thesis_id"] or "—", {"thesis": r["thesis_id"] or "—", "runs": 0, "done": 0}); th["runs"] += 1; th["done"] += 1 if r["state"] == "done" else 0
            ev = runs.events_after(c, r["run_id"], 0, 3000)
            for b in _tel.waterfall(ev):
                phase_tot.setdefault(b["phase"], []).append(b["duration_s"])
            for e in ev:
                if e["kind"] == "claude.result":
                    u = e["payload"].get("usage") or {}
                    tokens.append({"run": r["run_id"][-12:], "run_id": r["run_id"], "input": int(u.get("input_tokens") or 0), "cache": int(u.get("cache_read_input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0), "output": int(u.get("output_tokens") or 0), "latency_s": e["payload"].get("latency_s"), "status": e["payload"].get("status")})
                    if e["payload"].get("latency_s") is not None:
                        latencies.append(float(e["payload"]["latency_s"]))
                if e["kind"] == "agent.batch":
                    for it in e["payload"].get("items", []):
                        if it.get("kind") == "agent.tool":
                            tools[it.get("tool") or "?"] = tools.get(it.get("tool") or "?", 0) + 1
        phases = [{"phase": k, "mean_s": round(sum(v) / len(v), 3), "n": len(v), "max_s": round(max(v), 3)} for k, v in phase_tot.items()]
        lat = _stats.bootstrap_mean(latencies, reps=500, seed=0) if len(latencies) >= 2 else {"value": _stats.NOT_DEFINED, "ci95": None, "n": len(latencies), "method": "bootstrap_percentile"}
        return {"n_runs": len(rs), "per_day": sorted(per_day.values(), key=lambda x: x["day"]), "tokens": tokens[-40:], "phases": sorted(phases, key=lambda x: x["phase"]), "tools": [{"tool": k, "n": v} for k, v in sorted(tools.items(), key=lambda kv: -kv[1])],
                "per_thesis": sorted(per_thesis.values(), key=lambda x: -x["runs"]), "latency": lat, "version": _stats.VERSION, "note": "counts from ros_runs / ros_run_events; token figures as exposed by the CLI (no decomposition claimed)"}


# -- R3: gate chain, measurement runs, verdict ---------------------------------------------------------------------------

from .control import measurement as _meas, prereg as _prereg  # noqa: E402


@router.get("/theses/{thesis_id}/gates")
def thesis_gates(thesis_id: str):
    with _conn() as c:
        return _prereg.chain_status(c, thesis_id)


@router.get("/theses/{thesis_id}/gate-log")
def thesis_gate_log(thesis_id: str, limit: int = 100):
    with _conn() as c:
        return {"log": _prereg.gate_log(c, thesis_id, limit), "gates": list(_prereg.GATES)}


@router.post("/theses/{thesis_id}/prereg/validate")
def prereg_validate(thesis_id: str, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        v = _prereg.validate(c, thesis_id, _actor(x_logos_actor))
        return {k: v[k] for k in v if k != "payload"} | {"payload_preview": {kk: (v.get("payload") or {}).get(kk) for kk in ("experiment_id", "question", "hypothesis", "falsification_criterion", "privacy_class", "dataset_hash", "prompt_bundle_hash")}}


@router.post("/theses/{thesis_id}/prereg/freeze")
def prereg_freeze(thesis_id: str, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return _prereg.freeze(c, thesis_id, _actor(x_logos_actor))


@router.post("/theses/{thesis_id}/dry-run")
def thesis_dry_run(thesis_id: str, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return _prereg.run_dry_run(c, thesis_id, _actor(x_logos_actor))


@router.post("/theses/{thesis_id}/measurement/enqueue")
def measurement_enqueue(thesis_id: str, x_logos_actor: str | None = Header(default=None)):
    """Founder: queue the measurement job (waits for the host executor). Requires READY_TO_RUN."""
    actor = _actor(x_logos_actor)
    with _conn() as c:
        d = service.thesis_detail(c, thesis_id)
        if d is None:
            raise HTTPException(404, thesis_id)
        if d["thesis"]["state"] != "READY_TO_RUN":
            raise HTTPException(409, {"detail": f"thesis is {d['thesis']['state']}, measurement needs READY_TO_RUN"})
        p = _meas.prepare(c, thesis_id, 0)
        if not p["ok"]:
            raise HTTPException(400, {"detail": p["reason"]})
        n = sum(1 for j in queue.list_jobs(c, 10000) if j["kind"] == "measurement" and j["thesis_id"] == thesis_id)
        job = queue.enqueue(c, "measurement", thesis_id=thesis_id, work_order_id=p["work_order_id"], payload={"prereg_hash": p["prereg_hash"], "planned": p["budget"]["planned"]}, attempt_group=n, actor=actor)
        gate = _gate_for(c, job)
        if gate["passed"] and actor == "founder":
            job = queue.start(c, job["job_id"], actor, gate)
            service.advance(c, thesis_id, "start_run", "founder", reason=f"measurement job #{job['job_id']} started", source_record=str(job["job_id"]))
        _prereg.log_gate(c, thesis_id, "ready_to_run", actor, gate["passed"], {"job_id": job["job_id"], "gate": gate["checks"]})
        return {"job": job, "gate": gate, "planned": p["budget"]["planned"]}


@router.get("/measurements")
def measurements_list(thesis_id: str | None = None, limit: int = 100):
    with _conn() as c:
        return {"measurements": _meas.list_measurements(c, thesis_id, limit)}


@router.get("/measurements/{measurement_id}")
def measurement_get(measurement_id: str):
    with _conn() as c:
        d = _meas.get(c, measurement_id)
        if d is None:
            raise HTTPException(404, measurement_id)
        return d


class VerdictIn(BaseModel):
    verdict: str
    reason: str = ""


@router.post("/measurements/{measurement_id}/verdict")
def measurement_verdict(measurement_id: str, v: VerdictIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return _meas.decide_verdict(c, measurement_id, v.verdict, _actor(x_logos_actor), v.reason)


class AgentSessionsIn(BaseModel):
    n: int


@router.post("/governor/agent-sessions")
def governor_agent_sessions(a: AgentSessionsIn, x_logos_actor: str | None = Header(default=None)):
    """Founder amendment INFERENCE-GOVERNANCE-CONCURRENCY-AMENDMENT-R1: parallel AGENT jobs (1..5). Measurement stays at 1."""
    with _conn() as c:
        return {"amendment": governor.set_agent_sessions(c, a.n, _actor(x_logos_actor)), "caps": governor.caps(c).__dict__}


# -- R4: Beobachtung, Erkenntnisse, Registerpflege ------------------------------------------------------------------------

from . import insights as _insights  # noqa: E402
from .control import observe as _observe, registry_edit as _redit  # noqa: E402


@router.get("/observability")
def observability(limit: int = 30):
    with _conn() as c:
        return _observe.overview(c, limit)


@router.get("/observability/systems")
def observability_systems():
    c = db.connect()
    try:
        return {"systems": _observe.systems(c)}
    finally:
        if c:
            c.close()


@router.get("/runs/{run_id}/all-traces")
def run_all_traces(run_id: str):
    with _conn() as c:
        d = _observe.all_traces(c, run_id)
        if not d["found"]:
            raise HTTPException(404, run_id)
        return d


@router.get("/insights")
def insights(days: int = 30):
    c = db.connect()
    try:
        return _insights.build(c, days=days)
    finally:
        if c:
            c.close()


@router.get("/registry/proposals")
def registry_proposals():
    c = db.connect()
    try:
        return _redit.proposals(c)
    finally:
        if c:
            c.close()


class RegistryEditIn(BaseModel):
    registry: str
    entity_id: str
    field: str
    value: Any
    reason: str = ""
    origin: dict[str, Any] = {}      # where the proposal came from (verdict draft, radar, revert) — named `origin` so it is not a memory-authority reader


@router.post("/registry/preview")
def registry_preview(e: RegistryEditIn):
    try:
        return _redit.preview(e.registry, e.entity_id, e.field, e.value, e.reason)
    except KeyError as ex:
        raise HTTPException(404, str(ex))
    except ValueError as ex:
        raise HTTPException(400, str(ex))


@router.post("/registry/apply")
def registry_apply(e: RegistryEditIn, x_logos_actor: str | None = Header(default=None)):
    with _conn() as c:
        return _redit.apply(c, e.registry, e.entity_id, e.field, e.value, _actor(x_logos_actor), e.reason, e.origin)


@router.get("/registry/changelog")
def registry_changelog(limit: int = 200):
    return {"changes": _redit.changelog(limit), "file": "docs/research/dashboard/registry-changelog.jsonl"}


@router.post("/registry/revert-proposal")
def registry_revert(index: int = 0):
    try:
        return _redit.revert_proposal(index)
    except KeyError as ex:
        raise HTTPException(404, str(ex))
