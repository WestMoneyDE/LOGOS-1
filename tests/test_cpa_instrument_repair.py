"""COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1 — resolver contract, captured fixture, F1..F12, IR-P1..P10, R-M1..R-M15, independent validation.

Deterministic. No `claude` process is started. Counters read 0 at the end.
"""
from __future__ import annotations

import copy
import itertools
import json
import os
import re
import subprocess

import _gamma_freeze
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

import logos_research.measurement as ms
from logos_research.measurement import claude_code as cc
from logos_research.measurement import result_model as rm

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests/fixtures/claude_code"
RAW = (FIX / "cpa_r1_first_invocation_raw.json").read_text(encoding="utf-8")
RAW_SHA = "d8898c970784dc5c0441171a5cde7745bb2ce133045d418a45a6a382aee51b2b"          # byte-for-byte stdout of the invalid run's invocation 1 (raw log artifact 5f887962…)
ORACLE = json.loads((FIX / "resolver_fixtures.json").read_text(encoding="utf-8"))
PIN = ORACLE["requested_model"]
CLEAN_ENV = {"PATH": "x"}
CAUGHT: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _zero():
    ms.reset_counters()
    yield
    ms.reset_counters()


# ==========================================================================
# independent reference oracle (Section 32): a second, minimal parser that never imports the resolver's logic
# ==========================================================================

def reference_classification(requested: str, output, fmt: str) -> dict:
    """Hard-coded reading of the documented contract; deliberately naive and separate from `result_model`."""
    def pin_like(k):
        return k == requested or bool(re.fullmatch(re.escape(requested) + r"-\d{8}", k))
    if fmt == "stream-json":
        assistants = [e["message"]["model"] for e in output if e.get("type") == "assistant" and e.get("parent_tool_use_id") is None and isinstance(e.get("message"), dict) and e["message"].get("model")]
        res = [e for e in output if e.get("type") == "result"][-1]
    else:
        assistants, res = [], output
    mu = res.get("modelUsage")
    if mu is not None and (not isinstance(mu, dict) or any(not isinstance(v, dict) for v in mu.values())):
        return {"status": "OUTPUT_INVALID"}
    if assistants:
        return {"status": "RESOLVED", "resolved": assistants[-1], "drift": not pin_like(assistants[-1])}
    if mu is None or not mu:
        return {"status": "AMBIGUOUS"}
    hits = [k for k, v in mu.items() if pin_like(k) or pin_like(str(v.get("canonicalModel") or ""))]
    if not hits:
        return {"status": "PIN_MISSING", "drift": True}
    return {"status": "RESOLVED", "resolved": requested, "drift": False}


def fixtures():
    return [(k, v) for k, v in ORACLE["fixtures"].items()]


# ==========================================================================
# captured fixture (Sections 11-12, 31)
# ==========================================================================

def test_captured_fixture_preserved_byte_for_byte():
    assert sha256(RAW.encode("utf-8")).hexdigest() == RAW_SHA
    doc = json.loads(RAW)
    assert doc["type"] == "result" and doc["subtype"] == "success" and doc["is_error"] is False and doc["num_turns"] == 1
    assert list(doc["modelUsage"]) == ["claude-haiku-4-5-20251001", "claude-opus-5"]          # auxiliary entry first — the exact trigger of CPA-F5
    assert "model" not in doc                                                                    # no documented top-level producer field in 2.1.275


def test_root_defect_reproduced_and_repaired_on_captured_fixture():
    doc = json.loads(RAW)
    old_reported = doc.get("model") or next(iter(doc["modelUsage"]))                              # the removed heuristic
    assert old_reported == "claude-haiku-4-5-20251001" and PIN not in old_reported                # old detector: false-positive drift
    r = rm.resolve_result_model(PIN, doc, "json")
    assert r.status == "RESOLVED" and r.resolved_model == PIN and r.evidence_class == "REQUEST_PIN_PLUS_USAGE_CONTAINMENT" and not r.drift
    assert r.auxiliary_models == ("claude-haiku-4-5-20251001",) and r.auxiliary_usage["claude-haiku-4-5-20251001"]["outputTokens"] == 12
    assert r.evidence_fields == ("requested_model", "modelUsage[claude-opus-5]") and "weaker" in r.reason_code
    src = (ROOT / "src/logos_research/measurement/claude_code.py").read_text(encoding="utf-8")
    assert "next(iter(doc[\"modelUsage\"]" not in src and "resolve_result_model(" in src           # first-key heuristic removed from the adapter


def test_adapter_on_captured_fixture_is_not_drift():
    p = cc.ClaudeCodeMaxProvider(runner=lambda argv, t, env: (0, RAW, ""), expected_cli_version="2.1.275 (Claude Code)")
    tok = cc.ActivationToken("r", PIN, 2, 1)
    r = p.invoke("q", PIN, {"run_id": "r"}, cc.Limits(1, 20000, 5.0), token=tok, env=CLEAN_ENV)
    assert r.status == "OK" and r.reported_model == PIN and r.resolution.status == "RESOLVED" and r.model_usage_raw is not None
    assert r.scaffolding == {"input_tokens": 2, "cache_creation_input_tokens": 23815, "cache_read_input_tokens": 0, "output_tokens": 156}
    assert json.loads(r.content)["final_choice"] == "OPT-1"


# ==========================================================================
# F1..F12 against the declarative oracle + the independent reference parser (Sections 13, 32)
# ==========================================================================

@pytest.mark.parametrize("name,f", fixtures())
def test_fixture_oracle(name, f):
    r = rm.resolve_result_model(PIN, f["output"], f["format"])
    e = f["expect"]
    assert (r.status, r.resolved_model, r.evidence_class, r.drift, sorted(r.auxiliary_models)) == (e["status"], e["resolved"], e["evidence"], e["drift"], sorted(e["aux"])), name
    ref = reference_classification(PIN, f["output"], f["format"])
    assert ref["status"] == r.status and ref.get("resolved", r.resolved_model) == r.resolved_model and ref.get("drift", r.drift) == r.drift, (name, ref)


def test_adapter_statuses_follow_resolution():
    tok = cc.ActivationToken("r", PIN, 50, 1)
    for name, f in fixtures():
        out = json.dumps(f["output"]) if f["format"] == "json" else "\n".join(json.dumps(e) for e in f["output"])
        p = cc.ClaudeCodeMaxProvider(runner=lambda argv, t, env, out=out: (0, out, ""))
        r = p.invoke("q", PIN, {"run_id": "r"}, cc.Limits(1, 20000, 5.0), token=tok, env=CLEAN_ENV, output_format=f["format"])
        e = f["expect"]
        expected = "MODEL_DRIFT" if e["drift"] else ("OK" if e["status"] == "RESOLVED" else ("INVALID_OUTPUT" if e["status"] == "OUTPUT_INVALID" else "RESULT_MODEL_AMBIGUOUS"))
        assert r.status == expected, (name, r.status)
        assert (r.content is not None) == (expected == "OK")


# ==========================================================================
# IR-P1..IR-P10
# ==========================================================================

def _perms(mu: dict):
    for order in itertools.permutations(mu):
        yield {k: mu[k] for k in order}


def test_IR_P1_ordering_invariant():
    base = ORACLE["fixtures"]["F3"]["output"]
    outs = set()
    for mu in _perms(base["modelUsage"]):
        r = rm.resolve_result_model(PIN, {**base, "modelUsage": mu}, "json")
        outs.add((r.status, r.resolved_model, r.evidence_class, r.drift, r.auxiliary_models))
    assert len(outs) == 1
    mu3 = {**base["modelUsage"], "claude-sonnet-5": {"inputTokens": 1, "outputTokens": 999, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}}   # a heavier foreign entry, any position
    outs = {(rm.resolve_result_model(PIN, {**base, "modelUsage": mu}, "json").status, rm.resolve_result_model(PIN, {**base, "modelUsage": mu}, "json").resolved_model) for mu in _perms(mu3)}
    assert outs == {("RESOLVED", PIN)}


def test_IR_P2_auxiliary_invariance():
    f1 = ORACLE["fixtures"]["F1"]["output"]; f2 = ORACLE["fixtures"]["F2"]["output"]
    a, b = rm.resolve_result_model(PIN, f1, "json"), rm.resolve_result_model(PIN, f2, "json")
    assert (a.status, a.resolved_model, a.evidence_class, a.drift) == (b.status, b.resolved_model, b.evidence_class, b.drift)
    assert a.auxiliary_models == () and b.auxiliary_models == ("claude-haiku-4-5-20251001",)


def test_IR_P3_pin_absence_not_resolved():
    for name in ("F4", "F5"):
        r = rm.resolve_result_model(PIN, ORACLE["fixtures"][name]["output"], "json")
        assert r.status == "PIN_MISSING" and r.drift and r.resolved_model is None


def test_IR_P4_P5_explicit_producer_dominates_and_mismatch_is_drift():
    f7 = ORACLE["fixtures"]["F7"]["output"]
    r = rm.resolve_result_model(PIN, f7, "stream-json")
    assert r.evidence_class == "EXPLICIT_ASSISTANT_MODEL" and r.resolved_model == "claude-sonnet-5" and r.drift          # pin present in usage does not rescue it
    f6 = ORACLE["fixtures"]["F6"]["output"]
    assert rm.resolve_result_model(PIN, f6, "stream-json").evidence_class == "EXPLICIT_ASSISTANT_MODEL"
    two = copy.deepcopy(f6); two.insert(2, {**two[1], "message": {**two[1]["message"], "model": "claude-sonnet-5"}})
    assert rm.resolve_result_model(PIN, two, "stream-json").status == "AMBIGUOUS"                                       # conflicting explicit producers -> fail closed


def test_IR_P6_ambiguity_fails_closed():
    for name in ("F9", "F11"):
        r = rm.resolve_result_model(PIN, ORACLE["fixtures"][name]["output"], "json")
        assert r.status == "AMBIGUOUS" and not r.drift and r.resolved_model is None
    assert rm.resolve_result_model(PIN, ORACLE["fixtures"]["F1"]["output"], "json", contract_version="cc-result-model/0").status == "CONTRACT_UNSUPPORTED"
    assert rm.resolve_result_model(PIN, ORACLE["fixtures"]["F1"]["output"], "text").status == "CONTRACT_UNSUPPORTED"
    assert rm.resolve_result_model(PIN, [], "stream-json").status == "OUTPUT_INVALID"
    with pytest.raises(ValueError):
        rm.ResultModelResolution("MAYBE", PIN, None, "PIN_ABSENT", (), (), "x")


def test_IR_P7_founder_pin_immutable():
    gate = (ROOT / "09-SESSIONS/2026-09-18-COGNITIVE-PROVENANCE-ABLATION-R1/MODEL-PIN-GATE.md").read_text(encoding="utf-8")
    assert "MODEL_PIN = claude-opus-5" in gate and "selection_owner = founder" in gate
    assert rm.is_pin("claude-opus-5") and not rm.is_pin("opus") and not rm.is_pin("")
    assert rm.resolve_result_model("opus", ORACLE["fixtures"]["F1"]["output"], "json").status == "PIN_MISSING"           # an alias is never a pin
    assert rm.same_model("claude-opus-5-20260301", PIN) and not rm.same_model("claude-opus-5-1", PIN) and not rm.same_model("claude-opus-50", PIN)


def test_IR_P8_P9_no_payg_or_provider_fallback():
    from logos_research import governance as gv
    g = gv.load_governance(); assert g.subscription_only and g.fallback == "NONE" and g.api_credit_fallback == "FORBIDDEN"
    argv = cc.build_argv("q", PIN, cc.Limits(1, 20000, 5.0))
    for flag in ("--fallback-model", "--dangerously-skip-permissions", "--allow-dangerously-skip-permissions", "--bare"):
        with pytest.raises(cc.ProviderPolicyError):
            cc.check_argv(argv + [flag, "x"])
    assert cc.classify_result({"is_error": True, "subtype": "success", "api_error_status": 429, "result": "limit"}, None) == "USAGE_LIMIT_REACHED"
    assert cc.classify_result({"is_error": False, "subtype": "success"}, [{"type": "assistant", "error": "rate_limit"}]) == "USAGE_LIMIT_REACHED"
    assert cc.classify_result({"is_error": True, "subtype": "success", "api_error_status": 401, "result": "x"}, None) == "AUTH_UNAVAILABLE"
    assert cc.classify_result({"is_error": False, "subtype": "success"}, [{"type": "assistant", "error": "model_not_found"}]) == "MODEL_DRIFT"
    assert cc.classify_result({"is_error": False, "subtype": "success"}, [{"type": "system", "subtype": "api_retry", "error": "billing_error"}]) == "AUTH_NOT_MAX_SUBSCRIPTION"
    assert cc.classify_result({"is_error": True, "subtype": "error_during_execution", "errors": ["boom"]}, None) == "PROCESS_ERROR"
    assert cc.classify_result({"is_error": False, "subtype": "success", "result": "{}"}, None) is None
    assert cc.STATUS_CLASSIFIER_VERSION == "cc-status/2" and "RESULT_MODEL_AMBIGUOUS" in cc.STATUSES


def test_IR_P10_no_scientific_output_and_counters_zero_after_fixture_validation():
    for name, f in fixtures():
        rm.resolve_result_model(PIN, f["output"], f["format"])
    assert ms.CALLS["claude_code_inference_invocations"] == 0 and ms.CALLS["model_calls"] == 0 and ms.CALLS["provider_calls"] == 0
    src = (ROOT / "src/logos_research/measurement/result_model.py").read_text(encoding="utf-8")
    assert "subprocess" not in src and "import requests" not in src and "socket" not in src


def test_token_v2_bindings_and_isolated_cwd():
    from logos_research.experiments.cognitive_provenance_r1 import harness as hz, dataset as ds, claude_runner as cr
    tasks = ds.build_tasks(); trials = ds.build_trials(tasks)
    cfg = hz.RunConfig("r", PIN, "a" * 64, "2.1.275 (Claude Code)", 156, dataset_hash="d" * 64, prompt_bundle_hash="p" * 64)
    gates = hz.RunGates(**{g: "PASS" for g in hz.GATE_NAMES})
    with pytest.raises(hz.GateError):                                                                                    # v1 token refused by a v2-bound run
        hz.run(tasks, trials, cc.ClaudeCodeMaxProvider(runner=lambda *a: (0, "", "")), cc.ActivationToken("r", PIN, 200, 1), cfg, gates, CLEAN_ENV)
    with pytest.raises(hz.GateError):                                                                                    # bound but to another CLI version
        hz.run(tasks, trials, cc.ClaudeCodeMaxProvider(runner=lambda *a: (0, "", "")), cc.ActivationToken("r", PIN, 200, 1, cli_version="9", contract_version="cc-result-model/1", dataset_hash="d" * 64, prompt_bundle_hash="p" * 64), cfg, gates, CLEAN_ENV)
    assert cfg.output_format == "json" and cfg.contract_version == rm.CONTRACT_VERSION            # REP-F1: stream-json requires --verbose (not approved)
    with pytest.raises(cc.ProviderPolicyError):
        cc.check_argv(cc.build_argv("q", PIN, cc.Limits(1, 1, 1.0), output_format="stream-json") + ["--verbose"])
    src = (ROOT / "src/logos_research/experiments/cognitive_provenance_r1/claude_runner.py").read_text(encoding="utf-8")
    assert "cwd=cwd" in src and "cwd: str | None" in src


def test_official_contract_note_exists():
    note = (ROOT / "docs/research/CLAUDE-CODE-OUTPUT-CONTRACT-R1.md").read_text(encoding="utf-8")
    for tok in ("modelUsage", "SDKAssistantMessage", "message.model", "cc-result-model/1", "order undocumented", "AuxiliaryModelUsage != PrimaryResponseModel", "--bare", "--fallback-model"):
        assert tok in note, tok


# ==========================================================================
# R-M1..R-M15
# ==========================================================================

def _battery():
    fx = ORACLE["fixtures"]
    doc = json.loads(RAW)
    r = rm.resolve_result_model(PIN, doc, "json")
    assert r.status == "RESOLVED" and r.resolved_model == PIN and not r.drift, "R-M1/R-M4"
    rev = {k: doc["modelUsage"][k] for k in reversed(list(doc["modelUsage"]))}
    r2 = rm.resolve_result_model(PIN, {**doc, "modelUsage": rev}, "json")
    assert (r2.status, r2.resolved_model, r2.drift) == (r.status, r.resolved_model, r.drift), "R-M1/R-M2"
    heavy = {**fx["F2"]["output"], "modelUsage": {**fx["F2"]["output"]["modelUsage"], "claude-haiku-4-5-20251001": {**fx["F2"]["output"]["modelUsage"]["claude-haiku-4-5-20251001"], "outputTokens": 9999}}}
    assert rm.resolve_result_model(PIN, heavy, "json").resolved_model == PIN, "R-M3"
    assert rm.resolve_result_model(PIN, fx["F3"]["output"], "json").drift is False, "R-M4"
    assert rm.resolve_result_model(PIN, fx["F4"]["output"], "json").status == "PIN_MISSING", "R-M5"
    r7 = rm.resolve_result_model(PIN, fx["F7"]["output"], "stream-json"); assert r7.drift and r7.resolved_model == "claude-sonnet-5", "R-M6"
    assert rm.resolve_result_model(PIN, fx["F11"]["output"], "json").status == "AMBIGUOUS", "R-M7"
    assert rm.resolve_result_model(PIN, fx["F8"]["output"], "json").status == "OUTPUT_INVALID", "R-M8"
    tok = cc.ActivationToken("r", PIN, 5, 1)
    p = cc.ClaudeCodeMaxProvider(runner=lambda argv, t, env: (0, RAW, ""))
    try:
        p.invoke("q", "claude-sonnet-5", {"run_id": "r"}, cc.Limits(1, 20000, 5.0), token=tok, env=CLEAN_ENV); changed = False
    except cc.ProviderPolicyError:
        changed = True
    ms.reset_counters(); assert changed, "R-M9"
    try:
        cc.check_argv(cc.build_argv("q", PIN, cc.Limits(1, 20000, 5.0)) + ["--fallback-model", "sonnet"]); ok = False
    except cc.ProviderPolicyError:
        ok = True
    assert ok, "R-M10"
    assert rm.resolve_result_model("opus", fx["F1"]["output"], "json").status == "PIN_MISSING" and not rm.same_model("claude-opus-5-1", PIN), "R-M11"
    assert rm.resolve_result_model(PIN, fx["F3"]["output"], "json").auxiliary_models == ("claude-haiku-4-5-20251001",), "R-M12"
    assert rm.resolve_result_model(PIN, fx["F1"]["output"], "json", contract_version="cc-result-model/0").status == "CONTRACT_UNSUPPORTED", "R-M13"
    assert sha256(RAW.encode("utf-8")).hexdigest() == RAW_SHA, "R-M14"
    pr = cc.ClaudeCodeMaxProvider(runner=lambda argv, t, env: (0, RAW, ""))
    res = pr.invoke("q", PIN, {"run_id": "r"}, cc.Limits(1, 20000, 5.0), token=tok, env=CLEAN_ENV); ms.reset_counters()
    assert res.status == "OK" and res.reported_model == PIN, "R-M15"


def _m(name):
    real = rm.resolve_result_model
    def first_key(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            r = real(req, out, fmt, cv); mu = (out if isinstance(out, dict) else out[-1]).get("modelUsage") or {}
            k = next(iter(mu), None)
            return replace(r, status="RESOLVED", resolved_model=k, evidence_class="EXPLICIT_RESULT_MODEL") if k else r
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def last_key(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            r = real(req, out, fmt, cv); mu = (out if isinstance(out, dict) else out[-1]).get("modelUsage") or {}
            k = list(mu)[-1] if mu else None
            return replace(r, status="RESOLVED", resolved_model=k, evidence_class="EXPLICIT_RESULT_MODEL") if k else r
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def heaviest(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            r = real(req, out, fmt, cv); mu = (out if isinstance(out, dict) else out[-1]).get("modelUsage") or {}
            k = max(mu, key=lambda x: (mu[x].get("outputTokens") or 0) if isinstance(mu[x], dict) else 0) if mu else None
            return replace(r, status="RESOLVED", resolved_model=k) if k else r
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def aux_drift(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            r = real(req, out, fmt, cv)
            return replace(r, status="PIN_MISSING", evidence_class="PIN_ABSENT", resolved_model=None) if r.auxiliary_models else r
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def pin_absent_ok(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            r = real(req, out, fmt, cv)
            return replace(r, status="RESOLVED", resolved_model=req, evidence_class="REQUEST_PIN_PLUS_USAGE_CONTAINMENT") if r.status == "PIN_MISSING" else r
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def foreign_ok(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            r = real(req, out, fmt, cv)
            return replace(r, resolved_model=req) if r.status == "RESOLVED" and r.drift else r
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def ambiguous_ok(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            r = real(req, out, fmt, cv)
            return replace(r, status="RESOLVED", resolved_model=req, evidence_class="REQUEST_PIN_PLUS_USAGE_CONTAINMENT") if r.status == "AMBIGUOUS" else r
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def malformed_ok(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            r = real(req, out, fmt, cv)
            return replace(r, status="RESOLVED", resolved_model=req, evidence_class="REQUEST_PIN_PLUS_USAGE_CONTAINMENT") if r.status == "OUTPUT_INVALID" else r
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def selector_change(mp):
        real_inv = cc.ClaudeCodeMaxProvider.invoke
        mp.setattr(cc.ClaudeCodeMaxProvider, "invoke", lambda self, prompt, model_pin, ctx, limits, *, token, env=None, output_format="json": real_inv(self, prompt, token.model_pin, ctx, limits, token=token, env=env, output_format=output_format))
    def fallback_flag(mp): mp.setattr(cc, "DOCUMENTED_FLAGS", cc.DOCUMENTED_FLAGS + ("--fallback-model",))
    def alias_ok(mp): mp.setattr(rm, "is_pin", lambda m: bool(m)); mp.setattr(rm, "same_model", lambda c, p: bool(c) and c.startswith(p))
    def drop_aux(mp):
        def f(req, out, fmt, cv=rm.CONTRACT_VERSION):
            return replace(real(req, out, fmt, cv), auxiliary_models=(), auxiliary_usage={})
        mp.setattr(rm, "resolve_result_model", f); mp.setattr(cc, "resolve_result_model", f)
    def contract_ignored(mp): mp.setattr(rm, "EXPLICIT_RESULT_FIELDS", {**rm.EXPLICIT_RESULT_FIELDS, "cc-result-model/0": ()})
    def fixture_drift(mp):
        global RAW
        mp.setattr(__import__(__name__), "RAW", RAW.replace('"claude-opus-5":', '"claude-opus-5x":'))
    def old_behaviour(mp):
        real_inv = cc.ClaudeCodeMaxProvider.invoke
        def inv(self, *a, **k):
            r = real_inv(self, *a, **k)
            mu = r.model_usage_raw or {}
            k0 = next(iter(mu), None)
            return replace(r, status="MODEL_DRIFT", content=None, reported_model=k0) if k0 and not rm.same_model(k0, r.requested_model) else r
        mp.setattr(cc.ClaudeCodeMaxProvider, "invoke", inv)
    return {"R-M1 first modelUsage key used as producer": first_key, "R-M2 last modelUsage key used as producer": last_key, "R-M3 highest-token model automatically used as producer": heaviest,
            "R-M4 auxiliary-first fixture triggers false drift": aux_drift, "R-M5 pinned model absent but accepted": pin_absent_ok, "R-M6 explicit foreign producer accepted because pin also appears": foreign_ok,
            "R-M7 ambiguous contract treated as drift-free": ambiguous_ok, "R-M8 malformed usage silently accepted": malformed_ok, "R-M9 requested model changed without detection": selector_change,
            "R-M10 --fallback-model accepted": fallback_flag, "R-M11 alias substituted without evidence": alias_ok, "R-M12 auxiliary models dropped from audit": drop_aux,
            "R-M13 CLI-version contract mismatch ignored": contract_ignored, "R-M14 captured raw fixture no longer reproduces repaired classification": fixture_drift,
            "R-M15 old false-positive behavior survives": old_behaviour}[name]


MUTANTS = ["R-M1 first modelUsage key used as producer", "R-M2 last modelUsage key used as producer", "R-M3 highest-token model automatically used as producer", "R-M4 auxiliary-first fixture triggers false drift",
           "R-M5 pinned model absent but accepted", "R-M6 explicit foreign producer accepted because pin also appears", "R-M7 ambiguous contract treated as drift-free", "R-M8 malformed usage silently accepted",
           "R-M9 requested model changed without detection", "R-M10 --fallback-model accepted", "R-M11 alias substituted without evidence", "R-M12 auxiliary models dropped from audit",
           "R-M13 CLI-version contract mismatch ignored", "R-M14 captured raw fixture no longer reproduces repaired classification", "R-M15 old false-positive behavior survives"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:80]


def test_MUT_zz_all_fifteen_caught_counters_zero():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 15
    assert all(v == 0 for v in ms.CALLS.values())
    out = os.environ.get("REP_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"mutants": CAUGHT, "calls": ms.CALLS, "fixture_sha256": RAW_SHA}, indent=1), encoding="utf-8")


def test_predecessor_protection_and_scope():
    diff = subprocess.run(["git", "diff", "--stat", "4ffda44", "HEAD", "--", 
                           # Γ and GAMMA.md are pinned by _gamma_freeze.assert_gamma_pinned() below, not by this diff:
                           # one recorded hash with an auditable supersede chain, checked on disk rather than between commits
                           ":(exclude)GAMMA.md", ":(exclude)src/logos_gamma",
                           "src/logos_authority", "src/logos_runtime", "src/logos_audit", "src/logos_effects", "src/logos_memory",
                           "src/logos_research/governance.py", "src/logos_research/experiments/cognitive_provenance_r1/dataset.py", "src/logos_research/experiments/cognitive_provenance_r1/prompts.py",
                           "src/logos_research/experiments/cognitive_provenance_r1/metrics.py", "docs/research/2026-08-20-PERSISTENT-STATE-PRIOR-ART-DELTA.md", "docs/research/INFERENCE-GOVERNANCE.json"],
                          capture_output=True, text=True, cwd=ROOT).stdout.strip()
    _gamma_freeze.assert_gamma_pinned()
    assert diff == "", diff                                                                    # scientific content, governance and production untouched (Section 23)


def test_source_classification_complete():
    cls = json.loads((ROOT / "docs/research/CPA-INSTRUMENT-REPAIR-SOURCE-CLASSIFICATION.json").read_text(encoding="utf-8"))
    sites = cls["sites"]
    assert cls["base"] == "4ffda44" and cls["unclassified"] == 0 and all(v["class"] in cls["vocabulary"] and v["class"] != "UNCLASSIFIED" for v in sites.values())
    assert not any(v["class"] == "PRODUCTION" for v in sites.values())
    changed = subprocess.run(["git", "diff", "--name-only", "4ffda44", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    files = {c for c in changed + untracked if "__pycache__" not in c and not c.endswith(".pyc")}
    assert files - set(sites) == set(), files - set(sites)
