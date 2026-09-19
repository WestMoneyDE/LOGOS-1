"""Control service: theses, thesis events, work orders, decisions, notes — every mutation = state-machine check + row + event + audit in ONE transaction.

Actors: `founder` (the only one who may pass gates), `agent` (Claude host job), `worker` (deterministic Docker worker), `system`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from psycopg.rows import dict_row

from .state_machines import AGENT_CEILING, IllegalTransition, THESIS_STATES, events_from, transition

WORK_ORDER_REQUIRED = ("question", "scope", "hypothesis", "falsification_criterion", "metrics", "governance", "caps")
ACTORS = ("founder", "agent", "worker", "system")


def _audit(cur, actor: str, action: str, subject: str, detail: dict | None = None) -> None:
    cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, %s, %s, %s)", (actor, action, subject, json.dumps(detail or {}, default=str)))


def _check_actor(actor: str) -> None:
    if actor not in ACTORS:
        raise ValueError(f"unknown actor {actor!r}; expected one of {ACTORS}")


# -- theses -------------------------------------------------------------------

def create_thesis(conn, thesis_id: str, claim_ids: list[str], title: str, track: str, actor: str, reason: str = "") -> dict:
    _check_actor(actor)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_theses (thesis_id, claim_ids, title, track, state, owner) VALUES (%s, %s, %s, %s, 'IDEA', %s) RETURNING *", (thesis_id, list(claim_ids), title, track, actor))
        row = cur.fetchone()
        cur.execute("INSERT INTO ros_thesis_events (thesis_id, from_state, to_state, event, actor, reason) VALUES (%s, NULL, 'IDEA', 'create', %s, %s)", (thesis_id, actor, reason))
        _audit(cur, actor, "thesis.create", thesis_id, {"claim_ids": list(claim_ids), "track": track})
    conn.commit()
    return row


def advance(conn, thesis_id: str, event: str, actor: str, reason: str = "", source_record: str | None = None, git_commit: str | None = None) -> dict:
    """Apply `event` to the thesis. Raises IllegalTransition (nothing written) on gate/illegal moves. Agents are additionally capped at AGENT_CEILING."""
    _check_actor(actor)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_theses WHERE thesis_id = %s FOR UPDATE", (thesis_id,))
        th = cur.fetchone()
        if th is None:
            raise KeyError(thesis_id)
        nxt = transition("thesis", th["state"], event, actor)
        if actor == "agent" and THESIS_STATES.index(nxt) > THESIS_STATES.index(AGENT_CEILING) and nxt not in ("SUPERSEDED",):
            raise IllegalTransition("thesis", th["state"], event, actor, f"agent autonomy ends at {AGENT_CEILING}")
        cur.execute("UPDATE ros_theses SET state = %s, updated_at = now() WHERE thesis_id = %s RETURNING *", (nxt, thesis_id))
        row = cur.fetchone()
        cur.execute("INSERT INTO ros_thesis_events (thesis_id, from_state, to_state, event, actor, reason, source_record, git_commit) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING event_id",
                    (thesis_id, th["state"], nxt, event, actor, reason, source_record, git_commit))
        row["event_id"] = cur.fetchone()["event_id"]
        _audit(cur, actor, "thesis.advance", thesis_id, {"event": event, "from": th["state"], "to": nxt, "reason": reason})
    conn.commit()
    return row


def list_theses(conn) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""SELECT t.*, (SELECT count(*) FROM ros_work_orders w WHERE w.thesis_id = t.thesis_id) AS n_work_orders,
                              (SELECT count(*) FROM ros_jobs j WHERE j.thesis_id = t.thesis_id AND j.state IN ('queued','running','paused','waiting_quota','waiting_dependency','waiting_governance')) AS n_open_jobs,
                              (SELECT max(at) FROM ros_thesis_events e WHERE e.thesis_id = t.thesis_id) AS last_event_at
                       FROM ros_theses t ORDER BY updated_at DESC""")
        return cur.fetchall()


def thesis_detail(conn, thesis_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_theses WHERE thesis_id = %s", (thesis_id,)); th = cur.fetchone()
        if th is None:
            return None
        cur.execute("SELECT * FROM ros_thesis_events WHERE thesis_id = %s ORDER BY event_id", (thesis_id,)); ev = cur.fetchall()
        cur.execute("SELECT * FROM ros_work_orders WHERE thesis_id = %s ORDER BY created_at", (thesis_id,)); wos = cur.fetchall()
        cur.execute("SELECT * FROM ros_decisions WHERE subject_ref = %s OR subject_ref = ANY(%s) ORDER BY created_at", (thesis_id, [w["work_order_id"] for w in wos])); dec = cur.fetchall()
        cur.execute("SELECT * FROM ros_jobs WHERE thesis_id = %s ORDER BY job_id DESC LIMIT 50", (thesis_id,)); jobs = cur.fetchall()
        cur.execute("SELECT * FROM ros_notes WHERE thesis_id = %s ORDER BY note_id DESC LIMIT 50", (thesis_id,)); notes = cur.fetchall()
        cur.execute("SELECT * FROM ros_runs WHERE thesis_id = %s ORDER BY created_at DESC LIMIT 50", (thesis_id,)); runs = cur.fetchall()
    return {"thesis": th, "events": ev, "work_orders": wos, "decisions": dec, "jobs": jobs, "notes": notes, "runs": runs,
            "available_events": events_from("thesis", th["state"]), "agent_ceiling": AGENT_CEILING, "states": list(THESIS_STATES)}


def delete_thesis(conn, thesis_id: str, actor: str) -> int:
    """Test hygiene only: ids must start with TEST-ROS-. Cascades to events, work orders, notes."""
    if not thesis_id.startswith("TEST-ROS-"):
        raise ValueError("only TEST-ROS-* theses may be deleted")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM ros_jobs WHERE thesis_id = %s", (thesis_id,))
        cur.execute("DELETE FROM ros_decisions WHERE subject_ref = %s OR subject_ref LIKE %s", (thesis_id, thesis_id + "%"))
        cur.execute("DELETE FROM ros_theses WHERE thesis_id = %s", (thesis_id,)); n = cur.rowcount
        _audit(cur, actor, "thesis.delete", thesis_id, {})
    conn.commit()
    return n


# -- work orders ---------------------------------------------------------------

def validate_spec(spec: dict) -> list[str]:
    missing = [k for k in WORK_ORDER_REQUIRED if not spec.get(k)]
    if isinstance(spec.get("metrics"), list) and not spec["metrics"]:
        missing.append("metrics")
    return sorted(set(missing), key=WORK_ORDER_REQUIRED.index)


def create_work_order(conn, work_order_id: str, thesis_id: str | None, spec: dict, actor: str) -> dict:
    _check_actor(actor)
    missing = validate_spec(spec)
    if missing:
        raise ValueError(f"work order spec missing mandatory fields: {missing}")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_work_orders (work_order_id, thesis_id, state, spec, created_by) VALUES (%s, %s, 'DRAFT', %s, %s) RETURNING *", (work_order_id, thesis_id, json.dumps(spec), actor))
        row = cur.fetchone()
        _audit(cur, actor, "work_order.create", work_order_id, {"thesis_id": thesis_id})
    conn.commit()
    return row


def wo_transition(conn, work_order_id: str, event: str, actor: str, reason: str = "", prereg_hash: str | None = None) -> dict:
    _check_actor(actor)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_work_orders WHERE work_order_id = %s FOR UPDATE", (work_order_id,)); wo = cur.fetchone()
        if wo is None:
            raise KeyError(work_order_id)
        nxt = transition("work_order", wo["state"], event, actor)
        if event == "approve":
            cur.execute("UPDATE ros_work_orders SET state = %s, approved_by = %s, approved_at = now(), prereg_hash = COALESCE(%s, prereg_hash), updated_at = now() WHERE work_order_id = %s RETURNING *", (nxt, actor, prereg_hash, work_order_id))
        else:
            cur.execute("UPDATE ros_work_orders SET state = %s, updated_at = now() WHERE work_order_id = %s RETURNING *", (nxt, work_order_id))
        row = cur.fetchone()
        _audit(cur, actor, "work_order.transition", work_order_id, {"event": event, "from": wo["state"], "to": nxt, "reason": reason})
    conn.commit()
    return row


def list_work_orders(conn) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""SELECT w.*, COALESCE(array_agg(d.parent) FILTER (WHERE d.parent IS NOT NULL), '{}') AS parents
                       FROM ros_work_orders w LEFT JOIN ros_work_order_deps d ON d.child = w.work_order_id GROUP BY w.work_order_id ORDER BY w.created_at DESC""")
        return cur.fetchall()


# -- decisions -----------------------------------------------------------------

def open_decision(conn, decision_id: str, kind: str, subject_ref: str, why: str, impact: str = "", if_approved: str = "", if_rejected: str = "", blocks: list[str] | None = None, actor: str = "system") -> dict:
    _check_actor(actor)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_decisions (decision_id, kind, subject_ref, state, why, impact, if_approved, if_rejected, blocks) VALUES (%s, %s, %s, 'WAITING', %s, %s, %s, %s, %s) RETURNING *",
                    (decision_id, kind, subject_ref, why, impact, if_approved, if_rejected, list(blocks or [])))
        row = cur.fetchone(); _audit(cur, actor, "decision.open", decision_id, {"kind": kind, "subject_ref": subject_ref})
    conn.commit()
    return row


def decide(conn, decision_id: str, event: str, actor: str, reason: str = "") -> dict:
    """event in approve|reject|defer|supersede — the first three are founder-only (state machine enforces)."""
    _check_actor(actor)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_decisions WHERE decision_id = %s FOR UPDATE", (decision_id,)); d = cur.fetchone()
        if d is None:
            raise KeyError(decision_id)
        nxt = transition("decision", d["state"], event, actor)
        cur.execute("UPDATE ros_decisions SET state = %s, decided_by = %s, decided_at = now() WHERE decision_id = %s RETURNING *", (nxt, actor, decision_id)); row = cur.fetchone()
        _audit(cur, actor, "decision.decide", decision_id, {"event": event, "to": nxt, "reason": reason})
    conn.commit()
    return row


def list_decisions(conn, state: str | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if state:
            cur.execute("SELECT * FROM ros_decisions WHERE state = %s ORDER BY created_at DESC", (state,))
        else:
            cur.execute("SELECT * FROM ros_decisions ORDER BY (state = 'WAITING') DESC, created_at DESC")
        return cur.fetchall()


# -- notes ---------------------------------------------------------------------

def add_note(conn, thesis_id: str | None, run_id: str | None, author: str, text: str, decision_flag: bool = False) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_notes (thesis_id, run_id, author, text, decision_flag) VALUES (%s, %s, %s, %s, %s) RETURNING *", (thesis_id, run_id, author, text, decision_flag)); row = cur.fetchone()
        _audit(cur, author, "note.add", thesis_id or run_id or "-", {"decision_flag": decision_flag})
    conn.commit()
    return row


def unconsumed_notes(conn, thesis_id: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_notes WHERE thesis_id = %s AND consumed_by_job IS NULL ORDER BY note_id", (thesis_id,)); return cur.fetchall()


def audit_tail(conn, limit: int = 100) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_audit ORDER BY audit_id DESC LIMIT %s", (limit,)); return cur.fetchall()


def events(conn, thesis_id: str | None = None, limit: int = 200) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if thesis_id:
            cur.execute("SELECT * FROM ros_thesis_events WHERE thesis_id = %s ORDER BY event_id DESC LIMIT %s", (thesis_id, limit))
        else:
            cur.execute("SELECT * FROM ros_thesis_events ORDER BY event_id DESC LIMIT %s", (limit,))
        return cur.fetchall()
