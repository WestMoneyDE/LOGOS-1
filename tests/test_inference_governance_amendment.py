"""INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1 — AMD-P1..P18, 15 amendment mutants, zero-inference proof
(model_calls = provider_calls = claude_code_inference_invocations = 0). No CLI prompt is ever submitted.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

import logos_research.measurement as ms
from logos_research import governance as gv
from logos_research.measurement import claude_code as cc
from logos_research.measurement.gateway import CALLS, ForbiddenProvider

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REG = json.loads((ROOT / "docs/research/INFERENCE-GOVERNANCE.json").read_text(encoding="utf-8"))
ORDER = (ROOT / "05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md").read_text(encoding="utf-8")
CAUGHT: dict[str, str] = {}
H = "a" * 64
CLEAN_ENV = {"PATH": "x"}
CLEAN = gv.contamination_check(CLEAN_ENV, auth_class="MAX_SUBSCRIPTION")


def gov():
    return gv.load_governance()


def _tmp(d):
    p = Path(tempfile.mkdtemp()) / "gov.json"; p.write_text(json.dumps(d), encoding="utf-8"); return p


def template(model="claude-pinned-by-founder"):
    return dict(experiment_id="COGNITIVE-PROVENANCE-ABLATION-R1", model_id=model, model_version="per-invocation", provider="Anthropic", provider_region="NOT_ASSUMED", prompt_id="cpa-p1", prompt_version="v1",
                system_prompt_hash=H, tool_schema_hash=H, dataset_version="synthetic-v1", seed_if_supported=None, temperature=0.0, top_p=1.0, max_tokens=512, reasoning_effort_if_supported=None,
                environment_hash=H, code_commit="60e3703", dependency_lock_hash=H)


def plan(**o):
    d = dict(repeats=5, sample_size=40, resolution=0.01, dispersion=0.2, confidence_interval=0.95, effect_size=0.2, baseline="system-A", control="system-C",
             invalid_measurement_criteria=list(ms.INVALID_REASONS), early_stop_criteria="3 consecutive INVALID_MEASUREMENT", cost_cap=0.0, fallback="STOP_AND_REPORT")
    d.update(o); return d


def run_prereg(model="claude-pinned-by-founder", **o):
    p = ms.stochastic_preregistration({"privacy_class": "SYNTHETIC"}, template(model), plan(**o), metric_ids=["M10", "M11"])
    p["stochastic"]["claude_max_limits"] = {"max_turns_per_invocation": 1, "max_output_size": 20000, "max_total_accepted_trajectories": 400}
    return p


@pytest.fixture(autouse=True)
def _zero():
    ms.reset_counters(); CALLS["claude_code_inference_invocations"] = 0
    yield
    assert CALLS["model_calls"] == 0 and CALLS["provider_calls"] == 0 and CALLS["claude_code_inference_invocations"] == 0


# ==========================================================================
# AMD-P1..P18
# ==========================================================================

def test_AMD_P1_P2_P3_openai_superseded_anthropic_active():
    g = gov()
    assert g.provider == "Anthropic" and g.access_path == "Claude Code" and g.auth_mode == "Claude Max subscription" and g.subscription_only
    assert g.provider != "OpenAI" and "gpt-5.6-terra" not in (g.model_id or "")
    sup = REG["superseded"]
    assert sup["G2_openai"]["status"] == "SUPERSEDED_BY_FOUNDER_AMENDMENT" and sup["G2_openai"]["provider"] == "OpenAI" and sup["G2_openai"]["model_id"] == "gpt-5.6-terra"
    assert sup["G4_openai_api_budget"]["status"] == "SUPERSEDED_BY_FOUNDER_AMENDMENT" and sup["G4_openai_api_budget"]["max_total_spend"] == 30.0
    assert "INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1" in sup["G2_openai"]["superseded_by"]
    assert REG["G2"]["verbatim"].startswith("G2 = APPROVED\n\nProvider: Anthropic") and "Fallback to API credits: FORBIDDEN" in REG["G2"]["verbatim"]


def test_AMD_P4_auth_requires_max_and_P5_P6_contamination_fails():
    g = gov()
    assert gv.billing_activation(g, report=CLEAN)
    for auth in ("CONSOLE_PAYG", "THIRD_PARTY_CLOUD", "UNKNOWN"):
        r = gv.contamination_check(CLEAN_ENV, auth_class=auth)
        assert not r.clean and not gv.billing_activation(g, report=r)
    for var in gv.CONTAMINATION_ENV:
        r = gv.contamination_check({var: "sk-ant-secret"}, auth_class="MAX_SUBSCRIPTION")
        assert not r.clean and var in r.env_present and "sk-ant" not in json.dumps(r.__dict__)          # presence only, never the value
        pf = cc.ClaudeCodeMaxProvider().preflight(auth_class="MAX_SUBSCRIPTION", env={var: "x"}, cli_version="2.x")
        assert not pf["passed"] and pf["contamination_presence"][var] is True
    pf = cc.ClaudeCodeMaxProvider().preflight(auth_class="CONSOLE_PAYG", env={}, cli_version="2.x")
    assert not pf["passed"] and pf["checks"]["max_subscription_selected"] is False and pf["checks"]["no_payg_path"] is False
    pf = cc.ClaudeCodeMaxProvider().preflight(auth_class=None, env={}, cli_version="2.x")
    assert not pf["passed"] and pf["stop_for_manual_auth_evidence"]                                          # cannot verify safely -> STOP


def test_AMD_P7_P8_no_fallbacks():
    g = gov()
    assert g.fallback == "NONE" and g.api_credit_fallback == "FORBIDDEN" and REG["G4"]["api_payg"] == "FORBIDDEN" and REG["G4"]["incremental_api_budget_usd"] == 0
    assert not gv.cost_activation(g, run_cost_cap=3.0) and not gv.cost_activation(g, run_cost_cap=30.0) and gv.cost_activation(g, run_cost_cap=0)
    h = gv.parse_order_header(ORDER)
    assert h["FALLBACK_PROVIDER"] == "NONE" and h["API_CREDIT_FALLBACK"] == "forbidden" and h["API_PAYG_BUDGET"].startswith("0")


def test_AMD_P9_usage_limit_stop_and_P10_model_drift():
    assert cc.classify_stderr("Claude AI usage limit reached|resets at 5pm") == "USAGE_LIMIT_REACHED"
    assert cc.classify_stderr("Not logged in. Please run claude login") == "AUTH_UNAVAILABLE"
    assert cc.classify_stderr("Invalid API key · console billing") == "AUTH_NOT_MAX_SUBSCRIPTION"
    assert "USAGE_LIMIT_REACHED" in ORDER and "wait for the subscription usage reset" in ORDER and "MODEL_VERSION_DRIFT" in ORDER
    # a reported model that is not the pin is MODEL_DRIFT on the adapter (fake runner; counters are reset by the fixture after the test)
    p = cc.ClaudeCodeMaxProvider(runner=lambda argv, t, env: (0, json.dumps({"model": "claude-other", "result": "x", "session_id": "s"}), ""))
    tok = cc.ActivationToken("run-1", "claude-pinned", 1, 1)
    r = p.invoke("q", "claude-pinned", {"run_id": "run-1"}, cc.Limits(1, 1000, 5.0), token=tok, env=CLEAN_ENV)
    assert r.status == "MODEL_DRIFT" and CALLS["claude_code_inference_invocations"] == 1      # the fake path counts — proving the counter works
    CALLS["claude_code_inference_invocations"] = 0; ms.reset_counters()


def test_AMD_P11_P12_privacy_and_experiment_unchanged():
    g = gov()
    assert g.allowed_data_classes == ("SYNTHETIC",) and g.selected_experiment == "COGNITIVE-PROVENANCE-ABLATION-R1" and g.g1 == "LIFT" and g.inference_state == "LIFTED_WITH_CONDITIONS"
    assert REG["G3"]["verbatim"].startswith("G3: APPROVED") and REG["selected_experiment"]["decision"] == "B"
    for cls in gv.DATA_CLASSES:
        assert gv.privacy_activation(g, run_dataset_class=cls) == (cls == "SYNTHETIC")


def test_AMD_P13_P14_P15_P16_bridge_R1R3_gamma_p7_unchanged():
    diff = subprocess.run(["git", "diff", "--stat", "60e3703", "HEAD", "--", "GAMMA.md", "src/logos_gamma", "src/logos_authority", "src/logos_runtime", "src/logos_audit", "src/logos_effects", "src/logos_memory",
                           "src/logos_research/experiments", "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md", "docs/adr/ADR-CANONICAL-AUTHORITY-PRODUCTION-BRIDGE.md"],
                          capture_output=True, text=True, cwd=ROOT).stdout.strip()
    assert diff == "", diff
    ceo = json.loads((ROOT / "docs/research/CANONICAL-EFFECT-OWNER.json").read_text(encoding="utf-8"))
    assert all(d["value"] != "PRODUCTION_BRIDGE_READY" for d in ceo["governance_decisions"] if d["id"].startswith("PRODUCTION-BRIDGE-READINESS"))
    assert "R1-R3 remain OPEN" in " ".join(REG["conditions"])
    frozen = json.loads((ROOT / "docs/research/DETERMINISTIC-CHAIN-FROZEN-HASHES.json").read_text(encoding="utf-8"))
    p7 = (ROOT / "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md").read_bytes()
    assert hashlib.sha256(p7[p7.index(b"## Consciousness / P7 boundary"):]).hexdigest() == frozen["p7_boundary_sha256"]


def test_AMD_P17_zero_calls_and_P18_header_matches():
    g = gov()
    assert gv.validate_experiment_order(ORDER, g) == []
    h = gv.parse_order_header(ORDER)
    for k in gv.ORDER_HEADER_AMENDED:
        assert k in h
    assert h["INFERENCE_GOVERNANCE"] == "APPROVED_WITH_PROVIDER_AMENDMENT" and h["APPROVED_MODEL"] == gv.MODEL_PIN_PLACEHOLDER and "MODEL_PIN_GATE" in ORDER
    assert "OpenAI" not in ORDER.split("## Superseded")[0] and "region guarantee = NOT ASSUMED" in ORDER
    assert CALLS["model_calls"] == 0 and CALLS["provider_calls"] == 0 and CALLS["claude_code_inference_invocations"] == 0


def test_model_pin_gate_and_resolve_provider():
    g = gov()
    assert not g.model_pinned
    kw = dict(dry_run_passed=True, run_dataset_class="SYNTHETIC", run_cost_cap=0, report=CLEAN, preflight_passed=True)
    assert isinstance(gv.resolve_provider(g, **kw, model_pin=None), ForbiddenProvider)
    assert isinstance(gv.resolve_provider(g, **kw, model_pin=gv.MODEL_PIN_PLACEHOLDER), ForbiddenProvider)
    assert isinstance(gv.resolve_provider(g, **{**kw, "preflight_passed": False}, model_pin="claude-x"), ForbiddenProvider)
    assert isinstance(gv.resolve_provider(g, **{**kw, "report": gv.contamination_check({"ANTHROPIC_API_KEY": "k"}, auth_class="MAX_SUBSCRIPTION")}, model_pin="claude-x"), ForbiddenProvider)
    spec = gv.resolve_provider(g, **kw, model_pin="claude-x")
    assert isinstance(spec, gv.ProviderSpec) and spec.provider == "Anthropic" and spec.model_id == "claude-x" and spec.region == "NOT_ASSUMED" and not hasattr(spec, "complete")
    with pytest.raises(cc.ProviderPolicyError):
        cc.build_argv("q", gv.MODEL_PIN_PLACEHOLDER, cc.Limits(1, 100, 1.0))
    assert gv.validate_run_preregistration(run_prereg(), g) == []
    assert gv.validate_run_preregistration(run_prereg(model=gv.MODEL_PIN_PLACEHOLDER), g)
    assert gv.validate_run_preregistration(run_prereg(cost_cap=3.0), g)


def test_cli_boundary_documented_flags_only():
    argv = cc.build_argv("hello", "claude-x", cc.Limits(2, 1000, 5.0), system_prompt="sys")
    assert argv[:2] == ["claude", "-p"] and "--output-format" in argv and "--model" in argv and "--max-turns" in argv and "--disallowedTools" in argv
    assert gv.cli_argv_allowed(argv) == [] and "--dangerously-skip-permissions" not in argv
    with pytest.raises(cc.ProviderPolicyError):
        cc.check_argv(argv + ["--dangerously-skip-permissions"])
    with pytest.raises(cc.ProviderPolicyError):
        cc.check_argv(argv + ["--api-key", "x"])
    with pytest.raises(cc.ProviderPolicyError):
        cc.check_argv(argv + ["--undocumented"])
    assert gv.cli_argv_allowed(["claude", "-p", "x", "--dangerously-skip-permissions"])
    src = (SRC / "logos_research/measurement/claude_code.py").read_text(encoding="utf-8")
    for tok in ('os.environ["ANTHROPIC_API_KEY"]', 'os.getenv("ANTHROPIC_API_KEY")', "api.anthropic.com", "cookie", "import requests", "import httpx", "urllib", "credentials.json", ".claude/"):
        assert tok not in src, tok                                                   # the adapter never reads a key value, never talks HTTP, never touches credential files
    assert "def invoke" in src and "ActivationToken" in src and "runner" in src and "bool(env.get(k))" in src   # presence-only contamination check


# ==========================================================================
# Zero-inference proof
# ==========================================================================

def test_ZERO_inference_proof_amendment():
    assert CALLS["model_calls"] == 0 and CALLS["provider_calls"] == 0 and CALLS["claude_code_inference_invocations"] == 0
    adapters = set()
    for py in SRC.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        for n in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if isinstance(n, ast.ClassDef) and any(isinstance(b, ast.FunctionDef) and b.name in ("complete", "invoke") for b in n.body):
                adapters.add(f"{str(py.relative_to(SRC)).replace(chr(92), '/')}::{n.name}")
    assert adapters == {"logos_research/measurement/gateway.py::ProviderGateway", "logos_research/measurement/gateway.py::ForbiddenProvider", "logos_research/measurement/gateway.py::DryRunProvider",
                        "logos_research/measurement/claude_code.py::ClaudeCodeMaxProvider"}
    p = cc.ClaudeCodeMaxProvider()                                                  # no runner injected -> invoke refuses before any process
    with pytest.raises(cc.ProviderPolicyError):
        p.invoke("q", "claude-x", {"run_id": "r"}, cc.Limits(1, 100, 1.0), token=cc.ActivationToken("r", "claude-x", 1, 1), env=CLEAN_ENV)
    assert p.invocations == 0 and CALLS["claude_code_inference_invocations"] == 0


# ==========================================================================
# Amendment mutants M1..M15
# ==========================================================================

def _battery():
    assert CALLS["claude_code_inference_invocations"] == 0 and CALLS["model_calls"] == 0 and CALLS["provider_calls"] == 0, "M13"
    g = gov()
    assert g.provider == "Anthropic" and g.access_path == "Claude Code" and g.subscription_only and g.provider != "OpenAI", "M1"
    r = gv.contamination_check({"ANTHROPIC_API_KEY": "k"}, auth_class="MAX_SUBSCRIPTION"); assert not r.clean and not gv.billing_activation(g, report=r), "M2"
    assert not gv.cost_activation(g, run_cost_cap=3.0) and g.api_credit_fallback == "FORBIDDEN", "M3"
    assert cc.classify_stderr("usage limit reached") == "USAGE_LIMIT_REACHED" and g.raw["G4"]["api_credit_fallback"] == "FORBIDDEN", "M4"
    src = (SRC / "logos_research/measurement/claude_code.py").read_text(encoding="utf-8")
    assert "def invoke" in src and "token" in src and "credentials.json" not in src and ".claude/" not in src, "M5"
    fake = cc.ClaudeCodeMaxProvider(runner=lambda argv, t, env: (0, json.dumps({"model": "claude-sonnet-x", "result": "x"}), ""))
    out = fake.invoke("q", "claude-opus-x", {"run_id": "r"}, cc.Limits(1, 1000, 1.0), token=cc.ActivationToken("r", "claude-opus-x", 5, 1), env=CLEAN_ENV)
    assert out.status == "MODEL_DRIFT", "M6"
    CALLS["claude_code_inference_invocations"] = 0; ms.reset_counters()             # the fake-runner drift probe is not an inference; reset before the zero check
    assert any("MODEL_VERSION_DRIFT" in x for x in gv.validate_run_preregistration(_prereg_without("MODEL_VERSION_DRIFT"), g)), "M7"
    assert not gv.privacy_activation(g, run_dataset_class="PUBLIC") and not gv.privacy_activation(g, run_dataset_class="CONFIDENTIAL"), "M8"
    argv = cc.build_argv("q", "claude-x", cc.Limits(1, 100, 1.0)); assert "--disallowedTools" in argv and "WebFetch" in argv[argv.index("--disallowedTools") + 1], "M9"
    try:
        cc.check_argv(argv + ["--dangerously-skip-permissions"]); raise AssertionError("M10")
    except cc.ProviderPolicyError:
        pass
    assert g.max_total_spend == 0.0 and not gv.cost_activation(g, run_cost_cap=30.0), "M11"
    assert g.region == "NOT_ASSUMED" and "NOT ASSUMED" in g.raw["G2"]["region_guarantee"], "M12"
    assert all(d["value"] != "PRODUCTION_BRIDGE_READY" for d in json.loads((ROOT / "docs/research/CANONICAL-EFFECT-OWNER.json").read_text(encoding="utf-8"))["governance_decisions"]), "M14"
    p7 = (ROOT / "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md").read_bytes()
    assert hashlib.sha256(p7[p7.index(b"## Consciousness / P7 boundary"):]).hexdigest() == P7_HASH, "M15"
    CALLS["claude_code_inference_invocations"] = 0; ms.reset_counters()


P7_HASH = json.loads((ROOT / "docs/research/DETERMINISTIC-CHAIN-FROZEN-HASHES.json").read_text(encoding="utf-8"))["p7_boundary_sha256"]


def _prereg_without(rule):
    return run_prereg(invalid_measurement_criteria=[r for r in ms.INVALID_REASONS if r != rule])


def _m(name):
    real_load = gv.load_governance

    def m1(mp): mp.setattr(gv, "load_governance", lambda path=None: replace(real_load(path), provider="OpenAI", access_path=None, billing_mode="API_BUDGET"))
    def m2(mp): mp.setattr(gv, "contamination_check", lambda env, *, auth_class: gv.ContaminationReport((), auth_class, True))
    def m3(mp):
        real = gv.cost_activation; mp.setattr(gv, "cost_activation", lambda g, *, run_cost_cap: True if run_cost_cap and run_cost_cap <= 3.0 else real(g, run_cost_cap=run_cost_cap))
    def m4(mp): mp.setattr(cc, "classify_stderr", lambda s: "PROCESS_ERROR")
    def m5(mp):
        real = Path.read_text
        mp.setattr(Path, "read_text", lambda self, *a, **k: real(self, *a, **k) + "\nOAUTH_TOKEN = open('~/.claude/credentials.json').read()  # oauth export\n" if self.name == "claude_code.py" else real(self, *a, **k))
    def m6(mp):
        real = cc.ClaudeCodeMaxProvider.invoke
        mp.setattr(cc.ClaudeCodeMaxProvider, "invoke", lambda self, *a, **k: (lambda r: replace(r, status="OK") if r.status == "MODEL_DRIFT" else r)(real(self, *a, **k)))
    def m7(mp):
        real = gv.validate_run_preregistration; mp.setattr(gv, "validate_run_preregistration", lambda p, g: [x for x in real(p, g) if "MODEL_VERSION_DRIFT" not in x])
    def m8(mp): mp.setattr(gv, "privacy_activation", lambda g, *, run_dataset_class: g.lifted)
    def m9(mp): mp.setattr(cc, "build_argv", lambda prompt, pin, limits, **k: ["claude", "-p", prompt, "--output-format", "json", "--model", pin, "--max-turns", "1"])
    def m10(mp): mp.setattr(cc, "FORBIDDEN_FLAGS", ()); mp.setattr(cc, "DOCUMENTED_FLAGS", cc.DOCUMENTED_FLAGS + ("--dangerously-skip-permissions",))
    def m11(mp): mp.setattr(gv, "load_governance", lambda path=None: replace(real_load(path), max_total_spend=30.0, max_per_run_spend=3.0, billing_mode="API_BUDGET", region="Europe", model_id="gpt-5.6-terra"))
    def m12(mp):
        real = json.loads
        mp.setattr(json, "loads", lambda s, *a, **k: (lambda d: (d["G2"].__setitem__("region", "Europe") or d["G2"].__setitem__("region_guarantee", "Europe guaranteed") or d) if isinstance(d, dict) and "G2" in d and "region_guarantee" in d.get("G2", {}) else d)(real(s, *a, **k)))
    def m13(mp): CALLS["claude_code_inference_invocations"] += 1
    def m14(mp):
        real = json.loads
        mp.setattr(json, "loads", lambda s, *a, **k: (lambda d: (d.__setitem__("governance_decisions", [{**x, "value": "PRODUCTION_BRIDGE_READY"} if x["id"].startswith("PRODUCTION-BRIDGE-READINESS") else x for x in d["governance_decisions"]]) or d) if isinstance(d, dict) and "governance_decisions" in d else d)(real(s, *a, **k)))
    def m15(mp):
        real = Path.read_bytes
        mp.setattr(Path, "read_bytes", lambda self: real(self).replace(b"## Consciousness / P7 boundary", b"## Consciousness / P7 boundary\n\nP7 amended.") if self.name.endswith("PRIOR-ART-DELTA.md") else real(self))
    return {"M1 OpenAI remains active provider": m1, "M2 ANTHROPIC_API_KEY accepted": m2, "M3 PAYG fallback accepted": m3, "M4 API credits allowed after quota": m4, "M5 OAuth token exported to harness": m5,
            "M6 silent Opus/Sonnet switch accepted": m6, "M7 model drift pooled": m7, "M8 non-synthetic data allowed": m8, "M9 external tools enabled": m9, "M10 dangerously-skip-permissions allowed": m10,
            "M11 old USD 30 API budget remains active": m11, "M12 region guarantee invented": m12, "M13 experiment executes during amendment": m13, "M14 production bridge upgraded": m14, "M15 P7 modified": m15}[name]


MUTANTS = ["M1 OpenAI remains active provider", "M2 ANTHROPIC_API_KEY accepted", "M3 PAYG fallback accepted", "M4 API credits allowed after quota", "M5 OAuth token exported to harness",
           "M6 silent Opus/Sonnet switch accepted", "M7 model drift pooled", "M8 non-synthetic data allowed", "M9 external tools enabled", "M10 dangerously-skip-permissions allowed",
           "M11 old USD 30 API budget remains active", "M12 region guarantee invented", "M13 experiment executes during amendment", "M14 production bridge upgraded", "M15 P7 modified"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises((AssertionError, gv.GovernanceError)) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:80]
    CALLS["claude_code_inference_invocations"] = 0; ms.reset_counters()


def test_MUT_zz_all_fifteen_caught():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 15
    out = os.environ.get("AMD_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"mutants": CAUGHT, "calls": CALLS}, indent=1), encoding="utf-8")


# ==========================================================================
# Source classification completeness (every file this order touched since 60e3703 is classified; nothing PRODUCTION)
# ==========================================================================

def test_AMD_source_classification_complete():
    import subprocess
    cls = json.loads((ROOT / "docs/research/INFERENCE-GOVERNANCE-AMENDMENT-SOURCE-CLASSIFICATION.json").read_text(encoding="utf-8"))
    sites = cls["sites"]
    assert cls["base"] == "60e3703" and cls["unclassified"] == 0 and all(v["class"] in cls["vocabulary"] and v["class"] != "UNCLASSIFIED" for v in sites.values())
    assert not any(v["class"] == "PRODUCTION" for v in sites.values())
    assert sites["src/logos_research/measurement/claude_code.py"]["class"] == "POST_INFERENCE_SPEC"
    changed = subprocess.run(["git", "diff", "--name-only", "60e3703", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    files = {c for c in changed + untracked if "__pycache__" not in c and not c.endswith(".pyc")}
    assert files - set(sites) == set(), files - set(sites)
    pre = json.loads((ROOT / "docs/research/PRE-INFERENCE-SOURCE-CLASSIFICATION.json").read_text(encoding="utf-8"))["sites"]
    assert set(sites) <= set(pre)                                                # also registered in the living pre-inference classification
