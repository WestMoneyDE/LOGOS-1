"""Governed measurement run: executes a FROZEN preregistration item by item through the documented Claude Code path.

Contract (differs from agent jobs on purpose):
  * `ClaudeCodeMaxProvider` with `--output-format json` and **no `--verbose`** — the flag amendment covers agent jobs only.
  * one invocation per dataset item, budget = planned + retry reserve ≤ caps.max_invocations, counters incremented by the provider.
  * stops closed: cap reached, `USAGE_LIMIT_REACHED` (quota state set, job -> waiting_quota), model drift, dataset/prompt drift, contamination.
  * scoring is deterministic (`measurement_contract.SCORERS`) and happens after each answer; unscorable answers are missingness.
  * the verdict is DERIVED from the frozen falsification rule and proposed to the founder; nothing is written into a registry here.
"""
from __future__ import annotations

import json
import os
import time
from hashlib import sha256
from pathlib import Path

from psycopg.rows import dict_row

from logos_research.measurement.claude_code import ActivationToken, ClaudeCodeMaxProvider, Limits, ProviderPolicyError, contamination

from .. import measurement_contract as mc
from . import governor, prereg, queue, runs, service, telemetry
from .state_machines import IllegalTransition

CONTRACT = mc.MEASUREMENT_SCHEMA
RETRY_RESERVE = 2


def budget(planned: int, cap: int, reserve: int = RETRY_RESERVE) -> dict:
    return {"planned": planned, "reserve": reserve, "cap": cap, "ok": planned > 0 and planned + reserve <= cap}


def _mid(thesis_id: str, job_id: int) -> str:
    return f"M-{thesis_id}-{job_id}"


def prepare(conn, thesis_id: str, job_id: int, worktree: Path | None = None) -> dict:
    """Everything that must hold before a single model call: frozen prereg, unchanged hashes, budget, gates."""
    d = service.thesis_detail(conn, thesis_id)
    if d is None:
        raise KeyError(thesis_id)
    th = d["thesis"]; h = th.get("prereg_hash")
    if not h:
        return {"ok": False, "reason": "no frozen preregistration"}
    payload = prereg.frozen_payload(thesis_id, h)
    if payload is None:
        return {"ok": False, "reason": "frozen preregistration not readable from the lab"}
    bundle = prereg.read_bundle(thesis_id, worktree)
    if bundle["missing"] or bundle["errors"]:
        return {"ok": False, "reason": f"files missing/invalid: {bundle['missing'] + bundle['errors']}"}
    ds, pr, m = bundle["DATASET.json"], bundle["PROMPTS.json"], bundle["MEASUREMENT.json"]
    ds_h, pb_h = mc.dataset_hash(ds), mc.prompt_bundle_hash(pr)
    if ds_h != payload.get("dataset_hash"):
        return {"ok": False, "reason": "DATASET_DRIFT", "invalid": "DATASET_DRIFT"}
    if pb_h != payload.get("prompt_bundle_hash"):
        return {"ok": False, "reason": "PROMPT_DRIFT", "invalid": "PROMPT_DRIFT"}
    caps_m = m.get("caps") or {}
    b = budget(len(ds["items"]), int(caps_m.get("max_invocations") or 0))
    if not b["ok"]:
        return {"ok": False, "reason": f"budget refused: {b}"}
    if any(contamination().values()):
        return {"ok": False, "reason": "CONTAMINATED_ENV", "invalid": "PROVIDER_DRIFT"}
    caps = governor.caps(conn)
    return {"ok": True, "thesis": th, "payload": payload, "dataset": ds, "prompts": pr, "measurement": m, "dataset_hash": ds_h, "prompt_bundle_hash": pb_h, "budget": b, "model_pin": caps.model_pin, "prereg_hash": h,
            "work_order_id": (next((w["work_order_id"] for w in d["work_orders"] if w["state"] in ("APPROVED", "READY", "RUNNING")), None))}


def run_measurement(conn, job: dict, cfg, *, worktree: Path | None = None, provider_factory=None) -> dict:
    """Execute one measurement job (already dequeued, state running). `cfg` is the ExecutorConfig (repo, runner_factory, cli_version, telemetry)."""
    job_id = job["job_id"]; thesis_id = job["thesis_id"]
    run_id = f"RUN-{job_id}-{int(time.time())}"
    p = prepare(conn, thesis_id, job_id, worktree)
    run = runs.create_run(conn, run_id, job_id=job_id, kind="measurement", thesis_id=thesis_id, work_order_id=job.get("work_order_id"))
    tel = telemetry.RunTelemetry(conn, cfg.telemetry_stack, run_id, thesis_id, job_id, "measurement")
    tel.start({"kind": "measurement", "cli_version": cfg.cli_version or ""})
    runs.emit(conn, run_id, "gate", {"checks": {"prepared": p["ok"]}, "passed": p["ok"], "reason": p.get("reason"), "caps": governor.caps(conn).__dict__})
    if not p["ok"]:
        runs.emit(conn, run_id, "error", {"reason": p["reason"]}); runs.finish_run(conn, run_id, "failed", p["reason"]); tel.finish("failed", None)
        prereg.log_gate(conn, thesis_id, "measurement", "system", False, {"reason": p["reason"]})
        from .executor import _set_state
        return _set_state(conn, job_id, "failed", f"MEASUREMENT_REFUSED:{p['reason'][:120]}")
    _ensure_running(conn, job_id)
    ds, pr, m, payload = p["dataset"], p["prompts"], p["measurement"], p["payload"]
    caps_m = m.get("caps") or {}
    mid = _mid(thesis_id, job_id)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""INSERT INTO ros_measurements (measurement_id, thesis_id, work_order_id, run_id, job_id, prereg_hash, dataset_hash, prompt_bundle_hash, model_pin, state, planned)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'running', %s) ON CONFLICT (measurement_id) DO UPDATE SET run_id = EXCLUDED.run_id, state = 'running', started = now() RETURNING *""",
                    (mid, thesis_id, p["work_order_id"], run_id, job_id, p["prereg_hash"], p["dataset_hash"], p["prompt_bundle_hash"], p["model_pin"], p["budget"]["planned"]))
        meas = cur.fetchone()
    conn.commit()
    runs.emit(conn, run_id, "phase", {"phase": "measurement", "measurement_id": mid, "planned": p["budget"]["planned"], "arms": ds["arms"]})
    tel.params({"prereg_hash": p["prereg_hash"], "dataset_hash": p["dataset_hash"], "prompt_bundle_hash": p["prompt_bundle_hash"], "planned": p["budget"]["planned"], "arms": ",".join(ds["arms"]), "primary_metric": m.get("primary_metric"), "rule": json.dumps(m.get("falsification"))})
    metric = next((x for x in m["metrics"] if x["metric_id"] == m["primary_metric"]), m["metrics"][0])
    token = ActivationToken(run_id=run_id, model_pin=p["model_pin"], max_invocations=int(caps_m["max_invocations"]), max_turns=int(caps_m["max_turns"]), issued_by="logos_dashboard.control.prereg(frozen)",
                            cli_version=cfg.cli_version, contract_version=CONTRACT, dataset_hash=p["dataset_hash"], prompt_bundle_hash=p["prompt_bundle_hash"])
    provider = (provider_factory or (lambda: ClaudeCodeMaxProvider(runner=cfg.runner_factory(worktree or cfg.repo), expected_cli_version=cfg.cli_version)))()
    limits = Limits(max_turns=int(caps_m["max_turns"]), max_output_bytes=int(caps_m["max_output_bytes"]), timeout_s=float(caps_m["timeout_s"]), disallowed_tools=("Bash", "Edit", "Write", "WebFetch", "WebSearch", "NotebookEdit"), allowed_tools=())
    items = sorted(ds["items"], key=lambda it: (str(it["arm"]), str(it["item_id"])))
    executed = 0; invalid_reason = None; stop_reason = None; scored: list[dict] = []
    for n, it in enumerate(items, start=1):
        if queue.stop_requested(conn, job_id):
            stop_reason = "founder_stop"; break
        if executed >= int(caps_m["max_invocations"]):
            stop_reason = "COST_CAP_REACHED"; invalid_reason = "COST_CAP_REACHED"; break
        system_p, user_p = mc.render_prompt(pr, it["arm"], it)
        try:
            res = provider.invoke(user_p, p["model_pin"], {"run_id": run_id, "system_prompt": system_p, "kind": "measurement"}, limits, token=token, env=dict(os.environ))
        except ProviderPolicyError as e:
            stop_reason = f"POLICY_BLOCK:{str(e)[:120]}"; invalid_reason = "CONSTRUCT_INVALID"; break
        executed += 1
        status = res.status
        answer = res.content if status == "OK" else None
        score = mc.score_item(metric["scorer"], answer, it.get("expected"), metric.get("target_field")) if status == "OK" else None
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO ros_measurement_items (measurement_id, item_id, arm, invocation, status, raw_sha256, answer, score, latency_s, tokens, resolved_model)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (measurement_id, item_id) DO NOTHING""",
                        (mid, it["item_id"], it["arm"], n, status, (res.artifact_refs[0] if res.artifact_refs else None), (answer or "")[:4000], score, res.latency_s, json.dumps(res.usage_metadata or {}), res.reported_model))
            cur.execute("UPDATE ros_measurements SET executed = %s WHERE measurement_id = %s", (executed, mid))
        conn.commit()
        scored.append({"arm": it["arm"], "score": score})
        if n % 5 == 0 or n == len(items):
            runs.emit(conn, run_id, "measure.item", {"done": n, "planned": p["budget"]["planned"], "item_id": it["item_id"], "arm": it["arm"], "status": status, "score": score, "rates": mc.arm_rates(scored)})
        if status == "USAGE_LIMIT_REACHED":
            governor.set_quota_state(conn, "USAGE_LIMIT_REACHED", "system", f"measurement {mid} item {it['item_id']}")
            stop_reason = "USAGE_LIMIT_REACHED"; break
        if status == "MODEL_DRIFT":
            stop_reason = "MODEL_VERSION_DRIFT"; invalid_reason = "MODEL_VERSION_DRIFT"; break
        if status in ("AUTH_UNAVAILABLE", "AUTH_NOT_MAX_SUBSCRIPTION", "POLICY_BLOCK"):
            stop_reason = status; invalid_reason = "PROVIDER_DRIFT"; break
    rates = mc.arm_rates(scored)
    complete = executed == p["budget"]["planned"] and stop_reason is None
    if stop_reason in ("founder_stop", "USAGE_LIMIT_REACHED"):
        # an interrupted run is incomplete, not invalid: the instrument was fine, the run simply did not finish
        proposal = {"verdict": "INCONCLUSIVE", "why": f"Lauf unvollständig ({executed}/{p['budget']['planned']}): {stop_reason}", "rule": m["falsification"], "numbers": rates, "derived": True}
    else:
        proposal = mc.derive_verdict(rates, m["falsification"], comparison=m.get("comparison"), invalid_reason=invalid_reason)
    summary = {"measurement_id": mid, "planned": p["budget"]["planned"], "executed": executed, "complete": complete, "stop_reason": stop_reason, "invalid_reason": invalid_reason, "rates": rates,
               "proposal": proposal, "primary_metric": metric["metric_id"], "scorer": metric["scorer"], "prereg_hash": p["prereg_hash"], "model_pin": p["model_pin"], "contract": CONTRACT}
    state = "stopped" if stop_reason == "founder_stop" else ("waiting_quota" if stop_reason == "USAGE_LIMIT_REACHED" else "done" if complete else "failed")
    with conn.cursor() as cur:
        cur.execute("UPDATE ros_measurements SET state = %s, stop_reason = %s, invalid_reason = %s, summary = %s, finished = now() WHERE measurement_id = %s", (state, stop_reason, invalid_reason, json.dumps(summary, default=str), mid))
    conn.commit()
    tel.metrics({"executed": executed, "planned": p["budget"]["planned"], "complete": 1 if complete else 0, **{f"rate_{a}": (r["rate"] if isinstance(r["rate"], (int, float)) else 0.0) for a, r in rates.items()}})
    tel.artifact("measurement_summary.json", json.dumps(summary, sort_keys=True, default=str).encode(), "measurement")
    runs.emit(conn, run_id, "done", summary)
    links = tel.finish(state if state != "waiting_quota" else "failed", summary)
    runs.finish_run(conn, run_id, state, stop_reason, {**summary, "telemetry": links})
    prereg.log_gate(conn, thesis_id, "measurement", "system", complete, {"executed": executed, "planned": p["budget"]["planned"], "stop_reason": stop_reason, "proposal": proposal["verdict"], "measurement_id": mid})
    th_state = (service.thesis_detail(conn, thesis_id) or {}).get("thesis", {}).get("state")
    if th_state == "RUNNING":
        service.advance(conn, thesis_id, "finish_run", "system", reason=f"measurement {mid}: {executed}/{p['budget']['planned']} — Vorschlag {proposal['verdict']}", source_record=mid)
    if state == "waiting_quota":
        from .executor import _set_state
        return _set_state(conn, job_id, "waiting_quota", "USAGE_LIMIT_REACHED")
    if state == "stopped":
        return queue.stop(conn, job_id, actor="founder")
    if state == "failed":
        return queue.fail(conn, job_id, stop_reason or "INCOMPLETE", actor="system")
    return queue.complete(conn, job_id, summary, actor="system")


def _ensure_running(conn, job_id: int) -> None:
    """The runner owns the job while it executes; a job handed over as `queued` (direct call, restart) is moved to running first."""
    with conn.cursor() as cur:
        cur.execute("SELECT state FROM ros_jobs WHERE job_id = %s", (job_id,)); r = cur.fetchone()
    if r and r[0] == "queued":
        cur_state = queue._apply(conn, job_id, "dequeue", "worker")
        assert cur_state["state"] == "running"


def get(conn, measurement_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_measurements WHERE measurement_id = %s", (measurement_id,)); m = cur.fetchone()
        if m is None:
            return None
        cur.execute("SELECT * FROM ros_measurement_items WHERE measurement_id = %s ORDER BY row_id", (measurement_id,)); items = cur.fetchall()
    live = mc.arm_rates([{"arm": i["arm"], "score": i["score"]} for i in items])
    return {"measurement": m, "items": items, "rates": live, "progress": {"done": len(items), "planned": m["planned"]}}


def list_measurements(conn, thesis_id: str | None = None, limit: int = 100) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if thesis_id:
            cur.execute("SELECT * FROM ros_measurements WHERE thesis_id = %s ORDER BY started DESC LIMIT %s", (thesis_id, limit))
        else:
            cur.execute("SELECT * FROM ros_measurements ORDER BY started DESC LIMIT %s", (limit,))
        return cur.fetchall()


def decide_verdict(conn, measurement_id: str, verdict: str, actor: str, reason: str = "") -> dict:
    """Founder decision on the proposal. Writes the thesis event and a registry-update DRAFT — never a registry."""
    if actor != "founder":
        raise IllegalTransition("thesis", "ANALYSIS", "record_verdict", actor, "founder gate")
    if verdict not in mc.VERDICTS:
        raise ValueError(f"verdict must be one of {mc.VERDICTS}")
    d = get(conn, measurement_id)
    if d is None:
        raise KeyError(measurement_id)
    m = d["measurement"]; thesis_id = m["thesis_id"]; summary = m["summary"] or {}
    proposal = (summary.get("proposal") or {}).get("verdict")
    th = service.thesis_detail(conn, thesis_id)
    state = th["thesis"]["state"] if th else None
    event = {"SUPPORTED": "record_verdict", "FALSIFIED": "record_verdict", "INCONCLUSIVE": "inconclusive", "INVALID_MEASUREMENT": "invalid_measurement"}[verdict]
    if state == "ANALYSIS":
        service.advance(conn, thesis_id, event, "founder", reason=f"{verdict}: {reason or (summary.get('proposal') or {}).get('why', '')}"[:400], source_record=measurement_id)
        if verdict == "FALSIFIED":
            service.advance(conn, thesis_id, "falsified", "founder", reason="verdict FALSIFIED", source_record=measurement_id)
    draft = write_verdict_draft(thesis_id, measurement_id, verdict, proposal, summary, th, reason)
    prereg.log_gate(conn, thesis_id, "verdict", actor, True, {"verdict": verdict, "proposal": proposal, "followed_proposal": verdict == proposal, "draft": draft["path"], "measurement_id": measurement_id})
    return {"verdict": verdict, "proposal": proposal, "followed_proposal": verdict == proposal, "draft": draft, "thesis_state": (service.thesis_detail(conn, thesis_id) or {}).get("thesis", {}).get("state")}


def write_verdict_draft(thesis_id: str, measurement_id: str, verdict: str, proposal: str | None, summary: dict, th: dict | None, reason: str) -> dict:
    from .. import registries
    d = registries.DASH / "verdict-drafts"; d.mkdir(exist_ok=True)
    path = d / f"{thesis_id}-{measurement_id}.json"
    claims = (th or {}).get("thesis", {}).get("claim_ids") or []
    doc = {"schema": "logos.verdict-draft/1", "thesis_id": thesis_id, "measurement_id": measurement_id, "decided_by": "founder", "decided_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
           "verdict": verdict, "derived_proposal": proposal, "followed_proposal": verdict == proposal, "founder_reason": reason,
           "BEFORE": {"claims": claims, "registry_change": "none"},
           "PROPOSED": {"claims": claims, "note": f"Messlauf {measurement_id} ({summary.get('executed')}/{summary.get('planned')} Datenpunkte) → {verdict}", "status_change": "NONE — a status change needs a governed order and the founder's registry edit"},
           "EVIDENCE": {"prereg_hash": summary.get("prereg_hash"), "model_pin": summary.get("model_pin"), "primary_metric": summary.get("primary_metric"), "scorer": summary.get("scorer"), "rates": summary.get("rates"), "rule": (summary.get("proposal") or {}).get("rule"), "why": (summary.get("proposal") or {}).get("why")},
           "WHY": (summary.get("proposal") or {}).get("why"),
           "WHAT_WOULD_FALSIFY_IT": "ein Replikationslauf mit derselben eingefrorenen Preregistration, der das Konfidenzintervall auf die andere Seite der Regel legt",
           "registry_change": "NONE — this file is a draft for the founder; registries are edited by a governed order only"}
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"path": str(path.relative_to(registries.DASH.parents[2])).replace("\\", "/"), "doc": doc}
