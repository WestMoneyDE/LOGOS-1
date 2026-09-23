"""The navigator (spec §5, Component 4) and its shadow hook in `service.advance`.

Deterministic: every transport is a `FakeTransport`; no model and no network. The DB-backed
differential test uses the lab Postgres like `tests/test_ros_control_plane.py` and is skipped
when it is unreachable.
"""
from __future__ import annotations

import uuid

import pytest

from logos_dashboard.control.state_machines import (
    AGENT_CEILING, FOUNDER_GATES, THESIS_STATES, THESIS_TRANSITIONS, events_from,
)
from logos_laya.classify import SCHEMA_VERSION, ClassifyAnswer, ClassifyClient, FakeTransport
from logos_laya.navigator import (
    STAY, NavigatorMove, compile_step, interpret, navigate, offered_events, question_id_for,
)
from logos_laya.profiles import question_sha256

REV = "0123456789abcdef0123456789abcdef01234567"
PINS = {"package_version": "0.3.6", "hf_revision": REV, "route": "typed-decisions", "device": "cpu"}
CEIL = THESIS_STATES.index(AGENT_CEILING)
AGENT_PATH = ("triage", "start_prior_art", "define_question", "define_hypothesis", "define_metrics", "draft_prereg")


def choice_body(state: str, choice: str, probabilities: dict, confidence: float = 0.4) -> dict:
    return {"schema_version": SCHEMA_VERSION, "request_id": "__ECHO__", "question_id": question_id_for("thesis", state),
            "answer": {"type": "choice", "choice": choice, "probabilities": probabilities, "confidence": confidence},
            "pins": dict(PINS), "latency_ms": 17}


def answer(choice, probabilities, confidence=0.5, ok=True, reason=None) -> ClassifyAnswer:
    return ClassifyAnswer(question_id="thesis_nav_idea", type="choice", ok=ok, p_true=None, choice=choice if ok else None,
                          probabilities=probabilities if ok else {}, confidence=confidence if ok else None,
                          pins=PINS if ok else {}, abstain_reason=reason, latency_ms=5 if ok else None)


# -- offered events: the walls, for every state -----------------------------------

@pytest.mark.parametrize("state", THESIS_STATES)
def test_offered_events_respect_every_wall(state):
    offered = offered_events("thesis", state)
    assert offered == tuple(sorted(offered))
    assert not set(offered) & FOUNDER_GATES
    assert "supersede" not in offered
    if THESIS_STATES.index(state) >= CEIL:
        assert offered == ()
    for ev in offered:
        assert (state, ev) in THESIS_TRANSITIONS
        assert THESIS_STATES.index(THESIS_TRANSITIONS[(state, ev)]) <= CEIL


def test_offered_event_table_for_agent_reachable_states():
    assert {s: offered_events("thesis", s) for s in THESIS_STATES[:CEIL + 1]} == {
        "IDEA": ("triage",), "TRIAGE": ("define_question", "start_prior_art"), "PRIOR_ART": ("define_question",),
        "QUESTION_DEFINED": ("define_hypothesis",), "HYPOTHESIS_DEFINED": ("define_metrics",),
        "METRICS_DEFINED": ("draft_prereg",), "PREREG_DRAFT": ()}


def test_navigate_stops_at_the_walls_without_asking():
    t = FakeTransport([])
    c = ClassifyClient(transport=t)
    assert navigate(c, "thesis", "PREREG_DRAFT", "draft done").kind == "STOP_AT_GATE"
    assert navigate(c, "thesis", "PREREG_FROZEN", "x").kind == "STOP_AT_CEILING"
    assert navigate(c, "thesis", "DRY_RUN", "x").kind == "STOP_AT_CEILING"
    assert navigate(c, "thesis", "NOT_A_STATE", "x").kind in ("STOP_AT_CEILING", "STAND_STILL")
    assert t.calls == []
    assert compile_step("thesis", "PREREG_DRAFT", "x") is None


# -- compile_step -------------------------------------------------------------------

def test_compile_step_is_deterministic_and_uses_named_fields():
    for state in THESIS_STATES[:CEIL]:
        s1, q1 = compile_step("thesis", state, "output A")
        s2, q2 = compile_step("thesis", state, "a completely different output " * 200)
        assert question_sha256(q1) == question_sha256(q2)                  # fixed per-state text
        assert q1["type"] == "choice" and "`thesis_state`" in q1["instructions"] and "`step_output`" in q1["instructions"]
        assert set(q1["criteria"]) == set(offered_events("thesis", state)) | {STAY}
        assert set(s1) == {"thesis_state", "step_output"} and s1["thesis_state"] == state
        assert len(s2["step_output"]) == 1500
    hashes = {question_sha256(compile_step("thesis", s, "x")[1]) for s in THESIS_STATES[:CEIL]}
    assert len(hashes) == CEIL                                             # one distinct question per state


# -- interpret ----------------------------------------------------------------------

def test_interpret_out_of_set_abstain_stay_event():
    offered = ("define_question", "start_prior_art")
    gate = interpret(answer("freeze_prereg", {"freeze_prereg": 0.9, "stay": 0.1}), offered)
    assert gate.kind == "STAND_STILL" and gate.event is None
    assert interpret(answer("supersede", {"supersede": 1.0}), offered).kind == "STAND_STILL"
    ab = interpret(answer(None, {}, ok=False, reason="TIMEOUT"), offered)
    assert ab == NavigatorMove("STAND_STILL", None, "TIMEOUT")
    st = interpret(answer("stay", {"stay": 0.6, "define_question": 0.3, "start_prior_art": 0.1}), offered)
    assert st.kind == "STAY" and st.p_top == pytest.approx(0.6) and st.margin == pytest.approx(0.3)
    ev = interpret(answer("start_prior_art", {"start_prior_art": 0.7, "stay": 0.3}), offered)
    assert ev.kind == "EVENT" and ev.event == "start_prior_art"


def test_interpret_never_reads_confidence():
    probs = {"define_question": 0.55, "start_prior_art": 0.25, "stay": 0.2}
    a = interpret(answer("define_question", probs, confidence=0.01), ("define_question", "start_prior_art"))
    b = interpret(answer("define_question", probs, confidence=0.99), ("define_question", "start_prior_art"))
    assert a == b


def test_navigate_asks_the_typed_decisions_route_and_never_raises():
    t = FakeTransport([(200, choice_body("IDEA", "triage", {"triage": 0.8, "stay": 0.2}))])
    move = navigate(ClassifyClient(transport=t), "thesis", "IDEA", "a testable claim")
    assert move.kind == "EVENT" and move.event == "triage"
    assert t.calls[0][1]["route"] == "typed-decisions" and t.calls[0][1]["state"]["thesis_state"] == "IDEA"

    class Exploding:
        def ask(self, *a, **k):
            raise RuntimeError("boom")
    assert navigate(Exploding(), "thesis", "IDEA", "x").kind == "STAND_STILL"


# -- DB-backed: the differential test -------------------------------------------------

@pytest.fixture(scope="module")
def conn():
    from logos_dashboard import db
    c = db.connect()
    if c is None:
        pytest.skip("lab Postgres unreachable — dashboard runs records-only")
    db.ensure_schema(c)
    yield c
    c.close()


@pytest.fixture
def tids(conn):
    from logos_dashboard.control import service
    ids = [f"TEST-ROS-{uuid.uuid4().hex[:8]}" for _ in range(2)]
    yield ids
    conn.rollback()
    for t in ids:
        service.delete_thesis(conn, t, "system")
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ros_audit WHERE subject = %s AND action = 'laya.shadow'", (t,))
        conn.commit()


def _events(conn, tid):
    with conn.cursor() as cur:
        cur.execute("SELECT event, from_state, to_state FROM ros_thesis_events WHERE thesis_id = %s ORDER BY event_id", (tid,))
        return cur.fetchall()


def _shadow_rows(conn, tid):
    with conn.cursor() as cur:
        cur.execute("SELECT detail FROM ros_audit WHERE subject = %s AND action = 'laya.shadow' ORDER BY audit_id", (tid,))
        return [r[0] for r in cur.fetchall()]


def _state(conn, tid):
    with conn.cursor() as cur:
        cur.execute("SELECT state FROM ros_theses WHERE thesis_id = %s", (tid,))
        return cur.fetchone()[0]


def _drive(conn, tid):
    from logos_dashboard.control import service
    from logos_dashboard.control.state_machines import IllegalTransition
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "navigator differential", "authority", "founder")
    for e in AGENT_PATH:
        service.advance(conn, tid, e, "agent", reason=f"step output for {e}")
    with pytest.raises(IllegalTransition):
        service.advance(conn, tid, "freeze_prereg", "agent")              # the gate holds in both runs
    conn.rollback()


def test_shadow_is_differential_noop_under_an_adversarial_laya(conn, tids, monkeypatch):
    from logos_dashboard.control import service
    off, on = tids

    def forbidden():
        raise AssertionError("shadow off must not build a client")
    monkeypatch.delenv("LOGOS_LAYA_SHADOW", raising=False)
    monkeypatch.setattr(service, "_laya_client_factory", forbidden)
    _drive(conn, off)

    adversary = FakeTransport([
        (200, choice_body("IDEA", "freeze_prereg", {"freeze_prereg": 0.97, "stay": 0.03}, confidence=0.99)),  # a founder gate
        (200, {"garbage": True}),                                                                             # off-schema body
        (503, {"error_code": "LAYA_BUSY"}),                                                                   # service busy
        TimeoutError("scripted timeout"),                                                                     # timeout
        (200, choice_body("HYPOTHESIS_DEFINED", "supersede", {"supersede": 1.0})),                           # never offered
        (200, choice_body("METRICS_DEFINED", "draft_prereg", {"draft_prereg": 0.8, "stay": 0.2})),           # agrees
    ])
    monkeypatch.setenv("LOGOS_LAYA_SHADOW", "1")
    monkeypatch.setattr(service, "_laya_client_factory", lambda: ClassifyClient(transport=adversary))
    _drive(conn, on)

    assert _state(conn, off) == _state(conn, on) == "PREREG_DRAFT"
    ev_off, ev_on = _events(conn, off), _events(conn, on)
    assert ev_off == ev_on and len(ev_on) == 1 + len(AGENT_PATH)
    assert _shadow_rows(conn, off) == []
    rows = _shadow_rows(conn, on)
    assert len(rows) == len(AGENT_PATH) and len(adversary.calls) == len(AGENT_PATH)
    assert [r["actual_event"] for r in rows] == list(AGENT_PATH)
    assert [r["laya_move"] for r in rows] == ["STAND_STILL"] * 5 + ["EVENT"]
    assert [r["abstain_reason"] for r in rows] == [None, "WRONG_SCHEMA_VERSION", "SERVICE_BUSY", "TIMEOUT", None, None]
    assert [r["agreed"] for r in rows] == [False] * 5 + [True]
    assert all(r["laya_event"] is None or r["laya_event"] not in FOUNDER_GATES for r in rows)
    assert rows[0]["offered"] == ["triage"] and rows[1]["offered"] == ["define_question", "start_prior_art"]
    assert rows[5]["pins"] == PINS and rows[5]["p_top"] == pytest.approx(0.8) and rows[5]["margin"] == pytest.approx(0.6)


def test_shadow_survives_a_broken_client_factory(conn, tids, monkeypatch):
    from logos_dashboard.control import service
    tid = tids[0]

    def broken():
        raise RuntimeError("no client")
    monkeypatch.setenv("LOGOS_LAYA_SHADOW", "1")
    monkeypatch.setattr(service, "_laya_client_factory", broken)
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "navigator broken client", "authority", "founder")
    row = service.advance(conn, tid, "triage", "agent", reason="x")
    assert row["state"] == "TRIAGE" and _state(conn, tid) == "TRIAGE"
    rows = _shadow_rows(conn, tid)
    assert len(rows) == 1 and rows[0]["laya_move"] == "STAND_STILL" and rows[0]["laya_reason"].startswith("CLIENT_UNAVAILABLE")


def test_shadow_off_makes_no_network_call(conn, tids, monkeypatch):
    from logos_dashboard.control import service
    tid = tids[0]

    class Tripwire:
        def post(self, *a, **k):
            raise AssertionError("shadow off must not reach the network")
    monkeypatch.delenv("LOGOS_LAYA_SHADOW", raising=False)
    monkeypatch.setattr(service, "_laya_client_factory", lambda: ClassifyClient(transport=Tripwire()))
    service.create_thesis(conn, tid, ["LOGOS-AUTH-001"], "navigator shadow off", "authority", "founder")
    service.advance(conn, tid, "triage", "agent")
    monkeypatch.setenv("LOGOS_LAYA_SHADOW", "0")                          # only exactly "1" enables it
    service.advance(conn, tid, "define_question", "agent")
    assert _state(conn, tid) == "QUESTION_DEFINED" and _shadow_rows(conn, tid) == []
