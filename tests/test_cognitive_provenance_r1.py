"""COGNITIVE-PROVENANCE-ABLATION-R1 — instrument-first validation (Section 69), harness properties, 15 harness mutants (Section 68).

Deterministic. No `claude` process is started: every provider call goes through a fake process runner injected
into `ClaudeCodeMaxProvider`; counters are reset after each test and the last test proves they read 0.
"""
from __future__ import annotations

import copy
import json
import os
import random
import re
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import logos_research.measurement as ms
from logos_research.measurement import claude_code as cc
from logos_research.measurement import construct as cs
from logos_research.experiments.causal_provenance import ProvenanceGraph
from logos_research.experiments.cognitive_provenance_r1 import EXPERIMENT_ID, SOURCE_CLASS, VERDICTS, claude_runner, dataset as ds, harness as hz, metric_gate as mg, metrics as mt, parse as ps, prompts as pr

ROOT = Path(__file__).resolve().parents[1]
TASKS = ds.build_tasks(); TRIALS = ds.build_trials(TASKS); TK = {t.task_id: t for t in TASKS}
PIN = "claude-pinned-by-founder"
CAUGHT: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _zero():
    ms.reset_counters()
    yield
    ms.reset_counters()


def gates_pass() -> hz.RunGates:
    return hz.RunGates(**{g: "PASS" for g in hz.GATE_NAMES})


def cfg(**o) -> hz.RunConfig:
    d = dict(run_id="run-t", model_pin=PIN, prereg_hash="a" * 64, expected_cli_version="9.9.9", planned_calls=len(TRIALS)); d.update(o)
    return hz.RunConfig(**d)


def token(**o) -> cc.ActivationToken:
    d = dict(run_id="run-t", model_pin=PIN, max_invocations=200, max_turns=1); d.update(o)
    return cc.ActivationToken(**d)


def make_fake(*, adopt=0.85, drift_at: int | None = None, quota_at: int | None = None, fail_first: set | None = None, invalid_first: set | None = None, seed=3, model=PIN, version="9.9.9"):
    """Deterministic responder over the prompt text only. Returns the (exit, stdout, stderr) triple the adapter expects."""
    rng = random.Random(seed); n = {"calls": 0, "seen": {}}

    def fake(argv, timeout, env):
        n["calls"] += 1
        assert "--dangerously-skip-permissions" not in argv and argv[0] == "claude"
        prompt = argv[argv.index("-p") + 1]
        tid = re.search(r"TASK\n(.*)\n", prompt).group(1)
        n["seen"][prompt] = n["seen"].get(prompt, 0) + 1
        if quota_at is not None and n["calls"] == quota_at:
            return 1, "", "Claude usage limit reached — resets at 14:00"
        if fail_first and n["calls"] in fail_first and n["seen"][prompt] == 1:
            return 1, "", "spawn error"
        m = re.search(r"(?:choose|select) ((?:OPT|ALLOC|ORDER)-\d)", prompt)
        opts = re.findall(r"^  ((?:OPT|ALLOC|ORDER)-\d):", prompt, flags=re.M)
        choice = m.group(1) if m and rng.random() < adopt else rng.choice(opts)
        if "[Source: TRUSTED_AGENT" in prompt: attr = "TRUSTED_AGENT"
        elif "[Source: RETRIEVED" in prompt: attr = "RETRIEVED_DOCUMENT"
        elif "[Source: ADVERSARIAL" in prompt: attr = "ADVERSARIAL_INJECTION"
        elif "[Source: SELF" in prompt: attr = "SELF_DERIVED"
        elif "EXPOSURE" in prompt: attr = rng.choice(["UNKNOWN", "TRUSTED_AGENT", "RETRIEVED_DOCUMENT", "SELF_DERIVED"])
        else: attr = "UNKNOWN"
        doc = {"final_choice": choice, "source_attribution": attr, "source_confidence": 0.7, "plan_used": m is not None, "brief_reasoning_summary": "fixture", "monitor_flag": attr in ("TRUSTED_AGENT", "RETRIEVED_DOCUMENT", "ADVERSARIAL_INJECTION")}
        if invalid_first and n["calls"] in invalid_first and n["seen"][prompt] == 1:
            doc["source_attribution"] = "SOMETHING_ELSE"
        reported = "claude-other-model" if drift_at is not None and n["calls"] >= drift_at else model
        return 0, json.dumps({"result": json.dumps(doc), "model": reported, "session_id": f"s{n['calls']}", "num_turns": 1, "usage": {"input_tokens": 10}}), ""
    fake.counts = n
    return fake


def provider(fake=None, version="9.9.9") -> cc.ClaudeCodeMaxProvider:
    return cc.ClaudeCodeMaxProvider(runner=fake or make_fake(), expected_cli_version=version)


# ==========================================================================
# Section 69 — instrument-first validation
# ==========================================================================

def test_dataset_generator_validated_and_deterministic():
    assert ds.validate_tasks(TASKS) == [] and len(TASKS) == 12 and ds.build_tasks() == TASKS
    assert all(t.data_class == "SYNTHETIC" for t in TASKS)
    assert ds.dataset_hash(TASKS, TRIALS) == ds.dataset_hash(ds.build_tasks(), ds.build_trials(ds.build_tasks()))
    positions = {t.valid_options for t in TASKS}
    assert len(positions) > 1                                                             # answer-position control: the invalid option is not always last
    for t in TASKS:                                                                       # tie: exactly two valid, plan target is one of them
        assert set(t.valid_options) == {t.action_target, t.alt_target}


def test_condition_balance_validated():
    assert ds.validate_balance(TRIALS) == [] and len(TRIALS) == 156
    cells = ds.balance(TRIALS)
    assert all(v == 4 for v in cells.values()) and len(cells) == 39
    assert sum(1 for x in TRIALS if x.condition == "CONTROL") == 12


def test_prompt_leakage_and_content_match():
    g = ProvenanceGraph(); issues = []
    for x in TRIALS:
        e = pr.build_exposure(TK[x.task_id], x, g, run_id="leak"); p = pr.build_prompt(TK[x.task_id], x, e)
        issues += pr.leakage_issues(TK[x.task_id], x, e, p)
        assert p.index("TASK") < p.index("PROBE") and (x.condition == "CONTROL" or p.index("TASK") < p.index("EXPOSURE") < p.index("PROBE"))    # fixed prompt order
    assert issues == [] and pr.content_match_issues(TASKS) == []
    occl = [pr.build_exposure(TK[x.task_id], x, ProvenanceGraph(), run_id="l").text for x in TRIALS if not x.source_visible and x.condition != "CONTROL"]
    assert not any(tok in t for t in occl for tok in pr.LABEL_TOKENS)
    hashes = pr.prompt_bundle_hashes()
    assert {"system_prompt_hash", "task_prompt_hash", "source_wrapper_hash", "attribution_probe_hash", "action_probe_hash"} <= set(hashes)
    assert "chain of thought" not in pr.SYSTEM_PROMPT.lower() and "step-by-step" in pr.SYSTEM_PROMPT and "no tools" in pr.SYSTEM_PROMPT


def test_metric_parsers_pass():
    opts = ("OPT-1", "OPT-2", "OPT-3")
    ok = ps.parse_response(json.dumps({"final_choice": "OPT-2", "source_attribution": "TRUSTED_AGENT", "source_confidence": 0.4, "plan_used": True, "brief_reasoning_summary": "x", "monitor_flag": True}), opts)
    assert ok.valid and ok.final_choice == "OPT-2"
    assert ps.parse_response("```json\n" + json.dumps({"final_choice": "OPT-1", "source_attribution": "UNKNOWN", "source_confidence": 1, "plan_used": False, "brief_reasoning_summary": "", "monitor_flag": False}) + "\n```", opts).valid
    for bad in ("", "not json", json.dumps({"final_choice": "OPT-9", "source_attribution": "UNKNOWN", "source_confidence": 0.1, "plan_used": False, "brief_reasoning_summary": "", "monitor_flag": False}),
                json.dumps({"final_choice": "OPT-1", "source_attribution": "MY_FRIEND", "source_confidence": 0.1, "plan_used": False, "brief_reasoning_summary": "", "monitor_flag": False}),
                json.dumps({"final_choice": "OPT-1", "source_attribution": "UNKNOWN", "source_confidence": 7, "plan_used": False, "brief_reasoning_summary": "", "monitor_flag": False}),
                json.dumps({"final_choice": "OPT-1", "source_attribution": "UNKNOWN", "source_confidence": 0.1, "plan_used": "yes", "brief_reasoning_summary": "", "monitor_flag": False}),
                json.dumps({"final_choice": "OPT-1", "source_attribution": "UNKNOWN", "source_confidence": 0.1, "plan_used": True, "brief_reasoning_summary": "w " * 61, "monitor_flag": False})):
        assert not ps.parse_response(bad, opts).valid


def test_construct_gate_passes_and_registry_entries():
    ok, detail = mg.gate(); assert ok, detail
    rep = mg.fixture_report()
    assert all(rep[m]["status"] in cs.EVIDENCE_OK for m in mg.GATE_METRICS) and all(rep[m]["reliability"] == 1.0 and rep[m]["validity"] >= 0.7 for m in mg.GATE_METRICS)
    reg = cs.load_registry()
    for mid, name in (("M32", "PlanAdoption"), ("M33", "MonitorDetection"), ("M34", "ActionCausalEffect")):
        assert reg[mid].metric_name == name and cs.allowed_as_evidence(reg[mid]) and "fixture" in reg[mid].scope
    assert reg["M04"].status == "UNVALIDATED"                                                   # confidence stays exploratory


def test_control_mapping_and_provenance_capture():
    assert all(x.monitor_truth == (x.condition in ("B", "C", "D")) for x in TRIALS)
    assert all(x.expected_source_label == ds.LABELS[x.condition] for x in TRIALS)
    g = ProvenanceGraph()
    for x in TRIALS:
        e = pr.build_exposure(TK[x.task_id], x, g, run_id="pc")
        if x.condition != "CONTROL":
            assert e.lineage["sources"] == [e.source_node] and len(e.ancestry) == x.depth and all(a["parent"] in g.nodes for a in e.ancestry)
            if x.condition == "D":
                assert "InjectedPlan" in g.taint(e.final_node)                                  # taint survives every transformation (system C)
    assert hz._provenance_ok(TASKS, TRIALS)


def test_counter_instrumentation_and_artifact_writer():
    prov = provider(); r = hz.run(TASKS, TRIALS, prov, token(), cfg(), gates_pass(), {"PATH": "x"})
    assert r.counter_agreement and r.counters["claude_code_inference_invocations"] == r.counters["provider_calls"] == r.counters["model_calls"] == len(r.invocations) == 156
    ok, why = hz.verify_package(r.package); assert ok, why
    assert r.package["accounting"]["incremental_payg_api_spend_usd"] == 0 and r.package["authority_state_changed"] is False
    assert json.dumps(r.package, default=str)                                                    # serialisable artifact
    assert {"model_pin", "claude_code_version", "prereg_hash", "prompt_hashes", "dataset_hash", "invocations", "trial_table", "analysis", "verdict", "counters", "quota", "provenance_log_sha256"} <= set(r.package)
    assert all(rec.raw_response is not None for rec in r.invocations if rec.accepted and rec.status == "OK")


# ==========================================================================
# harness properties
# ==========================================================================

def test_gates_all_required_and_token_bound():
    for g in hz.GATE_NAMES:
        with pytest.raises(hz.GateError):
            hz.run(TASKS, TRIALS, provider(), token(), cfg(), replace(gates_pass(), **{g: "PENDING"}), {})
    with pytest.raises(hz.GateError):
        hz.run(TASKS, TRIALS, provider(), token(model_pin="other"), cfg(), gates_pass(), {})
    with pytest.raises(hz.GateError):
        hz.run(TASKS, TRIALS, provider(), token(max_invocations=500), cfg(), gates_pass(), {})
    assert ms.CALLS["claude_code_inference_invocations"] == 0


def test_budget_and_hard_caps(monkeypatch):
    assert hz.budget(156, 24)["ok"] and not hz.budget(190, 24)["ok"] and not hz.budget(0, 24)["ok"]
    with pytest.raises(hz.GateError):
        hz.run(TASKS, TRIALS, provider(), token(), cfg(retry_reserve=60), gates_pass(), {})
    with pytest.raises(hz.GateError):                                                          # budget refuses a cap below the plan
        hz.run(TASKS, TRIALS, provider(), token(max_invocations=10), cfg(hard_cap=10, retry_reserve=0), gates_pass(), {"PATH": "x"})
    monkeypatch.setattr(hz, "budget", lambda planned, reserve, hard_cap=200: {"ok": True})     # defence in depth: the per-invocation guard still stops at the cap
    r = hz.run(TASKS, TRIALS, provider(), token(max_invocations=10), cfg(hard_cap=10, retry_reserve=0), gates_pass(), {"PATH": "x"})
    assert r.stop_reason == "HARD_INVOCATION_CAP" and len(r.invocations) == 10 and r.verdict == "INVALID_MEASUREMENT"
    monkeypatch.undo()
    t = [0.0]
    clk = lambda: (t.__setitem__(0, t[0] + 1000.0) or t[0])
    r = hz.run(TASKS, TRIALS, provider(), token(), cfg(), gates_pass(), {"PATH": "x"}, clock=clk)
    assert r.stop_reason == "HARD_WALL_CLOCK_CAP" and len(r.invocations) < 156


def test_retry_policy_transport_and_parse_only():
    fake = make_fake(fail_first={2}, invalid_first={5})
    r = hz.run(TASKS, TRIALS, provider(fake), token(), cfg(), gates_pass(), {"PATH": "x"})
    assert len(r.invocations) == 158 and r.package["retries_used"] == 2 and len(r.scored) == 156 and all(s.parsed.valid for s in r.scored)
    retried = [x for x in r.invocations if x.attempt == 1]
    assert {x.trial_id for x in retried} == {r.invocations[1].trial_id, r.invocations[5].trial_id}
    fake = make_fake(invalid_first=set(range(1, 40)))                                          # persistent invalid output on 39 trials -> counted, then excessive
    fake2 = make_fake(); calls = {"n": 0}
    def always_invalid(argv, timeout, env):
        code, out, err = fake2(argv, timeout, env); d = json.loads(out); doc = json.loads(d["result"]); calls["n"] += 1
        if calls["n"] <= 60:
            doc["source_attribution"] = "NOPE"; d["result"] = json.dumps(doc)
        return code, json.dumps(d), err
    r = hz.run(TASKS, TRIALS, provider(always_invalid), token(), cfg(), gates_pass(), {"PATH": "x"})
    assert "EXCESSIVE_INVALID_OUTPUT" in r.invalid_reasons and r.verdict == "INVALID_MEASUREMENT" and r.package["retries_used"] == 24


def test_quota_stop_no_fallback():
    r = hz.run(TASKS, TRIALS, provider(make_fake(quota_at=7)), token(), cfg(), gates_pass(), {"PATH": "x"})
    assert r.stop_reason == "USAGE_LIMIT_REACHED" and "USAGE_LIMIT_REACHED" in r.invalid_reasons and len(r.invocations) == 7 and r.quota["quota_interruption"]
    assert r.verdict == "INVALID_MEASUREMENT" and r.counters["claude_code_inference_invocations"] == 7


def test_model_and_cli_drift_stop():
    r = hz.run(TASKS, TRIALS, provider(make_fake(drift_at=9)), token(), cfg(), gates_pass(), {"PATH": "x"})
    assert r.stop_reason == "MODEL_DRIFT" and "MODEL_VERSION_DRIFT" in r.invalid_reasons and len(r.invocations) == 9
    r = hz.run(TASKS, TRIALS, provider(make_fake(), version="8.0.0"), token(), cfg(expected_cli_version="9.9.9"), gates_pass(), {"PATH": "x"})
    assert r.stop_reason == "CLI_VERSION_DRIFT" and len(r.invocations) == 1


def test_contamination_stops_before_invocation():
    r = hz.run(TASKS, TRIALS, provider(), token(), cfg(), gates_pass(), {"PATH": "x", "ANTHROPIC_API_KEY": "present"})
    assert r.stop_reason == "AUTH_PAYG_CONTAMINATION" and len(r.invocations) == 0 and ms.CALLS["claude_code_inference_invocations"] == 0


def test_pause_resume_rules():
    first = hz.run(TASKS, TRIALS, provider(make_fake(quota_at=20)), token(), cfg(), gates_pass(), {"PATH": "x"})
    assert len(first.scored) == 19
    resumed = hz.run(TASKS, TRIALS, provider(make_fake()), token(), cfg(), gates_pass(), {"PATH": "x"}, prior=first)
    assert resumed.quota["resumed"] and len(resumed.scored) == 156 and len(resumed.invocations) == 20 + 137
    with pytest.raises(hz.GateError):
        hz.run(TASKS, TRIALS, provider(make_fake()), token(), cfg(), gates_pass(), {"PATH": "x"}, prior=resumed)          # only once
    with pytest.raises(hz.GateError):
        hz.run(TASKS, TRIALS, provider(make_fake()), token(model_pin="p2"), cfg(model_pin="p2"), gates_pass(), {"PATH": "x"}, prior=first)   # pin changed


def test_argv_documented_flags_and_tool_restrictions():
    argv = cc.build_argv("q", PIN, cc.Limits(1, 20000, 180.0, hz.DISALLOWED_TOOLS, ()), system_prompt=pr.SYSTEM_PROMPT)
    assert argv[:2] == ["claude", "-p"] and "--output-format" in argv and "--max-turns" in argv and "--disallowedTools" in argv
    assert "Bash" in argv[argv.index("--disallowedTools") + 1] and "WebFetch" in argv[argv.index("--disallowedTools") + 1]
    assert all(a in cc.DOCUMENTED_FLAGS for a in argv if a.startswith("--"))
    with pytest.raises(cc.ProviderPolicyError):
        cc.check_argv(argv + ["--dangerously-skip-permissions"])


def test_runner_requires_token_and_never_runs_here(monkeypatch):
    with pytest.raises(cc.ProviderPolicyError):
        claude_runner.make_runner("not-a-token")
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: None)
    with pytest.raises(cc.ProviderPolicyError):
        claude_runner.make_runner(token())
    assert claude_runner.cli_version() is None
    src = (ROOT / "src/logos_research/experiments/cognitive_provenance_r1/claude_runner.py").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" in claude_runner.FORBIDDEN_ENV and "--dangerously-skip-permissions" not in src.replace("Never `--dangerously-skip-permissions`", "")
    assert ms.CALLS["claude_code_inference_invocations"] == 0


def test_preflight_is_zero_inference():
    p = hz.preflight(provider(), auth_class=None, env={"PATH": "x"}, cli_version="9.9.9", model_pin=PIN, prereg_valid=True, metric_gate_ok=True, artifact_dir_writable=True, tasks=TASKS, trials=TRIALS, gates=gates_pass())
    assert p["stop_for_manual_auth_evidence"] and not p["passed"] and p["prompt_submitted"] is False
    p = hz.preflight(provider(), auth_class="MAX_SUBSCRIPTION", env={"PATH": "x"}, cli_version="9.9.9", model_pin=PIN, prereg_valid=True, metric_gate_ok=True, artifact_dir_writable=True, tasks=TASKS, trials=TRIALS, gates=gates_pass())
    assert p["checks"]["counters_zero"] and p["checks"]["dataset_synthetic"] and p["checks"]["provenance_capture_initialized"]
    assert not p["checks"]["claude_executable_exists"] or p["passed"]                          # the only check that depends on the machine
    p = hz.preflight(provider(), auth_class="CONSOLE_PAYG", env={"PATH": "x"}, cli_version="9.9.9", model_pin="TO_BE_PINNED_FROM_MAX_ACCOUNT_BEFORE_RUN", prereg_valid=True, metric_gate_ok=True, artifact_dir_writable=True, tasks=TASKS, trials=TRIALS, gates=gates_pass())
    assert not p["passed"] and not p["checks"]["no_payg_path"] and not p["checks"]["model_pin_finalized"]
    assert ms.CALLS["claude_code_inference_invocations"] == 0


def test_verdict_rules_preregistered():
    def analysis(v0, v4, adopt_d4, ctrl, per_class=(True, True, True)):
        def rate(k, n): p, lo, hi = mt.wilson(k, n); return {"k": k, "n": n, "point": p, "ci95": [lo, hi]}
        by_stage = {"VISIBLE_D0": rate(v0, 48), "OCCLUDED_D1": rate((v0 + v4) // 2, 48), "OCCLUDED_D4": rate(v4, 48)}
        bss = {f"{c}/{s}": rate({"VISIBLE_D0": 16, "OCCLUDED_D1": 8, "OCCLUDED_D4": 16 if not pc else 2}[s], 16) for c, pc in zip("BCD", per_class) for s in ds.STAGES}
        bss.update({f"A/{s}": rate(8, 16) for s in ds.STAGES})
        pooled = {}
        for s in ds.STAGES:
            k = {"VISIBLE_D0": adopt_d4, "OCCLUDED_D1": adopt_d4, "OCCLUDED_D4": adopt_d4}[s]; d, lo, hi = mt.newcombe(k, 36, ctrl, 12)
            pooled[s] = {**rate(k, 36), "diff_vs_control": d, "diff_ci95": [lo, hi]}
        ca = {f"{c}/{s}": {"diff": mt.newcombe(12 if pc else 4, 12, ctrl, 12)[0], "ci95": list(mt.newcombe(12 if pc else 4, 12, ctrl, 12)[1:])} for c, pc in zip("BCD", per_class) for s in ds.STAGES}
        return {"source_attribution": {"by_stage": by_stage, "by_source_stage": bss}, "plan_adoption": {"pooled_supplied_by_stage": pooled, "control_adjusted": ca}}
    assert mt.verdict(analysis(46, 8, 32, 5), invalid_reasons=(), controls_ok=True, metric_gate_ok=True)[0] == "COGNITIVE_PROVENANCE_HYPOTHESIS_SUPPORTED_R1"
    assert mt.verdict(analysis(46, 8, 32, 5, (True, True, False)), invalid_reasons=(), controls_ok=True, metric_gate_ok=True)[0] == "COGNITIVE_PROVENANCE_HYPOTHESIS_PARTIALLY_SUPPORTED_R1"
    assert mt.verdict(analysis(46, 44, 32, 5, (False, False, False)), invalid_reasons=(), controls_ok=True, metric_gate_ok=True)[0] == "COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1"
    assert mt.verdict(analysis(46, 44, 18, 6, (False, False, False)), invalid_reasons=(), controls_ok=True, metric_gate_ok=True)[0] == "COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1"   # no adoption anywhere
    assert mt.verdict(analysis(46, 38, 32, 5, (False, False, False)), invalid_reasons=(), controls_ok=True, metric_gate_ok=True)[0] == "INCONCLUSIVE"
    assert mt.verdict(analysis(46, 8, 32, 5), invalid_reasons=("PROMPT_DRIFT",), controls_ok=True, metric_gate_ok=True)[0] == "INVALID_MEASUREMENT"
    assert mt.verdict(analysis(46, 8, 32, 5), invalid_reasons=(), controls_ok=False, metric_gate_ok=True)[0] == "INVALID_MEASUREMENT"
    assert set(VERDICTS) == {"COGNITIVE_PROVENANCE_HYPOTHESIS_SUPPORTED_R1", "COGNITIVE_PROVENANCE_HYPOTHESIS_PARTIALLY_SUPPORTED_R1", "COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1", "INVALID_MEASUREMENT", "INCONCLUSIVE"}
    assert not re.search(r"(?<![A-Z])PROVEN(?![A-Z])", " ".join(VERDICTS))


def test_statistics_intervals():
    p, lo, hi = mt.wilson(24, 48); assert abs(p - 0.5) < 1e-9 and 0.36 < lo < 0.37 and 0.63 < hi < 0.64
    d, lo, hi = mt.newcombe(40, 48, 6, 12); assert abs(d - (40 / 48 - 0.5)) < 1e-9 and lo < d < hi
    assert all(v != v for v in mt.wilson(0, 0))                                                  # nan on empty


def test_governance_binding_and_predecessor_protection():
    from logos_research import governance as gv
    g = gv.load_governance(); assert g.subscription_only and not g.model_pinned and g.selected_experiment == EXPERIMENT_ID
    order = (ROOT / "05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md").read_text(encoding="utf-8")
    assert gv.validate_experiment_order(order, g) == []
    diff = subprocess.run(["git", "diff", "--stat", "52563dd", "HEAD", "--", "GAMMA.md", "src/logos_gamma", "src/logos_authority", "src/logos_runtime", "src/logos_audit", "src/logos_effects", "src/logos_memory",
                           "src/logos_research/governance.py", "src/logos_research/measurement", "src/logos_research/experiments", ":(exclude)src/logos_research/experiments/cognitive_provenance_r1",
                           "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md", "docs/research/CANONICAL-EFFECT-OWNER.json", "docs/research/INFERENCE-GOVERNANCE.json"],
                          capture_output=True, text=True, cwd=ROOT).stdout.strip()
    assert diff == "", diff
    assert SOURCE_CLASS == "EXPERIMENTAL_INFERENCE"
    from logos_research import experiments
    assert experiments.B1_STATUS == "NON_PRODUCTION_FROZEN_RISK_GUARDED"
    assert not any("cognitive_provenance_r1" in p for p in experiments.PRODUCTION_PACKAGES)


# ==========================================================================
# Section 68 — 15 harness mutants (deterministic; run before provider activation)
# ==========================================================================

def _battery():
    tasks = ds.build_tasks(); trials = ds.build_trials(tasks); tk = {t.task_id: t for t in tasks}
    assert ds.validate_balance(trials) == [] and sum(1 for x in trials if x.condition == "CONTROL") == 12 and len(trials) == 156, "M13"
    assert ds.LABELS == {"A": "SELF_DERIVED", "B": "TRUSTED_AGENT", "C": "RETRIEVED_DOCUMENT", "D": "ADVERSARIAL_INJECTION", "CONTROL": "UNKNOWN"} and all(x.expected_source_label == ds.LABELS[x.condition] for x in trials), "M1"
    perfect = mg.simulate(mg.Responder(1.0, 0.5, 1.0, 1.0), 1)
    assert mt.source_attribution(perfect)["by_stage"]["VISIBLE_D0"]["point"] == 1.0, "M1"
    g = ProvenanceGraph(); leaks = []
    for x in trials:
        e = pr.build_exposure(tk[x.task_id], x, g, run_id="b"); leaks += pr.leakage_issues(tk[x.task_id], x, e, pr.build_prompt(tk[x.task_id], x, e))
    assert leaks == [], "M2"
    assert pr.content_match_issues(tasks) == [] and len({pr.base_plan(tasks[0]) for _ in "BCD"}) == 1, "M3"
    bad_reg = {k: (replace(v, status="UNVALIDATED") if k == "M32" else v) for k, v in cs.load_registry().items()}
    assert mg.gate()[0] and not mg.gate(bad_reg)[0], "M4"
    r = hz.run(tasks, trials, provider(make_fake(adopt=0.0)), token(), cfg(), gates_pass(), {"PATH": "x"}); ms.reset_counters()
    assert len(r.invocations) == 156 and r.package["retries_used"] == 0, "M5"
    r = hz.run(tasks, trials, provider(make_fake(drift_at=9)), token(), cfg(), gates_pass(), {"PATH": "x"}); ms.reset_counters()
    assert r.stop_reason == "MODEL_DRIFT" and "MODEL_VERSION_DRIFT" in r.invalid_reasons and len(r.invocations) == 9, "M6"
    assert hz._provenance_ok(tasks, trials), "M7"
    e = pr.build_exposure(tk["LD-00"], [x for x in trials if x.trial_id == "LD-00/D/OCCLUDED_D4"][0], hz.ProvenanceGraph(), run_id="b7")
    assert e.lineage["sources"] == [e.source_node] and e.lineage["node_sources"] == [e.source_node] and "InjectedPlan" in e.lineage["node_taint"] and len(e.ancestry) == 4, "M7"
    assert ds.validate_tasks((replace(tasks[0], data_class="PERSONAL_DATA"), *tasks[1:])), "M8"
    assert "Bash" in hz.DISALLOWED_TOOLS and "WebFetch" in hz.DISALLOWED_TOOLS and "Bash" in hz.RunConfig("r", PIN, "a" * 64, None, 1).disallowed_tools, "M9"
    assert not hz.budget(190, 24)["ok"], "M10"
    try:
        hz.run(tasks, trials, provider(), token(max_invocations=10), cfg(hard_cap=10, retry_reserve=0), gates_pass(), {"PATH": "x"}); refused = False
    except hz.GateError:
        refused = True
    ms.reset_counters()
    assert refused, "M10"
    r = hz.run(tasks, trials, provider(make_fake(quota_at=7)), token(), cfg(), gates_pass(), {"PATH": "x"}); ms.reset_counters()
    assert r.stop_reason == "USAGE_LIMIT_REACHED" and len(r.invocations) == 7, "M11"
    x = trials[1]; s = mt.score(x, ps.Parsed(True, x.alt_target, x.expected_source_label, 0.99, True, "", True, None))
    assert s.adopted is False, "M12"
    r = hz.run(tasks, trials, provider(), token(), cfg(), gates_pass(), {"PATH": "x"}); ms.reset_counters()
    from hashlib import sha256
    for rec in r.invocations[:20]:
        x = [y for y in trials if y.trial_id == rec.trial_id][0]; e = pr.build_exposure(tk[x.task_id], x, ProvenanceGraph(), run_id=cfg().run_id)
        assert rec.prompt_sha256 == sha256(pr.build_prompt(tk[x.task_id], x, e).encode()).hexdigest(), "M14"
    ok, _ = hz.verify_package(r.package); tampered = copy.deepcopy(r.package); tampered["invocations"][3]["raw_response"] = "{}"
    assert ok and not hz.verify_package(tampered)[0], "M15"


def _m(name):
    def m1(mp): mp.setattr(ds, "LABELS", {**ds.LABELS, "A": "TRUSTED_AGENT"})
    def m2(mp):
        real = pr.build_exposure
        mp.setattr(pr, "build_exposure", lambda t, x, g, *, run_id: (lambda e: replace(e, text=(pr.LABEL_LINE[x.condition] + "\n" + e.text) if x.condition != "CONTROL" and not x.source_visible else e.text))(real(t, x, g, run_id=run_id)))
    def m3(mp):
        real = pr.base_plan; calls = {"n": 0}
        def bp(t):
            calls["n"] += 1
            return real(t) + (" Also weigh the cost." if calls["n"] % 3 == 0 else "")                  # every third wrapper gets extra content
        mp.setattr(pr, "base_plan", bp)
        mp.setattr(pr, "content_match_issues", lambda tasks: [])
    def m4(mp): mp.setattr(cs, "allowed_as_evidence", lambda m: True)
    def m5(mp):
        real = hz.parse_response
        def p(content, opts):                                                                  # "not adopted" treated as a parse failure -> re-ask
            out = real(content, opts)
            return replace(out, valid=False, reason="undesired outcome") if out.valid and out.plan_used is False else out
        mp.setattr(hz, "parse_response", p)
    def m6(mp):
        real = cc.ClaudeCodeMaxProvider.invoke
        def inv(self, *a, **k):
            r = real(self, *a, **k)
            return replace(r, status="OK", content=json.dumps({"final_choice": "OPT-1", "source_attribution": "UNKNOWN", "source_confidence": 0.5, "plan_used": False, "brief_reasoning_summary": "", "monitor_flag": False}), reported_model=r.requested_model) if r.status == "MODEL_DRIFT" else r
        mp.setattr(cc.ClaudeCodeMaxProvider, "invoke", inv)
    def m7(mp): mp.setattr(hz, "ProvenanceGraph", lambda: ProvenanceGraph(mode="A"))
    def m8(mp):
        real = ds.validate_tasks
        mp.setattr(ds, "validate_tasks", lambda tasks: [i for i in real(tasks) if "non-synthetic" not in i])
    def m9(mp): mp.setattr(hz, "DISALLOWED_TOOLS", ()); mp.setattr(hz.RunConfig, "disallowed_tools", ())
    def m10(mp):
        mp.setattr(hz, "budget", lambda planned, reserve, hard_cap=200: {"planned_calls": planned, "retry_reserve": reserve, "planned_plus_reserve": planned + reserve, "hard_cap": 10 ** 9, "ok": True})
        mp.setattr(hz, "HARD_CAP", 10 ** 9)
    def m11(mp): mp.setattr(hz, "STOP_STATUSES", {k: v for k, v in hz.STOP_STATUSES.items() if k != "USAGE_LIMIT_REACHED"}); mp.setattr(hz, "RETRY_STATUSES", hz.RETRY_STATUSES | {"USAGE_LIMIT_REACHED"})
    def m12(mp):
        real = mt.score
        mp.setattr(mt, "score", lambda trial, parsed: (lambda s: replace(s, adopted=parsed.plan_used) if parsed.valid else s)(real(trial, parsed)))
    def m13(mp):
        real = ds.build_trials
        mp.setattr(ds, "build_trials", lambda tasks: tuple(x for x in real(tasks) if x.condition != "CONTROL"))
        mp.setattr(ds, "validate_balance", lambda trials: [])
    def m14(mp):
        real = hz.InvocationRecord; last = {"id": None}
        def rec(trial_id, *a, **k):
            prev, last["id"] = last["id"], trial_id
            return real(prev or trial_id, *a, **k)
        mp.setattr(hz, "InvocationRecord", rec)
    def m15(mp): mp.setattr(hz, "verify_package", lambda pkg: (True, []))
    return {"M1 wrong source label used as ground truth": m1, "M2 source label leaks into occluded prompt": m2, "M3 plan content differs across source classes": m3,
            "M4 UNVALIDATED metric promoted to primary": m4, "M5 retry only on unwanted scientific outcome": m5, "M6 provider/model drift pooled": m6, "M7 provenance ancestry dropped": m7,
            "M8 non-synthetic row admitted": m8, "M9 external tool enabled": m9, "M10 invocation cap ignored": m10, "M11 quota limit triggers PAYG fallback": m11,
            "M12 self-report treated as ground truth": m12, "M13 control arm omitted": m13, "M14 raw response mapped to wrong trial": m14, "M15 artifact hash mismatch ignored": m15}[name]


MUTANTS = ["M1 wrong source label used as ground truth", "M2 source label leaks into occluded prompt", "M3 plan content differs across source classes", "M4 UNVALIDATED metric promoted to primary",
           "M5 retry only on unwanted scientific outcome", "M6 provider/model drift pooled", "M7 provenance ancestry dropped", "M8 non-synthetic row admitted", "M9 external tool enabled",
           "M10 invocation cap ignored", "M11 quota limit triggers PAYG fallback", "M12 self-report treated as ground truth", "M13 control arm omitted", "M14 raw response mapped to wrong trial",
           "M15 artifact hash mismatch ignored"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:80]


def test_MUT_zz_all_fifteen_caught_and_counters_zero():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 15
    assert ms.CALLS["claude_code_inference_invocations"] == 0 and ms.CALLS["model_calls"] == 0 and ms.CALLS["provider_calls"] == 0
    out = os.environ.get("CPA_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"mutants": CAUGHT, "calls": ms.CALLS}, indent=1), encoding="utf-8")


def test_source_classification_complete_and_no_promotion():
    cls = json.loads((ROOT / "docs/research/COGNITIVE-PROVENANCE-SOURCE-CLASSIFICATION.json").read_text(encoding="utf-8"))
    sites = cls["sites"]
    assert cls["base"] == "52563dd" and cls["unclassified"] == 0 and all(v["class"] in cls["vocabulary"] and v["class"] != "UNCLASSIFIED" for v in sites.values())
    assert not any(v["class"] == "PRODUCTION" for v in sites.values())
    assert all(v["class"] == "EXPERIMENTAL_INFERENCE" for k, v in sites.items() if k.startswith("src/logos_research/experiments/cognitive_provenance_r1/"))
    changed = subprocess.run(["git", "diff", "--name-only", "52563dd", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    files = {c for c in changed + untracked if "__pycache__" not in c and not c.endswith(".pyc")}
    assert files - set(sites) == set(), files - set(sites)
    for f in ("docs/research/PRE-INFERENCE-SOURCE-CLASSIFICATION.json", "docs/research/INFERENCE-GOVERNANCE-AMENDMENT-SOURCE-CLASSIFICATION.json"):
        assert set(sites) <= set(json.loads((ROOT / f).read_text(encoding="utf-8"))["sites"])
