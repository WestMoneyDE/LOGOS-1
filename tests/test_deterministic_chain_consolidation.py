"""DETERMINISTIC-CHAIN-CONSOLIDATION-R1 — the governance package is machine-checkable.

Source of truth: docs/research/DETERMINISTIC-CHAIN-CONSOLIDATION.json. The
markdown package is rendered from it; these tests check the JSON, the rendered
files, the evidence pointers, the frozen Γ / P7 bundles, the B1 guard and the
MBGV-F1 guard. Mutants edit an in-memory copy of the package (or patch the
guard) and must be caught by the same checks.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import inspect
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT / "scripts"))
import render_deterministic_chain as render  # noqa: E402

import logos_research.experiments as experiments  # noqa: E402
from logos_research.experiments import memory_authority as ma  # noqa: E402
from logos_research.experiments import risk_decomposition as rd  # noqa: E402
from logos_research.experiments import binding_repair as br  # noqa: E402
from logos_research.experiments.binding_state import BindingConstraint, ProposedAction, _base_contract  # noqa: E402
from logos_memory.store import MemoryStore  # noqa: E402

PKG = json.loads((ROOT / "docs/research/DETERMINISTIC-CHAIN-CONSOLIDATION.json").read_text(encoding="utf-8"))
FROZEN = {"gamma_bundle_sha256": "__set_at_freeze__", "p7_boundary_sha256": "__set_at_freeze__"}
_frozen_path = ROOT / "docs/research/DETERMINISTIC-CHAIN-FROZEN-HASHES.json"
if _frozen_path.exists():
    FROZEN = json.loads(_frozen_path.read_text(encoding="utf-8"))

REQUIRED = [f"GI-P{i}" for i in range(1, 8)]
REQUIRED_CE = ["CE1", "CE2", "VCE-1", "VCE-2", "VCE-3", "RAD-CE1", "B1-DEFECT-CLASS"]
REQUIRED_RESIDUAL = ["VF-2", "VF-3", "MAP-F1", "RSS-F1", "GAMMA-4-TIGHTENING", "MBGV-F1", "MBGV-F2", "MBGV-F3", "VOI-F1", "DCC-F1"]
FORBIDDEN_LABELS = ("PROVEN", "AXIOM", "FORMALLY_VERIFIED", "PRODUCTION_GUARANTEE")
FALSIFIED = {"BINDING-STATE-PRESERVATION-R1": "FALSIFIED", "BINDING-STATE-PRESERVATION-REPAIR-VALIDATION-R1": "REPAIR_FALSIFIED",
             "RISK-AWARENESS-DECOMPOSITION-R1": "FALSIFIED"}


# --------------------------------------------------------------------------
# Checks over a package dict (used directly and by the mutants)
# --------------------------------------------------------------------------

def check_package(d: dict) -> list[str]:
    """Return the list of violated checks; empty means consolidated."""
    v: list[str] = []
    ids = {i["id"] for i in d["invariants"]}
    if not all(r in ids for r in REQUIRED):
        v.append("DC-P1 missing GI-P1..P7")
    for i in d["invariants"]:
        if i["status"] != "PROPOSED":
            v.append(f"DC-P2 {i['id']} status {i['status']}")
        if not i.get("evidence"):
            v.append(f"DC-P3 {i['id']} no evidence")
        if not i.get("falsification"):
            v.append(f"DC-P4/DC-C7 {i['id']} no falsification")
        for e in i.get("evidence", []):
            if not (ROOT / e).exists():
                v.append(f"DC-C1 {i['id']} evidence missing {e}")
        blob = json.dumps(i)
        if any(re.search(rf"\b{f}\b", blob) for f in FORBIDDEN_LABELS) or i.get("adoption") in FORBIDDEN_LABELS + ("PRODUCTION_ADOPTED",):
            v.append(f"DC-P13/DC-C5 {i['id']} forbidden label")
        for x in i.get("experiments", []):
            if x not in d["experiments"]:
                v.append(f"DC-C2 {i['id']} unknown experiment {x}")
        if i["id"] == "GI-P0":
            if set(i.get("links", [])) != set(REQUIRED):
                v.append("DC-C10 GI-P0 must link GI-P1..P7")
            s = i["statement"].lower()
            if "may increase" in s or "can increase" in s or "must not increase" not in s:
                v.append("DC-C9/M11 umbrella wording lets non-authority raise authority")
            if "hypothesis" not in i.get("note", "").lower():
                v.append("GI-P0 must be marked a hypothesis")
    for name, verdict in FALSIFIED.items():
        if d["experiments"].get(name, {}).get("verdict") != verdict:
            v.append(f"DC-P5/DC-C4 {name} not marked {verdict}")
        if name not in d.get("falsified_experiments", []):
            v.append(f"DC-P5 {name} missing from falsified list")
    ce = {c["id"] for c in d["counterexamples"]}
    for r in REQUIRED_CE:
        if r not in ce:
            v.append(f"DC-P14 counterexample {r} missing")
    if not any("RAD-CE1" in i.get("counterexamples", []) for i in d["invariants"]):
        v.append("DC-P6 RAD-CE1 not referenced by an invariant")
    for c in d["counterexamples"]:
        if not any(c["id"] in i.get("counterexamples", []) for i in d["invariants"]) and c["id"] != "B1-DEFECT-CLASS":
            v.append(f"DC-C3 {c['id']} unlinked")
        if c["production_reachable"]:
            v.append(f"DC-C6 {c['id']} production reachable")
    rr = {r["id"]: r for r in d["residual_risks"]}
    for r in REQUIRED_RESIDUAL:
        if r not in rr:
            v.append(f"DC-P15 residual {r} missing")
    for r in d["residual_risks"]:
        if r["severity"] in ("HIGH", "CRITICAL") and not r.get("action"):
            v.append(f"DC-C6 {r['id']} no disposition")
        if r["severity"] in ("HIGH", "CRITICAL") and r["production_reachable"]:
            v.append(f"DC-C6 {r['id']} production reachable")
    for e in d["experiments"].values():
        if not (ROOT / e["closure"]).exists():
            v.append(f"DC-C1 closure missing {e['closure']}")
    for g in d["governance_decisions"]:
        if g["state"] not in ("PROPOSED", "APPROVED", "REJECTED", "DEFERRED"):
            v.append(f"governance state {g['state']}")
        if g["id"] == "EFFECT-ORACLE-SCOPE" and g["state"] == "APPROVED" and "production" in g["question"].lower():
            v.append("DC-P11 effect oracle promoted")
    if d.get("b1", {}).get("status") != "NON_PRODUCTION_FROZEN_RISK_GUARDED":
        v.append("DC-P7/M4 B1 status")
    return v


def gamma_bundle_hash() -> str:
    return hashlib.sha256(b"".join((ROOT / p).read_bytes() for p in sorted(PKG["gamma_bundle_files"]))).hexdigest()


def p7_hash() -> str:
    t = (ROOT / PKG["p7_boundary_file"]).read_bytes()
    return hashlib.sha256(t[t.index(b"## Consciousness / P7 boundary"):]).hexdigest()


# --------------------------------------------------------------------------
# DC-P / DC-C over the real package and the rendered files
# --------------------------------------------------------------------------

def test_DC_package_consolidated():
    assert check_package(PKG) == []


def test_DC_rendered_files_match_json(tmp_path):
    inv = (ROOT / "docs/research/GAMMA-INVARIANT-INVENTORY.md").read_text(encoding="utf-8")
    assert render.BEGIN in inv and render.END in inv
    assert inv[inv.index(render.BEGIN):inv.index(render.END) + len(render.END)] == render.inventory_section(PKG)
    for name, fn in (("DETERMINISTIC-CHAIN-EVIDENCE-MATRIX.md", render.evidence_matrix), ("DETERMINISTIC-CHAIN-GRAPH.md", render.graph),
                     ("COUNTEREXAMPLE-REGISTRY.md", render.counterexample_registry), ("RESIDUAL-RISK-REGISTRY.md", render.residual_registry)):
        assert (ROOT / "docs/research" / name).read_text(encoding="utf-8") == fn(PKG), name
    for r in REQUIRED:
        assert f"### {r} —" in inv
    section = inv[inv.index(render.BEGIN):]
    for f in FORBIDDEN_LABELS:
        assert not re.search(rf"\b{f}\b", section)
    assert section.count("Status: `PROPOSED`") == len(PKG["invariants"])
    assert (ROOT / "docs/adr/ADR-PROPOSED-CANONICAL-EFFECT-OWNERSHIP.md").exists()
    assert (ROOT / "docs/research/REAL-MODEL-READINESS-CHECKLIST.md").exists()


def test_DC_C2_verdicts_match_closure_records_and_registry():
    for name, e in PKG["experiments"].items():
        text = (ROOT / e["closure"]).read_text(encoding="utf-8")
        assert f"`{e.get('closure_status', e['verdict'])}`" in text, (name, e["verdict"])
    reg = json.loads((ROOT / "docs/research/RESEARCH-DELTA-REGISTRY.json").read_text(encoding="utf-8"))
    entries = reg.get("deltas") or reg.get("entries") or []
    voi = next(x for x in entries if x.get("id") == "VALUE-OF-INFORMATION-GATE")
    assert voi["status"] == "EXECUTED_R1_SUPPORTED"
    # CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1 (CAPB-F1): the check was depth-limited (`git log -20`) and would fail once the
    # chain grew past twenty commits; strengthened to full ancestry — every predecessor commit must be an ancestor of HEAD.
    log = subprocess.run(["git", "rev-list", "--abbrev-commit", "--abbrev=7", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    for e in PKG["experiments"].values():
        assert any(h.startswith(e["commit"]) for h in log), e


def test_DC_P9_P10_gamma_and_p7_unchanged():
    assert FROZEN["gamma_bundle_sha256"] == gamma_bundle_hash()
    assert FROZEN["p7_boundary_sha256"] == p7_hash()
    new_docs = ["docs/research/DETERMINISTIC-CHAIN-EVIDENCE-MATRIX.md", "docs/research/DETERMINISTIC-CHAIN-GRAPH.md",
                "docs/research/COUNTEREXAMPLE-REGISTRY.md", "docs/research/RESIDUAL-RISK-REGISTRY.md",
                "docs/adr/ADR-PROPOSED-CANONICAL-EFFECT-OWNERSHIP.md", "docs/research/REAL-MODEL-READINESS-CHECKLIST.md"]
    for p in new_docs:
        assert "PhenomenalConsciousness" not in (ROOT / p).read_text(encoding="utf-8")


def test_DC_P11_P12_effect_oracle_fixture_scoped_and_unknown_defers():
    from logos_research.experiments import effect_oracle as eo
    assert "EXPERIMENTAL_FIXTURE" in (eo.__doc__ or "")
    assert eo.canonical_effect("DISCOVER_SECRET", "vault-11") is None
    out, tr = ma.evaluate_with_memory([], ProposedAction("DISCOVER_SECRET", "vault-11", role="operator-A"), ma.GrantLedger(),
                                      tick=12, state_hash="a" * 64, fallback_contract=ma.canonical_contract())
    assert out == "DEFER" and tr["effect"] == "none" and tr["scope"] == "not-evaluated" and "gamma" not in tr
    assert not any(g["id"] == "EFFECT-ORACLE-SCOPE" and g["state"] == "APPROVED" for g in PKG["governance_decisions"])


def test_DC_C8_no_invariant_depends_on_inference():
    for i in PKG["invariants"]:
        blob = json.dumps(i).lower()
        assert "ruler" not in blob and "real model" not in blob.replace("real-model", "") and "llm" not in blob


# --------------------------------------------------------------------------
# B1 audit + guard tests (B1-G1..G7)
# --------------------------------------------------------------------------

PRODUCTION = ["logos_gamma", "logos_memory", "logos_pstate"]


def _importers_of_experiments() -> set[str]:
    out = set()
    for py in SRC.rglob("*.py"):
        rel = str(py.relative_to(SRC)).replace("\\", "/")
        if rel.startswith("logos_research/experiments/"):
            continue
        for n in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            mod = getattr(n, "module", None) or ""
            names = [a.name for a in getattr(n, "names", [])] if isinstance(n, (ast.Import, ast.ImportFrom)) else []
            if "experiments" in mod or any("experiments" in x for x in names):
                out.add(rel)
    return out


def test_B1_G1_production_import_is_refused():
    for mod in ("logos_memory.factory", "logos_gamma.kernel", "logos_pstate.retrieval", "logos_research.infra.runner", "logos_research.claims"):
        with pytest.raises(ImportError):
            experiments.assert_experimental_caller([mod, "tests.test_x"])
    assert experiments._is_production("logos_memory") and not experiments._is_production("logos_research.experiments.binding_state")


def test_B1_G2_experiment_and_test_modules_can_import():
    experiments.assert_experimental_caller(["tests.test_deterministic_chain_consolidation", "logos_research.experiments.memory_authority", "__main__", None])
    importlib.reload(experiments)                        # re-executes the module-level guard from a test frame: no error


def test_B1_G3_historical_defect_still_reproduces_in_experiments():
    c = BindingConstraint("dc", "APPROVAL_REQUIRED", _base_contract(targets=("silo-4",), externality="internal", reversibility="reversible",
                                                                     approval_required=False), authority_origin="model")
    assert br.evaluate_from_content(br.encode_envelope(c), ProposedAction("TRANSFER", "silo-4"), (10, 20))[0] == "ALLOW"
    with tempfile.TemporaryDirectory() as t:
        s = MemoryStore(Path(t) / "m"); L = ma.GrantLedger()
        r = ma.write_note(s, "ce1", ma.authority_note(None, ma.canonical_contract(externality="internal", reversibility="reversible", approval_required=False)))
        assert rd.b2_bridge([r], ma.TRANSFER, L, tick=12, state_hash="a" * 64)[0] == "ALLOW"          # RAD-CE1 historical path


def test_B1_G4_repaired_bridge_still_denies_rad_ce1():
    with tempfile.TemporaryDirectory() as t:
        s = MemoryStore(Path(t) / "m"); L = ma.GrantLedger()
        r = ma.write_note(s, "ce1", ma.authority_note(None, ma.canonical_contract(externality="internal", reversibility="reversible", approval_required=False)))
        out, tr = ma.evaluate_with_memory([r], ma.TRANSFER, L, tick=12, state_hash="a" * 64)
        assert out == "DENY" and tr["effect"] == "external/irreversible/approval=True"


def test_B1_G5_G6_G7_no_entrypoint_cli_or_registry_exposes_b1():
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" not in py and "entry_points" not in py and "console_scripts" not in py
    assert _importers_of_experiments() == set()
    for f in ROOT.rglob("*.py"):
        if ".venv" in f.parts or "tests" in f.parts or "experiments" in f.parts:
            continue
        txt = f.read_text(encoding="utf-8", errors="ignore")
        assert "evaluate_action" not in txt and "importlib.import_module(\"logos_research.experiments" not in txt, f
    assert PKG["b1"]["status"] == experiments.B1_STATUS == "NON_PRODUCTION_FROZEN_RISK_GUARDED"


# --------------------------------------------------------------------------
# MBGV-F1 audit + guard tests (F1-G1..G5)
# --------------------------------------------------------------------------

def _decide_callers():
    out = set()
    for py in (SRC / "logos_research/experiments").rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                fn = n.func; nm = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
                if nm == "_decide":
                    kws = {k.arg for k in n.keywords}
                    out.add((py.name, "effect" in kws, "canonical_contract" in kws))
    return out


def test_F1_audit_all_callers_state_their_effect_source():
    callers = _decide_callers()
    assert callers == {("memory_authority.py", False, True),      # evaluate_canonical: caller-held contract
                       ("memory_authority.py", True, False),      # evaluate_with_memory: oracle effect
                       ("relational_swap.py", False, True)}       # evaluate_held: caller-held contract


def test_F1_G1_omitting_effect_without_the_flag_raises():
    c = ma.canonical_contract()
    with pytest.raises(TypeError):
        ma._decide(ma.TRANSFER, c, None, (), tick=12, state_hash="a" * 64)
    with pytest.raises(TypeError):
        ma._decide(ma.TRANSFER, c, None, (), tick=12, state_hash="a" * 64, effect=None, canonical_contract=False)


def test_F1_G2_G3_G4_unknown_effect_exits_before_scope_and_gamma(monkeypatch):
    called = []
    monkeypatch.setattr(ma.gamma, "validate", lambda *a, **k: called.append("gamma"))
    monkeypatch.setattr(ma.ScopeDecision, "evaluate", lambda self, req: called.append("scope"))
    out, tr = ma.evaluate_with_memory([], ProposedAction("LAUNCH", "silo-4", role="operator-A"), ma.GrantLedger(),
                                      tick=12, state_hash="a" * 64, fallback_contract=ma.canonical_contract())
    assert out == "DEFER" and called == [] and tr["scope"] == "not-evaluated"


def test_F1_G5_semantics_preserved_for_canonical_callers():
    L = ma.GrantLedger(); c = ma.canonical_contract()
    L.issue("g", origin="human", action=ma.TRANSFER, contract=c, window=(10, 20), state_hash="a" * 64)
    assert ma.evaluate_canonical(ma.TRANSFER, L, "g", c, tick=12, state_hash="a" * 64)[0] == "ALLOW"
    assert ma.evaluate_canonical(ma.TRANSFER, L, None, c, tick=12, state_hash="a" * 64)[0] == "DENY"
    from logos_research.experiments import relational_swap as rs
    assert rs.evaluate_held([], ma.TRANSFER, L, "g", tick=12, state_hash="a" * 64, own_provenance=True, contract=c)[0] == "ALLOW"


# --------------------------------------------------------------------------
# Production/experiment boundary audit (Section 24)
# --------------------------------------------------------------------------

def test_boundary_audit_classified():
    refs = {"effect_oracle": set(), "canonical_proposal": set(), "evaluate_with_memory_prerepair": set(), "evaluate_action": set()}
    for py in SRC.rglob("*.py"):
        rel = str(py.relative_to(SRC)).replace("\\", "/")
        txt = py.read_text(encoding="utf-8")
        for k in refs:
            if k in txt:
                refs[k].add(rel)
    for k, files in refs.items():
        assert all(f.startswith("logos_research/experiments/") for f in files), (k, files)      # experiment only


# --------------------------------------------------------------------------
# Mutation suite M1..M12
# --------------------------------------------------------------------------

def _mut(fn):
    d = copy.deepcopy(PKG); fn(d); return check_package(d)


def _gi(d, i): return next(x for x in d["invariants"] if x["id"] == i)


MUTANTS = [
    ("M1 GI-P7 -> PRODUCTION_GUARANTEE", lambda: _mut(lambda d: _gi(d, "GI-P7").__setitem__("adoption", "PRODUCTION_GUARANTEE"))),
    ("M2 remove RAD-CE1 pointer", lambda: _mut(lambda d: [i["counterexamples"].remove("RAD-CE1") for i in d["invariants"] if "RAD-CE1" in i["counterexamples"]])),
    ("M4 reclassify B1 production-safe without guard", lambda: _mut(lambda d: d["b1"].__setitem__("status", "PRODUCTION_SAFE"))),
    ("M5 promote effect oracle without approval", lambda: _mut(lambda d: next(g for g in d["governance_decisions"] if g["id"] == "EFFECT-ORACLE-SCOPE").update(state="APPROVED", question="promote to production"))),
    ("M6 delete a falsified verdict", lambda: _mut(lambda d: d["experiments"]["RISK-AWARENESS-DECOMPOSITION-R1"].__setitem__("verdict", "SUPPORTED"))),
    ("M7 remove a falsification condition", lambda: _mut(lambda d: _gi(d, "GI-P3").__setitem__("falsification", ""))),
    ("M11 umbrella wording lets trust/risk/VOI raise authority", lambda: _mut(lambda d: _gi(d, "GI-P0").__setitem__("statement", "trust, risk and information value may increase canonical authority when they agree"))),
    ("M12 remove MBGV-F3 residual entry", lambda: _mut(lambda d: d.__setitem__("residual_risks", [r for r in d["residual_risks"] if r["id"] != "MBGV-F3"]))),
]


@pytest.mark.parametrize("label,run", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_mutant_is_caught(label, run):
    assert run() != [], f"mutant survived: {label}"


def test_M3_production_import_of_b1_is_caught():
    with pytest.raises(ImportError):
        experiments.assert_experimental_caller(["logos_memory.factory"])
    # and the static boundary would flag a production importer
    fake = SRC / "logos_memory" / "_mutant_import.py"
    fake.write_text("from logos_research.experiments import binding_state\n", encoding="utf-8")
    try:
        assert _importers_of_experiments() == {"logos_memory/_mutant_import.py"}
    finally:
        fake.unlink()


def test_M8_M9_changing_gamma_or_p7_is_caught(tmp_path):
    assert hashlib.sha256(b"".join((ROOT / p).read_bytes() for p in sorted(PKG["gamma_bundle_files"])) + b"x").hexdigest() != FROZEN["gamma_bundle_sha256"]
    assert hashlib.sha256(b"mutated P7 boundary").hexdigest() != FROZEN["p7_boundary_sha256"]


def test_M10_permissive_unknown_effect_is_caught(monkeypatch):
    from logos_research.experiments import effect_oracle as eo
    monkeypatch.setattr(ma, "canonical_effect", lambda a, t: eo.EffectClass("internal", "reversible", False))
    out, _ = ma.evaluate_with_memory([], ProposedAction("DISCOVER_SECRET", "vault-11", role="operator-A"), ma.GrantLedger(),
                                     tick=12, state_hash="a" * 64, fallback_contract=ma.canonical_contract(targets=("vault-11",)),
                                     effect_oracle=ma.canonical_effect)
    assert out == "ALLOW"          # the mutant would be visible: DC-P12 asserts DEFER on the real oracle


def test_DCC_F1_no_backspace_bytes_in_new_sources():
    """A backspace byte where a regex word boundary was intended makes a scan
    vacuous (DCC-F1). The one historical occurrence is frozen evidence; nothing
    else may contain it."""
    historical = {"tests/test_binding_repair_r2_validation.py"}
    offenders = set()
    for base in ("src", "tests", "scripts"):
        for f in (ROOT / base).rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            rel = str(f.relative_to(ROOT)).replace("\\", "/")
            if bytes([8]) in f.read_bytes() and rel not in historical:
                offenders.add(rel)
    assert offenders == set()
