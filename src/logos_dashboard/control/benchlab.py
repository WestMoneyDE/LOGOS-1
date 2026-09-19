"""Benchmark lab persistence: suite definitions (DRAFT until founder approval), metric results, immutable snapshots, monthly progress."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from psycopg.rows import dict_row

from .. import benchmarks as bm, stats


def sync_definitions(conn) -> list[dict]:
    d = bm.definitions()
    with conn.cursor(row_factory=dict_row) as cur:
        for sid, spec in d["suites"].items():
            cur.execute("""INSERT INTO ros_benchmark_suites (suite_id, definition, definition_sha256) VALUES (%s, %s, %s)
                           ON CONFLICT (suite_id) DO UPDATE SET definition = EXCLUDED.definition, definition_sha256 = EXCLUDED.definition_sha256, updated_at = now(),
                           status = CASE WHEN ros_benchmark_suites.definition_sha256 <> EXCLUDED.definition_sha256 THEN 'DRAFT_PENDING_FOUNDER_APPROVAL' ELSE ros_benchmark_suites.status END""",
                        (sid, json.dumps({**spec, "hard_gates": d["hard_gates"], "modes": d["modes"], "version": d["version"]}), d["sha256"]))
        conn.commit()
        cur.execute("SELECT * FROM ros_benchmark_suites ORDER BY suite_id"); return cur.fetchall()


def approve_definition(conn, suite_id: str, actor: str) -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("benchmark definitions are approved by the founder only")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("UPDATE ros_benchmark_suites SET status = 'APPROVED', approved_by = %s, approved_at = now() WHERE suite_id = %s RETURNING *", (actor, suite_id)); row = cur.fetchone()
        if row is None:
            raise KeyError(suite_id)
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'benchmark.approve_definition', %s, %s)", (actor, suite_id, json.dumps({"sha256": row["definition_sha256"]})))
    conn.commit()
    return row


def record_metric(conn, suite_id: str, mode: str, metric: str, k: int | None, n: int | None, context: dict, run_id: str | None = None, job_id: int | None = None) -> dict:
    w = stats.wilson(k, n) if (k is not None and n is not None) else None
    val = w["value"] if w and w["value"] != stats.NOT_DEFINED else None; ci = w["ci95"] if w and w["ci95"] else (None, None)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_metric_results (suite_id, mode, metric, k, n, value, ci_low, ci_high, method, version, context, run_id, job_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'wilson', %s, %s, %s, %s) RETURNING *",
                    (suite_id, mode, metric, k, n, val, ci[0], ci[1], stats.VERSION, json.dumps(context), run_id, job_id)); row = cur.fetchone()
    conn.commit()
    return row


def latest_results(conn, suite_id: str | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""SELECT DISTINCT ON (suite_id, mode, metric) * FROM ros_metric_results """ + ("WHERE suite_id = %s " if suite_id else "") + "ORDER BY suite_id, mode, metric, result_id DESC", (suite_id,) if suite_id else ())
        return cur.fetchall()


def scorecard(conn) -> dict:
    d = bm.definitions(); res = latest_results(conn); by = {(r["suite_id"], r["mode"], r["metric"]): r for r in res}
    out = {}
    for sid, spec in d["suites"].items():
        rows = []
        for mode in ("LOGOS_AGENT", "BASELINE_AGENT", "LOGOS_ABLATION", "DETERMINISTIC"):
            for metric in spec["dimensions"]:
                r = by.get((sid, mode, metric))
                rows.append({**bm.scorecard_row(metric, r["k"] if r else None, r["n"] if r else None, context=(r["context"] if r else {"mode": mode})), "mode": mode, "recorded_at": r["created_at"] if r else None})
        out[sid] = {"rows": rows, "gates": bm.hard_gate_verdict([r for r in rows if r["mode"] == "DETERMINISTIC"]), "track": spec["track"], "fixtures": spec["fixtures"]}
    return {"definitions": d, "suites": out, "modes_note": d["note"]}


def freeze_snapshot(conn, suite_id: str, mode: str, actor: str, run_id: str | None = None, month: str | None = None) -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("snapshots are frozen by the founder only")
    res = [r for r in latest_results(conn, suite_id) if r["mode"] == mode]
    if not res:
        raise ValueError(f"no results for {suite_id}/{mode}")
    rows = [bm.scorecard_row(r["metric"], r["k"], r["n"], context=r["context"]) for r in res]
    payload = bm.snapshot_payload(suite_id, mode, rows, {"results": [r["result_id"] for r in res]}, month)
    sid = f"{suite_id}:{mode}:{payload['month']}:{payload['sha256'][:12]}"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_benchmark_snapshots (snapshot_id, suite_id, mode, month, run_id, payload, sha256) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *", (sid, suite_id, mode, payload["month"], run_id, json.dumps(payload, default=str), payload["sha256"])); row = cur.fetchone()
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'benchmark.freeze_snapshot', %s, %s)", (actor, sid, json.dumps({"sha256": payload["sha256"]})))
    conn.commit()
    return row


def snapshots(conn, suite_id: str | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_benchmark_snapshots " + ("WHERE suite_id = %s " if suite_id else "") + "ORDER BY created_at DESC", (suite_id,) if suite_id else ()); return cur.fetchall()


def month_over_month(conn, suite_id: str, mode: str) -> dict:
    snaps = [s for s in snapshots(conn, suite_id) if s["mode"] == mode]
    if len(snaps) < 2:
        return {"status": "NOT_COMPARABLE", "reason": "fewer than two snapshots"}
    cur, prev = snaps[0]["payload"], snaps[1]["payload"]
    comp = bm.comparability({**cur["context"], "definition_version": cur["definition_version"], "suite": suite_id, "mode": mode}, {**prev["context"], "definition_version": prev["definition_version"], "suite": suite_id, "mode": mode})
    if comp["badge"] != "COMPARABLE":
        return {"status": "NOT_COMPARABLE", "reason": comp["reasons"], "current": cur["month"], "previous": prev["month"]}
    deltas = []
    pm = {r["metric"]: r for r in prev["rows"]}
    for r in cur["rows"]:
        p = pm.get(r["metric"])
        if p and r["n"] and p["n"]:
            d = stats.newcombe(r["k"], r["n"], p["k"], p["n"]); deltas.append({"metric": r["metric"], "delta": d["value"], "ci95": d["ci95"], "pp": stats.pp_delta(r["value"], p["value"])["value"]})
    return {"status": "COMPARABLE", "current": cur["month"], "previous": prev["month"], "deltas": deltas}


def monthly_progress(conn, closures: list[dict], regs: dict, month: str | None = None) -> dict:
    """Monthly progress (§34) from repository records + the run table. Counts only; rates carry Wilson CIs; NOT_DEFINED on empty denominators."""
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    cl = [c for c in closures if (c.get("closed") or "").startswith(month)]
    n = len(cl); fals = sum(1 for c in cl if c.get("verdict_class") == "falsified"); inv = sum(1 for c in cl if c.get("verdict_class") == "invalid"); sup = sum(1 for c in cl if c.get("verdict_class") in ("supported", "validated", "partial"))
    reps = regs["replication"]["replications"]; covered = sum(1 for r in reps if r.get("count") != "0/5")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*), count(*) FILTER (WHERE state = 'done'), avg(EXTRACT(EPOCH FROM (finished - started))) FROM ros_runs WHERE to_char(created_at, 'YYYY-MM') = %s", (month,)); runs_n, runs_done, avg_s = cur.fetchone()
        cur.execute("SELECT count(*) FROM ros_theses WHERE to_char(created_at, 'YYYY-MM') = %s", (month,)); theses_new = cur.fetchone()[0]
    return {"month": month, "closures": n, "verdicts": {"supported_or_partial": sup, "falsified": fals, "invalid_measurement": inv},
            "falsification_rate": stats.wilson(fals, n), "invalid_measurement_rate": stats.wilson(inv, n), "replication_coverage": stats.wilson(covered, len(reps)),
            "agent_runs": int(runs_n or 0), "agent_run_success": stats.wilson(int(runs_done or 0), int(runs_n or 0)), "mean_run_seconds": float(avg_s) if avg_s is not None else stats.NOT_DEFINED, "theses_created": int(theses_new or 0),
            "time_to_verdict": "NOT_DEFINED (order start timestamps are not recorded in closures)", "version": stats.VERSION}


def freeze_month(conn, payload: dict, actor: str) -> dict:
    if actor != "founder":
        from logos_research.governance import GovernanceError
        raise GovernanceError("monthly snapshots are frozen by the founder only")
    h = __import__("hashlib").sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("INSERT INTO ros_monthly_snapshots (month, payload, sha256, frozen_by) VALUES (%s, %s, %s, %s) RETURNING *", (payload["month"], json.dumps(payload, default=str), h, actor)); row = cur.fetchone()
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'progress.freeze_month', %s, %s)", (actor, payload["month"], json.dumps({"sha256": h})))
    conn.commit()
    return row


def months(conn) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_monthly_snapshots ORDER BY month DESC"); return cur.fetchall()
