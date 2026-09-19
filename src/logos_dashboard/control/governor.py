"""ConcurrencyGovernor (spec §5) + governed settings.

Caps come from docs/research/INFERENCE-GOVERNANCE.json (`max_concurrent_sessions`, `max_claude_code_invocations`) — they are read, never written here.
Raising a cap through this module raises `GovernanceError`: that is a founder amendment order, not an API call.
Quota: `USAGE_LIMIT_REACHED` blocks every Claude job until the founder resets the state (no fallback provider/model, no auto-retry).
Auth evidence: class-level fields of the documented `claude auth status --json` (loggedIn, authMethod, apiProvider, subscriptionType) + `claude --version`;
identifiers are never stored. Evidence older than ATTESTATION_TTL_H hours is stale -> Start refused.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from psycopg.rows import dict_row

from logos_research.governance import GovernanceError, load_governance
from logos_research.measurement.claude_code import MODEL_PIN_PLACEHOLDER, contamination

from .queue import CLAUDE_KINDS, DETERMINISTIC_KINDS

ATTESTATION_TTL_H = 24
FOUNDER_MODEL_PIN = "claude-opus-5"   # founder pin (selection_owner = founder, 2026-09-18; 09-SESSIONS/2026-09-18-COGNITIVE-PROVENANCE-ABLATION-R1/MODEL-PIN-GATE.md); a change is a founder decision, never an API call
FOUNDER_MODEL_PIN_SOURCE = "09-SESSIONS/2026-09-18-COGNITIVE-PROVENANCE-ABLATION-R1/MODEL-PIN-GATE.md"
AUTH_FIELDS = ("loggedIn", "authMethod", "apiProvider", "subscriptionType")      # class-level only; email/orgId/orgName/paths are never read into the record
DEFAULTS = {"max_active_theses": 3, "max_parallel_deterministic_jobs": 2, "max_claude_invocations_per_job": 3}


@dataclass(frozen=True)
class Caps:
    max_parallel_claude_sessions: int
    max_claude_invocations_total: int
    max_claude_invocations_per_job: int
    max_active_theses: int
    max_parallel_deterministic_jobs: int
    model_pin: str
    governance_status: str


def get_setting(conn, key: str, default=None):
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM ros_settings WHERE key = %s", (key,)); r = cur.fetchone()
    return r[0] if r else default


def set_setting(conn, key: str, value, actor: str) -> None:
    if key in ("max_parallel_claude_sessions", "max_claude_invocations_total", "model_pin"):
        raise GovernanceError(f"{key} is governed by INFERENCE-GOVERNANCE.json; raising or changing it requires a founder amendment order")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ros_settings (key, value, set_by, set_at) VALUES (%s, %s, %s, now()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, set_by = EXCLUDED.set_by, set_at = now()", (key, json.dumps(value), actor))
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'settings.set', %s, %s)", (actor, key, json.dumps({"value": value})))
    conn.commit()


def caps(conn=None) -> Caps:
    g = load_governance()
    pin = g.model_id if g.model_id and g.model_id != MODEL_PIN_PLACEHOLDER else FOUNDER_MODEL_PIN
    per_job = DEFAULTS["max_claude_invocations_per_job"]; active = DEFAULTS["max_active_theses"]; det = DEFAULTS["max_parallel_deterministic_jobs"]
    if conn is not None:
        per_job = int(get_setting(conn, "max_claude_invocations_per_job", per_job)); active = int(get_setting(conn, "max_active_theses", active)); det = int(get_setting(conn, "max_parallel_deterministic_jobs", det))
    total = int(g.max_claude_code_invocations or 0)
    return Caps(int(g.max_concurrent_sessions or 1), total, min(per_job, total or per_job), active, det, pin, g.inference_state)


def preflight_evidence(timeout: float = 30.0) -> dict:
    """Documented zero-inference commands only: `claude --version`, `claude auth status --json`. Returns class-level evidence (identifiers dropped)."""
    exe = shutil.which("claude")
    out = {"claude_executable": bool(exe), "cli_version": None, "auth": None, "auth_class": None, "contamination_presence": contamination(), "at": datetime.now(timezone.utc).isoformat()}
    if not exe:
        return out
    try:
        cp = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, shell=False, stdin=subprocess.DEVNULL)
        out["cli_version"] = (cp.stdout or cp.stderr).strip() or None
        cp = subprocess.run([exe, "auth", "status", "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, shell=False, stdin=subprocess.DEVNULL)
        doc = json.loads(cp.stdout or "{}")
        out["auth"] = {k: doc.get(k) for k in AUTH_FIELDS}
        out["auth_class"] = classify_auth(out["auth"])
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        out["error"] = type(e).__name__
    return out


def classify_auth(a: dict | None) -> str | None:
    if not a or not a.get("loggedIn"):
        return None
    if a.get("apiProvider") != "firstParty":
        return "THIRD_PARTY_CLOUD"
    if a.get("authMethod") == "claude.ai" and str(a.get("subscriptionType", "")).lower() == "max":
        return "MAX_SUBSCRIPTION"
    if a.get("authMethod") == "console" or a.get("subscriptionType") in (None, "", "none"):
        return "CONSOLE_PAYG"
    return "OTHER_SUBSCRIPTION"


def record_attestation(conn, evidence: dict, actor: str) -> dict:
    """Founder-triggered; stores class-level evidence only."""
    if actor != "founder":
        raise GovernanceError("only the founder records auth evidence")
    rec = {"auth_class": evidence.get("auth_class"), "auth": evidence.get("auth"), "cli_version": evidence.get("cli_version"), "contamination_presence": evidence.get("contamination_presence"), "at": evidence.get("at") or datetime.now(timezone.utc).isoformat()}
    set_setting(conn, "claude_auth", rec, actor)
    return rec


def attestation(conn) -> dict:
    rec = get_setting(conn, "claude_auth")
    if not rec:
        return {"present": False, "fresh": False, "auth_class": None}
    try:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(rec["at"])).total_seconds() / 3600
    except (KeyError, ValueError):
        age_h = 1e9
    return {**rec, "present": True, "age_h": round(age_h, 2), "fresh": age_h <= ATTESTATION_TTL_H}


def quota_state(conn) -> dict:
    return get_setting(conn, "quota_state", {"state": "OK"})


def set_quota_state(conn, state: str, actor: str, detail: str = "") -> dict:
    if state not in ("OK", "USAGE_LIMIT_REACHED"):
        raise ValueError(state)
    if state == "OK" and actor != "founder":
        raise GovernanceError("only the founder resets the quota state after a usage limit")
    v = {"state": state, "detail": detail, "at": datetime.now(timezone.utc).isoformat(), "by": actor}
    set_setting(conn, "quota_state", v, actor)
    return v


def running_counts(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT kind, count(*) FROM ros_jobs WHERE state = 'running' GROUP BY kind"); rows = dict(cur.fetchall())
        cur.execute("SELECT count(DISTINCT thesis_id) FROM ros_jobs WHERE state IN ('running','queued') AND thesis_id IS NOT NULL"); active = cur.fetchone()[0]
    return {"claude": sum(int(v) for k, v in rows.items() if k in CLAUDE_KINDS), "deterministic": sum(int(v) for k, v in rows.items() if k in DETERMINISTIC_KINDS), "active_theses": int(active)}


def state(conn) -> dict:
    c = caps(conn)
    return {"caps": c.__dict__, "running": running_counts(conn), "quota": quota_state(conn), "attestation": attestation(conn), "contamination_presence": contamination(),
            "cap_change_path": "founder amendment order (INFERENCE-GOVERNANCE.json); not settable via API"}


def can_dispatch(conn, kind: str) -> tuple[bool, str]:
    c = caps(conn); r = running_counts(conn)
    if kind in CLAUDE_KINDS:
        if c.governance_status not in ("LIFTED_WITH_CONDITIONS", "LIFTED"):
            return False, f"GOVERNANCE_STATE:{c.governance_status}"
        q = quota_state(conn)
        if q.get("state") != "OK":
            return False, "USAGE_LIMIT_REACHED"
        a = attestation(conn)
        if not a["fresh"]:
            return False, "AUTH_EVIDENCE_STALE" if a["present"] else "AUTH_EVIDENCE_MISSING"
        if a.get("auth_class") != "MAX_SUBSCRIPTION":
            return False, f"AUTH_CLASS:{a.get('auth_class')}"
        if any(contamination().values()):
            return False, "CONTAMINATED_ENV"
        if r["claude"] >= c.max_parallel_claude_sessions:
            return False, "CONCURRENCY_CAP"
        return True, "OK"
    if r["deterministic"] >= c.max_parallel_deterministic_jobs:
        return False, "DETERMINISTIC_CAP"
    return True, "OK"


def pre_run_gate(conn, job: dict, thesis_state: str | None, agent_ceiling: str, thesis_states: tuple[str, ...], repo_dirty: bool | None = None) -> dict:
    """§75 pre-run integrity gate for a Claude job — evaluated at founder Start and again at dispatch."""
    c = caps(conn); q = quota_state(conn); a = attestation(conn)
    checks = {"db_ok": True, "governance_lifted": c.governance_status in ("LIFTED_WITH_CONDITIONS", "LIFTED"), "quota_ok": q.get("state") == "OK", "auth_evidence_fresh": a["fresh"], "auth_class_max": a.get("auth_class") == "MAX_SUBSCRIPTION",
              "contamination_clean": not any(contamination().values()), "model_pin_present": bool(c.model_pin), "job_is_claude_kind": job["kind"] in CLAUDE_KINDS, "job_waiting_or_queued": job["state"] in ("waiting_governance", "queued")}
    if job["kind"] == "radar_process":
        checks["radar_item_known"] = bool((job.get("payload") or {}).get("radar_id"))
    if job["kind"] == "thesis_advance":
        checks["thesis_known"] = thesis_state is not None
        checks["thesis_below_agent_ceiling"] = thesis_state is not None and thesis_state in thesis_states and thesis_states.index(thesis_state) < thesis_states.index(agent_ceiling)
    if repo_dirty is not None:
        checks["repo_head_clean_for_worktree"] = True   # worktrees branch from HEAD; a dirty main tree does not enter the worktree
    return {"checks": checks, "passed": all(checks.values()), "caps": c.__dict__, "at": datetime.now(timezone.utc).isoformat()}


def heartbeat(conn, worker_id: str, kind: str, host: str, kinds: list[str], current_job: int | None = None, info: dict | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO ros_worker_heartbeats (worker_id, kind, host, kinds, last_seen, current_job, info) VALUES (%s, %s, %s, %s, now(), %s, %s)
                       ON CONFLICT (worker_id) DO UPDATE SET last_seen = now(), current_job = EXCLUDED.current_job, kinds = EXCLUDED.kinds, info = EXCLUDED.info""", (worker_id, kind, host, list(kinds), current_job, json.dumps(info or {})))
    conn.commit()


def workers(conn) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT *, (now() - last_seen) < interval '30 seconds' AS alive FROM ros_worker_heartbeats ORDER BY kind, worker_id"); return cur.fetchall()
