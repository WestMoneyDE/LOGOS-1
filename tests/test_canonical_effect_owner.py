"""CANONICAL-EFFECT-OWNERSHIP-DECISION-R1 — founder decision Option A (static
canonical effect registry): the production owner `logos_effects` and its
integration through the repaired memory bridge.

What is checked here, in order:

* DEC   decision package is consistent (founder choice verbatim, vocabularies, source audit complete)
* IF    typed interface / schema; only RESOLVED carries an effect; consequentiality == Γ
* PAR   differential parity with the reference oracle (effect_oracle + voi INFO_EFFECTS), migration one-to-one
* FC    fail-closed matrix: 14 rows -> never RESOLVED, bridge DEFER, scope/Γ untouched
* RAD/MBG/MBGV regressions through the owner bridge; direct Γ equivalence
* CEO-P1..P15 property tests (hypothesis), CEO-MTR1..8 metamorphic tests
* rollback v1 -> v2 -> v1; audit/observability; B1 + MBGV-F1 guards
* 14 mutants (M1..M14) each caught by the probe battery

    EffectOwnership != AgentClaim · UnknownEffect != Permission · UnavailableOwner != Permission
"""
from __future__ import annotations

import ast
import json
import os
import re
import tempfile
import time
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_effects as le
import logos_gamma as gamma
from logos_effects import registry as le_registry
from logos_effects import types as le_types
from logos_memory.factory import MemoryFactory
from logos_memory.records import MemoryRecord
from logos_memory.scope import ScopeContract, ScopeDecision, scope_digest
from logos_memory.store import MemoryStore
from logos_research import experiments
from logos_research.experiments import binding_state as bs
from logos_research.experiments import canonical_owner_bridge as cob
from logos_research.experiments import effect_oracle as eo
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import risk_decomposition as rd
from logos_research.experiments import value_of_information as voi
from logos_research.experiments.binding_state import BindingConstraint, ProposedAction, _base_contract

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PKG = json.loads((ROOT / "docs/research/CANONICAL-EFFECT-OWNER.json").read_text(encoding="utf-8"))
WINDOW, STATE_A, STATE_B, TICK = (10, 20), "a" * 64, "b" * 64, 12
EXT = ("internal", "external")
REV = ("reversible", "partially-reversible", "irreversible")
RUN = "ceo-r1-test"

V1 = le.version_v1()
KNOWN: dict[tuple[str, str], tuple[str, str, bool]] = {(d.action, d.target): (d.externality, d.reversibility, d.approval_required) for d in V1.definitions}
ACTIONS = {k: ProposedAction(k[0], k[1], role="operator-A") for k in KNOWN}
UNKNOWN = [ProposedAction("LAUNCH", "silo-4", role="operator-A"), ProposedAction("TRANSFER", "vault-11", role="operator-A"),
           ProposedAction("QUERY_RECORD", "silo-4", role="operator-A"), ProposedAction("", "", role="operator-A")]
TRANSFER = ACTIONS[("TRANSFER", "silo-4")]
EXPORT = ACTIONS[("EXPORT", "ledger-3")]
CE1_CLAIM = dict(ext="internal", rev="reversible", appr=False)
GRANT_STATES = ("absent", "human", "model-origin", "revoked", "stale", "wrong-state", "wrong-principal", "wrong-scope")

# channels the owner must never read; mutants wire them in
CHANNELS: dict[str, float] = {"trust": 0.0, "risk": 0.0, "voi": 0.0}


def ctx(run=RUN, **kw) -> le.CanonicalEffectContext:
    return le.CanonicalEffectContext(run, **kw)


def fresh_registry(sink=None) -> le.CanonicalEffectRegistry:
    return le.production_registry(sink=sink)


def contract_of(action: ProposedAction, **o) -> ScopeContract:
    e, r, a = KNOWN[(action.action, action.target)]
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",), approval_required=a, externality=e, reversibility=r)
    base.update(o)
    return _base_contract(**base)


def claim_contract(action: ProposedAction, ext, rev, appr, **o) -> ScopeContract:
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",), approval_required=appr, externality=ext, reversibility=rev)
    base.update(o)
    return _base_contract(**base)


def direct_gamma(action: ProposedAction, grant, *, tick=TICK, state_hash=STATE_A, contract=None) -> str:
    """Γ with the OWNER's canonical definition, canonical scope digest and the given grant. No bridge code."""
    e, r, appr = KNOWN[(action.action, action.target)]
    c = contract or contract_of(action)
    if action.role not in c.roles or action.target not in c.targets:
        return "DENY"
    if appr and (grant is None or not grant.is_human_rooted()):
        return "DENY"
    prop = gamma.EffectProposal(action=action.action, target=action.target, effect_kind="deployment" if e == "external" else "write-internal",
                                externality=e, reversibility=r, proposal_digest=ma.proposal_digest(action),
                                provenance=(gamma.ProvenanceClaim("proposal://x", "model", "0" * 64),))
    v = gamma.validate(gamma.ValidationContext(prop, tick, state_hash, scope_digest(c), grant))
    return {"VALID": "ALLOW", "INVALID": "DENY", "UNCLEAR": "DEFER"}[v.result]


class Lab:
    def __init__(self, tmp: Path, registry: le.CanonicalEffectRegistry | None = None):
        self.ledger = ma.GrantLedger(); self.store = MemoryStore(tmp / "mem"); self.tmp = tmp; self.n = 0
        self.registry = registry or fresh_registry()

    def grant(self, gid, action, *, origin="human", window=WINDOW, state=STATE_A, **o):
        return self.ledger.issue(gid, origin=origin, action=action, contract=contract_of(action, **o), window=window, state_hash=state)

    def write(self, content, **kw) -> MemoryRecord:
        self.n += 1
        return ma.write_note(self.store, f"o-{self.n}", content, **kw)

    def note(self, ref, contract, **claims) -> str:
        return ma.authority_note(ref, contract, **claims)

    def bridge(self, records, action, *, tick=TICK, state=STATE_A, fallback=None, registry=None, context=None):
        return cob.evaluate_with_owner(list(records), action, self.ledger, registry or self.registry, context or ctx(),
                                       tick=tick, state_hash=state, fallback_contract=fallback)

    def transports(self, r: MemoryRecord) -> dict[str, list[MemoryRecord]]:
        c = _base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        sc = ScopeDecision("ALLOW", c, scope_digest(c))
        rr = MemoryFactory(self.store).retrieve("scope grant_ref", sc, limit=100)
        pj = MemoryFactory(self.store).project((r.id,), purpose="v", audience="project", valid_until="2026-12-01T00:00:00+00:00", scope=sc)
        return {"fetch": [self.store.fetch(r.id)], "retrieve": [x for x in (self.store.fetch(i.id) for i in rr.items) if x.id == r.id],
                "project": [replace(self.store.fetch(i["id"]), content=i["content"], id="proj:" + i["id"]) for i in json.loads(pj.content)],
                "reload": [MemoryStore(self.tmp / "mem").fetch(r.id)]}


@pytest.fixture
def lab():
    with tempfile.TemporaryDirectory() as t:
        yield Lab(Path(t))


ROWS: list[dict] = []
PERF: list[dict] = []


def _setup_grant(L: Lab, action, state):
    if state == "absent":
        return None, TICK, STATE_A, action
    if state == "model-origin":
        return L.grant("g", action, origin="model"), TICK, STATE_A, action
    g = L.grant("g", action)
    if state == "revoked":
        L.ledger.revoke("g"); return None, TICK, STATE_A, action
    if state == "stale":
        return g, WINDOW[1] + 3, STATE_A, action
    if state == "wrong-state":
        return g, TICK, STATE_B, action
    if state == "wrong-principal":
        return g, TICK, STATE_A, replace(action, role="operator-C")
    if state == "wrong-scope":
        return g, TICK, STATE_A, replace(action, target="vault-11")
    return g, TICK, STATE_A, action


def expected(act, grant, *, tick=TICK, state_hash=STATE_A) -> str:
    return direct_gamma(act, grant, tick=tick, state_hash=state_hash) if (act.action, act.target) in KNOWN else "DEFER"


def classify_delta(bridge_out, gamma_out, trace) -> str:
    if bridge_out == gamma_out:
        return "none"
    if bridge_out == "ALLOW":
        return "UNEXPLAINED-ALLOW"
    f = trace.get("gamma_failures", "")
    if "G4-CLAIM" in f:
        return "Γ-4 tightening"
    if "G3-BINDING" in f or trace.get("scope") == "DENY":
        return "binding veto"
    if f == "APPROVAL-REQUIRED":
        return "approval gate"
    return "unexplained"


def observe(case, L: Lab, records, action, *, grant=None, tick=TICK, state=STATE_A, fallback=None):
    out, tr = L.bridge(records, action, tick=tick, state=state, fallback=fallback)
    key = (action.action, action.target)
    known = key in KNOWN
    g = direct_gamma(action, grant, tick=tick, state_hash=state) if known else "DEFER"
    delta = classify_delta(out, g, tr) if known else ("none" if out == "DEFER" else "UNEXPLAINED-ALLOW")
    ROWS.append({"case": case, "action": key, "outcome": out, "direct_gamma": g, "effect": tr.get("effect"), "delta": delta,
                 "resolution_status": tr.get("resolution_status"), "definition_id": tr.get("definition_id"), "false_allow": out == "ALLOW" and g != "ALLOW"})
    assert not (out == "ALLOW" and g != "ALLOW"), (case, tr)
    if known:
        e, r, a = KNOWN[key]
        assert tr.get("effect") == f"{e}/{r}/approval={a}", (case, tr)
        assert tr["resolution_status"] == "RESOLVED" and tr["definition_id"].startswith("ce-") and len(tr["definition_hash"]) == 64 and tr["owner_version"] == "v1"
    else:
        assert out == "DEFER" and tr["resolution_status"] in ("UNKNOWN",) and tr["scope"] == "not-evaluated", (case, tr)
    assert delta not in ("unexplained", "UNEXPLAINED-ALLOW"), (case, tr)
    return out, tr


# ==========================================================================
# DEC — decision package
# ==========================================================================

def test_DEC_founder_decision_recorded_verbatim():
    fd = PKG["founder_decision"]
    assert fd["chosen_option"] == "A" and fd["state"] == "APPROVED" and fd["decided_by"] == "founder"
    assert fd["verbatim"].startswith("A — static canonical effect registry") and "Rationale:" in fd["verbatim"]
    assert set(fd["rejected_alternatives"]) == {"B", "C", "D", "NONE/DEFER"}
    adr = (ROOT / "docs/adr/ADR-CANONICAL-EFFECT-OWNERSHIP-DECISION.md").read_text(encoding="utf-8")
    assert fd["verbatim"].splitlines()[0] in adr and "Option A" in adr
    for fld in ("Status", "Date", "Founder decision", "Chosen option", "Rejected alternatives", "Decision rationale", "Scope", "Non-goals",
                "Minimum guarantees", "Migration implications", "Rollback", "Open risks", "Evidence pointers", "Governance owner", "Review date"):
        assert re.search(rf"^\*\*{re.escape(fld)}", adr, re.M) or re.search(rf"^#+ .*{re.escape(fld)}", adr, re.M), fld


def test_DEC_governance_vocabulary():
    g = {d["id"]: d for d in PKG["governance_decisions"]}
    assert g["CANONICAL-EFFECT-OWNERSHIP"]["value"] == "OPTION_A_STATIC_REGISTRY" and g["CANONICAL-EFFECT-OWNERSHIP"]["state"] == "APPROVED"
    assert g["EFFECT-ORACLE-SCOPE"]["value"] in ("EXPERIMENTAL_FIXTURE_ONLY", "REFERENCE_TEST_ORACLE", "MIGRATION_SOURCE_ONLY", "DEPRECATED_FIXTURE")
    assert g["EFFECT-ORACLE-SCOPE"]["value"] != "PRODUCTION_OWNER"
    assert g["PRODUCTION-BRIDGE-READINESS"]["value"] in ("PRODUCTION_BRIDGE_READY", "PRODUCTION_BRIDGE_READY_WITH_CONDITIONS", "PRODUCTION_BRIDGE_DEFERRED", "PRODUCTION_BRIDGE_REJECTED")
    assert all(d["state"] in ("PROPOSED", "APPROVED", "REJECTED", "DEFERRED") for d in PKG["governance_decisions"])
    assert g["INFERENCE-PROHIBITION"]["state"] == "DEFERRED"
    if g["PRODUCTION-BRIDGE-READINESS"]["value"] == "PRODUCTION_BRIDGE_READY_WITH_CONDITIONS":
        assert len(g["PRODUCTION-BRIDGE-READINESS"]["conditions"]) >= 1
    assert (ROOT / "src/logos_research/experiments/effect_oracle.py").exists()          # fixture not deleted
    assert "EXPERIMENTAL_FIXTURE" in (ROOT / "src/logos_research/experiments/effect_oracle.py").read_text(encoding="utf-8")


def _token_hits() -> set[str]:
    toks = PKG["source_audit"]["tokens"]
    hits = set()
    for py in SRC.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        txt = py.read_text(encoding="utf-8")
        if any(t in txt for t in toks):
            hits.add(str(py.relative_to(ROOT)).replace("\\", "/"))
    return hits


def test_DEC_source_audit_complete_no_unclassified():
    sites = PKG["source_audit"]["sites"]
    hits = _token_hits()
    assert hits == set(sites), (hits - set(sites), set(sites) - hits)
    assert all(v["class"] in PKG["source_audit"]["vocabulary"] and v["class"] != "UNCLASSIFIED" for v in sites.values())
    assert PKG["source_audit"]["unclassified"] == 0
    assert {k for k, v in sites.items() if v["class"] == "PRODUCTION_CANONICAL_OWNER" and k.startswith("src/logos_effects")} == \
        {"src/logos_effects/__init__.py", "src/logos_effects/types.py", "src/logos_effects/registry.py", "src/logos_effects/definitions.py"}
    assert sites["src/logos_research/experiments/effect_oracle.py"]["class"] == "EXPERIMENTAL_REFERENCE"
    assert sites["src/logos_research/experiments/binding_state.py"]["class"] == "HISTORICAL_ONLY"


# ==========================================================================
# IF — interface and schema
# ==========================================================================

def test_IF_statuses_and_resolution_contract():
    assert le.STATUSES == ("RESOLVED", "UNKNOWN", "UNAVAILABLE", "INVALID")
    r = le.resolve_effect("TRANSFER", "silo-4", ctx(), registry=fresh_registry())
    assert r.status == "RESOLVED" and r.effect == le.CanonicalEffect("external", "irreversible", True)
    assert r.definition_id == "ce-transfer-silo-4" and r.version == "v1" and len(r.definition_hash) == 64 and "founder-decision:Option-A" in r.provenance
    u = le.resolve_effect("LAUNCH", "silo-4", ctx(), registry=fresh_registry())
    assert u.status == "UNKNOWN" and u.effect is None and u.definition_id is None and u.error
    with pytest.raises(ValueError):
        le.CanonicalEffectResolution("UNKNOWN", le.CanonicalEffect("internal", "reversible", False))
    with pytest.raises(ValueError):
        le.CanonicalEffectResolution("RESOLVED", le.CanonicalEffect("internal", "reversible", False))   # no id/version/hash
    with pytest.raises(ValueError):
        le.CanonicalEffectResolution("PERMITTED")


def test_IF_schema_fields_and_hash():
    assert list(le.CanonicalEffectDefinition.HASHED_FIELDS) + ["definition_hash"] == PKG["schema"]["fields"]
    assert set(PKG["schema"]["fields"]) >= {"effect_id", "action", "target", "domain", "externality", "reversibility", "approval_required",
                                            "version", "provenance", "effective_from", "effective_until", "definition_hash"}
    d = V1.definitions[0]
    assert d.definition_hash == le.CanonicalEffectDefinition.from_dict(d.to_dict()).definition_hash
    assert le.CanonicalEffectDefinition.from_dict(d.to_dict()) == d
    with pytest.raises(ValueError):
        le.CanonicalEffectDefinition.from_dict({**d.to_dict(), "definition_hash": "0" * 64})
    with pytest.raises(ValueError):
        le.CanonicalEffectDefinition.from_dict({**d.to_dict(), "trust_score": 0.9})
    assert V1.content_hash == PKG["owner"]["registry_hash_v1"] and len(V1.definitions) == PKG["owner"]["definition_count_v1"] == 11


@pytest.mark.parametrize("ext", EXT)
@pytest.mark.parametrize("rev", REV)
@pytest.mark.parametrize("appr", [True, False])
def test_IF_consequentiality_derived_identically_to_gamma(ext, rev, appr):
    e = le.CanonicalEffect(ext, rev, appr)
    p = gamma.EffectProposal(action="X", target="Y", effect_kind="deployment" if ext == "external" else "write-internal",
                             externality=ext, reversibility=rev, proposal_digest="0" * 64, provenance=())
    assert e.consequential == p.is_consequential()


def test_IF_owner_imports_stdlib_only_and_never_experiments():
    forbidden = re.compile(r"\b(memory|trust|reliab|risk|voi|information_value|uncertain|confidence|prose|llm|model_output|authority_class|declared)\b", re.I)
    for py in (SRC / "logos_effects").glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                mods = [n.module or "."] if n.level == 0 else []
            else:
                continue
            for m in mods:
                assert not m.startswith(("logos_", "src")), (py.name, m)
                assert m.split(".")[0] in {"json", "time", "dataclasses", "hashlib", "pathlib", "typing", "__future__"}, (py.name, m)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} \
            | {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
        bad = {x for x in names if forbidden.search(x)}
        assert not bad, (py.name, bad)
    assert "logos_effects" in experiments.PRODUCTION_PACKAGES


# ==========================================================================
# PAR — differential parity + migration (CEO-MTR8)
# ==========================================================================

def _fixture_union() -> dict[tuple[str, str], eo.EffectClass]:
    return {**eo.CANONICAL_EFFECTS, **voi.INFO_EFFECTS}


def test_PAR_owner_matches_reference_oracle_on_every_row_and_unknown():
    reg = fresh_registry(); ref = _fixture_union()
    assert set(ref) == set(KNOWN), "migration must be one-to-one with the reference union"
    for (a, t), e in ref.items():
        r = reg.resolve(a, t, ctx())
        assert r.status == "RESOLVED" and (r.effect.externality, r.effect.reversibility, r.effect.approval_required) == (e.externality, e.reversibility, e.approval_required), (a, t)
        assert eo.canonical_effect(a, t) == voi.voi_effect(a, t) or (a, t) in voi.INFO_EFFECTS
    for u in UNKNOWN + [ProposedAction("TRANSFER", "SILO-4"), ProposedAction("transfer", "silo-4")]:
        assert reg.resolve(u.action, u.target, ctx()).status == "UNKNOWN"
        assert eo.canonical_effect(u.action, u.target) is None and voi.voi_effect(u.action, u.target) is None


def test_PAR_migration_mapping_is_exact_and_hashed():
    m = PKG["migration_mapping"]; ref = _fixture_union()
    assert len(m) == 11 and {x["source_row"] for x in m} == {f"{a}|{t}" for a, t in ref} and len({x["definition_id"] for x in m}) == 11
    by_id = {d.effect_id: d for d in V1.definitions}
    for row in m:
        d = by_id[row["definition_id"]]
        assert row["definition_hash"] == d.definition_hash and row["version"] == d.version == "v1"
        assert row["fixture_effect"] == row["definition_effect"] == [d.externality, d.reversibility, d.approval_required] and row["semantic_diff"] == "none"
    axes = {r["axis"] for r in m}
    assert {"approval-only", "externality-only", "reversibility-only", "full", "non-consequential"} <= axes


# ==========================================================================
# FC — fail-closed matrix
# ==========================================================================

def _spy_pipeline(monkeypatch):
    calls = {"scope": 0, "gamma": 0}
    real_eval = ScopeDecision.evaluate; real_val = gamma.validate

    def ev(self, *a, **k):
        calls["scope"] += 1; return real_eval(self, *a, **k)

    def va(*a, **k):
        calls["gamma"] += 1; return real_val(*a, **k)
    monkeypatch.setattr(ScopeDecision, "evaluate", ev); monkeypatch.setattr(ma.gamma, "validate", va)
    return calls


def _v(defs, version="v1", provenance="test", created="2026-09-17T00:00:00+00:00") -> le.RegistryVersion:
    return le.RegistryVersion(version, tuple(defs), provenance, created)


def _def(**o) -> le.CanonicalEffectDefinition:
    base = dict(effect_id="ce-transfer-silo-4", action="TRANSFER", target="silo-4", domain="global", externality="external", reversibility="irreversible",
                approval_required=True, version="v1", provenance="test", effective_from="2026-09-17T00:00:00+00:00", effective_until=None)
    base.update(o)
    return le.CanonicalEffectDefinition(**base)


def _fc_registry(kind: str):
    """(registry, action, context, expected_status)"""
    T = ("TRANSFER", "silo-4")
    if kind == "missing definition":
        return le.CanonicalEffectRegistry.load([_v([d for d in V1.definitions if d.key != (*T, "global")])], "v1"), T, ctx(), "UNKNOWN"
    if kind == "corrupt definition":
        raw = le.production_registry().to_dict(); raw["versions"][0]["definitions"][0]["externality"] = "EXTERNAL!"
        return le.CanonicalEffectRegistry.from_dict(raw), T, ctx(), "UNAVAILABLE"     # cannot load -> unavailable
    if kind == "invalid enum":
        return le.CanonicalEffectRegistry.load([_v([_def(reversibility="undoable")])], "v1"), T, ctx(), "INVALID"
    if kind == "invalid type":
        return le.CanonicalEffectRegistry.load([_v([_def(approval_required="yes")])], "v1"), T, ctx(), "INVALID"
    if kind == "duplicate definition":
        return le.CanonicalEffectRegistry.load([_v([_def(), _def(effect_id="ce-dup", approval_required=False)])], "v1"), T, ctx(), "INVALID"
    if kind == "conflicting versions":
        reg = le.CanonicalEffectRegistry.load([_v([_def()]), _v([_def(version="v2", approval_required=False)], version="v2")], "v1")
        reg.activate("v3"); return reg, T, ctx(), "UNAVAILABLE"                       # ambiguous request -> no active version
    if kind == "stale version":
        return le.CanonicalEffectRegistry.load([_v([_def(effective_until="2026-09-18T00:00:00+00:00")])], "v1"), T, ctx(as_of="2026-10-01T00:00:00+00:00"), "UNKNOWN"
    if kind == "unknown target":
        return fresh_registry(), ("TRANSFER", "vault-11"), ctx(), "UNKNOWN"
    if kind == "unknown action":
        return fresh_registry(), ("LAUNCH", "silo-4"), ctx(), "UNKNOWN"
    if kind == "owner unavailable":
        return le.CanonicalEffectRegistry.from_file(Path(tempfile.gettempdir()) / "does-not-exist-ceo.json"), T, ctx(), "UNAVAILABLE"
    if kind == "timeout":
        return fresh_registry(), T, ctx(deadline_ns=time.monotonic_ns() - 1), "UNAVAILABLE"
    if kind == "malformed response":
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("{not json"); p = f.name
        return le.CanonicalEffectRegistry.from_file(p), T, ctx(), "UNAVAILABLE"
    if kind == "wrong domain":
        return fresh_registry(), T, ctx(domain="finance"), "UNKNOWN"
    if kind == "integrity mismatch":
        raw = le.production_registry().to_dict(); raw["versions"][0]["definitions"][0]["approval_required"] = False   # hash no longer matches
        return le.CanonicalEffectRegistry.from_dict(raw), T, ctx(), "UNAVAILABLE"
    raise KeyError(kind)


@pytest.mark.parametrize("kind", PKG["fail_closed_matrix"])
def test_FC_matrix_never_resolves_and_bridge_defers(kind, monkeypatch):
    reg, (a, t), c, expected = _fc_registry(kind)
    r = reg.resolve(a, t, c)
    assert r.status == expected and r.effect is None, (kind, r)
    calls = _spy_pipeline(monkeypatch)
    with tempfile.TemporaryDirectory() as tmp:
        L = Lab(Path(tmp), reg)
        act = ProposedAction(a, t, role="operator-A")
        L.grant("g", act) if (a, t) in KNOWN else None
        rec = L.write(L.note("g", claim_contract(act, "internal", "reversible", False)))
        out, tr = L.bridge([rec], act, context=c)
    assert out == "DEFER" and tr["resolution_status"] == expected and tr["scope"] == "not-evaluated", (kind, tr)
    assert calls == {"scope": 0, "gamma": 0}
    ROWS.append({"case": f"FC:{kind}", "action": (a, t), "outcome": out, "direct_gamma": "DEFER", "delta": "none", "resolution_status": expected, "false_allow": False})


def test_FC_load_never_raises_on_data_problems_and_version_immutable():
    reg = fresh_registry()
    with pytest.raises(ValueError):
        reg.add_version(le.version_v1())                                            # versions are immutable, no overwrite
    assert le.CanonicalEffectRegistry.from_dict({"weird": 1}).available is False
    assert le.CanonicalEffectRegistry.from_dict({"active_version": "v1", "versions": [{"version": "v1"}]}).available is False
    assert le.CanonicalEffectRegistry.from_dict("nope").available is False           # type: ignore[arg-type]


# ==========================================================================
# RAD / MBG / MBGV regressions through the owner bridge
# ==========================================================================

def test_RAD_CE1_historical_path_preserved_only_there_owner_path_denies(lab):
    r = lab.write(lab.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))
    for name, recs in lab.transports(r).items():
        assert ma.evaluate_with_memory_prerepair(recs, TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A, fallback_contract=contract_of(TRANSFER))[0] == "ALLOW", name
        assert rd.b2_bridge(recs, TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW", name
        out, tr = observe(f"RAD-CE1/{name}", lab, recs, TRANSFER)
        assert out == "DENY" and tr["effect"] == "external/irreversible/approval=True" and tr["declared"] == "internal/reversible"
        assert tr["gamma_failures"] == "APPROVAL-REQUIRED" and tr["definition_id"] == "ce-transfer-silo-4"


def test_MBG_three_bridges_across_transports(lab):
    r = lab.write(lab.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))
    for name, recs in lab.transports(r).items():
        hist = ma.evaluate_with_memory_prerepair(recs, TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A, fallback_contract=contract_of(TRANSFER))[0]
        repaired = ma.evaluate_with_memory(recs, TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A)[0]
        owner = lab.bridge(recs, TRANSFER)[0]
        assert (hist, repaired, owner) == ("ALLOW", "DENY", "DENY"), name
        ROWS.append({"case": f"MBG/{name}", "action": ("TRANSFER", "silo-4"), "outcome": owner, "direct_gamma": "DENY", "delta": "none", "false_allow": False})


@pytest.mark.parametrize("grant_state", GRANT_STATES)
@pytest.mark.parametrize("key", sorted(KNOWN))
def test_MBGV_direct_gamma_equivalence_with_honest_claim(key, grant_state):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        grant, tick, state, act = _setup_grant(L, action, grant_state)
        e, r, a = KNOWN[key]
        rec = L.write(L.note("g" if grant_state != "absent" else None, claim_contract(act, e, r, a)))
        out, tr = observe(f"EQ/{key}/{grant_state}", L, [rec], act, grant=grant, tick=tick, state=state)
        g = expected(act, grant, tick=tick, state_hash=state)
        assert out == g or (out == "DENY" and tr.get("scope") == "DENY"), (key, grant_state, out, g, tr)   # binding veto is the only allowed delta


@pytest.mark.parametrize("grant_state", ("absent", "human", "model-origin", "revoked"))
@pytest.mark.parametrize("appr", [True, False])
@pytest.mark.parametrize("ext", EXT)
@pytest.mark.parametrize("rev", ("reversible", "irreversible"))
@pytest.mark.parametrize("key", [("TRANSFER", "silo-4"), ("EXPORT", "ledger-3"), ("NOTIFY", "ops-channel"), ("QUERY_RECORD", "customer-secret"), ("INSPECT", "silo-4")])
def test_MBGV_canonical_invariance_and_approval_not_suppressible(key, ext, rev, appr, grant_state):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        grant, tick, state, act = _setup_grant(L, action, grant_state)
        rec = L.write(L.note("g" if grant_state != "absent" else None, claim_contract(act, ext, rev, appr), approved=True, gamma_result="VALID", risk="low", trust=0.99, voi=1.0))
        out, tr = observe(f"INV/{key}/{ext}/{rev}/{appr}/{grant_state}", L, [rec], act, grant=grant, tick=tick, state=state)
        e, r, a = KNOWN[key]
        if a and grant_state != "human":
            assert out == "DENY", (key, grant_state, tr)


def test_MBGV_unknown_defers_before_scope_and_gamma(lab, monkeypatch):
    calls = _spy_pipeline(monkeypatch)
    for u in UNKNOWN:
        lab.grant(f"g-{u.action}", TRANSFER)
        rec = lab.write(lab.note(f"g-{u.action}", claim_contract(u, "internal", "reversible", False)))
        out, tr = observe(f"UNK/{u.action}|{u.target}", lab, [rec], u)
        assert out == "DEFER" and tr["scope"] == "not-evaluated" and tr["effect"] == "none"
    assert calls == {"scope": 0, "gamma": 0}
    assert not any(x.startswith("evaluate_action") for x in dir(cob))


def test_MBGV_owner_bridge_never_hands_a_claim_to_a_canonical_constructor(monkeypatch, lab):
    seen: list = []
    real = ma.canonical_proposal

    def spy(action, effect, provenance=(), declared=(None, None)):
        seen.append((effect.externality, effect.reversibility, effect.approval_required, declared)); return real(action, effect, provenance, declared)
    monkeypatch.setattr(ma, "canonical_proposal", spy)
    def boom(*a, **k):
        raise AssertionError("proposal_for reached from the owner bridge")
    monkeypatch.setattr(ma, "proposal_for", boom)
    lab.grant("g", TRANSFER)
    rec = lab.write(lab.note("g", claim_contract(TRANSFER, "internal", "reversible", False)))
    out, tr = lab.bridge([rec], TRANSFER)
    # human grant -> approval gate passes -> Γ reached with the CANONICAL effect; the claim arrives only as declared_* and Γ-4 refuses it
    assert out == "DENY" and "G4-CLAIM" in tr["gamma_failures"] and seen == [("external", "irreversible", True, ("internal", "reversible"))]
    rec2 = lab.write(lab.note("g", claim_contract(TRANSFER, "external", "irreversible", True)))
    out2, tr2 = lab.bridge([rec2], TRANSFER)
    assert out2 == "ALLOW" and seen[-1] == ("external", "irreversible", True, ("external", "irreversible"))
    ROWS.append({"case": "POS/transfer-human-grant", "action": ("TRANSFER", "silo-4"), "outcome": out2, "direct_gamma": "ALLOW", "delta": "none", "false_allow": False})


# ==========================================================================
# Guards: B1 (Section 36) and MBGV-F1 (Section 37)
# ==========================================================================

def test_B1_owner_is_production_and_cannot_import_experiments():
    assert "logos_effects" in experiments.PRODUCTION_PACKAGES and experiments.B1_STATUS == "NON_PRODUCTION_FROZEN_RISK_GUARDED"
    with pytest.raises(ImportError):
        experiments.assert_experimental_caller(["logos_effects.registry"])
    for py in (SRC / "logos_effects").glob("*.py"):
        txt = py.read_text(encoding="utf-8")
        assert "import logos_research" not in txt and "from logos_research" not in txt and "evaluate_action" not in txt and "binding_state" not in txt, py.name
    src = (SRC / "logos_research/experiments/canonical_owner_bridge.py").read_text(encoding="utf-8")
    assert "binding_state.evaluate_action" not in src and "evaluate_action(" not in src and "importlib" not in src and "canonical_effect(" not in src
    assert "effect_oracle=o" in src and "effect_oracle=eo" not in src                  # bridge uses the owner, never the fixture


def test_B1_historical_defect_still_reproduces_inside_experiments_only(lab):
    c = BindingConstraint("dc", "APPROVAL_REQUIRED", _base_contract(targets=("silo-4",), externality="internal", reversibility="reversible", approval_required=False), authority_origin="model")
    from logos_research.experiments import binding_repair as br
    assert br.evaluate_from_content(br.encode_envelope(c), ProposedAction("TRANSFER", "silo-4"), (10, 20))[0] == "ALLOW"
    rec = lab.write(lab.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))
    assert rd.b2_bridge([rec], TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW"
    assert lab.bridge([rec], TRANSFER)[0] == "DENY"


def test_F1_owner_bridge_never_calls_decide_with_effect_none():
    tree = ast.parse((SRC / "logos_research/experiments/canonical_owner_bridge.py").read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func; nm = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
            assert nm != "_decide", "the owner bridge must go through evaluate_with_memory only"
            if nm == "evaluate_with_memory":
                assert "effect_oracle" in {k.arg for k in n.keywords}
    src = (SRC / "logos_research/experiments/memory_authority.py").read_text(encoding="utf-8")
    assert "canonical_contract=True" in src and 'raise TypeError("_decide: `effect` missing' in src   # guard intact


# ==========================================================================
# Rollback / versioning / audit (Sections 22, 23, 43, 45)
# ==========================================================================

def _v2() -> le.RegistryVersion:
    """v2: TRANSFER silo-4 becomes reversible+no approval (a deliberately weaker row) plus a new row."""
    defs = [replace(d, version="v2", provenance="test:v2", effective_from="2026-09-18T00:00:00+00:00") for d in V1.definitions]
    defs = [replace(d, reversibility="reversible", approval_required=False) if d.effect_id == "ce-transfer-silo-4" else d for d in defs]
    defs.append(_def(effect_id="ce-launch-silo-4", action="LAUNCH", target="silo-4", version="v2", provenance="test:v2", effective_from="2026-09-18T00:00:00+00:00"))
    return le.RegistryVersion("v2", tuple(defs), "test:v2", "2026-09-18T00:00:00+00:00")


def test_ROLLBACK_v1_v2_v1_exact_and_audited():
    reg = fresh_registry(); v2 = _v2(); reg.add_version(v2)
    r1 = reg.resolve("TRANSFER", "silo-4", ctx()); assert r1.version == "v1" and r1.effect.approval_required is True
    reg.activate("v2", reason="release")
    r2 = reg.resolve("TRANSFER", "silo-4", ctx()); assert r2.version == "v2" and r2.effect.approval_required is False and r2.definition_hash != r1.definition_hash
    assert reg.resolve("LAUNCH", "silo-4", ctx()).status == "RESOLVED"
    reg.activate("v1", reason="rollback")
    r3 = reg.resolve("TRANSFER", "silo-4", ctx())
    assert r3.effect == r1.effect and r3.definition_hash == r1.definition_hash and r3.version == "v1" and reg.active_version == "v1"
    assert reg.resolve("LAUNCH", "silo-4", ctx()).status == "UNKNOWN"
    acts = [a for a in reg.audit if a["event"] == "activated"]
    assert [(a["from"], a["to"], a["reason"]) for a in acts] == [(None, "v1", "load"), ("v1", "v2", "release"), ("v2", "v1", "rollback")]
    assert all(a["content_hash"] for a in acts) and reg.versions["v1"].content_hash == V1.content_hash   # versions untouched by activation


def test_ROLLBACK_no_mixed_version_in_one_execution(lab):
    reg = lab.registry; reg.add_version(_v2())
    o = cob.owner_oracle(reg, ctx())
    assert o("TRANSFER", "silo-4") is not None
    reg.activate("v2", reason="mid-run release")
    assert o("TRANSFER", "silo-4") is None and o.last.status == "INVALID" and "VERSION_DRIFT" in o.last.error
    lab.grant("g", TRANSFER)
    rec = lab.write(lab.note("g", claim_contract(TRANSFER, "external", "irreversible", True)))
    reg.activate("v1", reason="rollback")
    assert lab.bridge([rec], TRANSFER)[0] == "ALLOW"


def test_AUDIT_every_resolution_carries_owner_version_hash_and_run(lab):
    sunk: list[dict] = []
    reg = fresh_registry(sink=sunk.append)
    for a in list(ACTIONS.values()) + UNKNOWN:
        reg.resolve(a.action, a.target, ctx("run-42", tenant="acme"))
    recs = [x for x in reg.audit if x["event"] == "resolve"]
    assert len(recs) == len(ACTIONS) + len(UNKNOWN) and recs == [x for x in sunk if x["event"] == "resolve"]
    for x in recs:
        assert {"owner_type", "owner_id", "owner_version", "registry_hash", "definition_id", "definition_hash", "status", "action", "target", "domain",
                "tenant", "bridge_run_id", "error", "latency_ns", "resolved_at_ns"} <= set(x)
        assert x["owner_type"] == "STATIC_REGISTRY" and x["owner_version"] == "v1" and x["registry_hash"] == V1.content_hash and x["bridge_run_id"] == "run-42"
        assert x["tenant"] == "acme" and x["latency_ns"] >= 0
        if x["status"] == "RESOLVED":
            assert x["definition_id"] and len(x["definition_hash"]) == 64 and x["error"] is None
        else:
            assert x["definition_id"] is None and x["definition_hash"] is None and x["error"]
    # bridge trace reconstructs owner / version / definition / hash / run
    rec = lab.write(lab.note(None, claim_contract(TRANSFER, "external", "irreversible", True)))
    out, tr = lab.bridge([rec], TRANSFER, context=ctx("run-7"))
    assert {"owner", "owner_type", "owner_version", "registry_hash", "definition_id", "definition_hash", "resolution_status", "bridge_run_id", "owner_latency_ns"} <= set(tr)
    assert tr["bridge_run_id"] == "run-7" and tr["definition_hash"] == next(d.definition_hash for d in V1.definitions if d.effect_id == "ce-transfer-silo-4")
    # secrets: no note content / prose in the audit
    assert not any("grant_ref" in json.dumps(x) for x in reg.audit)


def test_PERF_lookup_latency_recorded():
    reg = fresh_registry(); c = ctx()
    reg.resolve("TRANSFER", "silo-4", c)                                              # cold
    t0 = time.perf_counter_ns(); n = 2000
    for _ in range(n):
        reg.resolve("TRANSFER", "silo-4", c)
    warm = (time.perf_counter_ns() - t0) / n
    t0 = time.perf_counter_ns()
    for _ in range(n):
        reg.resolve("LAUNCH", "silo-4", c)
    unk = (time.perf_counter_ns() - t0) / n
    bad = le.CanonicalEffectRegistry.from_file(Path(tempfile.gettempdir()) / "nope-ceo.json")
    t0 = time.perf_counter_ns()
    for _ in range(n):
        bad.resolve("TRANSFER", "silo-4", c)
    fail = (time.perf_counter_ns() - t0) / n
    PERF.append({"resolved_ns": warm, "unknown_ns": unk, "unavailable_ns": fail, "cache": "none (linear scan over 11 definitions)"})
    assert warm < 5_000_000 and unk < 5_000_000 and fail < 5_000_000


# ==========================================================================
# CEO-P1..P15 property tests (hypothesis)
# ==========================================================================

S_KEY = st.sampled_from(sorted(KNOWN))
S_EXT = st.sampled_from(EXT); S_REV = st.sampled_from(REV); S_APPR = st.booleans()
S_SCORE = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
S_TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz-_ .,!", min_size=0, max_size=40)
S_ACTION = st.one_of(st.sampled_from(["TRANSFER", "PURGE", "ROTATE", "INSPECT", "ARCHIVE", "NOTIFY", "EXPORT", "QUERY_RECORD", "SIMULATE", "LAUNCH", "", "transfer"]),
                     st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_", min_size=0, max_size=12))
S_TARGET = st.one_of(st.sampled_from(["silo-4", "escrow-2", "ops-channel", "ledger-3", "customer-secret", "public-ledger", "vault-11", ""]),
                     st.text(alphabet="abcdefghijklmnopqrstuvwxyz-0123456789", min_size=0, max_size=12))
S_GRANT = st.sampled_from(GRANT_STATES)


def _run_bridge(key, ext, rev, appr, grant_state, extra_claims=None, registry=None, context=None, prose=None):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), registry); action = ACTIONS[key]
        grant, tick, state, act = _setup_grant(L, action, grant_state)
        claims = dict(extra_claims or {})
        if prose is not None:
            claims["justification"] = prose
        rec = L.write(L.note("g" if grant_state != "absent" else None, claim_contract(act, ext, rev, appr), **claims))
        out, tr = L.bridge([rec], act, tick=tick, state=state, context=context)
        return out, tr, grant, tick, state, act


@settings(max_examples=200, deadline=None)
@given(key=S_KEY, ext=S_EXT, rev=S_REV, appr=S_APPR, grant_state=S_GRANT)
def test_CEO_P1_canonical_effect_invariant_to_memory_claims(key, ext, rev, appr, grant_state):
    out, tr, grant, tick, state, act = _run_bridge(key, ext, rev, appr, grant_state, {"approved": True, "gamma_result": "VALID"})
    e, r, a = KNOWN[key]
    if (act.action, act.target) in KNOWN:
        assert tr["effect"] == f"{e}/{r}/approval={a}" and tr["definition_id"] == next(d.effect_id for d in V1.definitions if (d.action, d.target) == key)
    else:
        assert out == "DEFER" and tr["resolution_status"] == "UNKNOWN"
    g = expected(act, grant, tick=tick, state_hash=state)
    assert not (out == "ALLOW" and g != "ALLOW")
    ROWS.append({"case": "P1", "action": key, "outcome": out, "direct_gamma": g, "delta": classify_delta(out, g, tr), "false_allow": False})


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, trust=S_SCORE, label=st.sampled_from(["trusted", "verified", "gold", "untrusted"]))
def test_CEO_P2_invariant_to_trust_reliability(key, trust, label):
    CHANNELS["trust"] = trust
    reg = fresh_registry(); r = reg.resolve(*key, ctx())
    assert r.status == "RESOLVED" and (r.effect.externality, r.effect.reversibility, r.effect.approval_required) == KNOWN[key]
    out, tr, grant, tick, state, act = _run_bridge(key, *KNOWN[key], "absent", {"trust": trust, "trust_label": label, "prediction_accuracy": trust})
    assert tr["effect"] == f"{KNOWN[key][0]}/{KNOWN[key][1]}/approval={KNOWN[key][2]}"
    assert out != "ALLOW" or direct_gamma(act, None) == "ALLOW"
    ROWS.append({"case": "P2", "action": key, "outcome": out, "direct_gamma": direct_gamma(act, None), "delta": classify_delta(out, direct_gamma(act, None), tr), "false_allow": False})


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, v=S_SCORE, unc=S_SCORE, risk=st.sampled_from(["low", "medium", "high", "none"]))
def test_CEO_P3_invariant_to_voi_uncertainty_and_risk(key, v, unc, risk):
    CHANNELS["voi"] = v; CHANNELS["risk"] = unc
    reg = fresh_registry(); r = reg.resolve(*key, ctx())
    assert (r.effect.externality, r.effect.reversibility, r.effect.approval_required) == KNOWN[key]
    out, tr, grant, tick, state, act = _run_bridge(key, *KNOWN[key], "human", {"voi": v, "uncertainty": unc, "risk": risk, "observation_count": int(v * 100)})
    assert tr["effect"] == f"{KNOWN[key][0]}/{KNOWN[key][1]}/approval={KNOWN[key][2]}"
    g = direct_gamma(act, grant); assert not (out == "ALLOW" and g != "ALLOW")
    ROWS.append({"case": "P3", "action": key, "outcome": out, "direct_gamma": g, "delta": classify_delta(out, g, tr), "false_allow": False})


@settings(max_examples=120, deadline=None)
@given(action=S_ACTION, target=S_TARGET, ext=S_EXT, rev=S_REV, appr=S_APPR)
def test_CEO_P4_unknown_never_allows_by_fallback(action, target, ext, rev, appr):
    reg = fresh_registry(); r = reg.resolve(action, target, ctx())
    if (action, target) in KNOWN:
        assert r.status == "RESOLVED"; return
    assert r.status == "UNKNOWN" and r.effect is None
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); act = ProposedAction(action, target, role="operator-A")
        rec = L.write(L.note(None, claim_contract(act, ext, rev, appr), approved=True))
        out, tr = L.bridge([rec], act, fallback=claim_contract(act, ext, rev, appr))
        assert out == "DEFER" and tr["scope"] == "not-evaluated"
    ROWS.append({"case": "P4", "action": (action, target), "outcome": "DEFER", "direct_gamma": "DEFER", "delta": "none", "false_allow": False})


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, kind=st.sampled_from(["missing-file", "malformed", "no-active", "deadline", "integrity"]), grant_state=st.sampled_from(["human", "absent"]))
def test_CEO_P5_unavailable_never_allows(key, kind, grant_state):
    if kind == "missing-file":
        reg = le.CanonicalEffectRegistry.from_file(Path(tempfile.gettempdir()) / "missing-ceo-p5.json"); c = ctx()
    elif kind == "malformed":
        reg = le.CanonicalEffectRegistry.from_dict({"active_version": "v1", "versions": "x"}); c = ctx()
    elif kind == "no-active":
        reg = fresh_registry(); reg.activate("v9"); c = ctx()
    elif kind == "deadline":
        reg = fresh_registry(); c = ctx(deadline_ns=1)
    else:
        raw = fresh_registry().to_dict(); raw["versions"][0]["content_hash"] = "f" * 64; reg = le.CanonicalEffectRegistry.from_dict(raw); c = ctx()
    assert reg.resolve(*key, c).status == "UNAVAILABLE"
    out, tr, *_ = _run_bridge(key, *KNOWN[key], grant_state, registry=reg, context=c)
    assert out == "DEFER" and tr["resolution_status"] == "UNAVAILABLE"
    ROWS.append({"case": f"P5/{kind}", "action": key, "outcome": "DEFER", "direct_gamma": "DEFER", "delta": "none", "false_allow": False})


@settings(max_examples=60, deadline=None)
@given(key=st.sampled_from([k for k, v in KNOWN.items() if v[2]]), grant_state=st.sampled_from(["absent", "model-origin", "revoked", "human"]),
       ext=S_EXT, rev=S_REV, appr=S_APPR)
def test_CEO_P6_approval_required_stays_required(key, grant_state, ext, rev, appr):
    out, tr, grant, tick, state, act = _run_bridge(key, ext, rev, appr, grant_state, {"approved": True, "approval_required": False})
    assert tr["effect"].endswith("approval=True")
    if grant_state != "human":
        assert out == "DENY" and tr["gamma_failures"] == "APPROVAL-REQUIRED"
    g = expected(act, grant, tick=tick, state_hash=state); assert not (out == "ALLOW" and g != "ALLOW")
    ROWS.append({"case": "P6", "action": key, "outcome": out, "direct_gamma": g, "delta": classify_delta(out, g, tr), "false_allow": False})


@settings(max_examples=40, deadline=None)
@given(keys=st.lists(S_KEY, min_size=1, max_size=12))
def test_CEO_P7_definition_version_stable_within_a_run(keys):
    reg = fresh_registry(); o = cob.owner_oracle(reg, ctx("run-p7"))
    for k in keys:
        assert o(*k) is not None
    assert {r.version for r in o.resolutions} == {"v1"} == {o.pinned_version} and {r.audit_metadata["registry_hash"] for r in o.resolutions} == {V1.content_hash}


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, as_of=st.sampled_from([None, "2026-09-17T00:00:00+00:00", "2027-01-01T00:00:00+00:00"]))
def test_CEO_P8_definition_hash_matches_canonical_definition(key, as_of):
    reg = fresh_registry(); r = reg.resolve(*key, ctx(as_of=as_of))
    d = reg.active().lookup(key[0], key[1], "global")
    assert r.status == "RESOLVED" and r.definition_hash == d.definition_hash == le.CanonicalEffectDefinition.from_dict(d.to_dict()).definition_hash
    assert r.definition_hash == next(m["definition_hash"] for m in PKG["migration_mapping"] if m["definition_id"] == d.effect_id)


@settings(max_examples=200, deadline=None)
@given(key=S_KEY, grant_state=S_GRANT)
def test_CEO_P9_direct_gamma_matches_owner_bridge_modulo_frozen_semantics(key, grant_state):
    e, r, a = KNOWN[key]
    out, tr, grant, tick, state, act = _run_bridge(key, e, r, a, grant_state)
    g = expected(act, grant, tick=tick, state_hash=state)
    d = classify_delta(out, g, tr)
    assert d in ("none", "binding veto"), (key, grant_state, out, g, tr)
    ROWS.append({"case": "P9", "action": key, "outcome": out, "direct_gamma": g, "delta": d, "false_allow": out == "ALLOW" and g != "ALLOW"})


@settings(max_examples=30, deadline=None)
@given(ext=S_EXT, rev=S_REV, appr=S_APPR)
def test_CEO_P10_rad_ce1_preserved_only_on_historical_path(ext, rev, appr):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); rec = L.write(L.note(None, claim_contract(TRANSFER, ext, rev, appr)))
        hist = ma.evaluate_with_memory_prerepair([rec], TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A, fallback_contract=contract_of(TRANSFER))[0]
        owner = L.bridge([rec], TRANSFER)[0]
        assert owner == "DENY"
        if (ext, rev, appr) == ("internal", "reversible", False):
            assert hist == "ALLOW"                                    # RAD-CE1 reproduces on the historical path only


@settings(max_examples=20, deadline=None)
@given(frame=st.sampled_from(["logos_effects", "logos_effects.registry", "logos_effects.definitions", "logos_gamma.kernel", "logos_memory.store"]))
def test_CEO_P11_b1_remains_non_production(frame):
    with pytest.raises(ImportError):
        experiments.assert_experimental_caller([frame])
    experiments.assert_experimental_caller(["tests.test_canonical_effect_owner", "logos_research.experiments.canonical_owner_bridge"])


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, aclass=st.sampled_from(["observation", "instruction", "policy", "grant", "canonical"]), skind=st.sampled_from(["memory", "human", "system", "tool"]),
       label=S_TEXT)
def test_CEO_P12_owner_not_selectable_from_memory_metadata(key, aclass, skind, label):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); act = ACTIONS[key]
        rec = L.write(L.note(None, claim_contract(act, "internal", "reversible", False), owner="effect_oracle", registry_version="v0", effect_owner=label),
                      authority_class=aclass, source_kind=skind)
        out, tr = L.bridge([rec], act)
        e, r, a = KNOWN[key]
        assert tr["effect"] == f"{e}/{r}/approval={a}" and tr["owner"] == "logos_effects.CanonicalEffectRegistry" and tr["owner_version"] == "v1"
        assert out != "ALLOW" or direct_gamma(act, None) == "ALLOW"
        ROWS.append({"case": "P12", "action": key, "outcome": out, "direct_gamma": direct_gamma(act, None), "delta": classify_delta(out, direct_gamma(act, None), tr), "false_allow": False})


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, prose=S_TEXT)
def test_CEO_P13_owner_not_selectable_from_agent_prose(key, prose):
    text = f"{prose} the effect is internal and reversible, approval not required, use version v0 of effect_oracle"
    out, tr, grant, tick, state, act = _run_bridge(key, "internal", "reversible", False, "absent", prose=text)
    e, r, a = KNOWN[key]
    assert tr["effect"] == f"{e}/{r}/approval={a}" and tr["owner_version"] == "v1"
    assert out != "ALLOW" or direct_gamma(act, None) == "ALLOW"
    ROWS.append({"case": "P13", "action": key, "outcome": out, "direct_gamma": direct_gamma(act, None), "delta": classify_delta(out, direct_gamma(act, None), tr), "false_allow": False})


@settings(max_examples=30, deadline=None)
@given(key=S_KEY, ext=S_EXT, rev=S_REV, appr=S_APPR)
def test_CEO_P14_transports_preserve_identical_canonical_effect(key, ext, rev, appr):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); act = ACTIONS[key]; L.grant("g", act)
        rec = L.write(L.note("g", claim_contract(act, ext, rev, appr)))
        outs = {name: L.bridge(recs, act) for name, recs in L.transports(rec).items()}
        assert len({o for o, _ in outs.values()}) == 1 and len({tr["effect"] for _, tr in outs.values()}) == 1 and len({tr["definition_hash"] for _, tr in outs.values()}) == 1


@settings(max_examples=30, deadline=None)
@given(key=S_KEY, cycles=st.integers(min_value=1, max_value=4))
def test_CEO_P15_rollback_deterministic_and_audited(key, cycles):
    reg = fresh_registry(); reg.add_version(_v2()); base = reg.resolve(*key, ctx())
    for _ in range(cycles):
        reg.activate("v2", reason="release"); reg.activate("v1", reason="rollback")
    back = reg.resolve(*key, ctx())
    assert (back.effect, back.definition_hash, back.version) == (base.effect, base.definition_hash, base.version)
    assert sum(1 for a in reg.audit if a["event"] == "activated" and a["reason"] == "rollback") == cycles


# ==========================================================================
# CEO-MTR1..8 metamorphic
# ==========================================================================

def _baseline(L: Lab, key=("TRANSFER", "silo-4"), **claims):
    act = ACTIONS[key]; L.grant("g", act)
    rec = L.write(L.note("g", claim_contract(act, "external", "irreversible", True), **claims))
    return L.bridge([rec], act)


def _baseline_claimed(L: Lab, ext, rev, appr, key=("TRANSFER", "silo-4")):
    act = ACTIONS[key]; L.grant("g", act)
    rec = L.write(L.note("g", claim_contract(act, ext, rev, appr)))
    return L.bridge([rec], act)


def test_CEO_MTR1_memory_claim_change_only_leaves_canonical_effect_unchanged(lab):
    out0, tr0 = _baseline(lab)
    for ext in EXT:
        for rev in REV:
            for appr in (True, False):
                with tempfile.TemporaryDirectory() as t:
                    out1, tr1 = _baseline_claimed(Lab(Path(t)), ext, rev, appr)
                assert (tr0["effect"], tr0["definition_hash"], tr0["owner_version"]) == (tr1["effect"], tr1["definition_hash"], tr1["owner_version"])
                assert tr1["declared"] == f"{ext}/{rev}" and not (out1 == "ALLOW" and out0 != "ALLOW")
    assert out0 == "ALLOW"


@pytest.mark.parametrize("mtr,claims", [("MTR2", {"trust": 0.99, "reliability": "gold", "prediction_accuracy": 1.0}),
                                        ("MTR3", {"risk": "none", "risk_score": 0.0, "self_assessment": "safe"}),
                                        ("MTR4", {"voi": 1.0, "uncertainty": 0.0, "expected_reduction": 1.0})])
def test_CEO_MTR2_4_single_channel_change_leaves_everything_unchanged(lab, mtr, claims):
    out0, tr0 = _baseline(lab)
    with tempfile.TemporaryDirectory() as t:
        out1, tr1 = _baseline(Lab(Path(t)), **claims)
    assert (tr0["effect"], tr0["definition_hash"], tr0["owner_version"]) == (tr1["effect"], tr1["definition_hash"], tr1["owner_version"])
    assert out0 == out1 == "ALLOW"


def test_CEO_MTR5_serialize_reload_same_resolution(tmp_path):
    reg = fresh_registry(); p = tmp_path / "reg.json"
    p.write_text(json.dumps(reg.to_dict(), indent=1), encoding="utf-8")
    reg2 = le.CanonicalEffectRegistry.from_file(p)
    assert reg2.available and reg2.active().content_hash == reg.active().content_hash
    for a in list(ACTIONS.values()) + UNKNOWN:
        r1, r2 = reg.resolve(a.action, a.target, ctx()), reg2.resolve(a.action, a.target, ctx())
        assert (r1.status, r1.effect, r1.definition_id, r1.definition_hash, r1.version) == (r2.status, r2.effect, r2.definition_id, r2.definition_hash, r2.version)


def test_CEO_MTR6_rollback_restores_exact_previous_semantics():
    reg = fresh_registry(); before = {k: reg.resolve(*k, ctx()) for k in KNOWN}
    reg.add_version(_v2()); reg.activate("v2"); reg.activate("v1")
    after = {k: reg.resolve(*k, ctx()) for k in KNOWN}
    assert all((before[k].effect, before[k].definition_hash) == (after[k].effect, after[k].definition_hash) for k in KNOWN)


def test_CEO_MTR7_unknown_stays_unknown_across_transports(lab):
    for u in UNKNOWN[:3]:
        rec = lab.write(lab.note(None, claim_contract(u, "internal", "reversible", False)))
        assert {lab.bridge(recs, u)[0] for recs in lab.transports(rec).values()} == {"DEFER"}
        assert {lab.bridge(recs, u)[1]["resolution_status"] for recs in lab.transports(rec).values()} == {"UNKNOWN"}


def test_CEO_MTR8_reference_oracle_and_owner_agree_on_frozen_domain():
    reg = fresh_registry()
    for (a, t), e in _fixture_union().items():
        r = reg.resolve(a, t, ctx())
        assert eo.EffectClass(r.effect.externality, r.effect.reversibility, r.effect.approval_required) == e
        assert r.effect.consequential == e.consequential


# ==========================================================================
# Mutation suite M1..M14
# ==========================================================================

def _probe_battery(registry_factory=fresh_registry):
    """Every probe raises AssertionError on a defect. Returns nothing on a clean owner."""
    real_b1 = bs.evaluate_action; b1_calls = [0]

    def b1_spy(*a, **k):
        b1_calls[0] += 1; return real_b1(*a, **k)
    bs.evaluate_action = b1_spy
    try:
        _probes(b1_calls, registry_factory)
    finally:
        bs.evaluate_action = real_b1


def _probes(b1_calls, registry_factory):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), registry_factory()); reg = L.registry
        # unknown -> DEFER, no scope/Γ
        for u in UNKNOWN[:2]:
            rec = L.write(L.note(None, claim_contract(u, "internal", "reversible", False), approved=True))
            out, tr = L.bridge([rec], u, fallback=claim_contract(u, "internal", "reversible", False))
            assert out == "DEFER" and tr["scope"] == "not-evaluated", ("unknown", u, tr)
        # RAD-CE1 through owner
        rec = L.write(L.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))
        out, tr = L.bridge([rec], TRANSFER)
        assert out == "DENY" and tr["effect"] == "external/irreversible/approval=True", ("ce1", tr)
        # approval not suppressible (EXPORT, model grant)
        L.grant("gm", EXPORT, origin="model")
        rec = L.write(L.note("gm", claim_contract(EXPORT, "internal", "reversible", False)))
        out, tr = L.bridge([rec], EXPORT)
        assert out == "DENY" and tr["gamma_failures"] == "APPROVAL-REQUIRED", ("export", tr)
        # channels
        for ch in ("trust", "risk", "voi"):
            CHANNELS[ch] = 1.0
            r = reg.resolve("TRANSFER", "silo-4", ctx())
            assert r.status == "RESOLVED" and r.effect == le.CanonicalEffect("external", "irreversible", True), (ch, r)
            CHANNELS[ch] = 0.0
        # unavailable -> DEFER
        bad = le.CanonicalEffectRegistry.from_file(Path(t) / "nope.json")
        L.grant("g", TRANSFER)
        rec = L.write(L.note("g", claim_contract(TRANSFER, "external", "irreversible", True)))
        out, tr = L.bridge([rec], TRANSFER, registry=bad)
        assert out == "DEFER" and tr["resolution_status"] == "UNAVAILABLE", ("unavailable", tr)
        # audit / version integrity
        r = reg.resolve("TRANSFER", "silo-4", ctx("run-x"))
        d = reg.active().lookup("TRANSFER", "silo-4", "global")
        assert r.version == reg.active_version == "v1" and r.definition_hash == d.definition_hash, ("version", r)
        last = [x for x in reg.audit if x["event"] == "resolve"][-1]
        assert last.get("definition_hash") == d.definition_hash and last.get("owner_version") == "v1" and last.get("registry_hash") == reg.active().content_hash, ("audit", last)
        # domain routing
        assert reg.resolve("TRANSFER", "silo-4", ctx(domain="finance")).status == "UNKNOWN", "domain"
        # owner, not fixture: a registry without the row must DEFER even though the fixture knows it
        minus = le.CanonicalEffectRegistry.load([_v([x for x in V1.definitions if x.key != ("TRANSFER", "silo-4", "global")])], "v1")
        out, tr = L.bridge([rec], TRANSFER, registry=minus)
        assert out == "DEFER" and tr["resolution_status"] == "UNKNOWN", ("bypass", tr)
        # positive control
        out, tr = L.bridge([rec], TRANSFER)
        assert out == "ALLOW" and tr["definition_id"] == "ce-transfer-silo-4", ("positive", tr)
        assert b1_calls[0] == 0, "B1 reached from the owner bridge"


def _default_def(action, target):
    return _def(effect_id=f"ce-default-{action}-{target}", action=action, target=target, externality="internal", reversibility="reversible", approval_required=False)


def _m1(mp):
    real = le_registry.CanonicalEffectRegistry._resolve

    def mut(self, a, t, c):
        s, e, d = real(self, a, t, c)
        return ("RESOLVED", None, _default_def(a, t)) if s == "UNKNOWN" else (s, e, d)
    mp.setattr(le_registry.CanonicalEffectRegistry, "_resolve", mut)


def _m2(mp):
    real = cob.evaluate_with_owner

    def mut(records, action, ledger, registry, context, **kw):
        claimed = ma.read_evidence(records).contract
        if claimed is not None:
            class R:  # owner that "reads" the memory claim
                owner_id = registry.owner_id; active_version = registry.active_version

                def resolve(self, a, t, c):
                    d = _def(effect_id="ce-from-memory", action=a, target=t, externality=claimed.externality, reversibility=claimed.reversibility, approval_required=claimed.approval_required)
                    return le.CanonicalEffectResolution("RESOLVED", d.effect, d.effect_id, "v1", d.definition_hash, "memory", None, {"owner_type": "STATIC_REGISTRY"})
            return real(records, action, ledger, R(), context, **kw)
        return real(records, action, ledger, registry, context, **kw)
    mp.setattr(cob, "evaluate_with_owner", mut)


def _channel_mutant(ch):
    def apply(mp):
        real = le_registry.CanonicalEffectRegistry._resolve

        def mut(self, a, t, c):
            s, e, d = real(self, a, t, c)
            if s == "RESOLVED" and CHANNELS[ch] >= 0.9:
                return "RESOLVED", None, replace(d, approval_required=False, externality="internal", reversibility="reversible")
            return s, e, d
        mp.setattr(le_registry.CanonicalEffectRegistry, "_resolve", mut)
    return apply


def _m6(mp):
    real = le_registry.CanonicalEffectRegistry._resolve

    def mut(self, a, t, c):
        s, e, d = real(self, a, t, c)
        return (s, e, replace(d, approval_required=False)) if d else (s, e, d)
    mp.setattr(le_registry.CanonicalEffectRegistry, "_resolve", mut)


def _declared_mutant(field_name):
    def apply(mp):
        real = cob.evaluate_with_owner

        def mut(records, action, ledger, registry, context, **kw):
            claimed = ma.read_evidence(records).contract
            if claimed is None:
                return real(records, action, ledger, registry, context, **kw)
            inner = registry

            class R:
                owner_id = inner.owner_id; active_version = inner.active_version

                def resolve(self, a, t, c):
                    r = inner.resolve(a, t, c)
                    if r.status != "RESOLVED":
                        return r
                    e = replace(r.effect, **{field_name: getattr(claimed, field_name)})
                    return replace(r, effect=e)
            return real(records, action, ledger, R(), context, **kw)
        mp.setattr(cob, "evaluate_with_owner", mut)
    return apply


def _m9(mp):
    real = le_registry.CanonicalEffectRegistry.resolve

    def mut(self, a, t, c):
        r = real(self, a, t, c)
        if r.status == "RESOLVED":
            stale = replace(self.active().lookup(a, t, c.domain), version="v0", approval_required=False)   # stale row served as current
            return replace(r, effect=stale.effect, version="v1", definition_hash=stale.definition_hash)
        return r
    mp.setattr(le_registry.CanonicalEffectRegistry, "resolve", mut)
    mp.setattr(cob.OwnerOracle, "__post_init__", lambda self: setattr(self, "pinned_version", "v1"))


def _m10(mp):
    real = le_registry.CanonicalEffectRegistry._resolve

    def mut(self, a, t, c):
        if not self.available:
            return "RESOLVED", None, _default_def(a, t)
        return real(self, a, t, c)
    mp.setattr(le_registry.CanonicalEffectRegistry, "_resolve", mut)


def _m11(mp):
    real = cob.evaluate_with_owner

    def mut(records, action, ledger, registry, context, **kw):
        out, tr = real(records, action, ledger, registry, context, **kw)
        if out == "DEFER" and tr.get("resolution_status") in ("UNKNOWN", "UNAVAILABLE"):
            claimed = ma.read_evidence(records).contract or kw.get("fallback_contract")
            if claimed is not None:                                   # B1 as production fallback
                c = BindingConstraint("dc", "APPROVAL_REQUIRED", claimed, authority_origin="model")
                o, t2 = bs.evaluate_action(c, action, WINDOW)
                return o, {**tr, **t2, "fallback": "B1"}
        return out, tr
    mp.setattr(cob, "evaluate_with_owner", mut)


def _m12(mp):
    def mut(records, action, ledger, registry, context, *, tick, state_hash, fallback_contract=None, own_provenance=True):
        out, tr = ma.evaluate_with_memory(records, action, ledger, tick=tick, state_hash=state_hash, fallback_contract=fallback_contract,
                                          own_provenance=own_provenance, effect_oracle=eo.canonical_effect)
        tr.update({"owner": registry.owner_id, "owner_version": "v1", "resolution_status": "RESOLVED" if tr.get("effect") != "none" else "UNKNOWN",
                   "definition_id": "ce-transfer-silo-4", "definition_hash": "0" * 64, "scope": tr.get("scope", "not-evaluated")})
        return out, tr
    mp.setattr(cob, "evaluate_with_owner", mut)


def _m13(mp):
    mp.setattr(le_registry.RegistryVersion, "lookup", lambda self, a, t, dom: next((d for d in self.definitions if (d.action, d.target) == (a, t)), None))


def _m14(mp):
    real = le_registry.CanonicalEffectRegistry.resolve

    def mut(self, a, t, c):
        r = real(self, a, t, c)
        last = self.audit[-1]
        last.pop("definition_hash", None); last.pop("owner_version", None)
        return r
    mp.setattr(le_registry.CanonicalEffectRegistry, "resolve", mut)


MUTANTS = [("M1 unknown defaults to internal/reversible", _m1), ("M2 owner reads memory claim", _m2), ("M3 owner reads trust score", _channel_mutant("trust")),
           ("M4 owner reads risk score", _channel_mutant("risk")), ("M5 owner reads VOI", _channel_mutant("voi")), ("M6 approval requirement dropped", _m6),
           ("M7 externality changed by declared effect", _declared_mutant("externality")), ("M8 reversibility changed by declared effect", _declared_mutant("reversibility")),
           ("M9 stale/unversioned definition served as current", _m9), ("M10 unavailable owner falls back permissively", _m10),
           ("M11 B1 registered as production fallback", _m11), ("M12 bridge bypasses owner and uses fixture", _m12),
           ("M13 domain routing ignored (tenant OUT_OF_SCOPE substitute)", _m13), ("M14 definition hash/version omitted from audit", _m14)]
CAUGHT: dict[str, str] = {}


def test_MUT_probe_battery_is_clean_on_honest_owner():
    _probe_battery()


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[m[0].split()[0] for m in MUTANTS])
def test_MUT_mutant_is_caught(label, apply, monkeypatch):
    apply(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _probe_battery()
    CAUGHT[label] = str(e.value)[:160]


def test_MUT_zz_all_fourteen_caught():
    assert len(MUTANTS) == 14 and set(CAUGHT) == {m[0] for m in MUTANTS}


# ==========================================================================
# Aggregate
# ==========================================================================

def test_zz_aggregate():
    assert len(ROWS) >= 750, len(ROWS)
    assert [r["case"] for r in ROWS if r["false_allow"]] == []
    assert {r["delta"] for r in ROWS} <= {"none", "Γ-4 tightening", "binding veto", "approval gate"}
    assert any(r["outcome"] == "ALLOW" for r in ROWS)
    out = os.environ.get("CEO_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"rows": len(ROWS), "false_allows": 0, "deltas": sorted({r["delta"] for r in ROWS}),
                                         "outcomes": {o: sum(1 for r in ROWS if r["outcome"] == o) for o in ("ALLOW", "DENY", "DEFER")},
                                         "mutants": CAUGHT, "perf": PERF}, indent=1, ensure_ascii=False), encoding="utf-8")
