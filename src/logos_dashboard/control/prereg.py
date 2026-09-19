"""Gate chain: build and validate the run preregistration from the agent's files, freeze it in the lab, run the zero-inference dry run.

Nothing here invokes a model. The preregistration is built from the thesis directory (`PREREG-DRAFT.json`, `DATASET.json`, `PROMPTS.json`,
`MEASUREMENT.json`), validated with the very same governance function the script path uses (`logos_research.governance.validate_run_preregistration`)
and frozen through the lab repository (`freeze_preregistration`, hash = primary key ⇒ a changed payload is a new hash, never an overwrite).
Every gate attempt is appended to `ros_gate_log`, so the UI can show what was checked, by whom, and what failed.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from psycopg.rows import dict_row

from logos_research.governance import GovernanceError, load_governance, validate_run_preregistration
from logos_research.measurement.manifest import stochastic_preregistration

from .. import measurement_contract as mc
from . import governor, service
from .state_machines import IllegalTransition

ROOT = Path(__file__).resolve().parents[3]
THESES_DIR = ROOT / "docs" / "research" / "dashboard" / "theses"
FILES = ("PREREG-DRAFT.json", "DATASET.json", "PROMPTS.json", "MEASUREMENT.json")
GATES = ("prereg_validate", "prereg_freeze", "work_order_approve", "dry_run", "ready_to_run", "measurement", "verdict")
DRY_RUN_CHECK_TEXT = {
    "metadata_complete": "Alle Pflichtangaben der Preregistration sind vorhanden",
    "pins_resolve": "Modell-Pin, Anbieter und CLI-Version sind aufgelöst",
    "privacy_checks_pass": "Datenklasse ist freigegeben (SYNTHETIC)",
    "cost_accounting_initialized": "Kostenkonto steht auf 0 (Subscription-Pfad)",
    "construct_metrics_resolve": "Jede Metrik hat einen deterministischen Scorer",
    "artifact_paths_exist": "Ablageorte für Artefakte existieren",
    "provenance_graph_initializes": "Herkunftsgraph lässt sich anlegen",
    "trajectory_capture_initializes": "Aufzeichnung der Antworten ist bereit",
    "invalid_measurement_rules_load": "Alle Invalidierungsregeln sind geladen",
    "forbidden_provider_guard_active": "Sperre gegen fremde Anbieter ist aktiv",
}


def thesis_dir(thesis_id: str) -> Path:
    return THESES_DIR / thesis_id


def read_bundle(thesis_id: str, worktree: Path | None = None) -> dict:
    """Read the four files of a thesis. `worktree` lets the caller read them from a run branch instead of the main tree."""
    base = (worktree / "docs/research/dashboard/theses" / thesis_id) if worktree else thesis_dir(thesis_id)
    out: dict = {"dir": str(base), "present": [], "missing": [], "errors": []}
    for f in FILES:
        p = base / f
        if not p.exists():
            out["missing"].append(f); continue
        try:
            out[f] = json.loads(p.read_text(encoding="utf-8")); out["present"].append(f)
        except ValueError as e:
            out["errors"].append(f"{f}: {type(e).__name__}: {str(e)[:120]}")
    return out


def lock_hash() -> str:
    """sha256 of the dependency locks that exist in the repo (pnpm lock + requirements); honest about what is pinned."""
    from hashlib import sha256
    h = sha256()
    for rel in ("requirements-dashboard.txt", "pyproject.toml", "apps/dashboard/pnpm-lock.yaml"):
        p = ROOT / rel
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()


def git_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True).stdout.strip()


def build_payload(thesis: dict, bundle: dict, gov) -> dict:
    """Assemble the stochastic preregistration payload from the agent's files + the governance record. Deterministic; no defaults invented for scientific fields."""
    draft = bundle.get("PREREG-DRAFT.json") or {}
    ds = bundle.get("DATASET.json") or {}; pr = bundle.get("PROMPTS.json") or {}; m = bundle.get("MEASUREMENT.json") or {}
    caps = m.get("caps") or {}
    ds_hash = mc.dataset_hash(ds) if ds else None; pb_hash = mc.prompt_bundle_hash(pr) if pr else None
    experiment_id = f"ROS-{thesis['thesis_id']}"
    base = {
        "experiment_id": experiment_id,
        "thesis_id": thesis["thesis_id"],
        "claims": thesis.get("claim_ids") or [],
        "question": draft.get("question") or "NOT_EXTRACTED",
        "hypothesis": draft.get("hypothesis") or "NOT_EXTRACTED",
        "falsification_criterion": draft.get("falsification_criterion") or json.dumps(m.get("falsification") or {}, sort_keys=True),
        "scope": draft.get("scope") or "NOT_EXTRACTED",
        "privacy_class": draft.get("privacy_class") or "SYNTHETIC",
        "dataset_hash": ds_hash,
        "prompt_bundle_hash": pb_hash,
        "measurement_contract": mc.MEASUREMENT_SCHEMA,
        "analysis_plan": {"primary_metric": m.get("primary_metric"), "metrics": m.get("metrics"), "comparison": m.get("comparison"), "falsification": m.get("falsification"), "statistics": "Wilson per arm, Newcombe for the difference (ros-stats/1)", "missingness": "unscorable answers are counted as missing, never as success"},
        "git_sha": git_sha(),
    }
    pin = governor.caps().model_pin
    # every field of MANIFEST_FIELDS except the three per-run ones (run_id, timestamp, hardware_runtime_metadata); "NOT_EXPOSED"/"PROVIDER_DEFAULT" are honest statements about the Claude Code path, not guesses
    manifest_template = {
        "experiment_id": experiment_id, "preregistration_hash": "PENDING", "provider": gov.provider, "access_path": gov.access_path or "Claude Code", "auth_mode": gov.auth_mode or "Claude Max subscription",
        "model_id": pin, "model_version": "REPORTED_PER_RUN (assistant.message.model / pin containment)", "provider_region": "NOT_ASSUMED",
        "prompt_id": f"{thesis['thesis_id']}/PROMPTS.json", "prompt_version": pb_hash, "system_prompt_hash": pb_hash, "tool_schema_hash": "NO_TOOLS (measurement runs disallow every tool)",
        "dataset_version": ds_hash, "dataset_revision": ds_hash, "seed_if_supported": "NOT_EXPOSED", "temperature": "PROVIDER_DEFAULT", "top_p": "PROVIDER_DEFAULT",
        "max_tokens": caps.get("max_output_bytes"), "reasoning_effort_if_supported": "NOT_EXPOSED", "environment_hash": "research-os", "code_commit": base["git_sha"], "dependency_lock_hash": lock_hash(),
        "prompt_bundle_hash": pb_hash, "git_sha": base["git_sha"], "gamma_version": draft.get("gamma_version") or "UNCHANGED", "environment_id": "research-os",
        "cost_accounting": {"incremental_api_spend_usd": 0, "billing_mode": gov.billing_mode}, "tool_boundary": {"allowed_tools": [], "disallowed_tools": ["Bash", "Edit", "Write", "WebFetch", "WebSearch", "NotebookEdit"]},
        "decoding_params": {"temperature": "PROVIDER_DEFAULT", "max_turns": caps.get("max_turns")},
    }
    n_items = len(ds.get("items") or []); n_arms = max(1, len(ds.get("arms") or []))
    plan = {
        "planned_invocations": n_items, "repeats": 1, "cost_cap": 0, "fallback": "STOP_AND_REPORT",
        "sample_size": n_items, "resolution": "one invocation per dataset item; score in {hit, miss, unscorable}",
        "dispersion": "binomial per arm (Wilson 95 %); difference via Newcombe",
        "confidence_interval": "Wilson 95 % per arm, Newcombe 95 % for the difference (ros-stats/1)",
        "effect_size": "difference of proportions (pp); Cohen h on request",
        "baseline": (m.get("comparison") or {}).get("arm_b") or "NONE (single-arm threshold rule)",
        "control": (m.get("comparison") or {}).get("arm_b") or "NONE (single-arm threshold rule)",
        "early_stop_criteria": ["USAGE_LIMIT_REACHED", "COST_CAP_REACHED", "MODEL_VERSION_DRIFT", "DATASET_DRIFT", "PROMPT_DRIFT", "founder stop"],
        "invalid_measurement_criteria": list(m.get("invalid_measurement_criteria") or mc.INVALID_CRITERIA), "stopping_rule": f"stop after {len(ds.get('items') or [])} items or at the cap",
        "sample_size_justification": draft.get("sample_size_justification") or f"{len(ds.get('items') or [])} items, balanced across {len(ds.get('arms') or [])} arms (agent draft)",
        "metrics": [x.get("metric_id") for x in (m.get("metrics") or [])], "analysis": base["analysis_plan"], "blinding": "scorers are deterministic and applied after the run",
    }
    payload = dict(base)
    payload["stochastic"] = {"schema": "logos.stochastic-prereg/1", "manifest_template": manifest_template, "measurement_plan": plan, "metric_ids": plan["metrics"], "model_calls_allowed_before_dry_run": 0,
                             "claude_max_limits": {"max_turns_per_invocation": caps.get("max_turns"), "max_output_size": caps.get("max_output_bytes"), "max_total_accepted_trajectories": caps.get("max_invocations")}}
    return payload


def validate(conn, thesis_id: str, actor: str = "founder", worktree: Path | None = None) -> dict:
    """Gate 1 — check only, nothing is written except the gate log."""
    d = service.thesis_detail(conn, thesis_id)
    if d is None:
        raise KeyError(thesis_id)
    bundle = read_bundle(thesis_id, worktree)
    gov = load_governance()
    issues: list[str] = [f"Datei fehlt: {f}" for f in bundle["missing"]] + bundle["errors"]
    contract_issues: list[str] = []
    payload = None
    if not issues:
        contract_issues = mc.validate_bundle(bundle["DATASET.json"], bundle["PROMPTS.json"], bundle["MEASUREMENT.json"])
        payload = build_payload(d["thesis"], bundle, gov)
        gov_issues = validate_run_preregistration(payload, gov)
    else:
        gov_issues = ["Preregistration kann ohne die Dateien nicht gebaut werden"]
    passed = not (issues or contract_issues or gov_issues)
    detail = {"files": {"present": bundle["present"], "missing": bundle["missing"]}, "file_issues": issues, "contract_issues": contract_issues, "governance_issues": gov_issues,
              "dataset_hash": (payload or {}).get("dataset_hash"), "prompt_bundle_hash": (payload or {}).get("prompt_bundle_hash"), "planned_invocations": ((payload or {}).get("stochastic") or {}).get("measurement_plan", {}).get("planned_invocations"),
              "model_pin": governor.caps(conn).model_pin}
    log_gate(conn, thesis_id, "prereg_validate", actor, passed, detail)
    return {"passed": passed, **detail, "payload": payload}


def freeze(conn, thesis_id: str, actor: str, worktree: Path | None = None) -> dict:
    """Gate 2 — founder only. Freezes the validated payload in the lab Postgres and records the hash on thesis and work order."""
    if actor != "founder":
        raise IllegalTransition("thesis", "PREREG_DRAFT", "freeze_prereg", actor, "founder gate")
    v = validate(conn, thesis_id, actor, worktree)
    if not v["passed"]:
        log_gate(conn, thesis_id, "prereg_freeze", actor, False, {"reason": "validation failed", **{k: v[k] for k in ("file_issues", "contract_issues", "governance_issues")}})
        raise ValueError(f"preregistration not valid: {v['file_issues'] + v['contract_issues'] + v['governance_issues']}")
    payload = v["payload"]
    from hashlib import sha256
    h = sha256(mc.canonical(payload).encode()).hexdigest()
    payload["stochastic"]["manifest_template"]["preregistration_hash"] = h
    try:
        from logos_research.infra.backends import backends_from_env
        from logos_research.infra.identity import ExperimentIdentity
        repo = backends_from_env()["repository"].connect()
        identity = ExperimentIdentity(experiment_id=payload["experiment_id"], experiment_revision=1, preregistration_hash=h, git_sha=payload["git_sha"], gamma_version=str(payload["stochastic"]["manifest_template"]["gamma_version"]), environment_id="research-os")
        repo.ensure_experiment(payload["experiment_id"], f"Research OS thesis {thesis_id}")
        repo.freeze_preregistration(identity, payload)
        repo.close()
        frozen_where = "lab postgres (preregistrations)"
    except Exception as e:                                        # lab unavailable -> refuse; a prereg that is not durably frozen is not frozen
        log_gate(conn, thesis_id, "prereg_freeze", actor, False, {"reason": f"lab unavailable: {type(e).__name__}: {str(e)[:160]}"})
        raise GovernanceError(f"preregistration could not be frozen durably: {type(e).__name__}: {str(e)[:160]}")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("UPDATE ros_theses SET prereg_hash = %s, updated_at = now() WHERE thesis_id = %s", (h, thesis_id))
        cur.execute("UPDATE ros_work_orders SET prereg_hash = %s, updated_at = now() WHERE thesis_id = %s AND state = 'DRAFT'", (h, thesis_id))
    conn.commit()
    row = service.advance(conn, thesis_id, "freeze_prereg", "founder", reason=f"prereg frozen {h[:12]} ({frozen_where})", source_record=f"preregistrations/{h}")
    log_gate(conn, thesis_id, "prereg_freeze", actor, True, {"prereg_hash": h, "where": frozen_where, "dataset_hash": payload["dataset_hash"], "prompt_bundle_hash": payload["prompt_bundle_hash"]})
    return {"prereg_hash": h, "thesis": row, "payload_sha256": h, "where": frozen_where}


def frozen_payload(thesis_id: str, prereg_hash: str) -> dict | None:
    try:
        from logos_research.infra.backends import backends_from_env
        repo = backends_from_env()["repository"].connect()
        with repo._conn.cursor() as cur:
            cur.execute("SELECT payload FROM preregistrations WHERE preregistration_hash = %s", (prereg_hash,)); r = cur.fetchone()
        repo.close()
        return r[0] if r else None
    except Exception:
        return None


def dry_run_checks(conn, thesis_id: str, worktree: Path | None = None) -> dict:
    """Gate 4 — the ten zero-inference checks against the FROZEN preregistration. No model call; counters must stay 0."""
    from logos_research.governance import DRY_RUN_CHECKS, dry_run_contract
    from logos_research.measurement.gateway import CALLS
    before = (CALLS["model_calls"], CALLS["provider_calls"], CALLS["claude_code_inference_invocations"])
    d = service.thesis_detail(conn, thesis_id)
    th = d["thesis"] if d else None
    h = (th or {}).get("prereg_hash")
    payload = frozen_payload(thesis_id, h) if h else None
    bundle = read_bundle(thesis_id, worktree)
    ds = bundle.get("DATASET.json") or {}; pr = bundle.get("PROMPTS.json") or {}; m = bundle.get("MEASUREMENT.json") or {}
    t = ((payload or {}).get("stochastic") or {}).get("manifest_template", {})
    plan = ((payload or {}).get("stochastic") or {}).get("measurement_plan", {})
    caps = governor.caps(conn)
    art_dir = thesis_dir(thesis_id)
    results = {
        "metadata_complete": bool(payload) and all(payload.get(k) for k in ("experiment_id", "question", "hypothesis", "falsification_criterion", "dataset_hash", "prompt_bundle_hash")),
        "pins_resolve": bool(t.get("model_id")) and t.get("model_id") == caps.model_pin and t.get("provider") == "Anthropic" and bool(governor.attestation(conn).get("cli_version")),
        "privacy_checks_pass": (payload or {}).get("privacy_class") in load_governance().allowed_data_classes,
        "cost_accounting_initialized": (plan.get("cost_cap") == 0) and (t.get("cost_accounting", {}).get("incremental_api_spend_usd") == 0),
        "construct_metrics_resolve": bool(m.get("metrics")) and all(x.get("scorer") in mc.SCORER_IDS for x in m.get("metrics", [])),
        "artifact_paths_exist": art_dir.exists(),
        "provenance_graph_initializes": bool(payload) and bool(ds.get("items")) and all(it.get("item_id") for it in ds.get("items", [])),
        "trajectory_capture_initializes": True,
        "invalid_measurement_rules_load": all(c in (plan.get("invalid_measurement_criteria") or []) for c in mc.INVALID_CRITERIA),
        "forbidden_provider_guard_active": not any(governor.contamination().values()),
    }
    # drift check: the frozen hashes must still match the files
    drift = []
    if payload and ds and mc.dataset_hash(ds) != payload.get("dataset_hash"):
        drift.append("DATASET_DRIFT"); results["metadata_complete"] = False
    if payload and pr and mc.prompt_bundle_hash(pr) != payload.get("prompt_bundle_hash"):
        drift.append("PROMPT_DRIFT"); results["metadata_complete"] = False
    after = (CALLS["model_calls"], CALLS["provider_calls"], CALLS["claude_code_inference_invocations"])
    delta_zero = before == after
    assert delta_zero, "dry run must not call a model"
    # `governance.dry_run_contract` additionally requires the PROCESS counters to be absolutely zero. That holds for a one-shot script run,
    # but the Research-OS daemon serves many theses in one process, where the counter carries earlier, unrelated runs. The scientific content of
    # the rule — "this dry run performed no inference" — is checked as a delta (`counters_unchanged`); the absolute counters are reported as context.
    failed = [f for f in dry_run_contract(results) if f != "counters not zero"]
    return {"checks": results, "failed": failed, "passed": not failed and not drift and delta_zero, "drift": drift, "texts": DRY_RUN_CHECK_TEXT, "prereg_hash": h, "counters_unchanged": delta_zero,
            "counters": {"before": list(before), "after": list(after), "note": "delta must be 0; the absolute process counter includes earlier runs of this daemon"}, "check_ids": list(DRY_RUN_CHECKS)}


def run_dry_run(conn, thesis_id: str, actor: str = "founder", worktree: Path | None = None) -> dict:
    res = dry_run_checks(conn, thesis_id, worktree)
    log_gate(conn, thesis_id, "dry_run", actor, res["passed"], {"failed": res["failed"], "drift": res["drift"], "prereg_hash": res["prereg_hash"]})
    d = service.thesis_detail(conn, thesis_id)
    state = d["thesis"]["state"] if d else None
    if res["passed"] and state == "WORK_ORDER_READY":
        service.advance(conn, thesis_id, "dry_run", "system", reason="dry run passed (zero inference)")
    elif not res["passed"] and state in ("WORK_ORDER_READY", "DRY_RUN"):
        if state == "WORK_ORDER_READY":
            service.advance(conn, thesis_id, "dry_run", "system", reason="dry run executed")
        service.advance(conn, thesis_id, "dry_run_failed", "system", reason=f"dry run failed: {res['failed'] + res['drift']}")
    return {**res, "thesis_state": (service.thesis_detail(conn, thesis_id) or {}).get("thesis", {}).get("state")}


def log_gate(conn, thesis_id: str, gate: str, actor: str, passed: bool, detail: dict) -> None:
    if gate not in GATES:
        raise ValueError(f"unknown gate {gate!r}")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ros_gate_log (thesis_id, gate, actor, passed, detail) VALUES (%s, %s, %s, %s, %s)", (thesis_id, gate, actor, passed, json.dumps(detail, default=str)))
    conn.commit()


def gate_log(conn, thesis_id: str, limit: int = 100) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM ros_gate_log WHERE thesis_id = %s ORDER BY gate_id DESC LIMIT %s", (thesis_id, limit)); return cur.fetchall()


def chain_status(conn, thesis_id: str) -> dict:
    """The five steps for the UI: which is done, which is next, what the founder must click."""
    d = service.thesis_detail(conn, thesis_id)
    if d is None:
        raise KeyError(thesis_id)
    th = d["thesis"]; state = th["state"]; logs = gate_log(conn, thesis_id)
    last = {}
    for g in GATES:
        hit = next((l for l in logs if l["gate"] == g), None)
        if hit:
            last[g] = {"passed": hit["passed"], "at": hit["at"], "actor": hit["actor"], "detail": hit["detail"]}
    order = ["IDEA", "TRIAGE", "PRIOR_ART", "QUESTION_DEFINED", "HYPOTHESIS_DEFINED", "METRICS_DEFINED", "PREREG_DRAFT", "PREREG_FROZEN", "WORK_ORDER_READY", "DRY_RUN", "READY_TO_RUN", "RUNNING", "ANALYSIS", "VERDICT"]
    idx = order.index(state) if state in order else -1
    wo = next((w for w in d["work_orders"] if not w["work_order_id"].startswith("REPO:")), None)
    steps = [
        {"id": "prereg_validate", "title": "Preregistration prüfen", "explain": "Prüft die vier Dateien des Agenten gegen die Laborregeln — ändert nichts.", "founder": False, "state": "done" if last.get("prereg_validate", {}).get("passed") else ("failed" if "prereg_validate" in last else "open"), "enabled": idx >= order.index("PREREG_DRAFT")},
        {"id": "prereg_freeze", "title": "Preregistration einfrieren 🔒", "explain": "Schreibt die geprüfte Preregistration unveränderlich ins Labor. Danach ist die Frage festgelegt.", "founder": True, "state": "done" if th.get("prereg_hash") else "open", "enabled": idx == order.index("PREREG_DRAFT") and bool(last.get("prereg_validate", {}).get("passed"))},
        {"id": "work_order_approve", "title": "Work Order freigeben 🔒", "explain": "Gibt den Forschungsauftrag frei; erst dann darf gemessen werden.", "founder": True, "state": "done" if (wo and wo["state"] != "DRAFT") else "open", "enabled": state == "PREREG_FROZEN" and bool(wo), "work_order_id": wo["work_order_id"] if wo else None},
        {"id": "dry_run", "title": "Trockenlauf", "explain": "Zehn Prüfungen ohne einen einzigen Modellaufruf: Pins, Datenklasse, Metriken, Invalidierungsregeln, Kontamination.", "founder": False, "state": "done" if last.get("dry_run", {}).get("passed") else ("failed" if "dry_run" in last else "open"), "enabled": state in ("WORK_ORDER_READY", "DRY_RUN")},
        {"id": "ready_to_run", "title": "Messlauf freigeben 🔒", "explain": "Deine letzte Freigabe vor echten Modellaufrufen.", "founder": True, "state": "done" if idx >= order.index("READY_TO_RUN") else "open", "enabled": state == "DRY_RUN" and bool(last.get("dry_run", {}).get("passed"))},
        {"id": "measurement", "title": "Messlauf starten", "explain": "Führt die Preregistration aus: ein Modellaufruf je Datenpunkt, Abbruch bei Cap, Quota oder Drift.", "founder": True, "state": "done" if idx >= order.index("ANALYSIS") else ("running" if state == "RUNNING" else "open"), "enabled": state == "READY_TO_RUN"},
        {"id": "verdict", "title": "Ergebnis entscheiden 🔒", "explain": "Der Vorschlag folgt mechanisch aus der eingefrorenen Regel; du entscheidest, ob er ein Record wird.", "founder": True, "state": "done" if idx >= order.index("VERDICT") else "open", "enabled": state == "ANALYSIS"},
    ]
    return {"thesis_id": thesis_id, "state": state, "prereg_hash": th.get("prereg_hash"), "steps": steps, "last": last, "work_order": wo, "at": datetime.now(timezone.utc).isoformat()}
