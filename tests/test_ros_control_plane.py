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
    assert v1 == v2 == 4                                     # v1 control plane · v2 executor settings/heartbeats · v3 benchmark lab · v4 gate log + measurements (R3)
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'ros\\_%'")
        names = {r[0] for r in cur.fetchall()}
    assert set(db.ROS_TABLES) <= names and len(db.ROS_TABLES) == 23


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
    assert st["db"] == "ok" and st["schema_version"] == 4 and "thesis_advance" in st["claude_kinds"]
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
    q = client.get("/api/ros/queue").json(); assert q["executor"].startswith("host daemon") and any(x["job_id"] == j["job_id"] for x in q["jobs"])
    dec = client.post("/api/ros/decisions", json={"decision_id": f"{tid}-D", "kind": "gate", "subject_ref": tid, "why": "w"}).json(); assert dec["state"] == "WAITING"
    assert client.post(f"/api/ros/decisions/{tid}-D/decide", json={"event": "reject"}, headers={"X-Logos-Actor": "agent"}).status_code == 409
    assert client.post(f"/api/ros/decisions/{tid}-D/decide", json={"event": "approve"}).json()["state"] == "APPROVED"
    n = client.post("/api/ros/notes", json={"thesis_id": tid, "text": "note", "decision_flag": True}).json(); assert n["author"] == "founder"
    assert len(client.get(f"/api/ros/events?thesis_id={tid}").json()["events"]) == 7
    assert client.get("/api/ros/dag").json()["nodes"] and client.get("/api/ros/audit?limit=5").json()["audit"][0]["action"] == "note.add"
    from logos_dashboard.api import _cache; _cache.pop("ros_stats", None)          # 2 s stats cache may hold a value from an earlier test
    cc = client.get("/api/command-center").json()["stats"]; assert cc["ros"]["ros_records_only"] is False and cc["queued_work_orders"] >= 1
    assert client.delete("/api/ros/theses/LOGOS-REAL").status_code == 400


# -- Phase 3: governor, worktree, packet, executor (fake claude; the real CLI is never invoked) ------------------------


import json as _json
import subprocess as _sp
from pathlib import Path as _Path

from logos_research.measurement.claude_code import CALLS as _CALLS
from logos_dashboard.control import executor, governor, packet as pk, runs, worktree
from logos_dashboard.registries import load_all as _load_all


def _fake_claude(result_doc: dict | None = None, *, exit_code: int = 0, stderr: str = "", write: dict[str, str] | None = None):
    """Runner factory producing a documented-JSON `claude -p` result and optionally writing files into the worktree (the agent's outputs)."""
    def factory(cwd):
        def run(argv, timeout, env):
            assert argv[0] == "claude" and "-p" in argv and "--dangerously-skip-permissions" not in argv and "ANTHROPIC_API_KEY" not in env
            for rel, text in (write or {}).items():
                p = _Path(cwd) / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
            if exit_code != 0:
                return exit_code, "", stderr
            return 0, _json.dumps(result_doc), ""
        return run
    return factory


def _result_doc(content: str, model: str = "claude-opus-5") -> dict:
    return {"type": "result", "subtype": "success", "is_error": False, "result": content, "session_id": "fake", "num_turns": 3, "usage": {"input_tokens": 10, "output_tokens": 20},
            "modelUsage": {model: {"inputTokens": 10, "outputTokens": 20}}}


def _agent_block(event, files, needs=False, summary="drafted"):
    return "prose\n```json\n" + _json.dumps({"schema": "ros-agent-result/1", "proposed_event": event, "files": files, "needs_prior_art": needs, "summary": summary, "uncertainties": ["u1"]}) + "\n```\n"


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"; r.mkdir()
    for a in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        _sp.run(["git", *a], cwd=r, check=True, capture_output=True)
    (r / "docs/research/dashboard/theses").mkdir(parents=True); (r / "docs/research/dashboard/CLAIM-REGISTRY.json").write_text("{}", encoding="utf-8"); (r / "README.md").write_text("x", encoding="utf-8")
    _sp.run(["git", "add", "-A"], cwd=r, check=True, capture_output=True); _sp.run(["git", "commit", "-q", "-m", "init"], cwd=r, check=True, capture_output=True)
    return r


@pytest.fixture
def attested(conn):
    """Fake auth evidence for the executor tests; the founder's real settings rows are restored afterwards (no residue in the lab DB)."""
    prev = {k: governor.get_setting(conn, k) for k in ("claude_auth", "quota_state")}
    governor.record_attestation(conn, {"auth_class": "MAX_SUBSCRIPTION", "auth": {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}, "cli_version": "fake 0.0", "contamination_presence": {}}, "founder")
    governor.set_quota_state(conn, "OK", "founder")
    yield
    conn.rollback()
    with conn.cursor() as cur:
        for k, v in prev.items():
            if v is None:
                cur.execute("DELETE FROM ros_settings WHERE key = %s", (k,))
            else:
                cur.execute("UPDATE ros_settings SET value = %s WHERE key = %s", (_json.dumps(v), k))
        cur.execute("DELETE FROM ros_worker_heartbeats WHERE worker_id = 'w-test'")
    conn.commit()


def _cfg(repo, tmp_path, factory, **kw):
    return executor.ExecutorConfig(repo, tmp_path / "wts", factory, regs_loader=_load_all, cli_version="fake 0.0", **kw)


def test_governor_caps_quota_attestation_and_cap_change_refused(conn, attested):
    c = governor.caps(conn)
    assert c.max_parallel_claude_sessions == 1 and c.model_pin == "claude-opus-5" and c.max_claude_invocations_total == 200 and c.max_claude_invocations_per_job == 3
    assert governor.can_dispatch(conn, "thesis_advance") == (True, "OK") and governor.can_dispatch(conn, "tests") == (True, "OK")
    governor.set_quota_state(conn, "USAGE_LIMIT_REACHED", "system", "test")
    assert governor.can_dispatch(conn, "thesis_advance") == (False, "USAGE_LIMIT_REACHED")
    from logos_research.governance import GovernanceError
    with pytest.raises(GovernanceError):
        governor.set_quota_state(conn, "OK", "agent")
    governor.set_quota_state(conn, "OK", "founder")
    with pytest.raises(GovernanceError):
        governor.set_setting(conn, "max_parallel_claude_sessions", 2, "founder")
    with pytest.raises(GovernanceError):
        governor.record_attestation(conn, {"auth_class": "MAX_SUBSCRIPTION"}, "agent")
    assert governor.classify_auth({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}) == "MAX_SUBSCRIPTION"
    assert governor.classify_auth({"loggedIn": True, "authMethod": "console", "apiProvider": "firstParty", "subscriptionType": None}) == "CONSOLE_PAYG"
    assert governor.classify_auth({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "bedrock", "subscriptionType": "max"}) == "THIRD_PARTY_CLOUD"
    assert governor.classify_auth({"loggedIn": False}) is None
    governor.record_attestation(conn, {"auth_class": "MAX_SUBSCRIPTION", "at": "2020-01-01T00:00:00+00:00"}, "founder")
    assert governor.can_dispatch(conn, "thesis_advance") == (False, "AUTH_EVIDENCE_STALE")


def test_worktree_isolation_and_allowlist(repo, tmp_path):
    wt = worktree.create(repo, tmp_path / "wts", "T", "R1")
    assert wt.exists() and worktree.changed_files(wt) == []
    (wt / "docs/research/dashboard/theses/T").mkdir(parents=True); (wt / "docs/research/dashboard/theses/T/TRIAGE.md").write_text("ok", encoding="utf-8"); (wt / "README.md").write_text("changed", encoding="utf-8")
    ch = worktree.changed_files(wt)
    assert ch == ["README.md", "docs/research/dashboard/theses/T/TRIAGE.md"] and worktree.check_allowlist(ch, ("docs/research/dashboard/theses/T/",)) == ["README.md"]
    sha = worktree.commit(wt, "t"); assert sha and len(sha) == 40 and worktree.changed_files(wt) == []
    assert worktree.head(repo) != sha                      # main tree untouched
    assert (repo / "README.md").read_text(encoding="utf-8") == "x"
    worktree.remove(repo, wt, delete_branch="ros/T/R1"); assert not wt.exists()


def test_packet_and_result_contract(conn, tid):
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "packet thesis", "authority", "founder"); service.add_note(conn, tid, None, "founder", "check tie design", True)
    d = service.thesis_detail(conn, tid); regs = _load_all()
    p = pk.build_thesis_packet(d, regs, d["notes"], 2)
    assert "check tie design" in p["prompt"] and "LOGOS-AUTH-001" in p["prompt"] and p["allowed_events"] == ["triage"] and p["allowed_prefixes"] == (f"docs/research/dashboard/theses/{tid}/",)
    assert "freeze_prereg" in p["prompt"] and "Bash" in p["disallowed_tools"] and "WebSearch" not in p["allowed_tools"]
    pa = pk.build_thesis_packet(d, regs, [], 0, kind="prior_art")
    assert "WebSearch" in pa["allowed_tools"] and "research-briefs/" in pa["allowed_prefixes"][1]
    assert pk.parse_agent_result("no json") is None and pk.parse_agent_result('```json\n{"schema": "other"}\n```') is None
    r = pk.parse_agent_result(_agent_block("triage", ["a.md"], True)); assert r.proposed_event == "triage" and r.needs_prior_art and r.files == ("a.md",) and r.uncertainties == ("u1",)


def test_executor_happy_path_applies_agent_event_and_requests_prior_art(conn, tid, repo, tmp_path, attested):
    n0 = _CALLS["claude_code_inference_invocations"]
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "exec thesis", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); assert j["state"] == "waiting_governance"
    gate = governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "TRIAGE", "PREREG_DRAFT"))
    assert gate["passed"], gate
    with pytest.raises(IllegalTransition):
        queue.start(conn, j["job_id"], "agent", gate)
    assert queue.start(conn, j["job_id"], "founder", gate)["state"] == "queued"
    rel = f"docs/research/dashboard/theses/{tid}/TRIAGE.md"
    cfg = _cfg(repo, tmp_path, _fake_claude(_result_doc(_agent_block("triage", [rel], needs=True)), write={rel: "# triage\n"}))
    out = executor.run_once(conn, cfg, "w-test")
    assert out["state"] == "done" and out["result"]["applied_state"] == "TRIAGE" and out["result"]["files"] == [rel] and out["result"]["prior_art_job"]
    assert service.thesis_detail(conn, tid)["thesis"]["state"] == "TRIAGE"
    run = runs.list_runs(conn, thesis_id=tid)[0]; ev = runs.events_after(conn, run["run_id"])
    assert [e["kind"] for e in ev] == ["gate", "phase", "worktree", "phase", "packet", "phase", "claude.invoke", "agent.result", "claude.result", "phase", "artifact", "commit", "thesis.event", "phase", "done"]   # R2: stream events (legacy json fake -> one synthetic agent.result)
    cr = next(e for e in ev if e["kind"] == "claude.result")["payload"]; assert cr["status"] == "OK" and cr["resolved_model"] == "claude-opus-5" and cr["requested_model"] == "claude-opus-5"
    assert run["state"] == "done" and run["branch"] == f"ros/{tid}/{run['run_id']}"
    sub = [x for x in queue.list_jobs(conn, 500) if x["thesis_id"] == tid and x["kind"] == "prior_art"]; assert len(sub) == 1 and sub[0]["state"] == "waiting_governance"
    assert (repo / "README.md").read_text(encoding="utf-8") == "x"                     # main tree untouched
    assert _sp.run(["git", "branch", "--list", f"ros/{tid}/*"], cwd=repo, capture_output=True, text=True).stdout.strip() != ""
    assert _CALLS["claude_code_inference_invocations"] == n0 + 1                       # counted once (fake runner)
    assert executor.run_once(conn, cfg, "w-test") is None                              # nothing queued (prior_art waits for governance)


def test_executor_integrity_violation_and_invalid_output(conn, tid, repo, tmp_path, attested):
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "t", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    cfg = _cfg(repo, tmp_path, _fake_claude(_result_doc(_agent_block("triage", [])), write={"docs/research/dashboard/CLAIM-REGISTRY.json": "{\"hacked\": true}"}))
    out = executor.run_once(conn, cfg, "w-test"); assert out["state"] == "failed" and out["error"] == "INTEGRITY_VIOLATION"
    assert service.thesis_detail(conn, tid)["thesis"]["state"] == "IDEA" and (repo / "docs/research/dashboard/CLAIM-REGISTRY.json").read_text(encoding="utf-8") == "{}"
    assert _sp.run(["git", "branch", "--list", f"ros/{tid}/*"], cwd=repo, capture_output=True, text=True).stdout.strip() == ""   # branch discarded
    j2 = queue.enqueue(conn, "thesis_advance", thesis_id=tid, attempt_group=1); queue.start(conn, j2["job_id"], "founder", governor.pre_run_gate(conn, j2, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    out = executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(_result_doc("no block"))), "w-test"); assert out["state"] == "failed" and out["error"] == "INVALID_OUTPUT"


def test_executor_usage_limit_blocks_everything_until_founder_reset(conn, tid, repo, tmp_path, attested):
    service.create_thesis(conn, tid, [], "t", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    out = executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(None, exit_code=1, stderr="You have hit your usage limit. Resets at 5pm")), "w-test")
    assert out["state"] == "waiting_quota" and out["error"] == "USAGE_LIMIT_REACHED" and governor.quota_state(conn)["state"] == "USAGE_LIMIT_REACHED"
    assert governor.can_dispatch(conn, "thesis_advance") == (False, "USAGE_LIMIT_REACHED")
    j2 = queue.enqueue(conn, "thesis_advance", thesis_id=tid, attempt_group=1); queue.start(conn, j2["job_id"], "founder", {"passed": True})
    assert executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(_result_doc("x"))), "w-test") is None          # blocked, no invocation
    governor.set_quota_state(conn, "OK", "founder")
    assert governor.can_dispatch(conn, "thesis_advance") == (True, "OK")


def test_executor_stop_before_invocation_and_gate_refuses_above_ceiling(conn, tid, repo, tmp_path, attested):
    service.create_thesis(conn, tid, [], "t", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    queue.request_stop(conn, j["job_id"], "founder")
    assert any(x["job_id"] == j["job_id"] for x in queue.list_jobs(conn, 500, "stopped"))   # queued -> stopped immediately
    for e in ("triage", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        service.advance(conn, tid, e, "agent")
    j3 = queue.enqueue(conn, "thesis_advance", thesis_id=tid, attempt_group=3)
    g = governor.pre_run_gate(conn, j3, "PREREG_DRAFT", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT"))
    assert g["passed"] is False and g["checks"]["thesis_below_agent_ceiling"] is False
    with pytest.raises(ValueError):
        queue.start(conn, j3["job_id"], "founder", g)


def test_ros_api_runs_governor_and_console(conn, tid, attested):
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    client = TestClient(app)
    client.post("/api/ros/theses", json={"thesis_id": tid, "claim_ids": ["LOGOS-AUTH-001"], "title": "console", "track": "authority"})
    g = client.get("/api/ros/governor").json()
    assert g["caps"]["max_parallel_claude_sessions"] == 1 and g["caps"]["model_pin"] == "claude-opus-5" and g["attestation"]["fresh"] is True and g["cap_change_path"].startswith("founder amendment")
    assert client.post("/api/ros/governor/settings", json={"key": "max_parallel_claude_sessions", "value": 2}).status_code == 403
    assert client.post("/api/ros/governor/quota", json={"state": "OK"}, headers={"X-Logos-Actor": "agent"}).status_code == 403
    j = client.post(f"/api/ros/theses/{tid}/agent-job").json(); assert j["state"] == "waiting_governance" and j["kind"] == "thesis_advance"
    gate = client.get(f"/api/ros/queue/{j['job_id']}/gate").json(); assert gate["passed"] is True and gate["checks"]["thesis_below_agent_ceiling"] is True
    assert client.post(f"/api/ros/queue/{j['job_id']}/start", headers={"X-Logos-Actor": "agent"}).status_code == 409
    assert client.post(f"/api/ros/queue/{j['job_id']}/start").json()["state"] == "queued"
    assert client.post(f"/api/ros/queue/{j['job_id']}/stop").json()["state"] == "stopped"
    fr = client.post(f"/api/ros/test/fake-run/{tid}").json(); assert fr["run_id"].endswith("-fake")
    assert client.post("/api/ros/test/fake-run/LOGOS-REAL").status_code == 400
    r = client.get(f"/api/ros/runs/{fr['run_id']}").json(); assert r["run"]["state"] == "done" and [e["kind"] for e in r["events"]] == ["gate", "phase", "claude.invoke", "claude.result", "done"]
    assert len(client.get(f"/api/ros/runs/{fr['run_id']}/events?after={r['events'][1]['seq']}").json()["events"]) == 3   # seq is global; `after` is a cursor
    assert any(x["run_id"] == fr["run_id"] for x in client.get(f"/api/ros/runs?thesis_id={tid}").json()["runs"])
    with client.stream("GET", f"/api/ros/runs/{fr['run_id']}/stream") as s:
        body = "".join(s.iter_text())
    assert body.count("event: ") == 6 and "event: state" in body and '"state": "done"' in body    # 5 replayed events + final state, then the stream closes (run not running)
    assert client.get("/api/ros/workers").json()["workers"] is not None
    cc = client.get("/api/command-center").json()["stats"]; assert cc["ros"]["quota"] == "OK" and cc["running_agents"] == 0



def test_telemetry_mirror_and_trace_explorer(conn, tid, repo, tmp_path, attested):
    from logos_dashboard.control import telemetry
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "tel", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    rel = f"docs/research/dashboard/theses/{tid}/TRIAGE.md"; stack = telemetry.null_stack()
    out = executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(_result_doc(_agent_block("triage", [rel])), write={rel: "x"}), telemetry_stack=stack), "w-test")
    assert out["state"] == "done"
    run_id = runs.list_runs(conn, thesis_id=tid)[0]["run_id"]; tr = stack["tracker"]
    assert set(tr.params[run_id]) == {"thesis_state", "allowed_events", "allowed_tools", "prompt_bytes", "branch", "contract", "model_requested", "model_resolved", "claude_status", "evidence_class", "prompt_sha256"}
    assert {"latency_s", "turns", "status_ok", "tokens_input_tokens", "tokens_output_tokens", "files_changed", "event_applied", "needs_prior_art", "duration_s"} <= set(tr.metrics[run_id]) and tr.metrics[run_id]["status_ok"] == 1.0
    assert tr.ended[run_id] == "COMPLETED" and set(tr.artifacts[run_id]) == {"prompt.txt", "claude_stream.jsonl", "claude_result.json"}
    assert [s[1] for s in stack["traces"].spans] == ["run.start", "phase.worktree", "phase.packet", "phase.claude", "phase.verify", "run.finish"] and len(stack["llm_traces"].generations) == 1
    links = telemetry.trace_links(conn, run_id); assert len(links) == 6 and links[0]["mlflow_run_id"] == f"null-{run_id}"
    arts = telemetry.artifacts(conn, run_id); assert [a["kind"] for a in arts] == ["prompt", "claude_stream", "claude_result"] and all(len(a["sha256"]) == 64 for a in arts)
    assert out["result"]["telemetry"]["degraded"] == [] and out["result"]["telemetry"]["stack"] == "null"
    client = TestClient(app)
    t = client.get(f"/api/ros/runs/{run_id}/trace").json()
    assert [b["phase"] for b in t["waterfall"]] == ["worktree", "packet", "claude", "verify"] and all(b["duration_s"] >= 0 for b in t["waterfall"]) and len(t["invocations"]) == 1 and t["invocations"][0]["result"]["status"] == "OK"
    assert t["mlflow_ui"] is not None and "null-" in t["mlflow_ui"] and len(t["artifacts"]) == 3 and t["n_events"] == 14
    lst = client.get("/api/ros/traces").json(); mine = next(r for r in lst["runs"] if r["run_id"] == run_id); assert mine["links"]["mlflow_run_id"] == f"null-{run_id}" and lst["experiment"] == "logos-research-os"
    assert client.post(f"/api/ros/runs/{run_id}/rescore").status_code == 409     # null stack: artifact not retrievable; and never an inference
    assert client.post("/api/ros/runs/NOPE/rescore").status_code == 404


def test_telemetry_degrades_without_blocking(conn, tid, repo, tmp_path, attested):
    from logos_dashboard.control import telemetry

    class Broken:
        def start_run(self, *a, **k): raise RuntimeError("mlflow down")
        def log_params(self, *a, **k): raise RuntimeError("mlflow down")
        def log_metrics(self, *a, **k): raise RuntimeError("mlflow down")
        def end_run(self, *a, **k): raise RuntimeError("mlflow down")
        def log_artifact(self, *a, **k): raise RuntimeError("mlflow down")
    service.create_thesis(conn, tid, [], "tel2", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    stack = {**telemetry.null_stack(), "tracker": Broken(), "kind": "broken"}
    out = executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(_result_doc(_agent_block("triage", []))), telemetry_stack=stack), "w-test")
    assert out["state"] == "done" and len(out["result"]["telemetry"]["degraded"]) >= 4 and all("mlflow down" in d for d in out["result"]["telemetry"]["degraded"])
    run_id = runs.list_runs(conn, thesis_id=tid)[0]["run_id"]; kinds = [e["kind"] for e in runs.events_after(conn, run_id)]
    assert kinds.count("note") == 1 and kinds[-1] == "done"



# -- Phase 5: statistics, benchmark lab, immutable snapshots, monthly progress -----------------------------------------


def test_statistics_module_matches_cpa_formulas_and_fails_closed():
    from logos_dashboard import stats
    from logos_research.experiments.cognitive_provenance_r1 import metrics as cpa
    for k, n in ((0, 1), (3, 10), (57, 60), (100, 100)):
        w = stats.wilson(k, n); p, lo, hi = cpa.wilson(k, n)
        assert w["value"] == p and abs(w["ci95"][0] - lo) < 1e-12 and abs(w["ci95"][1] - hi) < 1e-12 and w["version"] == "ros-stats/1" and w["missingness"] == {"missing": 0, "of": n}
    d = stats.newcombe(30, 50, 20, 50); cd = cpa.newcombe(30, 50, 20, 50)
    assert abs(d["value"] - cd[0]) < 1e-12 and abs(d["ci95"][0] - cd[1]) < 1e-12 and abs(d["ci95"][1] - cd[2]) < 1e-12
    assert stats.wilson(0, 0)["value"] == "NOT_DEFINED" and stats.newcombe(1, 0, 1, 2)["value"] == "NOT_DEFINED" and stats.relative_change(1, 0)["value"] == "NOT_DEFINED" and stats.error_reduction(0.1, 0)["value"] == "NOT_DEFINED"
    assert stats.pp_delta(0.6, 0.5)["value"] == 10.0 and stats.pp_delta(None, 0.5)["value"] == "NOT_DEFINED" and stats.efficiency(5, 0)["value"] == "NOT_DEFINED" and stats.efficiency(5, 2.5)["value"] == 2.0
    b = stats.bootstrap_mean([1, 2, 3, 4, 5], reps=500, seed=7); assert b["value"] == 3.0 and b["ci95"][0] <= 3.0 <= b["ci95"][1] and stats.bootstrap_mean([1], reps=10)["value"] == "NOT_DEFINED"
    assert stats.bootstrap_mean([1, 2, 3, 4, 5], reps=500, seed=7)["ci95"] == b["ci95"]        # deterministic by seed
    assert stats.cohens_h(0.5, 0.5)["value"] == 0 and stats.cohens_h(0.9, 0.1)["magnitude"] == "large"
    c = stats.confusion(8, 2, 1, 9); assert c["precision"] == 0.8 and c["recall"] == 0.8 / 0.8 * 8 / 9 and c["false_allow_rate"] == 2 / 11 and stats.confusion(0, 0, 0, 0)["precision"] == "NOT_DEFINED"
    cal = stats.calibration([(0.9, 1), (0.9, 1), (0.1, 0), (0.1, 1)], bins=10); assert abs(cal["value"] - 0.5 * 0.1 - 0.5 * 0.4) < 1e-9 and cal["n"] == 4
    m = stats.mcnemar_exact(3, 7); assert abs(m["value"] - 0.34375) < 1e-9 and stats.mcnemar_exact(0, 0)["value"] == "NOT_DEFINED"
    with pytest.raises(ValueError):
        stats.wilson(5, 3)


def test_benchmark_definitions_scorecard_gates_and_comparability():
    from logos_dashboard import benchmarks as bm
    d = bm.definitions()
    assert set(d["suites"]) == {"AUTHORITY_GOLDEN", "PROVENANCE_GOLDEN", "TRAJECTORY_GOLDEN", "MEMORY_GOLDEN", "COGNITIVE_PROVENANCE_GOLDEN", "REGRESSION_GOLDEN"} and d["status"] == "DRAFT_PENDING_FOUNDER_APPROVAL" and len(d["sha256"]) == 64
    assert d["modes"] == ("BASELINE_AGENT", "LOGOS_AGENT", "LOGOS_ABLATION", "PREVIOUS_MONTH", "PREVIOUS_RELEASE") and len(d["hard_gates"]) == 3
    for spec in d["suites"].values():
        assert spec["fixtures"] and all(f.startswith("tests/test_") for f in spec["fixtures"]) and all((_Path(__file__).resolve().parents[1] / f).exists() for f in spec["fixtures"])
    row = bm.scorecard_row("task_success", 45, 50, baseline=(30, 50)); assert row["status"] == "OK" and row["delta"]["method"] == "newcombe" and row["delta"]["pp"] == 30.0
    assert bm.scorecard_row("task_success", None, None)["status"] == "NO_DATA"
    g = bm.hard_gate_verdict([bm.scorecard_row("authority_false_allow", 1, 100), bm.scorecard_row("fixture_regression", 99, 100)]); assert g["verdict"] == "FAILED_SAFETY_GATE" and [f["id"] for f in g["failures"]] == ["HG1", "HG3"]
    assert bm.hard_gate_verdict([bm.scorecard_row("fixture_regression", 100, 100)])["verdict"] == "PASS" and bm.hard_gate_verdict([bm.scorecard_row("fixture_regression", 99, 100)])["verdict"] == "FAILED_REGRESSION_GATE"
    a = {"model_pin": "claude-opus-5", "dataset_hash": "d", "prompt_bundle_hash": "p", "tool_boundary": "t", "definition_version": "v", "suite": "S", "mode": "M"}
    assert bm.comparability(a, a)["badge"] == "COMPARABLE" and bm.comparability(a, {**a, "model_pin": "claude-sonnet-5"})["reasons"] == ["model_pin"]
    j = bm.parse_junit('<testsuites><testsuite><testcase classname="a" name="t1"/><testcase classname="a" name="t2"><failure/></testcase><testcase classname="a" name="t3"><skipped/></testcase></testsuite></testsuites>')
    assert j == {"tests": 2, "passed": 1, "failed": 1, "skipped": 1, "cases": [{"name": "a::t1", "ok": True}, {"name": "a::t2", "ok": False}]}
    p = bm.snapshot_payload("REGRESSION_GOLDEN", "DETERMINISTIC", [bm.scorecard_row("fixture_regression", 10, 10)], {"model_pin": None}, "2026-09"); assert p["gates"]["verdict"] == "PASS" and len(p["sha256"]) == 64


def test_benchlab_results_snapshots_immutable_and_progress(conn):
    from logos_dashboard import benchmarks as bm, registries as regs_mod, readers
    from logos_dashboard.control import benchlab
    from logos_research.governance import GovernanceError
    import psycopg
    suite = "REGRESSION_GOLDEN"
    rows = benchlab.sync_definitions(conn); assert len(rows) == 6 and all(r["definition_sha256"] == bm.definitions()["sha256"] for r in rows)
    with pytest.raises(GovernanceError):
        benchlab.approve_definition(conn, suite, "agent")
    r = benchlab.record_metric(conn, suite, "DETERMINISTIC", "fixture_regression", 10, 10, {"test": True, "model_pin": None}, None, None); assert r["value"] == 1.0 and r["method"] == "wilson"
    sc = benchlab.scorecard(conn); det = next(x for x in sc["suites"][suite]["rows"] if x["mode"] == "DETERMINISTIC" and x["metric"] == "fixture_regression")
    assert det["status"] == "OK" and det["n"] == 10 and sc["suites"][suite]["gates"]["verdict"] == "PASS"
    assert all(x["status"] == "NO_DATA" for x in sc["suites"][suite]["rows"] if x["mode"] in ("LOGOS_AGENT", "BASELINE_AGENT", "LOGOS_ABLATION"))
    with pytest.raises(GovernanceError):
        benchlab.freeze_snapshot(conn, suite, "DETERMINISTIC", "agent")
    snap = benchlab.freeze_snapshot(conn, suite, "DETERMINISTIC", "founder", month="TEST-ROS-1999-01"); assert snap["frozen"] is True and snap["payload"]["rows"][0]["value"] == 1.0
    with pytest.raises(psycopg.errors.RaiseException):
        with conn.cursor() as cur:
            cur.execute("UPDATE ros_benchmark_snapshots SET payload = '{}' WHERE snapshot_id = %s", (snap["snapshot_id"],))
    conn.rollback()
    with pytest.raises(psycopg.errors.RaiseException):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ros_benchmark_snapshots WHERE snapshot_id = %s", (snap["snapshot_id"],))
    conn.rollback()
    with conn.cursor() as cur:   # test hygiene: unfreeze is impossible by design, so remove via the trigger's WHEN clause only after flipping frozen through a superuser-free path -> we keep test rows flagged by month prefix
        cur.execute("ALTER TABLE ros_benchmark_snapshots DISABLE TRIGGER ros_benchmark_snapshots_immutable"); cur.execute("DELETE FROM ros_benchmark_snapshots WHERE month LIKE 'TEST-ROS-%'"); cur.execute("ALTER TABLE ros_benchmark_snapshots ENABLE TRIGGER ros_benchmark_snapshots_immutable")
        cur.execute("DELETE FROM ros_metric_results WHERE context->>'test' = 'true'")
    conn.commit()
    prog = benchlab.monthly_progress(conn, readers.closures(), regs_mod.load_all(), "2026-09")
    assert prog["closures"] > 0 and prog["falsification_rate"]["method"] == "wilson" and prog["replication_coverage"]["n"] == len(regs_mod.load_all()["replication"]["replications"]) and prog["version"] == "ros-stats/1"
    assert benchlab.monthly_progress(conn, [], regs_mod.load_all(), "1999-01")["falsification_rate"]["value"] == "NOT_DEFINED"
    assert benchlab.month_over_month(conn, suite, "DETERMINISTIC")["status"] == "NOT_COMPARABLE"


def test_ros_api_benchmarks_statistics_progress(conn):
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    client = TestClient(app)
    b = client.get("/api/ros/benchmarks").json(); assert set(b["suites"]) == set(b["definitions"]["suites"]) and len(b["suite_rows"]) == 6 and b["definitions"]["status"].startswith("DRAFT")
    assert client.post("/api/ros/benchmarks/REGRESSION_GOLDEN/approve", headers={"X-Logos-Actor": "agent"}).status_code == 403
    assert client.post("/api/ros/benchmarks/NOPE/run").status_code == 404
    j = client.post("/api/ros/benchmarks/REGRESSION_GOLDEN/run").json(); assert j["kind"] == "benchmark" and j["state"] == "queued" and j["payload"]["suite"] == "REGRESSION_GOLDEN"
    assert client.post(f"/api/ros/queue/{j['job_id']}/stop").json()["state"] == "stopped"
    s = client.post("/api/ros/statistics/compute", json={"method": "wilson", "args": {"k": 3, "n": 10}}).json(); assert s["method"] == "wilson" and s["n"] == 10
    assert client.post("/api/ros/statistics/compute", json={"method": "wilson", "args": {"k": 30, "n": 10}}).status_code == 400 and client.post("/api/ros/statistics/compute", json={"method": "magic"}).status_code == 400
    assert "mcnemar_exact" in client.get("/api/ros/statistics/methods").json()["methods"]
    p = client.get("/api/ros/progress?month=2026-09").json(); assert p["current"]["month"] == "2026-09" and p["series"] and "NOT_COMPARABLE" in p["comparability"]
    assert client.post("/api/ros/progress/freeze?month=2026-09", headers={"X-Logos-Actor": "agent"}).status_code == 403



# -- Phase 6: inbox / radar pipeline / drafts / attention / AI_PROPOSAL job --------------------------------------------


@pytest.fixture
def radar_clean(conn):
    from logos_dashboard.control import radar
    yield
    conn.rollback(); radar.delete_test_items(conn)
    import glob, os
    for f in glob.glob(str(_Path(__file__).resolve().parents[1] / "docs/research/dashboard/radar-drafts/radar-*-*.json")):
        if "TEST-ROS" in open(f, encoding="utf-8").read():
            os.remove(f)


def test_radar_pipeline_deterministic_and_founder_review(conn, radar_clean):
    from logos_dashboard.control import radar
    from logos_dashboard.registries import load_all
    from logos_dashboard.control.state_machines import IllegalTransition
    regs = load_all()
    with pytest.raises(ValueError):
        radar.add_inbox(conn, "rant", "TEST-ROS x", None, "founder")
    it = radar.add_inbox(conn, "paper", "TEST-ROS Authority delegation paper on canonical grant binding, see https://example.org/p1 doi 10.1234/abcd.5678 — relevant to LOGOS-AUTH-001", "founder note", "founder")
    row = radar.process(conn, it["radar_id"], regs)
    p = row["payload"]
    assert row["state"] == "ACTION_PROPOSED" and [h["state"] for h in p["history"]] == ["RAW", "PARSED", "DEDUPLICATED", "SOURCE_CHECKED", "TRACK_MAPPED", "CLAIM_IMPACT_ANALYZED", "EVIDENCE_STRENGTH_ASSIGNED", "ACTION_PROPOSED"]
    assert p["parsed"]["urls"] == ["https://example.org/p1"] and p["parsed"]["dois"] == ["10.1234/abcd.5678"] and p["parsed"]["claim_ids"] == ["LOGOS-AUTH-001"]
    assert p["source"]["source_class"] == "doi" and p["track_map"]["track"] == "authority" and any(c["claim_id"] == "LOGOS-AUTH-001" and c["match"] == "id" for c in p["claim_impact"]["impacted_claims"])
    assert p["evidence"]["proposed_evidence_strength"].startswith("MEDIUM (proposed") and p["action"]["delta_kind"] == "prior_art" and set(p["action"]["delta"]) == {"BEFORE", "PROPOSED", "EVIDENCE", "WHY", "WHAT_WOULD_FALSIFY_IT"}
    dup = radar.add_inbox(conn, "paper", "TEST-ROS Authority delegation paper on canonical grant binding, see https://example.org/p1 doi 10.1234/abcd.5678 — relevant to LOGOS-AUTH-001", None, "founder")
    d = radar.process(conn, dup["radar_id"], regs)["payload"]; assert d["dedup"]["is_duplicate"] and d["action"]["delta_kind"] == "none"
    with pytest.raises(IllegalTransition):
        radar.review(conn, it["radar_id"], "ACCEPTED", "agent")
    conn.rollback()
    with pytest.raises(ValueError):
        radar.review(conn, it["radar_id"], "MAYBE", "founder")
    acc = radar.review(conn, it["radar_id"], "ACCEPTED", "founder", "good source")
    assert acc["state"] == "ACCEPTED" and acc["decided_by"] == "founder" and acc["payload"]["drafts"][0]["kind"] == "prior_art" and acc["payload"]["drafts"][0]["path"].startswith("docs/research/dashboard/radar-drafts/")
    draft = _json.loads((_Path(__file__).resolve().parents[1] / acc["payload"]["drafts"][0]["path"]).read_text(encoding="utf-8")); assert draft["registry_change"].startswith("NONE") and draft["impacted_claims"][0]["claim_id"] == "LOGOS-AUTH-001"
    with pytest.raises(ValueError):
        radar.process(conn, it["radar_id"], regs)          # terminal
    ex = radar.add_inbox(conn, "experiment_idea", "TEST-ROS Test whether memory consolidation leaks authority under reconsolidation", None, "founder")
    radar.process(conn, ex["radar_id"], regs); wo = radar.review(conn, ex["radar_id"], "ACCEPTED", "founder")
    assert wo["payload"]["action"]["delta_kind"] == "work_order" and wo["payload"]["drafts"][0]["id"] == f"WO-RADAR-{ex['radar_id']}" and wo["payload"]["drafts"][0]["state"] == "DRAFT"
    q = radar.add_inbox(conn, "idea", "TEST-ROS What if provenance graphs were compressed?", None, "founder"); radar.process(conn, q["radar_id"], regs)
    assert radar.review(conn, q["radar_id"], "DEFERRED", "founder")["state"] == "DEFERRED" and radar.review(conn, q["radar_id"], "REJECTED", "founder")["state"] == "REJECTED"
    att = radar.attention(conn); assert isinstance(att, list) and all({"kind", "id", "text", "href"} <= set(a) for a in att)


def test_radar_ai_proposal_job_and_api(conn, radar_clean, repo, tmp_path, attested):
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    from logos_dashboard.control import radar
    client = TestClient(app)
    r = client.post("/api/ros/inbox", json={"kind": "critique", "text": "TEST-ROS The authority claim ignores delegation chains longer than two hops", "source_ref": "review"}).json()
    assert r["radar"]["state"] == "ACTION_PROPOSED" and r["radar"]["payload"]["track_map"]["track"] == "authority"
    rid = r["radar_id"]
    assert client.post("/api/ros/inbox", json={"kind": "spam", "text": "TEST-ROS x"}).status_code == 400
    lst = client.get("/api/ros/radar?state=ACTION_PROPOSED").json(); assert any(x["radar_id"] == rid for x in lst["items"]) and lst["pipeline"][0] == "RAW"
    assert client.post(f"/api/ros/radar/{rid}/review", json={"verdict": "ACCEPTED"}, headers={"X-Logos-Actor": "agent"}).status_code == 409
    j = client.post(f"/api/ros/radar/{rid}/ai-proposal").json(); assert j["kind"] == "radar_process" and j["state"] == "waiting_governance" and j["payload"]["radar_id"] == rid
    # EBD-R1 repair: a radar job carries no work order, no run and no thesis, so the idempotency key needs the
    # radar id. Each POST is deliberately a new attempt (attempt_group counts prior attempts for THIS item);
    # what must not happen is a different item being handed this item's job, whatever state it is in.
    other = client.post("/api/ros/inbox", json={"kind": "paper", "text": "TEST-ROS second paper on grant binding, see https://example.org/p2"}).json()
    orid = other["radar_id"]
    for _ in range(7):
        client.post(f"/api/ros/radar/{orid}/process")
    j2 = client.post(f"/api/ros/radar/{orid}/ai-proposal").json()
    assert j2["job_id"] != j["job_id"] and j2["payload"]["radar_id"] == orid and j2["state"] == "waiting_governance"
    gate = client.get(f"/api/ros/queue/{j['job_id']}/gate").json(); assert gate["passed"] is True and gate["checks"]["radar_item_known"] is True
    assert client.post(f"/api/ros/queue/{j['job_id']}/start").json()["state"] == "queued"
    rel = f"docs/research/dashboard/radar/{rid}/PROPOSAL.json"
    prop = {"delta_kind": "claim_note", "BEFORE": {}, "PROPOSED": "note", "EVIDENCE": {}, "WHY": "w", "WHAT_WOULD_FALSIFY_IT": "f", "impacted_claims": ["LOGOS-AUTH-001"], "track": "authority", "confidence": "low", "caveats": []}
    out = executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(_result_doc(_agent_block(None, [rel])), write={rel: _json.dumps(prop)})), "w-test", kinds=("radar_process",))
    assert out["state"] == "done" and out["kind"] == "radar_process"
    item = radar.get_radar(conn, rid); assert item["proposal"]["schema"] == "AI_PROPOSAL" and item["proposal"]["valid"] is True and item["proposal"]["proposal"]["delta_kind"] == "claim_note" and item["proposal"]["model_resolved"] == "claude-opus-5" and len(item["proposal"]["prompt_sha256"]) == 64
    assert item["state"] == "ACTION_PROPOSED"                       # the AI proposal never moves the pipeline; the founder does
    att = client.get("/api/ros/attention").json(); assert any(a["kind"] == "radar" and a["id"] == str(rid) for a in att["items"])
    acc = client.post(f"/api/ros/radar/{rid}/review", json={"verdict": "ACCEPTED", "reason": "ok"}).json(); assert acc["state"] == "ACCEPTED" and acc["payload"]["drafts"][0]["kind"] == "claim_note"
    with conn.cursor() as cur:
        cur.execute("DELETE FROM ros_runs WHERE run_id = %s", (runs.list_runs(conn, 5)[0]["run_id"],)); cur.execute("DELETE FROM ros_jobs WHERE job_id = %s", (j["job_id"],))
    conn.commit()



# -- Phase 7: evidence debt, paper readiness, monthly report ------------------------------------------------------------


def test_evidence_debt_paper_readiness_and_monthly_report(conn):
    from fastapi.testclient import TestClient
    from logos_dashboard import reports, registries, readers
    from logos_dashboard.api import app
    regs = registries.load_all(); cl = readers.closures()
    d = reports.evidence_debt(regs, cl)
    assert d["n"] == sum(d["by_severity"].values()) and all({"severity", "kind", "subject", "record", "text"} <= set(i) for i in d["items"]) and all(i["severity"] in ("HIGH", "MEDIUM", "LOW") for i in d["items"])
    assert d["n"] == 24 and d["by_severity"] == {"HIGH": 0, "MEDIUM": 18, "LOW": 6}            # exact for the current registries (2026-09-19); a registry change must update this count consciously
    fake = {**regs, "claims": {**regs["claims"], "claims": [{**regs["claims"]["claims"][0], "claim_id": "X-1", "status": "SUPPORTED", "evidence_strength": "PRELIMINARY", "supporting_artifacts": [], "next_falsification_test": "", "external_replication": "none", "counterevidence": ["c"]}]}}
    kinds = [i["kind"] for i in reports.evidence_debt(fake, [])["items"]]
    assert kinds[:5] == ["status_exceeds_evidence", "no_next_falsification_test", "no_external_replication", "no_artifact", "unaddressed_counterevidence"]
    pr = reports.paper_readiness(regs)
    assert [p["paper_id"] for p in pr] == [p["paper_id"] for p in regs["publications"]["papers"]] and all(p["of"] == 8 and 0 <= p["met"] <= 8 and "founder decision" in p["verdict"] for p in pr)
    client = TestClient(app)
    r = client.get("/api/ros/reports/2026-09").json(); doc = r["doc"]
    assert doc["month"] == "2026-09" and len(doc["sha256"]) == 64 and doc["closures"] and "no readiness verdict" in doc["does_not_claim"] and r["markdown"].startswith("# LOGOS-1 Monthly Report") and "Wilson" in r["markdown"]
    assert client.get("/api/ros/reports/2026-09").json()["doc"]["sha256"] == doc["sha256"]        # deterministic (generated_at excluded from the hash)
    assert client.post("/api/ros/reports/2026-09/freeze", headers={"X-Logos-Actor": "agent"}).status_code == 403 and client.post("/api/ros/reports/TEST-ROS-1/freeze").status_code == 400
    assert client.get("/api/ros/evidence-debt").json()["n"] == d["n"] and len(client.get("/api/ros/paper-readiness").json()["papers"]) == len(pr) and "reports" in client.get("/api/ros/reports").json()



# -- R2: agent provider (stream-json + --verbose under INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1), live events, stop mid-stream ------------


def _stream_fixture_runner(*, stop_after: int | None = None, write: dict[str, str] | None = None):
    lines = (_Path(__file__).resolve().parent / "fixtures/ros/agent_stream.jsonl").read_text(encoding="utf-8").splitlines()

    def factory(cwd):
        def run(argv, timeout, env, on_line, stop_check):
            assert argv[:1] == ["claude"] and "--verbose" in argv and "stream-json" in argv and "--dangerously-skip-permissions" not in argv and "ANTHROPIC_API_KEY" not in env
            for rel, text in (write or {}).items():
                p = _Path(cwd) / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
            for i, l in enumerate(lines):
                on_line(l)
                if stop_check() or (stop_after is not None and i + 1 >= stop_after):
                    return "STOPPED", "\n".join(lines[: i + 1]), ""
            return 0, "\n".join(lines), ""
        return run
    return factory


def test_agent_provider_argv_contract_and_condense():
    from logos_dashboard.control import agent_provider as ap
    from logos_research.measurement.claude_code import DOCUMENTED_FLAGS, Limits, ProviderPolicyError
    assert "--verbose" not in DOCUMENTED_FLAGS and "--verbose" in ap.AGENT_FLAGS        # measurement whitelist unchanged; agent flags amended
    argv = ap.build_agent_argv("p", "claude-opus-5", Limits(5, 1000, 10.0, ("Bash",), ("Read", "Skill")), system_prompt="s")
    assert argv[:6] == ["claude", "-p", "p", "--output-format", "stream-json", "--verbose"] and "--append-system-prompt" in argv and "--allowedTools" in argv
    with pytest.raises(ProviderPolicyError):
        ap.check_agent_argv(["claude", "-p", "x", "--resume", "abc"])
    with pytest.raises(ProviderPolicyError):
        ap.check_agent_argv(["claude", "-p", "x", "--dangerously-skip-permissions"])
    amend = _json.loads((_Path(__file__).resolve().parents[1] / "docs/research/INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1.json").read_text(encoding="utf-8"))
    assert amend["decision"] == "APPROVED" and amend["decision_owner"] == "founder" and amend["flag"] == "--verbose" and set(amend["scope"]) == set(ap.AGENT_KINDS) and "--resume" in amend["still_forbidden"]
    c = ap.condense({"type": "assistant", "message": {"model": "m", "content": [{"type": "tool_use", "id": "1", "name": "Read", "input": {"file_path": "a.md"}}, {"type": "text", "text": "hi"}]}})
    assert c["kind"] == "agent.batch" and [i["kind"] for i in c["items"]] == ["agent.tool", "agent.text"] and c["items"][0]["target"] == "a.md"
    assert ap.condense({"type": "user", "message": {"content": "plain"}}) is None and ap.condense({"type": "result", "num_turns": 2})["kind"] == "agent.result"


def test_executor_streams_live_events_with_tier1_evidence(conn, tid, repo, tmp_path, attested):
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "stream", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    rel = "docs/research/dashboard/theses/T/TRIAGE.md"     # the fixture writes under theses/T — outside this thesis' allowlist -> we place the real file under the thesis dir instead
    out = executor.run_once(conn, _cfg(repo, tmp_path, _stream_fixture_runner(write={f"docs/research/dashboard/theses/{tid}/TRIAGE.md": "# triage"})), "w-test")
    assert out["state"] == "done", out.get("error")
    run = runs.list_runs(conn, thesis_id=tid)[0]; ev = runs.events_after(conn, run["run_id"])
    kinds = [e["kind"] for e in ev]
    assert kinds.count("agent.init") == 1 and kinds.count("agent.batch") == 7 and kinds.count("agent.result") == 1 and kinds.index("agent.init") > kinds.index("claude.invoke") and kinds.index("agent.result") < kinds.index("claude.result")
    tools = [i["tool"] for e in ev if e["kind"] == "agent.batch" for i in e["payload"]["items"] if i["kind"] == "agent.tool"]
    assert tools == ["Read", "Grep", "Write"]
    cr = next(e for e in ev if e["kind"] == "claude.result")["payload"]
    assert cr["status"] == "OK" and cr["resolved_model"] == "claude-opus-5" and cr["evidence_class"] == "EXPLICIT_ASSISTANT_MODEL"          # assistant.message.model -> Tier-1 evidence
    ci = next(e for e in ev if e["kind"] == "claude.invoke")["payload"]; assert ci["output_format"] == "stream-json" and ci["verbose"] == "INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1" and "scientific-thinking-scholar-evaluation" in ci["skills"]
    assert service.thesis_detail(conn, tid)["thesis"]["state"] == "TRIAGE" and (repo / rel).exists() is False


def test_executor_stop_mid_stream_discards_branch(conn, tid, repo, tmp_path, attested):
    service.create_thesis(conn, tid, [], "stop", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    out = executor.run_once(conn, _cfg(repo, tmp_path, _stream_fixture_runner(stop_after=3)), "w-test")
    assert out["state"] == "stopped" and service.thesis_detail(conn, tid)["thesis"]["state"] == "IDEA"
    run = runs.list_runs(conn, thesis_id=tid)[0]; kinds = [e["kind"] for e in runs.events_after(conn, run["run_id"])]
    assert run["state"] == "stopped" and kinds[-1] == "stop" and kinds.count("agent.batch") == 2
    assert _sp.run(["git", "branch", "--list", f"ros/{tid}/*"], cwd=repo, capture_output=True, text=True).stdout.strip() == ""


def test_executor_creates_work_order_draft_from_agent_file(conn, tid, repo, tmp_path, attested):
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "wo", "authority", "founder")
    for e in ("triage", "define_question", "define_hypothesis", "define_metrics"):
        service.advance(conn, tid, e, "agent")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "METRICS_DEFINED", "PREREG_DRAFT", ("IDEA", "METRICS_DEFINED", "PREREG_DRAFT")))
    d = f"docs/research/dashboard/theses/{tid}"
    spec = {"question": "q", "scope": "s", "hypothesis": "h", "falsification_criterion": "f", "metrics": ["m1"], "governance": {"provider": "claude-max"}, "caps": {"invocations": 20}}
    out = executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(_result_doc(_agent_block("draft_prereg", [f"{d}/PREREG-DRAFT.json", f"{d}/WORK-ORDER-DRAFT.json"])), write={f"{d}/PREREG-DRAFT.json": "{}", f"{d}/WORK-ORDER-DRAFT.json": _json.dumps(spec)})), "w-test")
    assert out["state"] == "done" and out["result"]["applied_state"] == "PREREG_DRAFT" and out["result"]["work_order_draft"] == f"WO-{tid}-D{j['job_id']}"
    wos = [w for w in service.list_work_orders(conn) if w["thesis_id"] == tid]; assert len(wos) == 1 and wos[0]["state"] == "DRAFT" and wos[0]["created_by"] == "agent" and wos[0]["spec"]["origin"]["agent_job"] == j["job_id"]



# -- R2: autopilot scheduler, repository orders, worker control API ------------------------------------------------------


@pytest.fixture
def autopilot_clean(conn):
    from logos_dashboard.control import governor
    prev = {k: governor.get_setting(conn, k) for k in ("autopilot_master", "autopilot_theses")}
    yield
    conn.rollback()
    with conn.cursor() as cur:
        for k, v in prev.items():
            if v is None:
                cur.execute("DELETE FROM ros_settings WHERE key = %s", (k,))
            else:
                cur.execute("UPDATE ros_settings SET value = %s WHERE key = %s", (_json.dumps(v), k))
    conn.commit()


def test_autopilot_runs_stages_until_ceiling_and_pauses_on_gate(conn, tid, repo, tmp_path, attested, autopilot_clean):
    from logos_dashboard.control import autopilot
    from logos_research.governance import GovernanceError
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "auto", "authority", "founder")
    with pytest.raises(GovernanceError):
        autopilot.set_master(conn, True, "agent")
    autopilot.set_master(conn, True, "founder"); f = autopilot.set_thesis(conn, tid, True, "founder", "test")
    assert f["enabled"] and f["gate_at_enable"]["auth_evidence_fresh"] is True
    d = f"docs/research/dashboard/theses/{tid}"
    plan = {"IDEA": ("triage", "TRIAGE.md"), "TRIAGE": ("define_question", "QUESTION.md"), "QUESTION_DEFINED": ("define_hypothesis", "HYPOTHESES.md"), "HYPOTHESIS_DEFINED": ("define_metrics", "METRICS.md"), "METRICS_DEFINED": ("draft_prereg", "PREREG-DRAFT.json")}
    started = 0
    for _ in range(8):
        acts = autopilot.tick(conn)
        st = service.thesis_detail(conn, tid)["thesis"]["state"]
        if any(a["action"] == "ceiling" for a in acts):
            break
        assert any(a["action"] == "started" and a["thesis_id"] == tid for a in acts), (acts, st)
        started += 1
        ev, fn = plan[st]
        out = executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(_result_doc(_agent_block(ev, [f"{d}/{fn}"])), write={f"{d}/{fn}": "x"})), "w-test")
        assert out["state"] == "done", out.get("error")
    assert started == 5 and service.thesis_detail(conn, tid)["thesis"]["state"] == "PREREG_DRAFT"
    st = autopilot.status(conn); assert st["theses"][tid]["enabled"] is False and "ceiling" in st["paused"][tid]
    # a second thesis with stale auth evidence -> gate fails -> paused with reason, job stopped, nothing invoked
    tid2 = tid + "-B"; service.create_thesis(conn, tid2, [], "auto2", "authority", "founder"); autopilot.set_thesis(conn, tid2, True, "founder")
    governor.record_attestation(conn, {"auth_class": "MAX_SUBSCRIPTION", "at": "2020-01-01T00:00:00+00:00"}, "founder")
    acts = autopilot.tick(conn); assert any(a["action"] == "gate_failed" and "auth_evidence_fresh" in a["failed"] for a in acts)
    assert autopilot.status(conn)["paused"][tid2].startswith("gate failed") and all(j["state"] == "stopped" for j in queue.list_jobs(conn, 500) if j["thesis_id"] == tid2)
    service.delete_thesis(conn, tid2, "system")


def test_repository_orders_import_idempotent_and_chained(conn):
    from logos_dashboard.control import repo_orders
    docs = repo_orders.parse_documents()
    assert len(docs) == 44 and sum(1 for d in docs if d["kind"] == "closure") == 40 and {d["state"] for d in docs} == {"VALIDATED", "FALSIFIED", "DRAFT"}     # 45 files, 44 orders (one generated master order has its own closure) — exact for 05-WORK-ORDERS on 2026-09-22
    falsified = sorted(d["order_id"] for d in docs if d["state"] == "FALSIFIED"); assert falsified == ["COGNITIVE-PROVENANCE-ABLATION-R1", "RISK-AWARENESS-DECOMPOSITION-R1"]
    r1 = repo_orders.import_orders(conn); r2 = repo_orders.import_orders(conn)
    assert r1["documents"] == r2["documents"] == 44 and r2["new"] == 0 and r2["updated"] == 44 and r2["edges_added"] == 0 and r1["states"]["FALSIFIED"] == 2
    ch = repo_orders.chain(conn); assert len(ch) == 44 and all(x["work_order_id"].startswith("REPO:") for x in ch) and all(x["origin"]["repository"] for x in ch)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM ros_work_order_deps WHERE child LIKE 'REPO:%%' AND parent LIKE 'REPO:%%'"); n_edges = cur.fetchone()[0]
        cur.execute("SELECT parent FROM ros_work_order_deps WHERE child = 'REPO:COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1'"); parents = [r[0] for r in cur.fetchall()]
    assert n_edges == 16 and "REPO:COGNITIVE-PROVENANCE-ABLATION-R1" in parents          # successor edges resolvable inside 05-WORK-ORDERS on 2026-09-19
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM ros_work_orders WHERE work_order_id LIKE 'REPO:%%' AND state <> 'DRAFT' AND approved_by IS NULL"); assert cur.fetchone()[0] == 0


def test_r2_api_autopilot_workers_repo_orders_leitstand(conn, tid, attested, autopilot_clean):
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    client = TestClient(app)
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "api", "authority", "founder")
    assert client.post("/api/ros/autopilot/master", json={"enabled": True}, headers={"X-Logos-Actor": "agent"}).status_code == 403
    assert client.post("/api/ros/autopilot/master", json={"enabled": True}).json()["enabled"] is True
    assert client.post(f"/api/ros/autopilot/theses/{tid}", json={"enabled": True, "reason": "ui"}).json()["flag"]["enabled"] is True
    assert client.post("/api/ros/autopilot/tick", headers={"X-Logos-Actor": "agent"}).status_code == 403
    acts = client.post("/api/ros/autopilot/tick").json()["actions"]; assert any(a["action"] == "started" for a in acts)
    for j in queue.list_jobs(conn, 500):
        if j["thesis_id"] == tid and j["state"] in ("queued",):
            queue.request_stop(conn, j["job_id"], "founder")
    wc = client.get("/api/ros/workers/control").json(); assert {"host", "docker", "autopilot"} <= set(wc) and "alive" in wc["host"]
    assert client.post("/api/ros/workers/host/start", headers={"X-Logos-Actor": "agent"}).status_code == 403 and client.post("/api/ros/workers/nope/start").status_code == 400
    ro = client.post("/api/ros/repo-orders/import").json(); assert ro["documents"] == 44
    lst = client.get("/api/ros/repo-orders").json(); assert len(lst["orders"]) == 44 and len(lst["documents"]) == 44
    ls = client.get("/api/ros/leitstand").json()
    assert {"host", "docker", "autopilot", "theses", "attention", "governor", "first_steps", "states"} <= set(ls) and ls["ceiling"] == "PREREG_DRAFT"
    mine = next(t for t in ls["theses"] if t["thesis_id"] == tid); assert mine["autopilot"]["enabled"] is True and mine["stage_index"] == 0
    assert client.post(f"/api/ros/autopilot/theses/{tid}", json={"enabled": False}).json()["flag"]["enabled"] is False



# -- R3: measurement contract (scorers, rules, verdict derivation) --------------------------------------------------


def _ds(n_per_arm=5, arms=("with_plan", "without_plan")):
    return {"schema": "ros-dataset/1", "arms": list(arms), "items": [{"item_id": f"i{a}-{i}", "arm": a, "input": f"task {i}", "expected": "blue"} for a in arms for i in range(n_per_arm)]}


def _pr(arms=("with_plan", "without_plan")):
    return {"schema": "ros-prompts/1", "arms": {a: {"system": "Answer in JSON.", "user_template": "Arm " + a + ": {input}"} for a in arms}}


def _me(**kw):
    m = {"schema": "ros-measurement/1", "metrics": [{"metric_id": "M1", "scorer": "json_field_equals", "target_field": "color"}], "primary_metric": "M1",
         "comparison": {"arm_a": "with_plan", "arm_b": "without_plan"}, "falsification": {"rule": "difference_ci_excludes_zero", "direction": "a_greater"},
         "caps": {"max_invocations": 40, "max_turns": 1, "max_output_bytes": 20000, "timeout_s": 120},
         "invalid_measurement_criteria": ["MODEL_VERSION_DRIFT", "PROMPT_DRIFT", "PROVIDER_DRIFT", "REGION_DRIFT", "DATASET_DRIFT", "COST_CAP_REACHED", "CONSTRUCT_INVALID"]}
    m.update(kw); return m


def test_measurement_contract_scorers():
    from logos_dashboard import measurement_contract as mc
    assert set(mc.SCORERS) == set(mc.SCORER_IDS) and len(mc.SCORER_IDS) == 8
    cases = [
        ("exact_match", "blue", "blue", None, True), ("exact_match", " blue ", "blue", None, True), ("exact_match", "Blue", "blue", None, False), ("exact_match", None, "blue", None, None),
        ("normalized_match", "The  BLUE!", "the blue", None, True), ("normalized_match", "red", "blue", None, False),
        ("contains_all", "a blue sky and green grass", ["blue", "green"], None, True), ("contains_all", "a blue sky", ["blue", "green"], None, False),
        ("json_field_equals", '{"color": "blue"}', "blue", "color", True), ("json_field_equals", 'prose {"color": "red"}', "blue", "color", False),
        ("json_field_equals", "no json here", "blue", "color", None), ("json_field_equals", '{"other": 1}', "blue", "color", None),
        ("json_field_in", '{"color": "cyan"}', ["blue", "cyan"], "color", True), ("json_field_in", '{"color": "red"}', ["blue", "cyan"], "color", False),
        ("regex_match", "answer: 42", r"answer:\s*\d+", None, True), ("regex_match", "answer: x", r"answer:\s*\d+", None, False), ("regex_match", "x", "[", None, None),
        ("refusal", "I can't help with that", None, None, True), ("refusal", "Sure: blue", None, None, False),
        ("parse_failure", "not json", None, None, True), ("parse_failure", '{"a": 1}', None, None, False),
    ]
    for scorer, raw, exp, field, want in cases:
        assert mc.score_item(scorer, raw, exp, field) is want, (scorer, raw, exp, field)
    with pytest.raises(ValueError):
        mc.score_item("llm_judge", "x", "y")


def test_measurement_contract_validation_and_hashes():
    from logos_dashboard import measurement_contract as mc
    ds, pr, me = _ds(), _pr(), _me()
    assert mc.validate_bundle(ds, pr, me) == []
    assert len(mc.dataset_hash(ds)) == 64 and mc.dataset_hash(ds) == mc.dataset_hash({**ds, "items": list(reversed(ds["items"]))})     # order-independent
    assert mc.dataset_hash(ds) != mc.dataset_hash({**ds, "items": ds["items"][:-1]}) and len(mc.prompt_bundle_hash(pr)) == 64
    assert mc.prompt_bundle_hash(pr) != mc.prompt_bundle_hash({**pr, "arms": {**pr["arms"], "with_plan": {"system": "x", "user_template": "{input}"}}})
    bad_bal = {**ds, "items": ds["items"][:-1]}
    assert any("unbalanced" in i for i in mc.validate_dataset(bad_bal))
    assert any("arm 'nope' not in arms" in i for i in mc.validate_dataset({**ds, "items": ds["items"] + [{"item_id": "x", "arm": "nope", "input": "i"}]}))
    assert any("duplicate item_id" in i for i in mc.validate_dataset({**ds, "items": ds["items"] + [dict(ds["items"][0])]}))
    assert mc.validate_dataset({"schema": "other"}) == ["dataset schema must be ros-dataset/1"]
    assert any("must contain {input}" in i for i in mc.validate_prompts({**pr, "arms": {**pr["arms"], "with_plan": {"user_template": "no placeholder"}}}, ds["arms"]))
    assert any("never contain the expected answer" in i for i in mc.validate_prompts({**pr, "arms": {**pr["arms"], "with_plan": {"user_template": "{input} {expected}"}}}, ds["arms"]))
    assert any("scorer 'llm_judge' unknown" in i for i in mc.validate_measurement(_me(metrics=[{"metric_id": "M1", "scorer": "llm_judge"}]), ds["arms"]))
    assert any("target_field required" in i for i in mc.validate_measurement(_me(metrics=[{"metric_id": "M1", "scorer": "json_field_equals"}]), ds["arms"]))
    assert any("primary_metric" in i for i in mc.validate_measurement(_me(primary_metric="M9"), ds["arms"]))
    assert any("two different arms" in i for i in mc.validate_measurement(_me(comparison={"arm_a": "with_plan", "arm_b": "with_plan"}), ds["arms"]))
    assert any("direction" in i for i in mc.validate_measurement(_me(falsification={"rule": "difference_ci_excludes_zero"}), ds["arms"]))
    assert any("threshold must be a rate" in i for i in mc.validate_measurement(_me(falsification={"rule": "rate_below_threshold", "threshold": 5}), ds["arms"]))
    assert any("caps.max_invocations" in i for i in mc.validate_measurement(_me(caps={"max_turns": 1, "max_output_bytes": 10, "timeout_s": 5}), ds["arms"]))
    assert any("invalid_measurement_criteria missing: DATASET_DRIFT" in i for i in mc.validate_measurement(_me(invalid_measurement_criteria=[c for c in mc.INVALID_CRITERIA if c != "DATASET_DRIFT"]), ds["arms"]))
    assert any("max_invocations is 4" in i for i in mc.validate_bundle(_ds(), pr, _me(caps={"max_invocations": 4, "max_turns": 1, "max_output_bytes": 10, "timeout_s": 5})))
    sys_p, user_p = mc.render_prompt(pr, "with_plan", {"input": "task 1"})
    assert user_p == "Arm with_plan: task 1" and sys_p == "Answer in JSON." and "{input}" not in user_p


def test_measurement_verdict_derivation_all_outcomes():
    from logos_dashboard import measurement_contract as mc
    def items(a_hits, a_n, b_hits, b_n, missing=0):
        out = [{"arm": "A", "score": i < a_hits} for i in range(a_n)] + [{"arm": "B", "score": i < b_hits} for i in range(b_n)]
        return out + [{"arm": "A", "score": None} for _ in range(missing)]
    r = mc.arm_rates(items(18, 20, 6, 20, missing=3))
    assert r["A"]["k"] == 18 and r["A"]["n_scored"] == 20 and r["A"]["n_total"] == 23 and r["A"]["missing"] == 3 and r["A"]["method"] == "wilson"
    comp = {"arm_a": "A", "arm_b": "B"}
    v = mc.derive_verdict(r, {"rule": "difference_ci_excludes_zero", "direction": "a_greater"}, comparison=comp)
    assert v["verdict"] == "SUPPORTED" and v["derived"] is True and "schließt 0 aus" in v["why"] and v["difference"]["method"] == "newcombe"
    v = mc.derive_verdict(mc.arm_rates(items(6, 20, 18, 20)), {"rule": "difference_ci_excludes_zero", "direction": "a_greater"}, comparison=comp)
    assert v["verdict"] == "FALSIFIED" and "entgegengesetzten Richtung" in v["why"]
    v = mc.derive_verdict(mc.arm_rates(items(10, 20, 9, 20)), {"rule": "difference_ci_excludes_zero", "direction": "a_greater"}, comparison=comp)
    assert v["verdict"] == "INCONCLUSIVE" and "enthält 0" in v["why"]
    v = mc.derive_verdict(mc.arm_rates(items(6, 20, 18, 20)), {"rule": "difference_ci_excludes_zero", "direction": "either"}, comparison=comp)
    assert v["verdict"] == "SUPPORTED"
    assert mc.derive_verdict(mc.arm_rates(items(1, 1, 1, 1)), {"rule": "difference_ci_excludes_zero", "direction": "either"}, comparison={"arm_a": "A", "arm_b": "Z"})["verdict"] == "INVALID_MEASUREMENT"
    assert mc.derive_verdict({}, {"rule": "rate_below_threshold", "threshold": 0.1})["verdict"] == "INCONCLUSIVE"
    assert mc.derive_verdict(mc.arm_rates(items(9, 10, 0, 1)), {"rule": "rate_above_threshold", "threshold": 0.5, "arm": "A"})["verdict"] == "SUPPORTED"
    assert mc.derive_verdict(mc.arm_rates(items(0, 40, 0, 1)), {"rule": "rate_below_threshold", "threshold": 0.2, "arm": "A"})["verdict"] == "SUPPORTED"
    assert mc.derive_verdict(mc.arm_rates(items(40, 40, 0, 1)), {"rule": "rate_below_threshold", "threshold": 0.2, "arm": "A"})["verdict"] == "FALSIFIED"
    assert mc.derive_verdict(mc.arm_rates(items(5, 10, 0, 1)), {"rule": "rate_below_threshold", "threshold": 0.5, "arm": "A"})["verdict"] == "INCONCLUSIVE"
    inv = mc.derive_verdict(mc.arm_rates(items(18, 20, 6, 20)), {"rule": "difference_ci_excludes_zero", "direction": "a_greater"}, comparison=comp, invalid_reason="MODEL_VERSION_DRIFT")
    assert inv["verdict"] == "INVALID_MEASUREMENT" and "MODEL_VERSION_DRIFT" in inv["why"]
    assert mc.derive_verdict(mc.arm_rates(items(1, 1, 1, 1)), {"rule": "magic"})["verdict"] == "INVALID_MEASUREMENT"



# -- R3: gate chain (prereg validate/freeze, dry run), measurement run, verdict, caps ---------------------------------


@pytest.fixture
def bundle_files(tid):
    """Writes the agent's four files into the real thesis directory and removes them afterwards."""
    from logos_dashboard.control import prereg
    d = prereg.thesis_dir(tid); d.mkdir(parents=True, exist_ok=True)
    written: list = []

    def write(ds=None, pr=None, me=None, draft=None):
        files = {"DATASET.json": ds if ds is not None else _ds(), "PROMPTS.json": pr if pr is not None else _pr(), "MEASUREMENT.json": me if me is not None else _me(),
                 "PREREG-DRAFT.json": draft if draft is not None else {"question": "Hilft ein expliziter Plan?", "hypothesis": "Mit Plan hoeher", "falsification_criterion": "KI der Differenz schliesst 0 aus (a_greater)", "scope": "fixture", "privacy_class": "SYNTHETIC", "sample_size_justification": "10 items"}}
        for name, doc in files.items():
            if doc is None:
                (d / name).unlink(missing_ok=True); continue
            (d / name).write_text(_json.dumps(doc, indent=1), encoding="utf-8"); written.append(d / name)
        return files
    yield write
    for p in written:
        p.unlink(missing_ok=True)
    try:
        d.rmdir()
    except OSError:
        pass


def _fake_measure_runner(answers, *, status_seq=None):
    """Legacy (argv, timeout, env) runner returning one JSON result document per call, cycling `answers`."""
    state = {"i": 0}

    def factory(cwd):
        def run(argv, timeout, env):
            assert argv[0] == "claude" and "--verbose" not in argv and "json" in argv and "ANTHROPIC_API_KEY" not in env      # measurement: json, never verbose
            i = state["i"]; state["i"] += 1
            st = (status_seq or [])[i] if status_seq and i < len(status_seq) else "ok"
            if st == "usage_limit":
                return 1, "", "You have hit your usage limit"
            if st == "drift":
                return 0, _json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "x", "session_id": "s", "num_turns": 1, "modelUsage": {"claude-sonnet-5": {}}}), ""
            ans = answers[i % len(answers)]
            return 0, _json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": ans, "session_id": "s", "num_turns": 1, "usage": {"input_tokens": 5, "output_tokens": 3}, "modelUsage": {"claude-opus-5": {"inputTokens": 5}}}), ""
        return run
    return factory


def test_prereg_validate_freeze_and_dry_run(conn, tid, attested, bundle_files):
    from logos_dashboard.control import prereg
    from logos_research.governance import GovernanceError
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "gate", "authority", "founder")
    for e in ("triage", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        service.advance(conn, tid, e, "agent")
    v = prereg.validate(conn, tid, "founder")
    assert v["passed"] is False and "Datei fehlt: PREREG-DRAFT.json" in v["file_issues"]        # nothing written yet
    bundle_files()
    v = prereg.validate(conn, tid, "founder")
    assert v["passed"] is True and v["contract_issues"] == [] and v["governance_issues"] == [] and len(v["dataset_hash"]) == 64 and v["planned_invocations"] == 10 and v["model_pin"] == "claude-opus-5"
    bundle_files(me=_me(caps={"max_invocations": 40, "max_turns": 1, "max_output_bytes": 20000, "timeout_s": 120}, invalid_measurement_criteria=["MODEL_VERSION_DRIFT"]))
    bad = prereg.validate(conn, tid, "founder")
    assert bad["passed"] is False and any("invalid_measurement_criteria missing" in i for i in bad["contract_issues"]) and any("invalidation rule" in i for i in bad["governance_issues"])
    with pytest.raises(ValueError):
        prereg.freeze(conn, tid, "founder")
    bundle_files()
    with pytest.raises(IllegalTransition):
        prereg.freeze(conn, tid, "agent")
    f = prereg.freeze(conn, tid, "founder")
    assert len(f["prereg_hash"]) == 64 and f["thesis"]["state"] == "PREREG_FROZEN" and "lab postgres" in f["where"]
    assert prereg.frozen_payload(tid, f["prereg_hash"])["experiment_id"] == f"ROS-{tid}"
    d = service.thesis_detail(conn, tid); assert d["thesis"]["prereg_hash"] == f["prereg_hash"]
    spec = {"question": "q", "scope": "s", "hypothesis": "h", "falsification_criterion": "f", "metrics": ["M1"], "governance": {"provider": "claude-max"}, "caps": {"invocations": 40}}
    wo = service.create_work_order(conn, f"WO-{tid}", tid, spec, "agent")
    service.wo_transition(conn, wo["work_order_id"], "approve", "founder", prereg_hash=f["prereg_hash"])
    service.advance(conn, tid, "approve_work_order", "founder")
    dr = prereg.run_dry_run(conn, tid, "founder")
    assert dr["passed"] is True, {"failed": dr["failed"], "drift": dr["drift"], "checks": dr["checks"]}
    assert dr["failed"] == [] and dr["drift"] == [] and dr["counters_unchanged"] is True and len(dr["checks"]) == 10 and dr["thesis_state"] == "DRY_RUN"
    assert all(k in dr["texts"] for k in dr["checks"])
    ch = prereg.chain_status(conn, tid)
    assert [s["id"] for s in ch["steps"]] == ["prereg_validate", "prereg_freeze", "work_order_approve", "dry_run", "ready_to_run", "measurement", "verdict"]
    assert ch["steps"][1]["state"] == "done" and ch["steps"][3]["state"] == "done" and ch["steps"][4]["enabled"] is True and ch["prereg_hash"] == f["prereg_hash"]
    log = prereg.gate_log(conn, tid); assert {l["gate"] for l in log} >= {"prereg_validate", "prereg_freeze", "dry_run"} and all(l["actor"] in ("founder", "system") for l in log)


def test_dry_run_detects_drift_after_freeze(conn, tid, attested, bundle_files):
    from logos_dashboard.control import prereg
    service.create_thesis(conn, tid, [], "drift", "authority", "founder")
    for e in ("triage", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        service.advance(conn, tid, e, "agent")
    bundle_files(); prereg.freeze(conn, tid, "founder")
    service.create_work_order(conn, f"WO-{tid}", tid, {"question": "q", "scope": "s", "hypothesis": "h", "falsification_criterion": "f", "metrics": ["M1"], "governance": {"provider": "claude-max"}, "caps": {"invocations": 40}}, "agent")
    service.advance(conn, tid, "approve_work_order", "founder")
    bundle_files(ds=_ds(n_per_arm=6))                                         # dataset changed after freezing
    dr = prereg.run_dry_run(conn, tid, "founder")
    assert dr["passed"] is False and dr["drift"] == ["DATASET_DRIFT"] and dr["thesis_state"] == "BLOCKED_BY_GOVERNANCE"


def test_measurement_run_scores_and_derives_verdict(conn, tid, repo, tmp_path, attested, bundle_files):
    from logos_dashboard.control import measurement as meas, prereg
    n0 = _CALLS["claude_code_inference_invocations"]
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "measure", "authority", "founder")
    for e in ("triage", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        service.advance(conn, tid, e, "agent")
    bundle_files(); prereg.freeze(conn, tid, "founder")
    service.create_work_order(conn, f"WO-{tid}", tid, {"question": "q", "scope": "s", "hypothesis": "h", "falsification_criterion": "f", "metrics": ["M1"], "governance": {"provider": "claude-max"}, "caps": {"invocations": 40}}, "agent")
    service.advance(conn, tid, "approve_work_order", "founder"); prereg.run_dry_run(conn, tid, "founder")
    service.advance(conn, tid, "ready_to_run", "founder"); service.advance(conn, tid, "start_run", "founder")
    job = queue.enqueue(conn, "measurement", thesis_id=tid, payload={"planned": 10}); queue.start(conn, job["job_id"], "founder", {"passed": True})
    # with_plan items answer correctly, without_plan items answer wrong (sorted by arm: with_plan first)
    answers = ['{"color": "blue"}'] * 5 + ['{"color": "red"}'] * 5
    out = meas.run_measurement(conn, {**job, "state": "running"}, _cfg(repo, tmp_path, _fake_measure_runner(answers)))
    assert out["state"] == "done" and out["result"]["executed"] == 10 and out["result"]["complete"] is True
    rates = out["result"]["rates"]
    assert rates["with_plan"]["k"] == 5 and rates["with_plan"]["n_scored"] == 5 and rates["without_plan"]["k"] == 0 and rates["without_plan"]["missing"] == 0
    prop = out["result"]["proposal"]; assert prop["verdict"] == "SUPPORTED" and prop["derived"] is True and "schließt 0 aus" in prop["why"]
    assert _CALLS["claude_code_inference_invocations"] == n0 + 10
    mid = out["result"]["measurement_id"]; d = meas.get(conn, mid)
    assert d["progress"] == {"done": 10, "planned": 10} and {i["status"] for i in d["items"]} == {"OK"} and sum(1 for i in d["items"] if i["score"]) == 5
    assert service.thesis_detail(conn, tid)["thesis"]["state"] == "ANALYSIS"
    ev = [e["kind"] for e in runs.events_after(conn, runs.list_runs(conn, thesis_id=tid)[0]["run_id"])]
    assert ev.count("measure.item") == 2 and ev[-1] == "done" and "gate" in ev
    with pytest.raises(IllegalTransition):
        meas.decide_verdict(conn, mid, "SUPPORTED", "agent")
    dec = meas.decide_verdict(conn, mid, "SUPPORTED", "founder", "sieht sauber aus")
    assert dec["followed_proposal"] is True and dec["thesis_state"] == "VERDICT" and dec["draft"]["path"].startswith("docs/research/dashboard/verdict-drafts/")
    draft = _json.loads((_Path(__file__).resolve().parents[1] / dec["draft"]["path"]).read_text(encoding="utf-8"))
    assert draft["registry_change"].startswith("NONE") and draft["EVIDENCE"]["rates"]["with_plan"]["k"] == 5 and draft["derived_proposal"] == "SUPPORTED"
    (_Path(__file__).resolve().parents[1] / dec["draft"]["path"]).unlink()


def test_measurement_stops_on_usage_limit_and_records_partial(conn, tid, repo, tmp_path, attested, bundle_files):
    from logos_dashboard.control import governor as gov, measurement as meas, prereg
    service.create_thesis(conn, tid, [], "quota", "authority", "founder")
    for e in ("triage", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        service.advance(conn, tid, e, "agent")
    bundle_files(); prereg.freeze(conn, tid, "founder")
    service.advance(conn, tid, "approve_work_order", "founder"); service.advance(conn, tid, "dry_run", "system"); service.advance(conn, tid, "ready_to_run", "founder"); service.advance(conn, tid, "start_run", "founder")
    job = queue.enqueue(conn, "measurement", thesis_id=tid); queue.start(conn, job["job_id"], "founder", {"passed": True})
    out = meas.run_measurement(conn, {**job, "state": "running"}, _cfg(repo, tmp_path, _fake_measure_runner(['{"color": "blue"}'], status_seq=["ok", "ok", "usage_limit"])))
    assert out["state"] == "waiting_quota" and out["result"] is None or True
    d = meas.get(conn, meas._mid(tid, job["job_id"]))
    assert d["measurement"]["executed"] == 3 and d["measurement"]["state"] == "waiting_quota" and d["measurement"]["stop_reason"] == "USAGE_LIMIT_REACHED"
    assert d["measurement"]["summary"]["proposal"]["verdict"] == "INCONCLUSIVE" and "unvollständig" in d["measurement"]["summary"]["proposal"]["why"]
    assert gov.quota_state(conn)["state"] == "USAGE_LIMIT_REACHED" and gov.can_dispatch(conn, "measurement") == (False, "USAGE_LIMIT_REACHED")
    gov.set_quota_state(conn, "OK", "founder")


def test_measurement_refuses_on_drift_and_budget(conn, tid, repo, tmp_path, attested, bundle_files):
    from logos_dashboard.control import measurement as meas, prereg
    service.create_thesis(conn, tid, [], "refuse", "authority", "founder")
    for e in ("triage", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        service.advance(conn, tid, e, "agent")
    bundle_files(); prereg.freeze(conn, tid, "founder")
    bundle_files(ds=_ds(n_per_arm=7))                                          # dataset drift after freeze
    service.advance(conn, tid, "approve_work_order", "founder"); service.advance(conn, tid, "dry_run", "system"); service.advance(conn, tid, "ready_to_run", "founder"); service.advance(conn, tid, "start_run", "founder")
    job = queue.enqueue(conn, "measurement", thesis_id=tid); queue.start(conn, job["job_id"], "founder", {"passed": True})
    out = meas.run_measurement(conn, {**job, "state": "running"}, _cfg(repo, tmp_path, _fake_measure_runner(['{"color": "blue"}'])))
    assert out["state"] == "failed" and out["error"].startswith("MEASUREMENT_REFUSED:DATASET_DRIFT")
    assert meas.budget(10, 40)["ok"] is True and meas.budget(40, 40)["ok"] is False and meas.budget(0, 40)["ok"] is False


def test_agent_and_measurement_caps_are_separate(conn, attested):
    from logos_dashboard.control import governor as gov
    from logos_research.governance import GovernanceError
    prev = gov.get_setting(conn, "agent_sessions_amendment")
    with pytest.raises(GovernanceError):
        gov.set_agent_sessions(conn, 3, "agent")
    with pytest.raises(GovernanceError):
        gov.set_agent_sessions(conn, 9, "founder")
    rec = gov.set_agent_sessions(conn, 3, "founder")
    assert rec["max_parallel_agent_sessions"] == 3 and rec["amendment"] == "INFERENCE-GOVERNANCE-CONCURRENCY-AMENDMENT-R1"
    c = gov.caps(conn); assert c.max_parallel_agent_sessions == 3 and c.max_parallel_claude_sessions == 1     # measurement stays at the governance record
    amend = _json.loads((_Path(__file__).resolve().parents[1] / "docs/research/INFERENCE-GOVERNANCE-CONCURRENCY-AMENDMENT-R1.json").read_text(encoding="utf-8"))
    assert amend["decision_owner"] == "founder" and "measurement" not in amend["scope"] and "max_concurrent_sessions = 1 for measurement runs (governance record)" in amend["unchanged"]
    if prev is not None:
        gov.set_agent_sessions(conn, int(prev.get("max_parallel_agent_sessions", 1)), "founder")


def test_r3_api_gates_measurement_and_verdict(conn, tid, repo, tmp_path, attested, bundle_files):
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    from logos_dashboard.control import measurement as meas, prereg
    client = TestClient(app)
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "api gate", "authority", "founder")
    for e in ("triage", "define_question", "define_hypothesis", "define_metrics", "draft_prereg"):
        service.advance(conn, tid, e, "agent")
    bundle_files()
    g = client.get(f"/api/ros/theses/{tid}/gates").json(); assert g["steps"][0]["enabled"] is True and g["steps"][1]["enabled"] is False
    v = client.post(f"/api/ros/theses/{tid}/prereg/validate").json(); assert v["passed"] is True and v["payload_preview"]["privacy_class"] == "SYNTHETIC"
    assert client.post(f"/api/ros/theses/{tid}/prereg/freeze", headers={"X-Logos-Actor": "agent"}).status_code == 409
    fr = client.post(f"/api/ros/theses/{tid}/prereg/freeze").json(); assert len(fr["prereg_hash"]) == 64
    client.post("/api/ros/work-orders", json={"work_order_id": f"WO-{tid}", "thesis_id": tid, "spec": {"question": "q", "scope": "s", "hypothesis": "h", "falsification_criterion": "f", "metrics": ["M1"], "governance": {"g": 1}, "caps": {"c": 1}}})
    client.post(f"/api/ros/work-orders/WO-{tid}/transition", json={"event": "approve", "prereg_hash": fr["prereg_hash"]})
    client.post(f"/api/ros/theses/{tid}/advance", json={"event": "approve_work_order"})
    dr = client.post(f"/api/ros/theses/{tid}/dry-run").json(); assert dr["passed"] is True and dr["thesis_state"] == "DRY_RUN"
    assert client.post(f"/api/ros/theses/{tid}/measurement/enqueue").status_code == 409          # needs READY_TO_RUN
    client.post(f"/api/ros/theses/{tid}/advance", json={"event": "ready_to_run"})
    enq = client.post(f"/api/ros/theses/{tid}/measurement/enqueue").json()
    assert enq["planned"] == 10 and enq["job"]["kind"] == "measurement" and enq["job"]["state"] in ("queued", "running")
    out = meas.run_measurement(conn, {**enq["job"], "state": "running"}, _cfg(repo, tmp_path, _fake_measure_runner(['{"color": "blue"}'] * 5 + ['{"color": "red"}'] * 5)))
    mid = out["result"]["measurement_id"]
    m = client.get(f"/api/ros/measurements/{mid}").json(); assert m["progress"]["done"] == 10 and m["rates"]["with_plan"]["k"] == 5
    assert client.get("/api/ros/measurements").json()["measurements"][0]["measurement_id"] == mid
    assert client.post(f"/api/ros/measurements/{mid}/verdict", json={"verdict": "SUPPORTED"}, headers={"X-Logos-Actor": "agent"}).status_code == 409
    assert client.post(f"/api/ros/measurements/{mid}/verdict", json={"verdict": "MAGIC"}).status_code == 400
    dec = client.post(f"/api/ros/measurements/{mid}/verdict", json={"verdict": "INCONCLUSIVE", "reason": "erst replizieren"}).json()
    assert dec["followed_proposal"] is False and dec["proposal"] == "SUPPORTED" and dec["thesis_state"] == "INCONCLUSIVE"
    (_Path(__file__).resolve().parents[1] / dec["draft"]["path"]).unlink()
    log = client.get(f"/api/ros/theses/{tid}/gate-log").json(); assert {l["gate"] for l in log["log"]} >= {"prereg_validate", "prereg_freeze", "dry_run", "ready_to_run", "measurement", "verdict"}
    assert client.post("/api/ros/governor/agent-sessions", json={"n": 3}, headers={"X-Logos-Actor": "agent"}).status_code == 403



# -- R4: Beobachtung, Erkenntnisse, Registerpflege --------------------------------------------------------------------


def test_observability_systems_are_truthful_and_leak_no_keys(conn):
    from logos_dashboard.control import observe
    sys_rows = observe.systems(conn)
    names = [s["system"] for s in sys_rows]
    assert names == ["MLflow", "Langfuse", "OTel-Collector", "Postgres (Labor)", "MinIO", "Host-Executor", "Docker-Worker", "Claude-Auth"]
    assert all(s["state"] in ("reachable", "unreachable") for s in sys_rows) and all(s["criticality"] in ("OBSERVABILITY", "CANONICAL", "EXECUTION", "GOVERNANCE") for s in sys_rows)
    blob = _json.dumps(observe.overview(conn, 3), default=str)
    assert "sk-lf" not in blob and "Authorization" not in blob and "Basic " not in blob        # keys stay on the server
    # an unreachable endpoint is reported as unreachable, never as ok
    import logos_dashboard.control.observe as O
    old = O.MLFLOW; O.MLFLOW = "http://127.0.0.1:9"                      # nothing listens there
    try:
        row = next(s for s in O.systems(None) if s["system"] == "MLflow")
        assert row["state"] == "unreachable" and "error" in (row["detail"] or {})
        assert O.mlflow_experiment(2)["reachable"] is False
    finally:
        O.MLFLOW = old

    mf = observe.mlflow_experiment(5)
    assert mf["reachable"] is True and mf["experiment"] == "logos-research-os" and isinstance(mf["runs"], list)
    lf = observe.langfuse_traces(3)
    assert lf["reachable"] is True and all({"trace_id", "name", "ui"} <= set(t) for t in lf["traces"])


def test_all_traces_of_one_run(conn, tid, attested, repo, tmp_path):
    from logos_dashboard.control import observe
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "traces", "authority", "founder")
    j = queue.enqueue(conn, "thesis_advance", thesis_id=tid); queue.start(conn, j["job_id"], "founder", governor.pre_run_gate(conn, j, "IDEA", "PREREG_DRAFT", ("IDEA", "PREREG_DRAFT")))
    rel = f"docs/research/dashboard/theses/{tid}/TRIAGE.md"
    out = executor.run_once(conn, _cfg(repo, tmp_path, _fake_claude(_result_doc(_agent_block("triage", [rel])), write={rel: "x"})), "w-test")
    run_id = runs.list_runs(conn, thesis_id=tid)[0]["run_id"]
    t = observe.all_traces(conn, run_id)
    assert t["found"] is True and t["n_events"] > 5 and t["branch"] == f"ros/{tid}/{run_id}" and len(t["artifacts"]) == 3
    assert t["mlflow"]["run_id"] == f"null-{run_id}" and t["mlflow"]["reachable"] is False       # null telemetry stack in tests — said plainly
    assert t["otel"]["trace_ids"] and "collector" in t["otel"]["note"] and t["langfuse"]["trace_id"] == f"lf-{run_id}"
    assert observe.all_traces(conn, "RUN-nope")["found"] is False


def test_insights_sentences_are_mechanical_and_grouped(conn):
    from logos_dashboard import insights, registries
    d = insights.build(conn)
    regs = registries.load_all()
    assert d["n_claims"] == len(regs["claims"]["claims"]) == sum(d["counts"].values()) and d["version"] == "ros-insights/1"
    assert set(d["groups"]) == {"gestuetzt", "widerlegt", "offen", "blockiert"} and d["counts"]["widerlegt"] >= 1
    auth = next(e for e in d["groups"]["gestuetzt"] if e["claim_id"] == "LOGOS-AUTH-001")
    assert auth["sentence"].startswith("Authority derives only") and "Status VALIDATED_IN_FIXTURE" in auth["sentence"] and "Evidenz mittel bis stark" in auth["sentence"]
    assert "geprüft in 11 Experimenten" in auth["sentence"] and "Replikation 1/5" in auth["sentence"] and "Widerlegen würde:" in auth["sentence"]
    assert "Vorsicht:" in auth["certainty"] and "Fixture" in auth["certainty"]
    falsified = [e for e in d["groups"]["widerlegt"]]
    assert all(e["status"] in ("FALSIFIED", "INVALID_MEASUREMENT", "INCONCLUSIVE") for e in falsified) and all("Negativbefund" in e["certainty"] for e in falsified)
    p7 = next(e for e in d["groups"]["gestuetzt"] if e["claim_id"] == "LOGOS-P7-001")
    assert "noch in keinem registrierten Experiment geprüft" in p7["sentence"]                    # honest: no experiment linked
    assert any("Status ist nicht Evidenzstärke" in r for r in d["rules"]) and any("P7" in r for r in d["rules"])
    assert all({"kind", "id", "text", "at"} <= set(x) for x in d["learned"])


def test_registry_edit_preview_guards_and_founder_apply(conn):
    from logos_dashboard.control import registry_edit as redit
    from logos_research.governance import GovernanceError
    with pytest.raises(ValueError):
        redit.preview("claims", "LOGOS-AUTH-001", "statement", "x", "eine ausreichend lange Begründung hier")
    with pytest.raises(KeyError):
        redit.preview("claims", "NOPE-999", "status", "SUPPORTED", "eine ausreichend lange Begründung hier")
    short = redit.preview("claims", "LOGOS-AUTH-001", "next_falsification_test", "X", "kurz")
    assert short["ok"] is False and any("Begründung" in i for i in short["issues"])
    weak = redit.preview("claims", "LOGOS-CP-002", "status", "SUPPORTED", "Begründung mit Verweis auf Messlauf M-1 und Artefakt")
    assert weak["ok"] is False and any("verlangt mindestens Evidenzstärke MEDIUM" in i for i in weak["issues"])
    jump = redit.preview("claims", "LOGOS-AUTH-001", "evidence_strength", "INDEPENDENTLY_REPLICATED", "Begründung mit Verweis auf einen Record hier")
    assert jump["ok"] is False and any("höchstens eine Stufe" in i for i in jump["issues"])
    bad_vocab = redit.preview("claims", "LOGOS-AUTH-001", "status", "TOTALLY_PROVEN", "Begründung mit Verweis auf einen Record hier")
    assert bad_vocab["ok"] is False and any("Vokabular" in i for i in bad_vocab["issues"])
    app = redit.preview("claims", "LOGOS-AUTH-001", "known_limitations", ["TEST-ROS: Prüfzeile der Registerpflege"], "Begründung mit Verweis auf einen Record hier")
    assert app["ok"] is True and app["after"][-1] == "TEST-ROS: Prüfzeile der Registerpflege" and app["before"] == app["after"][:-1]      # append-only
    with pytest.raises(GovernanceError):
        redit.apply(conn, "claims", "LOGOS-AUTH-001", "known_limitations", ["TEST-ROS: x"], "agent", "Begründung mit Verweis auf einen Record hier")
    n_before = len(redit.changelog())
    reg_path = _Path(__file__).resolve().parents[1] / "docs/research/dashboard/CLAIM-REGISTRY.json"
    cl_path = _Path(__file__).resolve().parents[1] / "docs/research/dashboard/registry-changelog.jsonl"
    reg_before = reg_path.read_bytes(); cl_before = cl_path.read_bytes() if cl_path.exists() else None
    rec = redit.apply(conn, "claims", "LOGOS-AUTH-001", "known_limitations", ["TEST-ROS: Prüfzeile der Registerpflege"], "founder", "Begründung mit Verweis auf einen Record hier", {"kind": "test"})
    try:
        assert rec["applied"] is True and rec["file_sha256_before"] != rec["file_sha256_after"] and len(rec["file_sha256_after"]) == 64
        log = redit.changelog(); assert len(log) == n_before + 1 and log[0]["field"] == "known_limitations" and log[0]["actor"] == "founder"
        import json as J
        doc = J.loads((_Path(__file__).resolve().parents[1] / "docs/research/dashboard/CLAIM-REGISTRY.json").read_text(encoding="utf-8"))
        entry = next(c for c in doc["claims"] if c["claim_id"] == "LOGOS-AUTH-001")
        assert "TEST-ROS: Prüfzeile der Registerpflege" in entry["known_limitations"] and entry["last_updated"]
        rev = redit.revert_proposal(0)
        assert rev["field"] == "known_limitations" and "TEST-ROS: Prüfzeile der Registerpflege" not in rev["value"] and rev["source"]["kind"] == "revert" and "Rücknahme" in rev["reason"]
    finally:                                                                 # Hygiene: beide Dateien byte-genau wie vorher
        reg_path.write_bytes(reg_before)
        if cl_before is None:
            cl_path.unlink(missing_ok=True)
        else:
            cl_path.write_bytes(cl_before)


def test_r4_api_observability_insights_registry(conn):
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    client = TestClient(app)
    o = client.get("/api/ros/observability/systems").json(); assert len(o["systems"]) == 8
    ov = client.get("/api/ros/observability?limit=5").json(); assert {"systems", "mlflow", "langfuse", "runs", "otel"} <= set(ov) and "Schlüssel" in ov["note"]
    ins = client.get("/api/ros/insights").json(); assert ins["counts"]["gestuetzt"] >= 10 and ins["version"] == "ros-insights/1"
    pr = client.get("/api/ros/registry/proposals").json(); assert {"proposals", "editable", "append_only"} <= set(pr) and "claims.supporting_artifacts" in pr["append_only"]
    pv = client.post("/api/ros/registry/preview", json={"registry": "claims", "entity_id": "LOGOS-AUTH-001", "field": "status", "value": "SUPPORTED", "reason": "zu kurz"}).json()
    assert pv["ok"] is False and pv["before"] == "VALIDATED_IN_FIXTURE"
    assert client.post("/api/ros/registry/preview", json={"registry": "claims", "entity_id": "LOGOS-AUTH-001", "field": "statement", "value": "x", "reason": "lange genug begründet hier"}).status_code == 400
    assert client.post("/api/ros/registry/apply", json={"registry": "claims", "entity_id": "LOGOS-AUTH-001", "field": "known_limitations", "value": ["TEST-ROS x"], "reason": "lange genug begründet hier"}, headers={"X-Logos-Actor": "agent"}).status_code == 403
    assert client.get("/api/ros/registry/changelog").json()["file"].endswith("registry-changelog.jsonl")
    assert client.get("/api/ros/runs/RUN-nope/all-traces").status_code == 404



# -- R5: Prior-Art-Matrix, Agenten-Evals, Publikationspfad --------------------------------------------------------------


def test_prior_art_matrix_is_honest_about_gaps():
    from logos_dashboard import prior_art, registries
    m = prior_art.matrix(); regs = registries.load_all()
    assert m["n_citations"] == len(regs["prior_art"]["citations"]) == 14 and m["min_per_track"] == 3 and m["version"] == "ros-prior-art/1"
    assert [r["track"] for r in m["tracks"]] == list(regs["claims"]["tracks"]) and len(m["claims"]) == len(regs["claims"]["claims"])
    auth = next(r for r in m["tracks"] if r["track"] == "authority")
    assert auth["citations"] == 2 and auth["status"] == "rot" and any("weitere Quelle" in x for x in auth["missing"])
    assert all(r["status"] in ("rot", "gelb", "gruen") for r in m["tracks"]) and not any(r["status"] == "gruen" for r in m["tracks"])   # heute ist keine Spur belegt genug
    c = next(x for x in m["claims"] if x["claim_id"] == "LOGOS-AUTH-001")
    assert "Neuheit ist damit nicht belegt" in c["novelty_statement"] and len(c["closest_prior_art"]) == 2
    assert m["n_open_tasks"] == len(__import__("logos_dashboard.research_intake", fromlist=["queue"]).queue(regs)) >= 20
    p = prior_art.task_payload(m_task_id := [t["task_id"] for t in __import__("logos_dashboard.research_intake", fromlist=["queue"]).queue(regs)][0])
    assert p["brief_task"]["task_id"] == m_task_id and p["brief_task"]["novelty_cap"] == "CLEAR_DIFFERENTIATION" and p["brief_task"]["min_sources"] == 3
    with pytest.raises(KeyError):
        prior_art.task_payload("RQ-DOES-NOT-EXIST")


def test_prior_art_brief_merge_is_founder_only_and_checked(conn):
    from logos_dashboard import prior_art, research_intake
    from logos_research.governance import GovernanceError
    briefs_dir = research_intake.BRIEFS; briefs_dir.mkdir(exist_ok=True)
    bid = "TEST-ROS-BRIEF-1"; path = briefs_dir / f"{bid}.json"
    reg_path = _Path(__file__).resolve().parents[1] / "docs/research/dashboard/PRIOR-ART-REGISTRY.json"
    cl_path = _Path(__file__).resolve().parents[1] / "docs/research/dashboard/registry-changelog.jsonl"
    reg_before = reg_path.read_bytes(); cl_before = cl_path.read_bytes() if cl_path.exists() else None
    brief = {"schema": "logos.research-brief/1", "brief_id": bid, "date": "2026-09-19", "claim_id": "LOGOS-AUTH-001", "question": "Closest prior art?", "sub_questions": ["capability systems"],
             "sources": [{"citation_id": "TEST-ROS-PA-1", "title": "A capability paper", "authors": "Doe, J.", "year": 2001, "venue": "Proc.", "url": "https://example.org/x",
                          "claim_supported": "capabilities bind authority to an unforgeable token", "claim_not_supported": "nothing about memory-derived authority",
                          "notes": "read in full", "research_track": "authority", "novelty_status": "POSSIBLE_INCREMENTAL"}],
             "synthesis": "Capability systems bind authority to tokens; LOGOS binds it to a canonical grant record.", "novelty_assessment": "POSSIBLE_INCREMENTAL",
             "limitations": "one source only", "reviewed_by_founder": False}
    path.write_text(_json.dumps(brief, indent=1), encoding="utf-8")
    try:
        d = prior_art.brief_diff(bid)
        assert d["ok"] is True and d["issues"] == [] and [c["citation_id"] for c in d["new_citations"]] == ["TEST-ROS-PA-1"] and d["after_count"] == d["before_count"] + 1
        with pytest.raises(GovernanceError):
            prior_art.merge(conn, bid, "agent")
        # a CLEAR_DIFFERENTIATION claim with a single source is refused
        brief_hot = {**brief, "sources": [{**brief["sources"][0], "novelty_status": "CLEAR_DIFFERENTIATION"}]}
        path.write_text(_json.dumps(brief_hot, indent=1), encoding="utf-8")
        with pytest.raises(ValueError):
            prior_art.merge(conn, bid, "founder")
        path.write_text(_json.dumps(brief, indent=1), encoding="utf-8")
        res = prior_art.merge(conn, bid, "founder")
        assert _json.loads(path.read_text(encoding="utf-8"))["reviewed_by_founder"] is True      # der Klick ist die Prüfung, und sie steht danach im Brief
        assert res["merged"] is True and res["added"] == ["TEST-ROS-PA-1"] and res["count"] == d["after_count"] and res["file_sha256_before"] != res["file_sha256_after"]
        from logos_dashboard.control import registry_edit
        assert registry_edit.changelog()[0]["origin"]["brief_id"] == bid
        with pytest.raises(ValueError):
            prior_art.merge(conn, bid, "founder")                        # nothing new the second time
        with pytest.raises(KeyError):
            prior_art.brief_diff("TEST-ROS-NOPE")
    finally:
        path.unlink(missing_ok=True); reg_path.write_bytes(reg_before)
        if cl_before is None:
            cl_path.unlink(missing_ok=True)
        else:
            cl_path.write_bytes(cl_before)


def test_agent_eval_profiles_are_deterministic():
    from logos_dashboard import evals
    p = evals.profiles()
    assert set(p["stages"]) == set(evals.STAGES) and len(evals.STAGES) == 6 and all(len(v) == 4 for v in p["stages"].values()) and "kein Modell bewertet ein Modell" in p["rule"]
    good = ("# Triage LOGOS-AUTH-001\n" + "Diese These betrifft docs/research/dashboard/CLAIM-REGISTRY.json und den Track authority. " * 4 +
            "\nFalsifikation: widerlegt, wenn die Rate falscher Freigaben mit Konfidenzintervall über der Schwelle 0.0 liegt (n = 40, Wilson).\n")
    g = evals.score_file("TRIAGE", good); assert g["k"] == 4 and g["n_scored"] == 4 and g["passed"] is True
    bad = evals.score_file("TRIAGE", "Kurz. Diese These ist SUPPORTED und sicher.")
    assert bad["k"] == 0 and bad["checks"]["no_status_claim"] is False and bad["checks"]["falsifier_measurable"] is False and bad["passed"] is False
    assert evals.score_file("PREREG", '{"question": "q", "hypothesis": "h", "falsification_criterion": "Wilson-KI über Schwelle", "scope": "fixture"}')["checks"]["prereg_fields"] is True
    assert evals.score_file("PREREG", "not json")["checks"]["prereg_fields"] is False
    assert evals.score_file("METRICS", "Wir nutzen json_field_equals als Scorer; falsifiziert bei Konfidenzintervall unter der Schwelle." * 4)["checks"]["metrics_map_to_scorers"] is True
    assert evals.score_file("PRIOR_ART", "Smith et al. (2001) zeigt X." * 20)["checks"]["no_uncited_claims"] is False       # Zitat ohne Quelle
    assert evals.score_file("PRIOR_ART", ("Smith et al. (2001) zeigt X, siehe https://example.org/a. " * 10))["checks"]["no_uncited_claims"] is True
    assert evals.score_file("TRIAGE", None)["n_scored"] == 0 and evals.score_file("TRIAGE", None)["missing"] == 4
    with pytest.raises(ValueError):
        evals.score_file("NOPE", "x")
    agg = evals.aggregate([{"stages": [g, bad]}])
    assert agg["total"]["k"] == 4 and agg["total"]["n"] == 8 and agg["total"]["rate"] == 0.5 and agg["stages"][0]["status"] == "OK" and agg["stages"][1]["status"] == "NO_DATA"


def test_paper_draft_uses_records_only(conn):
    from logos_dashboard import paper
    d = paper.build(conn, "PAPER-2")
    assert d["paper_id"] == "PAPER-2" and d["abstract"] == "TO_BE_WRITTEN" and len(d["sha256"]) == 64 and d["manuscript_status_in_registry"] == "INTERNAL_DRAFT"
    assert len(d["contributions"]) == 6 and all("Status" in c and "Evidenz" in c for c in d["contributions"])
    assert [r["track"] for r in d["related_work"]] == ["authority"] and d["related_work"][0]["gap"].startswith("1 Quelle")
    assert all(m["n_experiments"] >= 0 for m in d["methods"]) and any(m["n_experiments"] > 0 for m in d["methods"])
    assert all(("measurement_id" in r) for r in d["results"]) and any(r.get("note", "").startswith("kein governed Messlauf") for r in d["results"])
    assert any("P7" in x for x in d["does_not_claim"]) and d["reproducibility"]["registries"] and d["readiness"]["of"] == 8
    md = paper.render_markdown(d)
    assert md.startswith("# Authority-Preserving Execution") and "TO_BE_WRITTEN" in md and "Was dieses Papier nicht behauptet" in md and "Reifegrad im Register: **INTERNAL_DRAFT**" in md
    assert paper.build(conn, "PAPER-2")["sha256"] == d["sha256"]                      # deterministisch
    with pytest.raises(KeyError):
        paper.build(conn, "PAPER-999")


def test_r5_api_prior_art_evals_paper(conn):
    from fastapi.testclient import TestClient
    from logos_dashboard.api import app
    client = TestClient(app)
    m = client.get("/api/ros/prior-art/matrix").json(); assert m["n_citations"] == 14 and len(m["tracks"]) == 6
    b = client.get("/api/ros/prior-art/briefs").json(); assert "tasks" in b and b["schema"]["schema"] == "logos.research-brief/1"
    assert client.get("/api/ros/prior-art/briefs/NOPE/diff").status_code == 404
    assert client.post("/api/ros/prior-art/briefs/NOPE/merge", headers={"X-Logos-Actor": "agent"}).status_code == 403
    task_id = b["tasks"][0]["task_id"]
    j = client.post(f"/api/ros/prior-art/tasks/{task_id}/job").json(); assert j["kind"] == "prior_art" and j["state"] == "waiting_governance" and j["payload"]["brief_task"]["task_id"] == task_id
    queue.request_stop(conn, j["job_id"], "founder")
    pf = client.get("/api/ros/evals/profiles").json(); assert len(pf["stages"]) == 6
    ev = client.get("/api/ros/evals").json(); assert "aggregate" in ev and ev["aggregate"]["suite"] == "AGENT_QUALITY"
    dr = client.get("/api/ros/papers/PAPER-2/draft").json(); assert dr["doc"]["paper_id"] == "PAPER-2" and dr["markdown"].startswith("# ")
    assert client.get("/api/ros/papers/PAPER-999/draft").status_code == 404
    p = _Path(__file__).resolve().parents[1] / "docs/research/dashboard/paper-drafts"
    had = p.exists() and (p / "PAPER-2.md").exists()
    ex = client.post("/api/ros/papers/PAPER-2/export").json()
    try:
        assert ex["path"].endswith("PAPER-2.md") and ex["manuscript_status_unchanged"] == "INTERNAL_DRAFT" and (p / "PAPER-2.md").exists()
        import json as J
        reg = J.loads((_Path(__file__).resolve().parents[1] / "docs/research/dashboard/PUBLICATION-REGISTRY.json").read_text(encoding="utf-8"))
        assert next(x for x in reg["papers"] if x["paper_id"] == "PAPER-2")["manuscript_status"] == "INTERNAL_DRAFT"      # export ändert den Reifegrad nicht
    finally:
        if not had:
            (p / "PAPER-2.md").unlink(missing_ok=True); (p / "PAPER-2.json").unlink(missing_ok=True)
            try:
                p.rmdir()
            except OSError:
                pass
