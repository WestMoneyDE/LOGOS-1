"""Observability mirror for executor runs (spec §7): MLflow run + OTel spans + Langfuse generation, linked in `ros_trace_links`.

OBSERVABILITY criticality: every failure degrades (listed in `degraded`, surfaced as a `note` event) and never blocks the job. The canonical
record remains `ros_run_events` + the run branch. No secret enters a tag, param or trace attribute; contamination is presence-only.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from psycopg.rows import dict_row

MLFLOW_EXPERIMENT = "logos-research-os"


@dataclass
class NullTracker:
    """Records calls in memory (tests, or stack unavailable)."""
    runs: dict = field(default_factory=dict); params: dict = field(default_factory=dict); metrics: dict = field(default_factory=dict); ended: dict = field(default_factory=dict); artifacts: dict = field(default_factory=dict)
    experiment_name: str = MLFLOW_EXPERIMENT
    def start_run(self, identity, run_id, tags):
        self.runs[run_id] = dict(tags); return type("R", (), {"mlflow_run_id": f"null-{run_id}", "mlflow_experiment_id": "0"})()
    def log_params(self, run_id, params): self.params.setdefault(run_id, {}).update(params)
    def log_metrics(self, run_id, metrics): self.metrics.setdefault(run_id, {}).update(metrics)
    def log_artifact(self, run_id, name, payload: bytes): self.artifacts.setdefault(run_id, {})[name] = payload
    def end_run(self, run_id, status): self.ended[run_id] = status
    def fetch(self, mlflow_run_id): return {"run_id": mlflow_run_id, "status": "FINISHED", "tags": {}, "metrics": {}, "params": {}}


@dataclass
class NullSpans:
    spans: list = field(default_factory=list)
    def emit(self, identity, run_id, span, attributes):
        self.spans.append((run_id, span, dict(attributes))); return type("R", (), {"otel_trace_id": f"{len(self.spans):032x}"})()
    def flush(self): pass


@dataclass
class NullGenerations:
    generations: list = field(default_factory=list)
    def emit_generation(self, identity, run_id, payload):
        self.generations.append((run_id, dict(payload))); return type("R", (), {"langfuse_trace_id": f"lf-{run_id}"})()


@dataclass(frozen=True)
class Identity:
    """Minimal identity for the lab adapters (they only read these fields)."""
    experiment_id: str
    experiment_revision: int = 1
    preregistration_hash: str = "ros-agent-job"
    git_sha: str = ""
    gamma_version: str = ""
    environment_id: str = "research-os"


def null_stack() -> dict:
    return {"tracker": NullTracker(), "traces": NullSpans(), "llm_traces": NullGenerations(), "kind": "null"}


def stack_from_env() -> dict:
    """Real lab adapters (MLflow 127.0.0.1:55000, OTel collector, Langfuse). Import lazily; fall back to the null stack when unavailable."""
    try:
        from logos_research.infra.backends import backends_from_env
        be = backends_from_env()
        tracker = be["tracker"]; tracker.experiment_name = MLFLOW_EXPERIMENT
        return {"tracker": tracker, "traces": be["traces"], "llm_traces": be["llm_traces"], "kind": "lab"}
    except Exception:
        return null_stack()


def _mlflow_log_artifact(tracker, run_id: str, name: str, payload: bytes) -> None:
    if hasattr(tracker, "log_artifact"):
        tracker.log_artifact(run_id, name, payload); return
    import tempfile, pathlib
    mlflow = tracker._mlflow()
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / name; p.write_bytes(payload); mlflow.log_artifact(str(p))


class RunTelemetry:
    def __init__(self, conn, stack: dict, run_id: str, thesis_id: str | None, job_id: int, kind: str):
        self.conn, self.stack, self.run_id, self.thesis_id, self.job_id, self.kind = conn, stack, run_id, thesis_id, job_id, kind
        self.identity = Identity(experiment_id=f"ROS-{thesis_id or 'nothesis'}")
        self.mlflow_run_id: str | None = None; self.mlflow_experiment_id: str | None = None; self.trace_ids: list[str] = []; self.langfuse_id: str | None = None
        self.degraded: list[str] = []; self.artifacts: list[dict] = []; self._t0 = time.time()

    def _try(self, what: str, fn):
        try:
            return fn()
        except Exception as e:
            self.degraded.append(f"{what}: {type(e).__name__}: {str(e)[:120]}"); return None

    def start(self, tags: dict) -> None:
        def go():
            refs = self.stack["tracker"].start_run(self.identity, self.run_id, {"logos.run_id": self.run_id, "logos.thesis_id": self.thesis_id or "", "logos.job_id": str(self.job_id), "logos.kind": self.kind, **{k: str(v) for k, v in tags.items()}})
            self.mlflow_run_id, self.mlflow_experiment_id = refs.mlflow_run_id, getattr(refs, "mlflow_experiment_id", None)
        self._try("mlflow.start_run", go)
        self.span("run.start", {"phase": "start"})
        self._link()

    def params(self, params: dict) -> None:
        self._try("mlflow.log_params", lambda: self.stack["tracker"].log_params(self.run_id, {k: str(v)[:500] for k, v in params.items()}))

    def metrics(self, metrics: dict) -> None:
        clean = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        if clean:
            self._try("mlflow.log_metrics", lambda: self.stack["tracker"].log_metrics(self.run_id, clean))

    def span(self, name: str, attrs: dict) -> str | None:
        def go():
            refs = self.stack["traces"].emit(self.identity, self.run_id, name, {"logos.thesis_id": self.thesis_id or "", "logos.job_id": str(self.job_id), "logos.kind": self.kind, **{k: str(v) for k, v in attrs.items()}})
            tid = getattr(refs, "otel_trace_id", None)
            if tid and tid not in self.trace_ids:
                self.trace_ids.append(tid)
            return tid
        return self._try("otel.emit", go)

    def generation(self, *, model_requested: str, model_resolved: str | None, status: str, evidence_class: str | None, prompt: str, output: str | None, usage: dict | None, turns: int | None, latency_s: float) -> None:
        def go():
            refs = self.stack["llm_traces"].emit_generation(self.identity, self.run_id, {"name": f"{self.kind}:claude", "model": model_resolved or model_requested, "input": prompt, "output": output or "", "usage": usage or {},
                                                                                     "status": status, "evidence_class": evidence_class or "", "model_requested": model_requested, "turns": turns, "latency_s": latency_s})
            self.langfuse_id = getattr(refs, "langfuse_trace_id", None)
        self._try("langfuse.emit_generation", go)
        self.params({"model_requested": model_requested, "model_resolved": model_resolved or "", "claude_status": status, "evidence_class": evidence_class or "", "prompt_sha256": sha256(prompt.encode()).hexdigest()})
        self.metrics({"latency_s": latency_s, "turns": turns or 0, "status_ok": 1 if status == "OK" else 0, **{f"tokens_{k}": v for k, v in (usage or {}).items() if isinstance(v, (int, float))}})
        self._link()

    def artifact(self, name: str, payload: bytes, kind: str = "telemetry") -> dict:
        h = sha256(payload).hexdigest(); uri = f"mlflow://{self.mlflow_run_id or 'null'}/{name}"
        self._try("mlflow.log_artifact", lambda: _mlflow_log_artifact(self.stack["tracker"], self.run_id, name, payload))
        aid = f"{self.run_id}:{name}"
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO ros_artifacts (artifact_id, sha256, uri, kind, run_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (artifact_id) DO UPDATE SET sha256 = EXCLUDED.sha256, uri = EXCLUDED.uri", (aid, h, uri, kind, self.run_id))
        self.conn.commit()
        rec = {"artifact_id": aid, "sha256": h, "uri": uri, "kind": kind, "bytes": len(payload)}; self.artifacts.append(rec); return rec

    def finish(self, state: str, summary: dict | None) -> dict:
        self.span("run.finish", {"phase": "finish", "state": state})
        self.metrics({"duration_s": time.time() - self._t0})
        self._try("mlflow.end_run", lambda: self.stack["tracker"].end_run(self.run_id, "COMPLETED" if state == "done" else "FAILED"))
        self._try("otel.flush", lambda: self.stack["traces"].flush())
        self._link()
        return self.links()

    def _link(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM ros_trace_links WHERE run_id = %s", (self.run_id,))
            rows = [(self.run_id, self.mlflow_run_id, t) for t in (self.trace_ids or [None])]
            for r in rows:
                cur.execute("INSERT INTO ros_trace_links (run_id, mlflow_run_id, trace_id) VALUES (%s, %s, %s)", r)
        self.conn.commit()

    def links(self) -> dict:
        return {"mlflow_run_id": self.mlflow_run_id, "mlflow_experiment_id": self.mlflow_experiment_id, "otel_trace_ids": list(self.trace_ids), "langfuse_trace_id": self.langfuse_id, "degraded": list(self.degraded), "stack": self.stack.get("kind"), "artifacts": list(self.artifacts)}


def trace_links(conn, run_id: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_trace_links WHERE run_id = %s ORDER BY link_id", (run_id,)); return cur.fetchall()


def artifacts(conn, run_id: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_artifacts WHERE run_id = %s ORDER BY created_at", (run_id,)); return cur.fetchall()


def waterfall(events: list[dict]) -> list[dict]:
    """Phase bars from the append-only events: each `phase` event opens a bar closed by the next phase / done / error."""
    from datetime import datetime
    def ts(e): return e["at"] if isinstance(e["at"], datetime) else datetime.fromisoformat(str(e["at"]))
    bars: list[dict] = []; open_bar: dict | None = None
    start = ts(events[0]) if events else None
    for e in events:
        if e["kind"] in ("phase", "done", "error", "stop", "quota"):
            if open_bar:
                open_bar["end_s"] = (ts(e) - start).total_seconds(); open_bar["duration_s"] = round(open_bar["end_s"] - open_bar["start_s"], 3); bars.append(open_bar); open_bar = None
            if e["kind"] == "phase":
                open_bar = {"phase": e["payload"].get("phase"), "start_s": (ts(e) - start).total_seconds(), "seq": e["seq"]}
    if open_bar:
        open_bar["end_s"] = open_bar["start_s"]; open_bar["duration_s"] = 0.0; bars.append(open_bar)
    return bars


def mlflow_ui_url(tracking_uri: str, experiment_id: str | None, mlflow_run_id: str | None) -> str | None:
    if not mlflow_run_id or not experiment_id:
        return None
    return f"{tracking_uri}/#/experiments/{experiment_id}/runs/{mlflow_run_id}"


def result_doc_hash(doc: dict) -> str:
    return sha256(json.dumps(doc, sort_keys=True, default=str).encode()).hexdigest()
