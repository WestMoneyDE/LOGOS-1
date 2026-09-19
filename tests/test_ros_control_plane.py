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
    assert v1 == v2 == 3                                     # v1 control plane (Phase 2) + v2 executor settings/heartbeats (Phase 3) + v3 benchmark lab (Phase 5)
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'ros\\_%'")
        names = {r[0] for r in cur.fetchall()}
    assert set(db.ROS_TABLES) <= names and len(db.ROS_TABLES) == 20


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
    assert st["db"] == "ok" and st["schema_version"] == 3 and "thesis_advance" in st["claude_kinds"]
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
    assert len(docs) == 39 and sum(1 for d in docs if d["kind"] == "closure") == 35 and {d["state"] for d in docs} == {"VALIDATED", "FALSIFIED", "DRAFT"}     # 40 files, 39 orders (one generated master order has its closure) — exact for 05-WORK-ORDERS on 2026-09-19
    falsified = sorted(d["order_id"] for d in docs if d["state"] == "FALSIFIED"); assert falsified == ["COGNITIVE-PROVENANCE-ABLATION-R1", "RISK-AWARENESS-DECOMPOSITION-R1"]
    r1 = repo_orders.import_orders(conn); r2 = repo_orders.import_orders(conn)
    assert r1["documents"] == r2["documents"] == 39 and r2["new"] == 0 and r2["updated"] == 39 and r2["edges_added"] == 0 and r1["states"]["FALSIFIED"] == 2
    ch = repo_orders.chain(conn); assert len(ch) == 39 and all(x["work_order_id"].startswith("REPO:") for x in ch) and all(x["origin"]["repository"] for x in ch)
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
    ro = client.post("/api/ros/repo-orders/import").json(); assert ro["documents"] == 39
    lst = client.get("/api/ros/repo-orders").json(); assert len(lst["orders"]) == 39 and len(lst["documents"]) == 39
    ls = client.get("/api/ros/leitstand").json()
    assert {"host", "docker", "autopilot", "theses", "attention", "governor", "first_steps", "states"} <= set(ls) and ls["ceiling"] == "PREREG_DRAFT"
    mine = next(t for t in ls["theses"] if t["thesis_id"] == tid); assert mine["autopilot"]["enabled"] is True and mine["stage_index"] == 0
    assert client.post(f"/api/ros/autopilot/theses/{tid}", json={"enabled": False}).json()["flag"]["enabled"] is False
