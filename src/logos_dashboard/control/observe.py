"""Observability: every trace of a run in one place — lab health, MLflow, Langfuse, OTel, artifacts, Playwright QA.

Read-only. Credentials (Langfuse keys) stay on the server: the API returns data, never a key. A system that cannot be reached is reported as
`unreachable` with the error class — never as "ok" — and a failure here degrades the view instead of breaking it.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from psycopg.rows import dict_row

MLFLOW = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:55000")
LANGFUSE = os.environ.get("LANGFUSE_HOST", "http://127.0.0.1:53000")
OTEL = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:54318")
OTEL_ZPAGES = os.environ.get("OTEL_ZPAGES", "http://127.0.0.1:55679/debug/tracez")
MINIO = os.environ.get("S3_ENDPOINT_URL", "http://127.0.0.1:59000")
EXPERIMENT = "logos-research-os"
TIMEOUT = 6.0
_CACHE: dict[str, tuple[float, Any]] = {}


def _cached(key: str, ttl: float, fn: Callable):
    now = time.time(); hit = _CACHE.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    val = fn(); _CACHE[key] = (now, val); return val


def _get_json(url: str, *, headers: dict | None = None, data: bytes | None = None, timeout: float = TIMEOUT) -> tuple[bool, Any]:
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})}, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "replace") or "null")
    except urllib.error.HTTPError as e:
        return False, {"http_status": e.code, "error": e.reason}
    except Exception as e:
        return False, {"error": f"{type(e).__name__}: {str(e)[:160]}"}


def _lf_auth() -> dict:
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-logos-local-dev"); sk = os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-logos-local-dev")
    return {"Authorization": "Basic " + base64.b64encode(f"{pk}:{sk}".encode()).decode()}      # stays server-side


# -- health ---------------------------------------------------------------------------------------------------------

def systems(conn=None) -> list[dict]:
    """One row per system. Truthful: reachable / unreachable / not configured, with the endpoint and what it is for."""
    out: list[dict] = []

    def row(name: str, purpose: str, endpoint: str, ok: bool, detail: Any = None, link: str | None = None, criticality: str = "OBSERVABILITY"):
        out.append({"system": name, "purpose": purpose, "endpoint": endpoint, "state": "reachable" if ok else "unreachable", "detail": detail, "link": link or endpoint, "criticality": criticality})

    ok, d = _get_json(f"{MLFLOW}/api/2.0/mlflow/experiments/get-by-name?experiment_name={EXPERIMENT}")
    row("MLflow", "Lauf-Parameter, Metriken, Artefakte", MLFLOW, ok, (d.get("experiment", {}) if ok else d), f"{MLFLOW}/#/experiments/{(d.get('experiment', {}) or {}).get('experiment_id', '')}" if ok else MLFLOW)
    ok, d = _get_json(f"{LANGFUSE}/api/public/health")
    row("Langfuse", "LLM-Generationen (Prompt, Antwort, Tokens)", LANGFUSE, ok, d, LANGFUSE)
    ok, d = _get_json(f"{OTEL}/v1/traces")
    row("OTel-Collector", "Spans je Phase (lokal, Export nur ins Collector-Log)", OTEL, ok or (isinstance(d, dict) and d.get("http_status") in (400, 405, 415)), d, OTEL_ZPAGES)
    try:
        from logos_research.infra.backends import backends_from_env
        be = backends_from_env()
        repo = be["repository"]
        try:
            repo.connect()
        except Exception:
            pass
        h = repo.health(); row("Postgres (Labor)", "kanonische Records, Preregistrations, ros_*", str(h.detail)[:80], h.status in ("HEALTHY", "PERSISTENT"), {"status": h.status, "version": h.version, "detail": str(h.detail)[:80]}, None, "CANONICAL")
        try:
            repo.close()
        except Exception:
            pass
        h = be["artifacts"].health(); row("MinIO", "Artefakte (inhaltsadressiert)", MINIO, h.status in ("HEALTHY", "PERSISTENT"), {"status": h.status, "version": h.version, "detail": str(h.detail)[:120]}, MINIO, "CANONICAL")
    except Exception as e:
        row("Postgres (Labor)", "kanonische Records", "", False, {"error": f"{type(e).__name__}: {str(e)[:120]}"}, None, "CANONICAL")
        row("MinIO", "Artefakte", MINIO, False, {"error": "adapters unavailable"}, MINIO, "CANONICAL")
    if conn is not None:
        from . import governor, procs
        hs = procs.host_status(conn); row("Host-Executor", "Claude-Jobs (Agenten, Messläufe)", "lokaler Prozess", bool(hs["alive"]), {k: hs[k] for k in ("pid", "current_job", "last_seen")}, "/#workers", "EXECUTION")
        ds = procs.docker_status(conn); row("Docker-Worker", "Tests, Benchmarks, Snapshots", "compose ros-worker", bool(ds["alive"]), {k: ds[k] for k in ("container_running", "current_job", "last_seen")}, "/system/workers", "EXECUTION")
        a = governor.attestation(conn); row("Claude-Auth", "Nachweis der Max-Anmeldung (24 h)", "claude auth status", bool(a.get("fresh")), {k: a.get(k) for k in ("auth_class", "age_h", "cli_version")}, "/system/claude", "GOVERNANCE")
    return out


# -- MLflow ---------------------------------------------------------------------------------------------------------

def mlflow_experiment(limit: int = 50) -> dict:
    ok, exp = _get_json(f"{MLFLOW}/api/2.0/mlflow/experiments/get-by-name?experiment_name={EXPERIMENT}")
    if not ok:
        return {"reachable": False, "detail": exp, "runs": [], "experiment_id": None, "ui": MLFLOW}
    eid = (exp.get("experiment") or {}).get("experiment_id")
    ok, res = _get_json(f"{MLFLOW}/api/2.0/mlflow/runs/search", data=json.dumps({"experiment_ids": [eid], "max_results": limit, "order_by": ["attributes.start_time DESC"]}).encode())
    runs = []
    for r in (res.get("runs") or []) if ok else []:
        info = r.get("info", {}); data = r.get("data", {})
        runs.append({"mlflow_run_id": info.get("run_uuid") or info.get("run_id"), "name": info.get("run_name"), "status": info.get("status"), "start": info.get("start_time"), "end": info.get("end_time"),
                     "params": {p["key"]: p["value"] for p in data.get("params", [])}, "metrics": {m["key"]: m["value"] for m in data.get("metrics", [])},
                     "tags": {t["key"]: t["value"] for t in data.get("tags", []) if t["key"].startswith("logos.")}, "ui": f"{MLFLOW}/#/experiments/{eid}/runs/{info.get('run_uuid') or info.get('run_id')}"})
    return {"reachable": True, "experiment_id": eid, "experiment": EXPERIMENT, "runs": runs, "n": len(runs), "ui": f"{MLFLOW}/#/experiments/{eid}", "detail": None if ok else res}


def mlflow_run(mlflow_run_id: str) -> dict:
    ok, d = _get_json(f"{MLFLOW}/api/2.0/mlflow/runs/get?run_id={mlflow_run_id}")
    if not ok:
        return {"reachable": False, "detail": d}
    r = d.get("run", {}); info = r.get("info", {}); data = r.get("data", {})
    ok2, arts = _get_json(f"{MLFLOW}/api/2.0/mlflow/artifacts/list?run_id={mlflow_run_id}")
    return {"reachable": True, "status": info.get("status"), "params": {p["key"]: p["value"] for p in data.get("params", [])}, "metrics": {m["key"]: m["value"] for m in data.get("metrics", [])},
            "artifacts": [a.get("path") for a in (arts.get("files") or [])] if ok2 else [], "ui": f"{MLFLOW}/#/experiments/{info.get('experiment_id')}/runs/{mlflow_run_id}"}


# -- Langfuse -------------------------------------------------------------------------------------------------------

def langfuse_traces(limit: int = 30, session_id: str | None = None) -> dict:
    q = f"?limit={limit}" + (f"&sessionId={session_id}" if session_id else "")
    ok, d = _get_json(f"{LANGFUSE}/api/public/traces{q}", headers=_lf_auth())
    if not ok:
        return {"reachable": False, "detail": d, "traces": [], "ui": LANGFUSE}
    traces = []
    for t in (d.get("data") or []):
        obs = t.get("observations") or []
        traces.append({"trace_id": t.get("id"), "name": t.get("name"), "session_id": t.get("sessionId"), "timestamp": t.get("timestamp"), "tags": t.get("tags"),
                       "latency_s": t.get("latency"), "total_cost": t.get("totalCost"), "observations": len(obs) if isinstance(obs, list) else obs,
                       "metadata": {k: v for k, v in (t.get("metadata") or {}).items() if str(k).startswith("logos.")}, "ui": f"{LANGFUSE}/trace/{t.get('id')}"})
    return {"reachable": True, "traces": traces, "n": len(traces), "ui": LANGFUSE}


def langfuse_observations(trace_id: str) -> dict:
    ok, d = _get_json(f"{LANGFUSE}/api/public/observations?traceId={trace_id}&limit=50", headers=_lf_auth())
    if not ok:
        return {"reachable": False, "detail": d, "observations": []}
    out = []
    for o in (d.get("data") or []):
        out.append({"id": o.get("id"), "type": o.get("type"), "name": o.get("name"), "model": o.get("model"), "usage": o.get("usage"), "latency_s": o.get("latency"), "level": o.get("level"),
                    "start": o.get("startTime"), "end": o.get("endTime")})
    return {"reachable": True, "observations": out, "n": len(out)}


# -- one run, all traces ----------------------------------------------------------------------------------------------

def all_traces(conn, run_id: str) -> dict:
    """Every trace of one run: DB events, MLflow run, Langfuse trace, OTel ids, artifacts, branch/commit."""
    from . import runs as R, telemetry as T
    run = R.get_run(conn, run_id)
    if run is None:
        return {"found": False, "run_id": run_id}
    events = R.events_after(conn, run_id, 0, 3000)
    links = T.trace_links(conn, run_id); arts = T.artifacts(conn, run_id)
    tl = (run.get("summary") or {}).get("telemetry") or {}
    ml_id = next((l["mlflow_run_id"] for l in links if l.get("mlflow_run_id")), None)
    ml = mlflow_run(ml_id) if ml_id and not str(ml_id).startswith("null-") else {"reachable": False, "detail": {"reason": "no MLflow run (telemetry stack was null)"} if ml_id else {"reason": "no MLflow link"}}
    lf_id = tl.get("langfuse_trace_id")
    lf = langfuse_observations(lf_id) if lf_id else {"reachable": False, "detail": {"reason": "no Langfuse trace"}, "observations": []}
    done = next((e["payload"] for e in events if e["kind"] == "done"), None)
    return {"found": True, "run": run, "n_events": len(events), "mlflow": {"run_id": ml_id, **ml}, "langfuse": {"trace_id": lf_id, "ui": f"{LANGFUSE}/trace/{lf_id}" if lf_id else LANGFUSE, **lf},
            "otel": {"trace_ids": [l["trace_id"] for l in links if l.get("trace_id")], "zpages": OTEL_ZPAGES, "note": "the local collector exports to its own log (debug exporter); span bodies are not queryable"},
            "artifacts": arts, "branch": run.get("branch"), "commit": (done or {}).get("commit"), "worktree": run.get("worktree"), "telemetry_degraded": tl.get("degraded", [])}


def overview(conn, limit: int = 30) -> dict:
    from . import runs as R
    rs = R.list_runs(conn, limit)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT run_id, mlflow_run_id, trace_id FROM ros_trace_links"); links: dict[str, dict] = {}
        for run_id, ml, tr in cur.fetchall():
            d = links.setdefault(run_id, {"mlflow_run_id": None, "otel": []}); d["mlflow_run_id"] = d["mlflow_run_id"] or ml
            if tr:
                d["otel"].append(tr)
    for r in rs:
        r["links"] = links.get(r["run_id"], {"mlflow_run_id": None, "otel": []})
    return {"systems": systems(conn), "mlflow": _cached("mlflow_exp", 15.0, lambda: mlflow_experiment(50)), "langfuse": _cached("lf_traces", 15.0, lambda: langfuse_traces(30)), "runs": rs,
            "otel": {"endpoint": OTEL, "zpages": OTEL_ZPAGES, "note": "lokaler Collector, Debug-Exporter: Spans liegen im Container-Log, kein Abfrage-API"},
            "note": "Zugangsschlüssel bleiben im Server; diese Antwort enthält keine Schlüssel."}
