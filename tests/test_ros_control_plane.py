"""Research OS Phase 2 — control plane: migrations, state machines, service, DAG, queue, API. Deterministic exact counts.

DB-backed tests use the lab Postgres (like tests/test_infra_self_falsification.py) with ids prefixed TEST-ROS- and clean up after themselves.
They are skipped (not failed) when the lab DB is unreachable, because the dashboard degrades to records-only in that case by design.
"""
from __future__ import annotations

import uuid

import pytest

from logos_dashboard import db
from logos_dashboard.control import dag, queue, service
from logos_dashboard.control.state_machines import (AGENT_CEILING, DECISION_TRANSITIONS, FOUNDER_GATES, JOB_TRANSITIONS, THESIS_STATES, THESIS_TRANSITIONS,
                                                    WORK_ORDER_TRANSITIONS, IllegalTransition, events_from, transition)

# -- pure state machines (no DB) ----------------------------------------------------------------------------------


def test_thesis_vocabulary_and_transition_counts():
    assert len(THESIS_STATES) == 23 and THESIS_STATES[0] == "IDEA" and AGENT_CEILING == "PREREG_DRAFT"
    assert len(THESIS_TRANSITIONS) == 48 and len(WORK_ORDER_TRANSITIONS) == 16 and len(JOB_TRANSITIONS) == 16 and len(DECISION_TRANSITIONS) == 7
    assert {"freeze_prereg", "approve_work_order", "ready_to_run", "approve", "raise_cap", "change_benchmark", "change_claim_status"} <= FOUNDER_GATES


def test_agent_happy_path_to_prereg_draft():
    s = "IDEA"
    for e in ("triage", "start_prior_art", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        s = transition("thesis", s, e, "agent")
    assert s == "PREREG_DRAFT"
    with pytest.raises(IllegalTransition) as ex:
        transition("thesis", s, "freeze_prereg", "agent")
    assert ex.value.reason == "founder gate"
    assert transition("thesis", s, "freeze_prereg", "founder") == "PREREG_FROZEN"
    assert transition("thesis", "TRIAGE", "define_question", "agent") == "QUESTION_DEFINED"  # prior art judged unnecessary
    with pytest.raises(IllegalTransition):
        transition("thesis", "IDEA", "define_metrics", "founder")
    with pytest.raises(IllegalTransition):
        transition("nope", "IDEA", "triage", "founder")


def test_work_order_job_decision_gates():
    with pytest.raises(IllegalTransition):
        transition("work_order", "DRAFT", "approve", "agent")
    assert transition("work_order", "DRAFT", "approve", "founder") == "APPROVED"
    assert transition("job", "queued", "dequeue", "worker") == "running" and transition("job", "running", "stop", "founder") == "stopped"
    with pytest.raises(IllegalTransition):
        transition("decision", "WAITING", "approve", "agent")
    assert transition("decision", "WAITING", "defer", "founder") == "DEFERRED"
    assert [e["event"] for e in events_from("thesis", "PREREG_DRAFT")] == ["freeze_prereg", "supersede"]
    assert events_from("thesis", "PREREG_DRAFT")[0]["founder_gate"] is True


# -- DB-backed ------------------------------------------------------------------------------------------------------


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
    yield t
    conn.rollback()
    service.delete_thesis(conn, t, "system")


def _count(conn, sql, *args):
    with conn.cursor() as cur:
        cur.execute(sql, args); return cur.fetchone()[0]


def test_ros_migrations_idempotent(conn):
    v1 = db.ensure_schema(conn); v2 = db.ensure_schema(conn)
    assert v1 == v2 == 1
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'ros\\_%'")
        names = {r[0] for r in cur.fetchall()}
    assert set(db.ROS_TABLES) <= names and len(db.ROS_TABLES) == 14


def test_service_thesis_events_and_audit(conn, tid):
    a0 = _count(conn, "SELECT count(*) FROM ros_audit")
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "test thesis", "authority", "founder")
    for e in ("triage", "start_prior_art", "define_question"):
        service.advance(conn, tid, e, "agent", reason=f"test {e}")
    d = service.thesis_detail(conn, tid)
    assert d["thesis"]["state"] == "QUESTION_DEFINED" and len(d["events"]) == 4 and [x["event"] for x in d["events"]] == ["create", "triage", "start_prior_art", "define_question"]
    assert _count(conn, "SELECT count(*) FROM ros_audit") - a0 == 4
    # agent cannot pass a founder gate; nothing is written
    for e in ("define_hypothesis", "define_metrics", "draft_prereg"):
        service.advance(conn, tid, e, "agent")
    with pytest.raises(IllegalTransition):
        service.advance(conn, tid, "freeze_prereg", "agent")
    conn.rollback()
    assert _count(conn, "SELECT count(*) FROM ros_thesis_events WHERE thesis_id = %s", tid) == 7
    assert service.advance(conn, tid, "freeze_prereg", "founder", reason="frozen in lab")["state"] == "PREREG_FROZEN"
    assert d["available_events"] and d["agent_ceiling"] == "PREREG_DRAFT"
    with pytest.raises(ValueError):
        service.delete_thesis(conn, "LOGOS-REAL", "system")


def test_work_orders_dag_and_readiness(conn, tid):
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "t", "authority", "founder")
    spec = {"question": "q", "scope": "s", "hypothesis": "h", "falsification_criterion": "f", "metrics": ["m1"], "governance": {"provider": "subscription"}, "caps": {"invocations": 10}}
    with pytest.raises(ValueError) as ex:
        service.create_work_order(conn, f"{tid}-WO0", tid, {k: v for k, v in spec.items() if k not in ("hypothesis", "caps")}, "agent")
    assert "['hypothesis', 'caps']" in str(ex.value)
    a = service.create_work_order(conn, f"{tid}-A", tid, spec, "agent"); b = service.create_work_order(conn, f"{tid}-B", tid, spec, "agent")
    assert a["state"] == "DRAFT" and b["created_by"] == "agent"
    dag.add_dependency(conn, b["work_order_id"], a["work_order_id"])
    with pytest.raises(dag.CycleError):
        dag.add_dependency(conn, a["work_order_id"], b["work_order_id"])
    with pytest.raises(dag.CycleError):
        dag.add_dependency(conn, a["work_order_id"], a["work_order_id"])
    with pytest.raises(IllegalTransition):
        service.wo_transition(conn, a["work_order_id"], "approve", "agent")
    conn.rollback()
    service.wo_transition(conn, a["work_order_id"], "approve", "founder", prereg_hash="a" * 64)
    service.wo_transition(conn, b["work_order_id"], "approve", "founder")
    mine = lambda ids: [x for x in ids if x.startswith(tid)]
    assert mine(dag.ready_ids(conn)) == [a["work_order_id"]]            # B waits on A
    assert [x["work_order_id"] for x in dag.blocked(conn) if x["work_order_id"].startswith(tid)] == [b["work_order_id"]]
    service.wo_transition(conn, a["work_order_id"], "dependencies_met", "system"); service.wo_transition(conn, a["work_order_id"], "start", "worker"); service.wo_transition(conn, a["work_order_id"], "validated", "worker")
    assert mine(dag.ready_ids(conn)) == [b["work_order_id"]]
    g = dag.graph(conn); nodes = {n["work_order_id"]: n for n in g["nodes"] if n["work_order_id"].startswith(tid)}
    assert nodes[a["work_order_id"]]["depth"] == 0 and nodes[b["work_order_id"]]["depth"] == 1 and nodes[b["work_order_id"]]["ready"] is True
    assert sum(1 for e in g["edges"] if e["child"] == b["work_order_id"]) == 1


def test_queue_idempotent_and_skip_locked(conn, tid):
    service.create_thesis(conn, tid, [], "t", "authority", "founder")
    wo = f"{tid}-WO"
    j1 = queue.enqueue(conn, "tests", work_order_id=wo, thesis_id=tid, payload={"x": 1}); j2 = queue.enqueue(conn, "tests", work_order_id=wo, thesis_id=tid, payload={"x": 2})
    assert j1["job_id"] == j2["job_id"] and j1["duplicate"] is False and j2["duplicate"] is True and j2["payload"] == {"x": 1}
    assert _count(conn, "SELECT count(*) FROM ros_jobs WHERE thesis_id = %s", tid) == 1
    j3 = queue.enqueue(conn, "dry_run", work_order_id=wo, thesis_id=tid)
    c = queue.enqueue(conn, "thesis_advance", thesis_id=tid, work_order_id=wo)
    assert c["state"] == "waiting_governance" and j3["state"] == "queued"
    with pytest.raises(ValueError):
        queue.enqueue(conn, "rm_rf", thesis_id=tid)
    # two workers on a second connection: distinct jobs, none twice, third gets nothing (claude job is not queued)
    other = db.connect()
    try:
        w1 = queue.dequeue(conn, "w1", ("tests", "dry_run")); w2 = queue.dequeue(other, "w2", ("tests", "dry_run")); w3 = queue.dequeue(other, "w3", ("tests", "dry_run", "thesis_advance"))
    finally:
        other.close()
    assert {w1["job_id"], w2["job_id"]} == {j1["job_id"], j3["job_id"]} and w3 is None and w1["locked_by"] == "w1" and w1["attempt"] == 1
    assert queue.complete(conn, w1["job_id"], {"passed": 3})["state"] == "done"
    assert queue.pause(conn, w2["job_id"])["state"] == "paused" and queue.resume(conn, w2["job_id"])["state"] == "queued" and queue.stop(conn, w2["job_id"])["state"] == "stopped"
    with pytest.raises(IllegalTransition):
        queue.complete(conn, w1["job_id"], {"again": True})   # done -> complete is illegal
    conn.rollback()
    assert queue.governance_pass(conn, c["job_id"])["state"] == "queued"
    s = queue.stats(conn)
    assert set(s) == set(("queued", "waiting_quota", "waiting_dependency", "waiting_governance", "running", "paused", "failed", "done", "stopped")) and all(isinstance(v, int) for v in s.values())
    mine = [j for j in queue.list_jobs(conn, 500) if j["thesis_id"] == tid]
    assert sorted(j["state"] for j in mine) == ["done", "queued", "stopped"]


def test_decisions_and_notes(conn, tid):
    service.create_thesis(conn, tid, [], "t", "authority", "founder")
    d = service.open_decision(conn, f"{tid}-D1", "prereg_freeze", tid, why="prereg drafted", if_approved="thesis -> PREREG_FROZEN", if_rejected="back to METRICS_DEFINED", blocks=[f"{tid}-WO"])
    assert d["state"] == "WAITING" and d["blocks"] == [f"{tid}-WO"]
    with pytest.raises(IllegalTransition):
        service.decide(conn, d["decision_id"], "approve", "agent")
    conn.rollback()
    assert service.decide(conn, d["decision_id"], "defer", "founder")["state"] == "DEFERRED"
    assert service.decide(conn, d["decision_id"], "approve", "founder", reason="ok")["decided_by"] == "founder"
    n = service.add_note(conn, tid, None, "founder", "check the tie design", decision_flag=True)
    assert n["decision_flag"] is True and [x["note_id"] for x in service.unconsumed_notes(conn, tid)] == [n["note_id"]]
    det = service.thesis_detail(conn, tid)
    assert len(det["decisions"]) == 1 and len(det["notes"]) == 1 and det["decisions"][0]["state"] == "APPROVED"


# -- API ------------------------------------------------------------------------------------------------------------


def test_ros_api_roundtrip(conn, tid):
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    client = TestClient(app)
    st = client.get("/api/ros/status").json()
    assert st["db"] == "ok" and st["schema_version"] == 1 and "thesis_advance" in st["claude_kinds"]
    r = client.post("/api/ros/theses", json={"thesis_id": tid, "claim_ids": ["LOGOS-AUTH-001"], "title": "api thesis", "track": "authority"}); assert r.status_code == 200 and r.json()["state"] == "IDEA"
    assert client.post("/api/ros/theses", json={"thesis_id": tid, "title": "dup", "track": "authority"}).status_code == 409
    r = client.post(f"/api/ros/theses/{tid}/advance", json={"event": "triage", "reason": "api"}, headers={"X-Logos-Actor": "agent"}); assert r.json()["state"] == "TRIAGE"
    for e in ("define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        client.post(f"/api/ros/theses/{tid}/advance", json={"event": e}, headers={"X-Logos-Actor": "agent"})
    r = client.post(f"/api/ros/theses/{tid}/advance", json={"event": "freeze_prereg"}, headers={"X-Logos-Actor": "agent"})
    assert r.status_code == 409 and r.json()["detail"]["reason"] == "founder gate"
    assert client.post(f"/api/ros/theses/{tid}/advance", json={"event": "freeze_prereg"}).json()["state"] == "PREREG_FROZEN"   # default actor = founder
    assert client.post(f"/api/ros/theses/{tid}/advance", json={"event": "nope"}).status_code == 409
    assert client.post(f"/api/ros/theses/{tid}/advance", json={"event": "triage"}, headers={"X-Logos-Actor": "robot"}).status_code == 400
    d = client.get(f"/api/ros/theses/{tid}").json(); assert len(d["events"]) == 7 and d["thesis"]["state"] == "PREREG_FROZEN"
    assert client.get("/api/ros/theses/NOPE").status_code == 404
    spec = {"question": "q", "scope": "s", "hypothesis": "h", "falsification_criterion": "f", "metrics": ["m"], "governance": {"x": 1}, "caps": {"n": 1}}
    assert client.post("/api/ros/work-orders", json={"work_order_id": f"{tid}-W", "thesis_id": tid, "spec": {"question": "q"}}).status_code == 400
    assert client.post("/api/ros/work-orders", json={"work_order_id": f"{tid}-W", "thesis_id": tid, "spec": spec}, headers={"X-Logos-Actor": "agent"}).json()["state"] == "DRAFT"
    assert client.post(f"/api/ros/work-orders/{tid}-W/transition", json={"event": "approve"}, headers={"X-Logos-Actor": "agent"}).status_code == 409
    assert client.post(f"/api/ros/work-orders/{tid}-W/transition", json={"event": "approve", "prereg_hash": "b" * 64}).json()["approved_by"] == "founder"
    wos = client.get("/api/ros/work-orders").json(); assert f"{tid}-W" in wos["ready"] and wos["required_fields"][0] == "question"
    j = client.post("/api/ros/queue/enqueue", json={"kind": "thesis_advance", "thesis_id": tid, "work_order_id": f"{tid}-W"}).json(); assert j["state"] == "waiting_governance"
    assert client.post("/api/ros/queue/enqueue", json={"kind": "thesis_advance", "thesis_id": tid, "work_order_id": f"{tid}-W"}).json()["duplicate"] is True
    assert client.post(f"/api/ros/queue/{j['job_id']}/stop").json()["state"] == "stopped"
    assert client.post(f"/api/ros/queue/{j['job_id']}/explode").status_code == 400
    q = client.get("/api/ros/queue").json(); assert q["executor"].startswith("NOT BUILT") and any(x["job_id"] == j["job_id"] for x in q["jobs"])
    dec = client.post("/api/ros/decisions", json={"decision_id": f"{tid}-D", "kind": "gate", "subject_ref": tid, "why": "w"}).json(); assert dec["state"] == "WAITING"
    assert client.post(f"/api/ros/decisions/{tid}-D/decide", json={"event": "reject"}, headers={"X-Logos-Actor": "agent"}).status_code == 409
    assert client.post(f"/api/ros/decisions/{tid}-D/decide", json={"event": "approve"}).json()["state"] == "APPROVED"
    n = client.post("/api/ros/notes", json={"thesis_id": tid, "text": "note", "decision_flag": True}).json(); assert n["author"] == "founder"
    assert len(client.get(f"/api/ros/events?thesis_id={tid}").json()["events"]) == 7
    assert client.get("/api/ros/dag").json()["nodes"] and client.get("/api/ros/audit?limit=5").json()["audit"][0]["action"] == "note.add"
    cc = client.get("/api/command-center").json()["stats"]; assert cc["ros"]["ros_records_only"] is False and cc["queued_work_orders"] >= 1
    assert client.delete("/api/ros/theses/LOGOS-REAL").status_code == 400
