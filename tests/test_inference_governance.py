"""INFERENCE-GOVERNANCE-LIFT-R1 — governance property tests GOV-P1..P15, 15 governance mutants, zero-inference proof.

No model call, no provider call, no experiment execution.

Amended by INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1 (2026-09-18): the founder superseded the OpenAI API boundary (G2/G4) with
Anthropic via the native Claude Code CLI under the Claude Max subscription. Historical values are asserted on
REG["superseded"] (preserved, not deleted) and the superseded API-budget code path is still exercised on a historical
record (`hist()`); the active record (`gov()`) is asserted on the amended values. No assertion was removed.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess

import _gamma_freeze
from dataclasses import replace
from pathlib import Path

import pytest

import logos_research.measurement as ms
from logos_research import governance as gv
from logos_research.measurement import construct as cs
from logos_research.measurement.gateway import CALLS, DryRunProvider, ForbiddenProvider
import logos_research.measurement.claude_code  # noqa: F401  amendment: registers CALLS["claude_code_inference_invocations"]

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REG = json.loads((ROOT / "docs/research/INFERENCE-GOVERNANCE.json").read_text(encoding="utf-8"))
ORDER = (ROOT / "05-WORK-ORDERS/COGNITIVE-PROVENANCE-ABLATION-R1.md").read_text(encoding="utf-8")
CAUGHT: dict[str, str] = {}
H = "a" * 64
SUP = REG["superseded"]                                   # amendment: superseded OpenAI G2/G4, preserved as governance history
PIN = "claude-pinned-by-founder"                          # explicit MODEL_PIN_GATE result used by the amended path in tests
CLEAN = gv.ContaminationReport((), "MAX_SUBSCRIPTION", True)


def gov():
    return gv.load_governance()


def hist():
    """The superseded API-budget record (OpenAI, USD 30) — exercises the retained API_BUDGET code path; never the active boundary."""
    return replace(gov(), provider="OpenAI", model_id="gpt-5.6-terra", region="Europe", billing_mode="API_BUDGET", max_total_spend=30.0, max_total_tokens=2000000, max_requests=400, max_per_run_spend=3.0)


def manifest_amended():
    return {**manifest_template(), "model_id": PIN, "model_version": "per-invocation", "provider": "Anthropic", "provider_region": "NOT_ASSUMED", "code_commit": "60e3703"}


def prereg_amended(**o):
    p = ms.stochastic_preregistration({"privacy_class": "SYNTHETIC"}, manifest_amended(), plan_dict(**{"cost_cap": 0.0, **o}), metric_ids=["M10", "M11"])
    p["stochastic"]["claude_max_limits"] = {"max_turns_per_invocation": 1, "max_output_size": 20000, "max_total_accepted_trajectories": 400}
    return p


def manifest_template():
    return dict(experiment_id="COGNITIVE-PROVENANCE-ABLATION-R1", model_id="gpt-5.6-terra", model_version="per-request", provider="OpenAI", provider_region="Europe", prompt_id="cpa-p1",
                prompt_version="v1", system_prompt_hash=H, tool_schema_hash=H, dataset_version="synthetic-v1", seed_if_supported=7, temperature=0.0, top_p=1.0, max_tokens=512, reasoning_effort_if_supported="low",
                environment_hash=H, code_commit="ea24e76", dependency_lock_hash=H)


def plan_dict(**o):
    d = dict(repeats=5, sample_size=40, resolution=0.01, dispersion=0.2, confidence_interval=0.95, effect_size=0.2, baseline="system-A", control="system-C",
             invalid_measurement_criteria=list(ms.INVALID_REASONS), early_stop_criteria="3 consecutive INVALID_MEASUREMENT", cost_cap=3.0, fallback="STOP_AND_REPORT")
    d.update(o); return d


@pytest.fixture(autouse=True)
def _zero():
    ms.reset_counters()
    yield
    assert CALLS["model_calls"] == 0 and CALLS["provider_calls"] == 0


# ==========================================================================
# GOV-P1..P15
# ==========================================================================

def test_GOV_P1_P15_no_inference_calls_and_counters_zero():
    g = gov()
    assert set(CALLS) >= {"model_calls", "provider_calls", "dry_run_calls"} and all(v == 0 for v in CALLS.values())      # amendment adds claude_code_inference_invocations
    with pytest.raises(ms.RealProviderForbidden):
        ForbiddenProvider().complete(ms.StochasticRunManifest.from_dict({**manifest_template(), "run_id": "r", "timestamp": "t", "hardware_runtime_metadata": {}}), {"q": 1})
    assert CALLS["model_calls"] == 0 and CALLS["provider_calls"] == 0


def test_GOV_record_is_the_founder_decision_verbatim():
    g = gov()
    assert g.lifted and g.inference_state == "LIFTED_WITH_CONDITIONS" and g.decision_owner == "founder" and g.decision_date == "2026-09-18"
    # historical (superseded, preserved verbatim)
    s2, s4 = SUP["G2_openai"], SUP["G4_openai_api_budget"]
    assert (s2["provider"], s2["model_id"], s2["region"], s2["fallback"]) == ("OpenAI", "gpt-5.6-terra", "Europe", "NONE") and g.allowed_data_classes == ("SYNTHETIC",)
    assert (s4["max_total_spend"], s4["max_total_tokens"], s4["max_requests"], s4["max_wall_clock_hours"], s4["max_repeats"], s4["max_per_run_spend"]) == (30.0, 2000000, 400, 3, 10, 3.0)
    assert s2["status"] == s4["status"] == "SUPERSEDED_BY_FOUNDER_AMENDMENT" and "INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1" in s2["superseded_by"]
    # active (amended)
    assert (g.provider, g.access_path, g.auth_mode, g.region, g.fallback, g.api_credit_fallback) == ("Anthropic", "Claude Code", "Claude Max subscription", "NOT_ASSUMED", "NONE", "FORBIDDEN")
    assert g.billing_mode == "CLAUDE_MAX_SUBSCRIPTION_ONLY" and (g.max_total_spend, g.max_per_run_spend, g.max_wall_clock_hours, g.max_repeats, g.max_claude_code_invocations, g.max_concurrent_sessions) == (0.0, 0.0, 3, 10, 200, 1)
    assert g.selected_experiment == "COGNITIVE-PROVENANCE-ABLATION-R1"
    for k in ("G1", "G2", "G3", "G4", "selected_experiment"):
        assert REG[k]["verbatim"].startswith(k.replace("selected_experiment", "Tier-A") + (" = " if k == "G2" else ":")) and REG[k]["owner"] == "founder"   # amended G2 verbatim reads "G2 = APPROVED"
    assert "LIFTED_WITH_CONDITIONS" in REG["G1"]["verbatim"] and "Fallback: NONE" in SUP["G2_openai"]["verbatim"] and "- SYNTHETIC" in REG["G3"]["verbatim"] and "$30" in SUP["G4_openai_api_budget"]["verbatim"]
    assert "Fallback provider: NONE" in REG["G2"]["verbatim"] and "API key: NONE" in REG["G2"]["verbatim"]
    assert REG["status"].startswith("INFERENCE_GOVERNANCE_LIFT_APPROVED_R1") and "INFERENCE_GOVERNANCE_PROVIDER_AMENDED_R1" in REG["status"]


def test_GOV_P2_provider_cannot_activate_without_approval_or_dry_run():
    a = gov()                                                                                             # amended: also needs clean report + preflight + explicit pin
    assert isinstance(gv.resolve_provider(a, dry_run_passed=False, run_dataset_class="SYNTHETIC", run_cost_cap=0, report=CLEAN, preflight_passed=True, model_pin=PIN), ForbiddenProvider)
    assert isinstance(gv.resolve_provider(replace(a, g2="DEFERRED"), dry_run_passed=True, run_dataset_class="SYNTHETIC", run_cost_cap=0, report=CLEAN, preflight_passed=True, model_pin=PIN), ForbiddenProvider)
    assert isinstance(gv.resolve_provider(a, dry_run_passed=True, run_dataset_class="SYNTHETIC", run_cost_cap=0), ForbiddenProvider)
    spec = gv.resolve_provider(a, dry_run_passed=True, run_dataset_class="SYNTHETIC", run_cost_cap=0, report=CLEAN, preflight_passed=True, model_pin=PIN)
    assert isinstance(spec, gv.ProviderSpec) and (spec.provider, spec.model_id, spec.region) == ("Anthropic", PIN, "NOT_ASSUMED") and not hasattr(spec, "complete")
    g = hist()                                                                                            # superseded API-budget path (retained code path)
    assert not gv.provider_activation(g, dry_run_passed=False)
    assert isinstance(gv.resolve_provider(g, dry_run_passed=False, run_dataset_class="SYNTHETIC", run_cost_cap=3.0), ForbiddenProvider)
    unapproved = replace(g, g2="DEFERRED")
    assert not gv.provider_activation(unapproved, dry_run_passed=True) and isinstance(gv.resolve_provider(unapproved, dry_run_passed=True, run_dataset_class="SYNTHETIC", run_cost_cap=3.0), ForbiddenProvider)
    retained = replace(g, g1="RETAIN", inference_state="ACTIVE")
    assert isinstance(gv.resolve_provider(retained, dry_run_passed=True, run_dataset_class="SYNTHETIC", run_cost_cap=3.0), ForbiddenProvider)
    spec = gv.resolve_provider(g, dry_run_passed=True, run_dataset_class="SYNTHETIC", run_cost_cap=3.0)
    assert isinstance(spec, gv.ProviderSpec) and spec.model_id == "gpt-5.6-terra" and not hasattr(spec, "complete")     # a spec, never a client


def test_GOV_P3_unapproved_data_class_cannot_reach_provider():
    g = gov()
    for cls in gv.DATA_CLASSES:
        ok = gv.privacy_activation(g, run_dataset_class=cls)
        assert ok == (cls == "SYNTHETIC")
        if not ok:
            assert isinstance(gv.resolve_provider(g, dry_run_passed=True, run_dataset_class=cls, run_cost_cap=3.0), ForbiddenProvider)
    with pytest.raises(gv.GovernanceError):
        gv.privacy_activation(g, run_dataset_class="REAL_CUSTOMER")


def test_GOV_P4_cost_cap_mandatory_and_bounded():
    a = gov()                                                                                             # amended: incremental API spend must be exactly 0
    assert not gv.cost_activation(a, run_cost_cap=None) and not gv.cost_activation(a, run_cost_cap=3.0) and not gv.cost_activation(a, run_cost_cap=0.01) and gv.cost_activation(a, run_cost_cap=0)
    assert gv.validate_run_preregistration(prereg_amended(), a) == []
    assert any("cost cap must be 0" in x for x in gv.validate_run_preregistration(prereg_amended(cost_cap=3.0), a))
    g = hist()                                                                                            # superseded API-budget path (retained code path)
    assert not gv.cost_activation(g, run_cost_cap=None) and not gv.cost_activation(g, run_cost_cap=0) and not gv.cost_activation(g, run_cost_cap=3.01) and gv.cost_activation(g, run_cost_cap=3.0)
    assert isinstance(gv.resolve_provider(g, dry_run_passed=True, run_dataset_class="SYNTHETIC", run_cost_cap=None), ForbiddenProvider)
    p = gv.validate_run_preregistration(ms.stochastic_preregistration({"privacy_class": "SYNTHETIC"}, manifest_template(), plan_dict(cost_cap=5.0), metric_ids=["M10"]), g)
    assert "run cost cap missing or above the per-run ceiling" in p


def test_GOV_P5_selected_experiment_tier_a_or_none():
    g = gov(); assert g.selected_experiment in gv.TIER_A
    bad = copy.deepcopy(REG); bad["selected_experiment"]["id"] = "BDH_LONG_HORIZON_DECOMPOSITION"
    with pytest.raises(gv.GovernanceError):
        gv.load_governance(_tmp(bad))
    none = copy.deepcopy(REG); none["selected_experiment"] = {"decision": "NONE"}
    assert gv.load_governance(_tmp(none)).selected_experiment is None


def _tmp(d):
    import tempfile
    p = Path(tempfile.mkdtemp()) / "gov-test.json"; p.write_text(json.dumps(d), encoding="utf-8"); return p


def test_GOV_P6_P7_P8_next_order_binds_prereg_metrics_and_drift():
    g = gov()
    assert gv.validate_experiment_order(ORDER, g) == []
    h = gv.parse_order_header(ORDER)
    assert h["PREREG_SCHEMA"] == "logos.stochastic-prereg/1" and h["DRY_RUN_REQUIRED"] == "true" and h["PRODUCTION_ACTIONS"] == "forbidden"
    assert gv.validate_experiment_order(ORDER.replace("PREREG_SCHEMA = logos.stochastic-prereg/1", "PREREG_SCHEMA = none"), g)
    assert any("MODEL_VERSION_DRIFT" in x for x in gv.validate_experiment_order(ORDER.replace("MODEL_VERSION_DRIFT", "MVD"), g))
    reg = ms.load_registry()
    assert gv.metric_activation("M10", ground_truth_mapping="synthetic source labels (exact)", registry=reg)
    assert not gv.metric_activation("M04", ground_truth_mapping="synthetic source labels", registry=reg)                # UNVALIDATED never primary
    assert not gv.metric_activation("M10", ground_truth_mapping=None, registry=reg) and not gv.metric_activation("M10", ground_truth_mapping="LLM judge", registry=reg)
    payload = ms.stochastic_preregistration({"privacy_class": "SYNTHETIC"}, manifest_template(), plan_dict(), metric_ids=["M10", "M11"])
    assert gv.validate_run_preregistration(payload, g), "a superseded OpenAI manifest must not validate against the amended record"
    assert gv.validate_run_preregistration(prereg_amended(), g) == []
    g = hist()
    assert gv.validate_run_preregistration(payload, g) == []
    assert gv.validate_run_preregistration({**payload, "privacy_class": "PUBLIC"}, g) and gv.validate_run_preregistration(ms.stochastic_preregistration({"privacy_class": "SYNTHETIC"}, {**manifest_template(), "provider_region": "US"}, plan_dict(), metric_ids=["M10"]), g)


def test_GOV_P9_provenance_and_trajectory_capture_required():
    assert "provenance" in ORDER and "TransformationOfInformation must not erase EpistemicAncestry" in ORDER and "trajectory" in ORDER
    assert any("provenance" in x for x in gv.validate_experiment_order(ORDER.replace("provenance", "prov."), gov()))


def test_GOV_P10_P11_bridge_not_upgraded_R1_R3_open():
    adr = (ROOT / "docs/adr/ADR-CANONICAL-AUTHORITY-PRODUCTION-BRIDGE.md").read_text(encoding="utf-8")
    assert "`PRODUCTION_BRIDGE_READY_WITH_CONDITIONS` · **State:** `APPROVED`" in adr and "R1–R3 are therefore **mandatory**" in adr
    ceo = json.loads((ROOT / "docs/research/CANONICAL-EFFECT-OWNER.json").read_text(encoding="utf-8"))
    assert all(d["value"] != "PRODUCTION_BRIDGE_READY" for d in ceo["governance_decisions"] if d["id"].startswith("PRODUCTION-BRIDGE-READINESS"))
    assert "R1-R3 remain OPEN" in " ".join(REG["conditions"]) and "PRODUCTION_BRIDGE_READY_WITH_CONDITIONS unchanged" in " ".join(REG["conditions"])
    chk = (ROOT / "docs/research/REAL-MODEL-READINESS-CHECKLIST.md").read_text(encoding="utf-8")
    assert "R1" in chk and "R2" in chk and "R3" in chk and "PRODUCTION-BRIDGE-OPERATIONS-R1" in chk


def test_GOV_P12_P13_P14_gamma_p7_predecessors_unchanged():
    diff = subprocess.run(["git", "diff", "--stat", "ea24e76", "HEAD", "--", 
                           # Γ and GAMMA.md are pinned by _gamma_freeze.assert_gamma_pinned() below, not by this diff:
                           # one recorded hash with an auditable supersede chain, checked on disk rather than between commits
                           ":(exclude)GAMMA.md", ":(exclude)src/logos_gamma",
                           "src/logos_authority", "src/logos_runtime", "src/logos_audit", "src/logos_effects", "src/logos_memory",
                           "src/logos_research/experiments", "src/logos_research/measurement", "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md", "05-WORK-ORDERS/NEXT-SESSION-*", ":(exclude)05-WORK-ORDERS/NEXT-SESSION-INFERENCE-GOVERNANCE-LIFT-R1.md",
                           "09-SESSIONS", ":(exclude)09-SESSIONS/2026-09-18-INFERENCE-GOVERNANCE-LIFT-R1",
                           # INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1: its own records and the adapter contract (frozen-hash checked by its own suite)
                           ":(exclude)05-WORK-ORDERS/NEXT-SESSION-INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1.md", ":(exclude)09-SESSIONS/2026-09-18-INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1",
                           ":(exclude)05-WORK-ORDERS/NEXT-SESSION-COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1.md", ":(exclude)09-SESSIONS/2026-09-18-COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1",
                           ":(exclude)05-WORK-ORDERS/NEXT-SESSION-LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1.md", ":(exclude)09-SESSIONS/2026-09-19-LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1",
                           # LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1 / -AUTOPILOT-R2: their own closure + session records (tooling orders; no Γ/P7/experiment/measurement file touched)
                           ":(exclude)05-WORK-ORDERS/NEXT-SESSION-LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1.md", ":(exclude)09-SESSIONS/2026-09-19-LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1",
                           ":(exclude)05-WORK-ORDERS/NEXT-SESSION-LOGOS1-RESEARCH-OS-AUTOPILOT-R2.md", ":(exclude)09-SESSIONS/2026-09-19-LOGOS1-RESEARCH-OS-AUTOPILOT-R2",
                           ":(exclude)05-WORK-ORDERS/NEXT-SESSION-LOGOS1-RESEARCH-OS-MEASUREMENT-R3.md", ":(exclude)09-SESSIONS/2026-09-19-LOGOS1-RESEARCH-OS-MEASUREMENT-R3",
                           ":(exclude)05-WORK-ORDERS/NEXT-SESSION-LOGOS1-RESEARCH-OS-OBSERVE-INSIGHTS-REGISTRY-R4.md", ":(exclude)09-SESSIONS/2026-09-19-LOGOS1-RESEARCH-OS-OBSERVE-INSIGHTS-REGISTRY-R4",
                               # -PRIORART-EVALS-PAPER-R5 / -EXECUTABLE-BOUNDARY-DEMO-R1: their own closure + session records
                               # (tooling orders; no Γ / P7 / experiment / measurement file touched)
                               ":(exclude)05-WORK-ORDERS/NEXT-SESSION-LOGOS1-RESEARCH-OS-PRIORART-EVALS-PAPER-R5.md", ":(exclude)09-SESSIONS/2026-09-19-LOGOS1-RESEARCH-OS-PRIORART-EVALS-PAPER-R5",
                               ":(exclude)05-WORK-ORDERS/NEXT-SESSION-LOGOS1-EXECUTABLE-BOUNDARY-DEMO-R1.md", ":(exclude)09-SESSIONS/2026-09-22-LOGOS1-EXECUTABLE-BOUNDARY-DEMO-R1",
                               ":(exclude)05-WORK-ORDERS/NEXT-SESSION-LOGOS1-GAMMA-EXTENSION-R1.md", ":(exclude)09-SESSIONS/2026-09-22-LOGOS1-GAMMA-EXTENSION-R1",
                           ":(exclude)src/logos_research/measurement/result_model.py", ":(exclude)src/logos_research/measurement/claude_code.py",   # COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1: resolver + repaired adapter (hash-recorded in the repair prereg/artifact)
                           ":(exclude)src/logos_research/experiments/cognitive_provenance_r1", ":(exclude)09-SESSIONS/2026-09-18-COGNITIVE-PROVENANCE-ABLATION-R1", ":(exclude)05-WORK-ORDERS/NEXT-SESSION-COGNITIVE-PROVENANCE-ABLATION-R1.md"],   # COGNITIVE-PROVENANCE-ABLATION-R1: its own EXPERIMENTAL_INFERENCE package and records

                          capture_output=True, text=True, cwd=ROOT).stdout.strip()
    _gamma_freeze.assert_gamma_pinned()
    assert diff == "", diff
    p7 = (ROOT / "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md").read_bytes()
    assert b"## Consciousness / P7 boundary" in p7
    from logos_research import experiments
    assert experiments.B1_STATUS == "NON_PRODUCTION_FROZEN_RISK_GUARDED"


def test_GOV_dry_run_contract_and_forbidden_guard():
    ok = {c: True for c in gv.DRY_RUN_CHECKS}
    assert gv.dry_run_contract(ok) == []
    assert gv.dry_run_contract({**ok, "forbidden_provider_guard_active": False}) == ["forbidden_provider_guard_active"]
    assert set(gv.DRY_RUN_CHECKS) == {"metadata_complete", "pins_resolve", "privacy_checks_pass", "cost_accounting_initialized", "construct_metrics_resolve", "artifact_paths_exist",
                                      "provenance_graph_initializes", "trajectory_capture_initializes", "invalid_measurement_rules_load", "forbidden_provider_guard_active"}


# ==========================================================================
# Zero-inference proof (Section 52): counters + spies + source audit + adapter inventory
# ==========================================================================

def test_ZERO_inference_proof():
    assert CALLS["model_calls"] == 0 and CALLS["provider_calls"] == 0
    adapters = set()
    for py in SRC.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        txt = py.read_text(encoding="utf-8")
        for tok in ("import openai", "from openai", "import anthropic", "from anthropic", "api.openai.com", "api.anthropic.com"):
            assert tok not in txt, (py, tok)                                                     # no model-provider client anywhere in src
        rel_py = str(py).replace("\\", "/")
        # lab infra (Postgres/MinIO/OTel health) and the dashboard's observability reader are the only network users; both talk to loopback telemetry only,
        # and the model-provider checks above (openai/anthropic clients, api.* hosts) still apply to them.
        if "logos_research/infra" not in rel_py and "logos_dashboard/control/observe.py" not in rel_py:
            for tok in ("import requests", "import httpx", "import urllib.request", "import socket"):
                assert tok not in txt, (py, tok)
        tree = ast.parse(txt)
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef) and any(isinstance(b, ast.FunctionDef) and b.name in ("complete", "invoke") for b in n.body):
                adapters.add(f"{str(py.relative_to(SRC)).replace(chr(92), '/')}::{n.name}")
    # adapter inventory: the protocol, the forbidden guard and the synthetic dry-run provider — nothing that can reach a model
    expected_adapters = {"logos_research/measurement/gateway.py::ProviderGateway", "logos_research/measurement/gateway.py::ForbiddenProvider", "logos_research/measurement/gateway.py::DryRunProvider",
                         "logos_research/measurement/claude_code.py::ClaudeCodeMaxProvider"}                   # amendment: contract only; invoke() needs an ActivationToken + injected runner
    # The dashboard is a separate deliverable and is not part of every checkout (founder decision,
    # 2026-09-22: the control plane stays out of the public default branch). The inventory stays EXACT
    # in both trees rather than becoming a subset check: any adapter this list does not name still fails.
    if (SRC / "logos_dashboard/control/agent_provider.py").exists():        # the file, not the directory: stale __pycache__ leaves empty dirs behind
        expected_adapters |= {"logos_dashboard/control/agent_provider.py::AgentProvider"}                      # LOGOS1-RESEARCH-OS-AUTOPILOT-R2: agent-job adapter (stream-json + --verbose per founder amendment); same token + injected-runner gate, own flag allowlist
    assert adapters == expected_adapters
    assert CALLS["claude_code_inference_invocations"] == 0
    gtxt = (SRC / "logos_research/governance.py").read_text(encoding="utf-8")
    assert "def complete" not in gtxt and "ProviderSpec" in gtxt


# ==========================================================================
# Mutation suite M1..M15
# ==========================================================================

def _battery():
    a = gov(); g = hist()
    assert a.lifted and a.g1 == "LIFT" and REG["G1"]["owner"] == "founder", "M1"
    assert isinstance(gv.resolve_provider(g, dry_run_passed=False, run_dataset_class="SYNTHETIC", run_cost_cap=3.0), ForbiddenProvider), "M2"
    assert isinstance(gv.resolve_provider(a, dry_run_passed=False, run_dataset_class="SYNTHETIC", run_cost_cap=0, report=CLEAN, preflight_passed=True, model_pin=PIN), ForbiddenProvider), "M2"
    assert SUP["G2_openai"]["model_id"] == "gpt-5.6-terra" and a.model_id == gv.MODEL_PIN_PLACEHOLDER, "M3"
    assert gv.validate_experiment_order(ORDER.replace("APPROVED_MODEL = TO_BE_PINNED_FROM_MAX_ACCOUNT_BEFORE_RUN", "APPROVED_MODEL = gpt-other"), a), "M3"
    assert gv.validate_experiment_order(ORDER.replace("APPROVED_PROVIDER = Anthropic", "APPROVED_PROVIDER = OpenAI"), a), "M3"
    assert g.fallback == "NONE" and a.fallback == "NONE" and a.api_credit_fallback == "FORBIDDEN", "M4"
    assert not gv.privacy_activation(g, run_dataset_class="PRODUCTION_CUSTOMER_DATA") and not gv.privacy_activation(g, run_dataset_class="SENSITIVE_PERSONAL_DATA"), "M5"
    assert not gv.cost_activation(g, run_cost_cap=None) and not gv.cost_activation(a, run_cost_cap=None), "M6"
    assert not gv.cost_activation(g, run_cost_cap=31.0) and g.max_total_spend == 30.0 and SUP["G4_openai_api_budget"]["max_total_spend"] == 30.0, "M7"
    assert not gv.cost_activation(a, run_cost_cap=1.0) and a.max_total_spend == 0.0, "M7"
    assert not gv.metric_activation("M04", ground_truth_mapping="exact"), "M8"
    assert gv.validate_run_preregistration({"privacy_class": "SYNTHETIC"}, g), "M9"
    p = ms.stochastic_preregistration({"privacy_class": "SYNTHETIC"}, manifest_template(), plan_dict(invalid_measurement_criteria=[r for r in ms.INVALID_REASONS if r != "MODEL_VERSION_DRIFT"]), metric_ids=["M10"])
    assert any("MODEL_VERSION_DRIFT" in x for x in gv.validate_run_preregistration(p, g)), "M10"
    p = ms.stochastic_preregistration({"privacy_class": "SYNTHETIC"}, manifest_template(), plan_dict(invalid_measurement_criteria=[r for r in ms.INVALID_REASONS if r != "PROMPT_DRIFT"]), metric_ids=["M10"])
    assert any("PROMPT_DRIFT" in x for x in gv.validate_run_preregistration(p, g)), "M11"
    assert CALLS["provider_calls"] == 0 and CALLS["model_calls"] == 0, "M12"
    assert all(d["value"] != "PRODUCTION_BRIDGE_READY" for d in json.loads((ROOT / "docs/research/CANONICAL-EFFECT-OWNER.json").read_text(encoding="utf-8"))["governance_decisions"]), "M13"
    assert "R1-R3 remain OPEN" in " ".join(a.raw["conditions"]), "M14"
    assert _gamma_freeze.p7_boundary_hash() == P7_HASH, "M15"   # one implementation, line-ending normalized


P7_HASH = json.loads((ROOT / "docs/research/DETERMINISTIC-CHAIN-FROZEN-HASHES.json").read_text(encoding="utf-8"))["p7_boundary_sha256"]


def _m(name):
    real_load = gv.load_governance
    def m1(mp):
        mp.setattr(gv, "load_governance", lambda path=None: replace(real_load(path), g1="DEFER"))
    def m2(mp):
        mp.setattr(gv, "provider_activation", lambda g, *, dry_run_passed: g.g2 == "APPROVED")
        real = gv.resolve_provider
        mp.setattr(gv, "resolve_provider", lambda g, **k: gv.ProviderSpec(g.provider, k.get("model_pin") or g.model_id, g.region, g.fallback) if g.g2 == "APPROVED" else real(g, **k))
    def m3(mp):
        real = gv.validate_experiment_order
        mp.setattr(gv, "validate_experiment_order", lambda text, g: [x for x in real(text, g) if "provider/model" not in x and "access path" not in x and "MODEL_PIN_GATE placeholder" not in x])
    def m4(mp):
        mp.setattr(gv, "load_governance", lambda path=None: replace(real_load(path), fallback="gpt-5.5"))
    def m5(mp):
        mp.setattr(gv, "privacy_activation", lambda g, *, run_dataset_class: g.lifted)
    def m6(mp):
        real = gv.cost_activation
        mp.setattr(gv, "cost_activation", lambda g, *, run_cost_cap: True if run_cost_cap is None else real(g, run_cost_cap=run_cost_cap))
    def m7(mp):
        mp.setattr(gv, "cost_activation", lambda g, *, run_cost_cap: bool(run_cost_cap))
        mp.setattr(gv, "load_governance", lambda path=None: replace(real_load(path), max_total_spend=1e9))
    def m8(mp):
        mp.setattr(gv, "metric_activation", lambda mid, *, ground_truth_mapping, registry=None: bool(ground_truth_mapping))
    def m9(mp):
        real = gv.validate_run_preregistration
        mp.setattr(gv, "validate_run_preregistration", lambda payload, g: [] if "stochastic" not in payload else real(payload, g))
    def m10(mp):
        real = gv.validate_run_preregistration
        mp.setattr(gv, "validate_run_preregistration", lambda payload, g: [x for x in real(payload, g) if "MODEL_VERSION_DRIFT" not in x])
    def m11(mp):
        real = gv.validate_run_preregistration
        mp.setattr(gv, "validate_run_preregistration", lambda payload, g: [x for x in real(payload, g) if "PROMPT_DRIFT" not in x])
    def m12(mp):
        CALLS["provider_calls"] += 1
    def m13(mp):
        real = json.loads
        mp.setattr(json, "loads", lambda s, *a, **k: (lambda d: (d.__setitem__("governance_decisions", [{**x, "value": "PRODUCTION_BRIDGE_READY"} if x["id"].startswith("PRODUCTION-BRIDGE-READINESS") else x for x in d["governance_decisions"]]) or d) if isinstance(d, dict) and "governance_decisions" in d else d)(real(s, *a, **k)))
    def m14(mp):
        mp.setattr(gv, "load_governance", lambda path=None: (lambda g: replace(g, raw={**g.raw, "conditions": [c for c in g.raw["conditions"] if "R1-R3" not in c] + ["R1-R3 closed"]}))(real_load(path)))
    def m15(mp):
        real = Path.read_bytes
        mp.setattr(Path, "read_bytes", lambda self: real(self).replace(b"## Consciousness / P7 boundary", b"## Consciousness / P7 boundary\n\nP7 amended: functional organization suffices.") if self.name.endswith("PRIOR-ART-DELTA.md") else real(self))
    return {"M1 inference lifted without founder decision": m1, "M2 provider activated without approval/dry run": m2, "M3 unapproved model used": m3, "M4 fallback silently enabled": m4,
            "M5 unapproved sensitive data allowed": m5, "M6 no cost cap": m6, "M7 budget auto-expands": m7, "M8 UNVALIDATED metric supports primary claim": m8,
            "M9 stochastic run accepted without prereg": m9, "M10 model drift pooled silently": m10, "M11 prompt drift pooled silently": m11, "M12 provider call during governance order": m12,
            "M13 production bridge upgraded to READY": m13, "M14 R1-R3 silently closed": m14, "M15 P7 changed": m15}[name]


MUTANTS = ["M1 inference lifted without founder decision", "M2 provider activated without approval/dry run", "M3 unapproved model used", "M4 fallback silently enabled",
           "M5 unapproved sensitive data allowed", "M6 no cost cap", "M7 budget auto-expands", "M8 UNVALIDATED metric supports primary claim", "M9 stochastic run accepted without prereg",
           "M10 model drift pooled silently", "M11 prompt drift pooled silently", "M12 provider call during governance order", "M13 production bridge upgraded to READY",
           "M14 R1-R3 silently closed", "M15 P7 changed"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:80]
    if name.startswith("M12"):
        ms.reset_counters()


def test_MUT_zz_all_fifteen_caught():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 15
    out = os.environ.get("GOV_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"mutants": CAUGHT, "calls": CALLS}, indent=1), encoding="utf-8")
