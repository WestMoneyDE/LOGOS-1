"""LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 — Phase 1 (REAL-MODEL-MEASUREMENT-READINESS-R1, subsumed):
manifest, measurement plan, executable INVALID_MEASUREMENT rules, instrument-first dry run,
provider boundary. No model call, no provider call.
"""
from __future__ import annotations

import ast
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_research.measurement as ms
from logos_research.instrument import InstrumentCharacterization
from logos_research.measurement import dryrun as dr
from logos_research.measurement import plan as pl
from logos_research.measurement.gateway import ForbiddenProvider

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CAUGHT: dict[str, str] = {}
H = "a" * 64


def manifest(**o) -> ms.StochasticRunManifest:
    base = dict(experiment_id="EXP-X", run_id="run-1", model_id="model-x", model_version="2026-09", provider="prov", provider_region="eu-1", prompt_id="p1", prompt_version="v1",
                system_prompt_hash=H, tool_schema_hash=H, dataset_version="ds-1", seed_if_supported=7, temperature=0.0, top_p=1.0, max_tokens=256, reasoning_effort_if_supported=None,
                timestamp="2026-09-17T00:00:00+00:00", environment_hash=H, code_commit="eb1f642", dependency_lock_hash=H, hardware_runtime_metadata={"gpu": "none"})
    base.update(o)
    return ms.StochasticRunManifest(**base)


def plan(**o) -> ms.MeasurementPlan:
    base = dict(repeats=3, sample_size=4, resolution=0.01, dispersion=0.2, confidence_interval=0.95, effect_size=0.1, baseline="B0", control="C0",
                invalid_measurement_criteria=ms.INVALID_REASONS, early_stop_criteria="3 consecutive INVALID_MEASUREMENT", cost_cap=5.0, fallback="STOP_AND_REPORT")
    base.update(o)
    return ms.MeasurementPlan(**base)


def instrument(**o) -> InstrumentCharacterization:
    base = dict(instrument_id="det-metric", modality="DETERMINISTIC_METRIC", repeatability_sd=0.0, resolution=0.01, n_characterization_samples=30)
    base.update(o)
    return InstrumentCharacterization(**base)


ITEMS = [{"id": i, "q": f"item-{i}"} for i in range(4)]


@pytest.fixture(autouse=True)
def _counters():
    ms.reset_counters()
    yield
    assert ms.CALLS["model_calls"] == 0 and ms.CALLS["provider_calls"] == 0


# ==========================================================================
# Schemas
# ==========================================================================

def test_manifest_fields_complete_and_validated():
    assert ms.MANIFEST_FIELDS == ("experiment_id", "run_id", "model_id", "model_version", "provider", "provider_region", "prompt_id", "prompt_version", "system_prompt_hash",
                                  "tool_schema_hash", "dataset_version", "seed_if_supported", "temperature", "top_p", "max_tokens", "reasoning_effort_if_supported", "timestamp",
                                  "environment_hash", "code_commit", "dependency_lock_hash", "hardware_runtime_metadata")
    m = manifest(); assert m.issues() == [] and ms.StochasticRunManifest.from_dict(m.to_dict()) == m and len(m.condition_hash) == 64
    assert manifest(system_prompt_hash="short").issues() and manifest(temperature=3.0).issues() and manifest(max_tokens=0).issues() and manifest(model_version="").issues()
    with pytest.raises(ValueError):
        ms.StochasticRunManifest.from_dict({**m.to_dict(), "extra": 1})
    with pytest.raises(ValueError):
        d = m.to_dict(); d.pop("provider_region"); ms.StochasticRunManifest.from_dict(d)
    assert manifest(run_id="other", timestamp="later").condition_hash == m.condition_hash and manifest(model_version="x").condition_hash != m.condition_hash


def test_plan_fields_and_vocabularies():
    assert ms.PLAN_FIELDS == ("repeats", "sample_size", "resolution", "dispersion", "confidence_interval", "effect_size", "baseline", "control", "invalid_measurement_criteria",
                              "early_stop_criteria", "cost_cap", "fallback")
    assert ms.INVALID_REASONS == ("MODEL_VERSION_DRIFT", "PROMPT_DRIFT", "PROVIDER_DRIFT", "REGION_DRIFT", "DATASET_DRIFT", "INSUFFICIENT_REPEATS", "SEED_UNCONTROLLED", "EXCESSIVE_VARIANCE",
                                  "MISSING_TRACE", "MISSING_GROUND_TRUTH", "CONSTRUCT_INVALID", "COST_CAP_REACHED", "INSTRUMENT_FAILURE")
    assert plan().issues() == []
    assert plan(fallback="CONTINUE").issues() and plan(repeats=1).issues() and plan(baseline="X", control="X").issues() and plan(invalid_measurement_criteria=("BOGUS",)).issues()
    with pytest.raises(ValueError):
        ms.MeasurementOutcome("INVALID_MEASUREMENT")
    with pytest.raises(ValueError):
        ms.MeasurementOutcome("VALID", ("PROMPT_DRIFT",))
    with pytest.raises(ValueError):
        ms.MeasurementOutcome("INVALID_MEASUREMENT", ("BOGUS",))


def test_stochastic_preregistration_extension():
    base = {"kind": "STOCHASTIC", "hypothesis": "H"}
    t = manifest().to_dict(); [t.pop(k) for k in ("run_id", "timestamp", "hardware_runtime_metadata")]
    p = ms.stochastic_preregistration(base, t, plan().__dict__, metric_ids=["M03"])
    assert p["stochastic"]["schema"] == "logos.stochastic-prereg/1" and ms.validate_stochastic_preregistration(p) == [] and p["kind"] == "STOCHASTIC"
    bad = dict(p); bad["stochastic"] = {**p["stochastic"], "manifest_template": {k: v for k, v in t.items() if k != "model_version"}}
    assert "manifest_template.model_version missing" in ms.validate_stochastic_preregistration(bad)
    with pytest.raises(ValueError):
        ms.stochastic_preregistration(base, t, {}, metric_ids=["M03"])
    with pytest.raises(ValueError):
        ms.stochastic_preregistration(base, t, plan().__dict__, metric_ids=[])


# ==========================================================================
# Invalidation rules — each reason executable
# ==========================================================================

def _samples(n=3, **mo):
    prov = ms.DryRunProvider(); t = manifest(**mo)
    return t, [prov.complete(replace(t, run_id=f"r{i}"), ITEMS[0]) for i in range(n)]


def test_honest_samples_are_valid():
    t, s = _samples()
    out = ms.invalidate(t, plan(), s, instrument=instrument(), construct_ok=True, cost_spent=0.03, ground_truth_present=True)
    assert out.status == "VALID" and out.reasons == () and out.detail["instrument"] == "ADMISSIBLE"


@pytest.mark.parametrize("reason", ms.INVALID_REASONS)
def test_each_reason_fires(reason):
    t, s = _samples()
    b = dr._break(reason, plan(), s, instrument(), 0.03)
    out = ms.invalidate(t, plan(), b["samples"], instrument=b["instrument"], construct_ok=b["construct_ok"], cost_spent=b["cost"], ground_truth_present=b["gt"])
    assert reason in out.reasons and out.status == ("FALLBACK" if reason == "COST_CAP_REACHED" else "INVALID_MEASUREMENT"), (reason, out)


def test_cost_cap_is_fallback_never_continue():
    t, s = _samples()
    out = ms.invalidate(t, plan(cost_cap=0.02), s, instrument=instrument(), construct_ok=True, cost_spent=0.03, ground_truth_present=True)
    assert out.status == "FALLBACK" and out.detail["fallback"] == "STOP_AND_REPORT" and out.reasons == ("COST_CAP_REACHED",)


def test_inactive_criteria_are_not_applied_but_plan_must_name_them():
    t, s = _samples()
    p = plan(invalid_measurement_criteria=("MISSING_TRACE",))
    out = ms.invalidate(t, p, s[:1], instrument=None, construct_ok=False, cost_spent=0.0, ground_truth_present=False)
    assert out.status == "VALID"                                                     # only the named rule is active — the preregistration decides


# ==========================================================================
# Dry run (Section 16) and provider boundary
# ==========================================================================

def test_dry_run_gates_all_pass_on_synthetic_provider():
    r = ms.dry_run(manifest(), plan(), ITEMS, instrument=instrument())
    assert r.passed and set(r.gates) == set(ms.DRY_RUN_GATES) and r.samples == 12 and abs(r.cost - 0.12) < 1e-9 and r.outcome_status == "VALID"
    assert set(r.rules_exercised) == set(ms.INVALID_REASONS)
    assert ms.CALLS == {"model_calls": 0, "provider_calls": 0, "dry_run_calls": 12}


def test_dry_run_fails_on_untyped_slot_missing_trace_uncharacterized_instrument():
    class Untyped(ms.DryRunProvider):
        def complete(self, m, item):
            s = super().complete(m, item); return replace(s, output_slots={**s.output_slots, "score": "0.5"})
    assert ms.dry_run(manifest(), plan(), ITEMS, instrument=instrument(), provider=Untyped()).gates["all_output_slots_typed"] is False

    class NoTrace(ms.DryRunProvider):
        def complete(self, m, item):
            return replace(super().complete(m, item), trace=None)
    assert ms.dry_run(manifest(), plan(), ITEMS, instrument=instrument(), provider=NoTrace()).gates["all_traces_reconstructable"] is False
    r = ms.dry_run(manifest(), plan(), ITEMS, instrument=None)
    assert r.passed is True and r.outcome_status == "INVALID_MEASUREMENT" and "INSTRUMENT_FAILURE" in r.detail["honest_reasons"]   # gates pass; the run itself is invalid
    assert ms.dry_run(manifest(), plan(cost_cap=0.05), ITEMS, instrument=instrument()).gates["all_costs_accounted"] is False


def test_real_provider_forbidden_and_counters_zero():
    with pytest.raises(ms.RealProviderForbidden):
        ForbiddenProvider().complete(manifest(), ITEMS[0])
    assert ms.CALLS["model_calls"] == 0 and ms.CALLS["provider_calls"] == 0
    for py in (SRC / "logos_research/measurement").glob("*.py"):
        txt = py.read_text(encoding="utf-8")
        for tok in ("requests", "httpx", "urllib", "socket", "openai", "anthropic", "boto3", "subprocess"):
            assert f"import {tok}" not in txt and f"from {tok}" not in txt, (py.name, tok)


def test_measurement_package_never_touches_authority():
    for py in (SRC / "logos_research/measurement").glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module or ""] if isinstance(n, ast.ImportFrom) and n.level == 0 else [])
            for m in mods:
                assert not m.startswith(("logos_authority", "logos_runtime", "logos_gamma", "logos_effects", "logos_memory", "logos_research.experiments")), (py.name, m)


@settings(max_examples=100, deadline=None)
@given(n=st.integers(0, 6), temp=st.sampled_from([0.0, 0.7]), seed=st.sampled_from([None, 1]), drift=st.sampled_from([None, "model_version", "prompt_version", "provider", "provider_region", "dataset_version"]))
def test_property_invalidation_is_deterministic_and_fail_closed(n, temp, seed, drift):
    t, s = _samples(max(n, 0), temperature=temp, seed_if_supported=seed)
    if drift and s:
        s[0] = replace(s[0], manifest=replace(s[0].manifest, **{drift: getattr(s[0].manifest, drift) + "-x"}))
    a = ms.invalidate(t, plan(), s, instrument=instrument(), construct_ok=True, cost_spent=0.01 * n, ground_truth_present=True)
    b = ms.invalidate(t, plan(), s, instrument=instrument(), construct_ok=True, cost_spent=0.01 * n, ground_truth_present=True)
    assert a == b
    if n < 3:
        assert "INSUFFICIENT_REPEATS" in a.reasons
    if temp > 0 and seed is None and s:
        assert "SEED_UNCONTROLLED" in a.reasons
    if drift and s:
        assert any(r.endswith("DRIFT") for r in a.reasons)
    if n >= 3 and not (temp > 0 and seed is None) and not drift:
        assert a.status == "VALID"


# ==========================================================================
# Mutants (8)
# ==========================================================================

def _battery():
    t, s = _samples()
    for reason in ms.INVALID_REASONS:
        b = dr._break(reason, plan(), s, instrument(), 0.03)
        out = ms.invalidate(t, plan(), b["samples"], instrument=b["instrument"], construct_ok=b["construct_ok"], cost_spent=b["cost"], ground_truth_present=b["gt"])
        assert reason in out.reasons, ("rule", reason, out)
    out = ms.invalidate(t, plan(cost_cap=0.02), s, instrument=instrument(), construct_ok=True, cost_spent=0.03, ground_truth_present=True)
    assert out.status == "FALLBACK", ("fallback", out)
    r = ms.dry_run(manifest(), plan(), ITEMS, instrument=instrument()); assert r.passed, ("dry", r.gates)
    assert ms.CALLS["model_calls"] == 0 and ms.CALLS["provider_calls"] == 0, "counters"
    with pytest.raises(ms.RealProviderForbidden):
        ForbiddenProvider().complete(manifest(), ITEMS[0])


def _m(name):
    def drift_ignored(mp): mp.setattr(pl, "DRIFT_FIELDS", {})
    def repeats_ignored(mp):
        real = pl.invalidate
        mp.setattr(ms, "invalidate", lambda t, p, s, **k: real(t, replace(p, repeats=1), s, **k)); mp.setattr(pl, "invalidate", ms.invalidate)
    def seed_ignored(mp):
        real = pl.invalidate
        mp.setattr(ms, "invalidate", lambda t, p, s, **k: real(t, replace(p, seed_required_when_stochastic=False), s, **k))
    def variance_ignored(mp):
        real = pl.invalidate
        mp.setattr(ms, "invalidate", lambda t, p, s, **k: real(t, replace(p, dispersion=10.0), s, **k))
    def trace_ignored(mp):
        real = pl.invalidate
        mp.setattr(ms, "invalidate", lambda t, p, s, **k: real(t, p, [replace(x, trace=x.trace or {"reconstructable": True}) for x in s], **k))
    def cost_cap_continue(mp):
        real = pl.invalidate
        mp.setattr(ms, "invalidate", lambda t, p, s, **k: real(t, replace(p, cost_cap=1e9), s, **k))
    def instrument_optional(mp):
        real = pl.invalidate
        mp.setattr(ms, "invalidate", lambda t, p, s, *, instrument, **k: real(t, p, s, instrument=instrument or instrument_ok(), **k))
    def counter_reset(mp):
        mp.setattr(ms.gateway.ForbiddenProvider, "complete", lambda self, m, item: ms.DryRunProvider().complete(m, item))
        mp.setattr(ForbiddenProvider, "complete", lambda self, m, item: ms.DryRunProvider().complete(m, item))
    return {"drift ignored": drift_ignored, "repeats not enforced": repeats_ignored, "seed uncontrolled accepted": seed_ignored, "variance ignored": variance_ignored,
            "missing trace padded": trace_ignored, "cost cap continues": cost_cap_continue, "uncharacterized instrument accepted": instrument_optional,
            "real provider silently served": counter_reset}[name]


def instrument_ok():
    return instrument()


MUTANTS = ["drift ignored", "repeats not enforced", "seed uncontrolled accepted", "variance ignored", "missing trace padded", "cost cap continues",
           "uncharacterized instrument accepted", "real provider silently served"]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("name", MUTANTS)
def test_MUT_caught(name, monkeypatch):
    _m(name)(monkeypatch)
    with pytest.raises((AssertionError, pytest.fail.Exception)) as e:
        _battery()
    CAUGHT[name] = str(e.value)[:100]


def test_MUT_zz_all_caught():
    assert set(CAUGHT) == set(MUTANTS) and len(MUTANTS) == 8
    out = os.environ.get("P1_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"mutants": CAUGHT, "calls": ms.CALLS}, indent=1), encoding="utf-8")
