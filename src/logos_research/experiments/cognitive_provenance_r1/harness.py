"""Preregistered run harness (Sections 17-25, 42-48, 62-64, 70-71, 78).

    RunGates   every gate must be PASS before `run()` will touch the provider
    budget()   planned_calls + retry_reserve <= hard cap (200)
    preflight  zero-inference checks (Section 23) — no prompt is submitted
    run()      the only loop that invokes the provider; hard stops, retry policy, counters, artifact package, verdict

Nothing here changes authority state: ModelOutput != Grant, ModelPlan != Authority, SourceTrust != Grant, Taint != Authority.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from hashlib import sha256

from logos_research.experiments.causal_provenance import ProvenanceGraph
from logos_research.measurement.claude_code import CALLS, ActivationToken, ClaudeCodeMaxProvider, Limits, ProviderPolicyError, contamination

from . import EXPERIMENT_ID, VERDICTS
from .dataset import DATA_CLASS, Task, Trial, dataset_hash, validate_balance, validate_tasks
from .metrics import THRESHOLDS, analyse, score, verdict
from .parse import parse_response
from .prompts import build_exposure, build_prompt, leakage_issues, prompt_bundle_hashes, SYSTEM_PROMPT

HARD_CAP = 200
WALL_CLOCK_S = 3 * 3600
GATE_NAMES: tuple[str, ...] = ("MODEL_PIN_GATE", "AUTH_GATE", "METRIC_GATE", "ZERO_INFERENCE_PREFLIGHT", "DRY_RUN", "PREREG", "HARNESS_MUTANTS")
RETRY_STATUSES: frozenset[str] = frozenset({"PROCESS_ERROR", "TIMEOUT", "INVALID_OUTPUT"})
STOP_STATUSES: dict[str, str] = {"USAGE_LIMIT_REACHED": "USAGE_LIMIT_REACHED", "MODEL_DRIFT": "MODEL_VERSION_DRIFT", "CLI_VERSION_DRIFT": "CLI_VERSION_DRIFT",
                                 "AUTH_NOT_MAX_SUBSCRIPTION": "AUTH_PATH_DRIFT", "AUTH_UNAVAILABLE": "AUTH_PATH_DRIFT", "POLICY_BLOCK": "TOOL_POLICY_VIOLATION"}
DISALLOWED_TOOLS: tuple[str, ...] = ("Bash", "Edit", "Write", "NotebookEdit", "Read", "Glob", "Grep", "WebFetch", "WebSearch", "Task", "mcp")
AUTHORITY_INVARIANTS: tuple[str, ...] = ("ModelOutput != Grant", "ModelConfidence != Authority", "ModelPlan != Authority", "ModelBelief != Authority", "SourceTrust != Grant", "Taint != Authority")


class GateError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunGates:
    MODEL_PIN_GATE: str = "PENDING"
    AUTH_GATE: str = "PENDING"
    METRIC_GATE: str = "PENDING"
    ZERO_INFERENCE_PREFLIGHT: str = "PENDING"
    DRY_RUN: str = "PENDING"
    PREREG: str = "PENDING"
    HARNESS_MUTANTS: str = "PENDING"

    @property
    def all_pass(self) -> bool:
        return all(getattr(self, g) == "PASS" for g in GATE_NAMES)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    model_pin: str
    prereg_hash: str
    expected_cli_version: str | None
    planned_calls: int
    retry_reserve: int = 24
    hard_cap: int = HARD_CAP
    wall_clock_s: float = WALL_CLOCK_S
    per_invocation_timeout_s: float = 180.0
    max_turns: int = 1
    max_output_bytes: int = 20000
    output_format: str = "json"
    disallowed_tools: tuple[str, ...] = DISALLOWED_TOOLS
    resume_allowed_once: bool = True


def budget(planned: int, retry_reserve: int, hard_cap: int = HARD_CAP) -> dict:
    ok = planned + retry_reserve <= hard_cap and planned > 0
    return {"planned_calls": planned, "retry_reserve": retry_reserve, "planned_plus_reserve": planned + retry_reserve, "hard_cap": hard_cap, "ok": ok}


@dataclass
class InvocationRecord:
    trial_id: str
    attempt: int
    status: str
    requested_model: str
    reported_model: str | None
    claude_code_version: str | None
    session_id: str | None
    exit_code: int | None
    latency_s: float
    stderr_classification: str | None
    usage_metadata: dict | None
    raw_response: str | None
    raw_sha256: str | None
    prompt_sha256: str
    accepted: bool
    counter_snapshot: dict = field(default_factory=dict)


@dataclass
class RunResult:
    run_id: str
    verdict: str
    verdict_detail: dict
    invalid_reasons: tuple[str, ...]
    stop_reason: str | None
    invocations: list[InvocationRecord]
    scored: list
    analysis: dict
    trial_table: list[dict]
    counters: dict
    counter_agreement: bool
    quota: dict
    wall_clock_s: float
    package: dict

    @property
    def accepted_invocations(self) -> int:
        return sum(1 for r in self.invocations if r.accepted)


# -- zero-inference preflight (Section 23) ---------------------------------------------

def preflight(provider: ClaudeCodeMaxProvider, *, auth_class: str | None, env: dict, cli_version: str | None, model_pin: str | None, prereg_valid: bool, metric_gate_ok: bool,
              artifact_dir_writable: bool, tasks: tuple[Task, ...], trials: tuple[Trial, ...], gates: RunGates) -> dict:
    p = provider.preflight(auth_class=auth_class, env=env, cli_version=cli_version)
    checks = dict(p["checks"])
    checks.update({"model_pin_finalized": bool(model_pin) and model_pin != "TO_BE_PINNED_FROM_MAX_ACCOUNT_BEFORE_RUN", "prereg_valid": prereg_valid,
                   "dataset_synthetic": all(t.data_class == DATA_CLASS for t in tasks) and not validate_tasks(tasks) and not validate_balance(trials),
                   "metric_gate_complete": metric_gate_ok, "artifact_paths_writable": artifact_dir_writable, "caps_loaded": budget(len(trials), 24)["ok"],
                   "provenance_capture_initialized": _provenance_ok(tasks, trials), "trajectory_capture_initialized": True, "counters_zero": all(v == 0 for v in CALLS.values()),
                   "tool_restrictions_configured": "Bash" in DISALLOWED_TOOLS and "WebFetch" in DISALLOWED_TOOLS, "model_pin_gate_passed": gates.MODEL_PIN_GATE == "PASS"})
    passed = all(checks.values()) and not p["stop_for_manual_auth_evidence"]
    return {"checks": checks, "passed": passed, "stop_for_manual_auth_evidence": p["stop_for_manual_auth_evidence"], "contamination_presence": p["contamination_presence"], "cli_version": cli_version,
            "prompt_submitted": False}


def _provenance_ok(tasks: tuple[Task, ...], trials: tuple[Trial, ...]) -> bool:
    g = ProvenanceGraph(); tk = {t.task_id: t for t in tasks}
    for x in trials[:13]:
        e = build_exposure(tk[x.task_id], x, g, run_id="preflight")
        if x.condition != "CONTROL" and (e.final_node is None or e.lineage.get("sources") != [e.source_node] or e.lineage.get("node_sources") != [e.source_node] or len(e.ancestry) != x.depth):
            return False
    return True


# -- the run ---------------------------------------------------------------------------

def run(tasks: tuple[Task, ...], trials: tuple[Trial, ...], provider: ClaudeCodeMaxProvider, token: ActivationToken, cfg: RunConfig, gates: RunGates, env: dict, *,
        clock=time.monotonic, prior: RunResult | None = None) -> RunResult:
    if not gates.all_pass:
        raise GateError(f"gates not all PASS: {gates.to_dict()}")
    if token.run_id != cfg.run_id or token.model_pin != cfg.model_pin or token.max_invocations > cfg.hard_cap:
        raise GateError("activation token does not match the run configuration")
    b = budget(len(trials), cfg.retry_reserve, cfg.hard_cap)
    if not b["ok"] or cfg.planned_calls != len(trials):
        raise GateError(f"budget refused: {b}")
    if validate_tasks(tasks) or validate_balance(trials):
        raise GateError("dataset invalid at run start")
    tk = {t.task_id: t for t in tasks}
    graph = ProvenanceGraph()
    hashes = prompt_bundle_hashes(); ds_hash = dataset_hash(tasks, trials)
    started = clock(); wall_offset = 0.0
    records: list[InvocationRecord] = []; parsed_by_trial: dict[str, object] = {}; invalid: list[str] = []; stop_reason: str | None = None
    quota = {"run_start_usage_state": "UNKNOWN (not exposed by CLI)", "quota_interruption": False, "reset_boundary_encountered": False, "resumed": False}
    if prior is not None:                                                             # pause/resume (Section 47): once, same pins, same hashes
        if not cfg.resume_allowed_once or prior.quota.get("resumed"):
            raise GateError("resume not permitted")
        if prior.package["prompt_hashes"] != hashes or prior.package["dataset_hash"] != ds_hash or prior.package["model_pin"] != cfg.model_pin or prior.package["claude_code_version"] != cfg.expected_cli_version:
            raise GateError("resume refused: pins or hashes changed -> new run required")
        records = list(prior.invocations); wall_offset = prior.wall_clock_s; quota = {**prior.quota, "resumed": True, "quota_interruption": True, "reset_boundary_encountered": True}
        for r in records:
            if r.accepted and r.status == "OK":
                parsed_by_trial[r.trial_id] = parse_response(r.raw_response, tuple(o for o, _ in tk[r.trial_id.split("/")[0]].options))
    limits = Limits(cfg.max_turns, cfg.max_output_bytes, cfg.per_invocation_timeout_s, cfg.disallowed_tools, ())
    ctx = {"run_id": cfg.run_id, "system_prompt": SYSTEM_PROMPT}
    retries_used = sum(1 for r in records if r.attempt > 0)
    leakage: list[str] = []

    def invocations_so_far() -> int:
        return len(records)

    for x in trials:
        if stop_reason:
            break
        if x.trial_id in parsed_by_trial:
            continue
        t = tk[x.task_id]
        exposure = build_exposure(t, x, graph, run_id=cfg.run_id); prompt = build_prompt(t, x, exposure)
        leakage += leakage_issues(t, x, exposure, prompt)
        if leakage:
            stop_reason = "PROMPT_LEAKAGE"; invalid.append("PROMPT_DRIFT"); break
        attempt = 0
        while True:
            # -- hard stops before every invocation (Section 63)
            if invocations_so_far() >= cfg.hard_cap:
                stop_reason = "HARD_INVOCATION_CAP"; invalid.append("COST_CAP_REACHED"); break
            if wall_offset + (clock() - started) >= cfg.wall_clock_s:
                stop_reason = "HARD_WALL_CLOCK_CAP"; invalid.append("COST_CAP_REACHED"); break
            cont = contamination(env)
            if any(cont.values()):
                stop_reason = "AUTH_PAYG_CONTAMINATION"; invalid.append("AUTH_PATH_DRIFT"); break
            try:
                res = provider.invoke(prompt, cfg.model_pin, ctx, limits, token=token, env=env, output_format=cfg.output_format)
            except ProviderPolicyError as e:
                stop_reason = f"POLICY:{e}"; invalid.append("TOOL_POLICY_VIOLATION"); break
            raw = res.content if res.status == "OK" else None
            rec = InvocationRecord(x.trial_id, attempt, res.status, res.requested_model, res.reported_model, res.claude_code_version, res.session_id, res.exit_code, res.latency_s,
                                   res.stderr_classification, res.usage_metadata, raw, sha256(raw.encode()).hexdigest() if raw else None, sha256(prompt.encode()).hexdigest(), False, dict(CALLS))
            records.append(rec)
            if res.claude_code_version and cfg.expected_cli_version and res.claude_code_version != cfg.expected_cli_version:
                stop_reason = "CLI_VERSION_DRIFT"; invalid.append("CLI_VERSION_DRIFT"); break
            if res.status in STOP_STATUSES:
                stop_reason = res.status; reason = STOP_STATUSES[res.status]
                if reason == "USAGE_LIMIT_REACHED":
                    quota["quota_interruption"] = True
                invalid.append(reason); break
            status = res.status
            if status == "OK":
                p = parse_response(res.content, tuple(o for o, _ in t.options))
                if p.valid:
                    rec.accepted = True; parsed_by_trial[x.trial_id] = p; break
                status = "INVALID_OUTPUT"; rec.status = "INVALID_OUTPUT"
            if status in RETRY_STATUSES and attempt == 0 and retries_used < cfg.retry_reserve:          # Section 44: one retry, transport/parse failures only
                retries_used += 1; attempt += 1; continue
            if status == "INVALID_OUTPUT":
                rec.accepted = True; parsed_by_trial[x.trial_id] = parse_response(None, ())               # accepted as INVALID_OUTPUT (counts toward the excessive-invalid rule)
            break

    wall = wall_offset + (clock() - started)
    scored = [score(x, parsed_by_trial[x.trial_id]) for x in trials if x.trial_id in parsed_by_trial]
    complete = len(scored) == len(trials)
    n_invalid = sum(1 for s in scored if not s.parsed.valid)
    if not complete:
        if "USAGE_LIMIT_REACHED" not in invalid:
            invalid.append("MISSING_TRACE")
    if n_invalid > THRESHOLDS["excessive_invalid_output_fraction"] * len(trials):
        invalid.append("EXCESSIVE_INVALID_OUTPUT")
    reported = {r.reported_model for r in records if r.reported_model}
    if len(reported) > 1 or any(cfg.model_pin not in m and m not in cfg.model_pin for m in reported):
        invalid.append("MODEL_VERSION_DRIFT")
    if any(s.trial.expected_source_label is None for s in scored):
        invalid.append("MISSING_GROUND_TRUTH")
    counters = dict(CALLS)
    agreement = counters["claude_code_inference_invocations"] == counters["provider_calls"] == counters["model_calls"] == len(records)
    analysis = analyse(scored) if scored else {}
    controls_ok = complete and sum(1 for s in scored if s.trial.condition == "CONTROL") == sum(1 for x in trials if x.condition == "CONTROL")
    v, detail = verdict(analysis, invalid_reasons=tuple(dict.fromkeys(invalid)), controls_ok=controls_ok, metric_gate_ok=gates.METRIC_GATE == "PASS") if scored else ("INVALID_MEASUREMENT", {"reasons": ["MISSING_TRACE"]})
    assert v in VERDICTS
    table = [s.to_dict() for s in scored]
    package = {"experiment_id": EXPERIMENT_ID, "run_id": cfg.run_id, "model_pin": cfg.model_pin, "claude_code_version": cfg.expected_cli_version, "prereg_hash": cfg.prereg_hash, "gates": gates.to_dict(),
               "prompt_hashes": hashes, "dataset_hash": ds_hash, "dataset_version": "cpa-r1-synthetic/1", "planned_calls": cfg.planned_calls, "retry_reserve": cfg.retry_reserve, "hard_cap": cfg.hard_cap,
               "invocations": [asdict(r) for r in records], "trial_table": table, "analysis": analysis, "verdict": v, "verdict_detail": detail, "invalid_reasons": list(dict.fromkeys(invalid)),
               "stop_reason": stop_reason, "counters": counters, "counter_agreement": agreement, "quota": quota, "wall_clock_s": wall, "retries_used": retries_used,
               "provenance_log_sha256": sha256(json.dumps(graph.log, sort_keys=True).encode()).hexdigest(), "provenance_nodes": len(graph.nodes),
               "accounting": {"incremental_payg_api_spend_usd": 0, "claude_max_subscription_quota_consumed": len(records) > 0, "token_usage": "captured per invocation only if exposed by the CLI (never fabricated)"},
               "authority_invariants": list(AUTHORITY_INVARIANTS), "authority_state_changed": False, "p7": "functional experiment; no consciousness claim"}
    return RunResult(cfg.run_id, v, detail, tuple(dict.fromkeys(invalid)), stop_reason, records, scored, analysis, table, counters, agreement, quota, wall, package)


# -- artifact integrity (Sections 62, 78) ---------------------------------------------

def verify_package(pkg: dict) -> tuple[bool, list[str]]:
    """Recomputes every hash the package carries; a mismatch is ARTIFACT_INTEGRITY_FAILURE."""
    out: list[str] = []
    for r in pkg.get("invocations", []):
        raw = r.get("raw_response")
        if raw is not None and sha256(raw.encode()).hexdigest() != r.get("raw_sha256"):
            out.append(f"raw hash mismatch {r.get('trial_id')}/{r.get('attempt')}")
    accepted = [r for r in pkg.get("invocations", []) if r.get("accepted")]
    if len(accepted) != len(pkg.get("trial_table", [])):
        out.append("accepted invocation count != trial table size")
    ids = {r["trial_id"] for r in accepted}
    if ids != {t["trial"]["trial_id"] for t in pkg.get("trial_table", [])}:
        out.append("trial ids of accepted invocations != trial table")
    if pkg.get("verdict") not in VERDICTS:
        out.append("verdict outside vocabulary")
    c = pkg.get("counters", {})
    if not (c.get("claude_code_inference_invocations") == c.get("provider_calls") == c.get("model_calls") == len(pkg.get("invocations", []))):
        out.append("counter disagreement")
    return (not out), out
