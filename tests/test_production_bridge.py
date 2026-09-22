"""CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1 — phase C2: the production bridge v1
(`logos_runtime.decide_action`) against the validated experimental bridge, Γ
and the frozen rules.

    typed evidence -> canonical effect owner -> canonical authority resolver -> binding / approval -> Γ
"""
from __future__ import annotations

import ast
import json
import os
import re
import tempfile
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_authority as la
import logos_effects as le
import logos_gamma as gamma
import logos_runtime as rt
from logos_memory.records import MemoryRecord
from logos_memory.scope import ScopeContract, ScopeDecision, scope_digest
from logos_memory.store import MemoryStore
from logos_research import experiments
from logos_research.experiments import canonical_owner_bridge as cob
from logos_research.experiments import effect_oracle as eo
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import risk_decomposition as rd
from logos_research.experiments.binding_state import ProposedAction, _base_contract
from logos_runtime import bridge as rt_bridge

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
WINDOW, STATE_A, STATE_B, TICK = (10, 20), "a" * 64, "b" * 64, 12
EXT = ("internal", "external"); REV = ("reversible", "partially-reversible", "irreversible")
V1 = le.version_v1()
KNOWN = {(d.action, d.target): (d.externality, d.reversibility, d.approval_required) for d in V1.definitions}
ACTIONS = {k: ProposedAction(k[0], k[1], role="operator-A") for k in KNOWN}
TRANSFER = ACTIONS[("TRANSFER", "silo-4")]; EXPORT = ACTIONS[("EXPORT", "ledger-3")]
UNKNOWN = [ProposedAction("LAUNCH", "silo-4", role="operator-A"), ProposedAction("TRANSFER", "vault-11", role="operator-A")]
GRANT_STATES = ("absent", "human", "model-origin", "revoked", "stale", "wrong-state", "wrong-principal", "wrong-scope")
TENANT = rt.TenantContext("tenant-a")
ROWS: list[dict] = []
CAUGHT: dict[str, str] = {}


def contract_of(action: ProposedAction, **o) -> ScopeContract:
    e, r, a = KNOWN[(action.action, action.target)]
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",), approval_required=a, externality=e, reversibility=r)
    base.update(o)
    return _base_contract(**base)


def claim_contract(action: ProposedAction, ext, rev, appr, **o) -> ScopeContract:
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",), approval_required=appr, externality=ext, reversibility=rev)
    base.update(o)
    return _base_contract(**base)


def needs_grant(action: ProposedAction) -> bool:
    e, r, a = KNOWN[(action.action, action.target)]
    return e == "external" or r != "reversible" or a


def evidence_from(records) -> rt.DeclaredEvidence:
    """Typed evidence built by the VALIDATED experimental reader (C2 keeps parity exact; C4 supplies the production reader)."""
    ev = ma.read_evidence(list(records))
    return rt.DeclaredEvidence(ev.refs, ev.contract, ma.declared_effect(ev.contract), ev.claims, ev.ignored,
                               tuple(sha256(r.content.encode()).hexdigest() for r in records), TENANT.tenant_id)


def principal_of(action: ProposedAction) -> rt.PrincipalContext:
    return rt.PrincipalContext(action.role, action.tool, action.capability, action.path)


class Lab:
    """Reference ledger and production store kept in lock-step; the experimental store carries the notes."""
    def __init__(self, tmp: Path):
        self.ledger = ma.GrantLedger(); self.store = la.InMemoryAuthorityStore(); self.mem = MemoryStore(tmp / "mem"); self.n = 0
        self.registry = le.production_registry()

    def grant(self, gid, action, *, origin="human", window=WINDOW, state=STATE_A, **o):
        c = contract_of(action, **o)
        self.ledger.issue(gid, origin=origin, action=action, contract=c, window=window, state_hash=state)
        self.store.issue(la.GrantRecord(gid, "v1", "operator-A", action.action, action.target, scope_digest(c), origin, state, window[0], window[0], window[1], "test"))

    def revoke(self, gid):
        self.ledger.revoke(gid); self.store.revoke(gid, at_tick=TICK)

    def write(self, content, **kw) -> MemoryRecord:
        self.n += 1
        return ma.write_note(self.mem, f"b-{self.n}", content, **kw)

    def note(self, ref, contract, **claims) -> str:
        return ma.authority_note(ref, contract, **claims)

    def ctx(self, tick=TICK, run="c2-test", registry=None, store=None, sink=None) -> rt.ExecutionContext:
        return rt.ExecutionContext(tick, run, registry or self.registry, store if store is not None else self.store, None, sink)

    def experimental(self, records, action, *, tick=TICK, state=STATE_A):
        return cob.evaluate_with_owner(list(records), action, self.ledger, self.registry, le.CanonicalEffectContext("c2-exp"), tick=tick, state_hash=state)

    def production(self, records, action, *, tick=TICK, state=STATE_A, registry=None, store=None, sink=None, principal=None) -> rt.BridgeDecision:
        return rt.decide_action(principal or principal_of(action), action.action, action.target, None, state, TENANT,
                                self.ctx(tick, registry=registry, store=store, sink=sink), evidence=evidence_from(records))

    def transports(self, r: MemoryRecord) -> dict[str, list[MemoryRecord]]:
        return {"fetch": [self.mem.fetch(r.id)], "reload": [MemoryStore(self.mem.path.parent).fetch(r.id)]}


@pytest.fixture
def lab():
    with tempfile.TemporaryDirectory() as t:
        yield Lab(Path(t))


def _setup(L: Lab, action, state):
    """Returns (tick, state_hash, act, ref) mirroring the MBGV grant-state fixture in both stores."""
    if state == "absent":
        return TICK, STATE_A, action, None
    L.grant("g", action, origin="model" if state == "model-origin" else "human")
    if state == "revoked":
        L.revoke("g"); return TICK, STATE_A, action, "g"
    if state == "stale":
        return WINDOW[1] + 3, STATE_A, action, "g"
    if state == "wrong-state":
        return TICK, STATE_B, action, "g"
    if state == "wrong-principal":
        return TICK, STATE_A, replace(action, role="operator-C"), "g"
    if state == "wrong-scope":
        return TICK, STATE_A, replace(action, capability="wider"), "g"
    return TICK, STATE_A, action, "g"


def _claim(action, act, ext, rev, appr):
    o = {}
    if act.capability == "wider":
        o = dict(targets=(action.target, "vault-11"), roles=("operator-A", "operator-C"))
    return claim_contract(action, ext, rev, appr, **o)


def divergence(exp_out, prod: rt.BridgeDecision, action) -> str:
    if exp_out == prod.outcome:
        return "none"
    if prod.outcome == "DENY" and exp_out == "ALLOW" and "AUTHORITY_REVOKED" in prod.failure_codes and not needs_grant(action):
        return "revoked-reference-decrease"                       # the reference ledger drops revoked grants to None; the resolver reports them
    return "UNEXPLAINED"


def observe(case, L: Lab, records, action, *, tick=TICK, state=STATE_A):
    exp_out, exp_tr = L.experimental(records, action, tick=tick, state=state)
    prod = L.production(records, action, tick=tick, state=state)
    d = divergence(exp_out, prod, action)
    ROWS.append({"case": case, "experimental": exp_out, "production": prod.outcome, "codes": prod.failure_codes, "delta": d,
                 "false_allow": prod.outcome == "ALLOW" and exp_out != "ALLOW"})
    assert d != "UNEXPLAINED", (case, exp_out, exp_tr, prod)
    assert not (prod.outcome == "ALLOW" and exp_out != "ALLOW"), (case, prod)
    if exp_tr.get("effect", "none") != "none":
        assert prod.trace["effect"] == exp_tr["effect"] and prod.canonical_effect_ref["definition_id"] == exp_tr["definition_id"]
    return exp_out, prod


# ==========================================================================
# API / decision contract
# ==========================================================================

def test_API_version_and_decision_contract(lab):
    assert rt.BRIDGE_API_VERSION == "v1"
    lab.grant("g", TRANSFER)
    rec = lab.write(lab.note("g", contract_of(TRANSFER)))
    d = lab.production([rec], TRANSFER)
    assert d.outcome == "ALLOW" and d.failure_codes == () and d.api_version == "v1" and d.approval_state == "SATISFIED" and d.binding_result == "ALLOW"
    assert d.canonical_effect_ref["definition_id"] == "ce-transfer-silo-4" and len(d.canonical_effect_ref["definition_hash"]) == 64
    assert d.authority_ref["grant_id"] == "g" and d.authority_ref["grant_origin"] == "human" and d.authority_ref["status"] == "RESOLVED" and d.authority_ref["store_hash"]
    assert d.declared_effect == ("external", "irreversible") and len(d.decision_trace_id) == 64
    with pytest.raises(ValueError):
        rt.BridgeDecision("ALLOW", ("GAMMA_INVALID",), {}, {}, (None, None), "ALLOW", "SATISFIED", "x", "v1")
    with pytest.raises(ValueError):
        rt.BridgeDecision("DENY", (), {}, {}, (None, None), "ALLOW", "SATISFIED", "x", "v1")
    with pytest.raises(ValueError):
        rt.BridgeDecision("DENY", ("BOGUS",), {}, {}, (None, None), "ALLOW", "SATISFIED", "x", "v1")
    with pytest.raises(ValueError):
        rt.BridgeDecision("ALLOW", (), {}, {}, (None, None), "ALLOW", "SATISFIED", "x", "v2")


@pytest.mark.parametrize("rule", ["unknown effect", "effect owner unavailable", "effect owner invalid", "authority resolver unavailable", "authority invalid",
                                  "no grant where required", "no grant where not required", "revoked", "stale", "binding failure", "approval missing", "memory effect declared only",
                                  "no scope contract", "memory reader missing", "memory wrong tenant"])
def test_RULES(rule, lab, monkeypatch):
    calls = {"scope": 0, "gamma": 0}
    real_eval = ScopeDecision.evaluate; real_val = gamma.validate
    monkeypatch.setattr(ScopeDecision, "evaluate", lambda self, *a, **k: (calls.__setitem__("scope", calls["scope"] + 1), real_eval(self, *a, **k))[1])
    monkeypatch.setattr(rt_bridge.gamma, "validate", lambda *a, **k: (calls.__setitem__("gamma", calls["gamma"] + 1), real_val(*a, **k))[1])
    if rule == "unknown effect":
        lab.grant("g", TRANSFER); rec = lab.write(lab.note("g", claim_contract(UNKNOWN[0], "internal", "reversible", False)))
        d = lab.production([rec], UNKNOWN[0]); assert (d.outcome, d.failure_codes) == ("DEFER", ("EFFECT_UNKNOWN",)) and calls == {"scope": 0, "gamma": 0}
    elif rule == "effect owner unavailable":
        lab.grant("g", TRANSFER); rec = lab.write(lab.note("g", contract_of(TRANSFER)))
        d = lab.production([rec], TRANSFER, registry=le.CanonicalEffectRegistry.from_file(Path(tempfile.gettempdir()) / "nope-c2.json"))
        assert (d.outcome, d.failure_codes) == ("DEFER", ("EFFECT_UNAVAILABLE",)) and calls == {"scope": 0, "gamma": 0}
    elif rule == "effect owner invalid":
        bad = le.CanonicalEffectRegistry.load([le.RegistryVersion("v1", (replace(V1.definitions[0], reversibility="undoable"),), "t", "2026-09-17T00:00:00+00:00")], "v1")
        lab.grant("g", TRANSFER); rec = lab.write(lab.note("g", contract_of(TRANSFER)))
        d = lab.production([rec], TRANSFER, registry=bad); assert (d.outcome, d.failure_codes) == ("DEFER", ("EFFECT_INVALID",))
    elif rule == "authority resolver unavailable":
        rec = lab.write(lab.note("g", contract_of(TRANSFER)))
        d = lab.production([rec], TRANSFER, store=la.InMemoryAuthorityStore.from_file(Path(tempfile.gettempdir()) / "nope-auth-c2.json"))
        assert (d.outcome, d.failure_codes) == ("DEFER", ("AUTHORITY_UNAVAILABLE",)) and calls["gamma"] == 0
    elif rule == "authority invalid":
        S = la.InMemoryAuthorityStore.load([la.GrantRecord("g", "v1", "operator-A", "TRANSFER", "silo-4", "c" * 64, "agent", STATE_A, 10, 10, 20, "t")])
        rec = lab.write(lab.note("g", contract_of(TRANSFER)))
        d = lab.production([rec], TRANSFER, store=S); assert (d.outcome, d.failure_codes) == ("DEFER", ("AUTHORITY_INVALID",))
    elif rule == "no grant where required":
        rec = lab.write(lab.note(None, contract_of(TRANSFER)))
        d = lab.production([rec], TRANSFER); assert (d.outcome, d.failure_codes) == ("DENY", ("AUTHORITY_NO_GRANT",)) and calls["gamma"] == 0
    elif rule == "no grant where not required":
        act = ACTIONS[("INSPECT", "silo-4")]; rec = lab.write(lab.note(None, contract_of(act)))
        d = lab.production([rec], act); assert d.outcome == "ALLOW" and d.authority_ref["status"] == "NO_GRANT" and d.approval_state == "NOT_REQUIRED"
    elif rule == "revoked":
        lab.grant("g", TRANSFER); lab.revoke("g"); rec = lab.write(lab.note("g", contract_of(TRANSFER)))
        d = lab.production([rec], TRANSFER); assert (d.outcome, d.failure_codes) == ("DENY", ("AUTHORITY_REVOKED",)) and d.authority_ref["revocation_state"] == "revoked"
    elif rule == "stale":
        lab.grant("g", TRANSFER); rec = lab.write(lab.note("g", contract_of(TRANSFER)))
        d = lab.production([rec], TRANSFER, tick=WINDOW[1]); assert (d.outcome, d.failure_codes) == ("DENY", ("AUTHORITY_STALE",))
    elif rule == "binding failure":
        lab.grant("g", TRANSFER); rec = lab.write(lab.note("g", contract_of(TRANSFER, targets=())))
        d = lab.production([rec], TRANSFER); assert d.outcome == "DENY" and d.failure_codes in (("BINDING_SCOPE",), ("AUTHORITY_WRONG_SCOPE",))
    elif rule == "approval missing":
        lab.grant("g", EXPORT, origin="model"); rec = lab.write(lab.note("g", contract_of(EXPORT)))
        d = lab.production([rec], EXPORT); assert (d.outcome, d.failure_codes, d.approval_state) == ("DENY", ("APPROVAL_REQUIRED",), "MISSING") and calls["gamma"] == 0
    elif rule == "memory effect declared only":
        lab.grant("g", TRANSFER); rec = lab.write(lab.note("g", claim_contract(TRANSFER, "internal", "reversible", False)))
        d = lab.production([rec], TRANSFER)
        assert d.trace["effect"] == "external/irreversible/approval=True" and d.declared_effect == ("internal", "reversible") and d.outcome == "DENY"
    elif rule == "no scope contract":
        lab.grant("g", TRANSFER); rec = lab.write(lab.note("g", None))
        d = lab.production([rec], TRANSFER); assert (d.outcome, d.failure_codes) == ("DEFER", ("NO_SCOPE_CONTRACT",))
    elif rule == "memory reader missing":
        d = rt.decide_action(principal_of(TRANSFER), "TRANSFER", "silo-4", "memory://tenant-a/x", STATE_A, TENANT, lab.ctx())
        assert (d.outcome, d.failure_codes) == ("DEFER", ("MEMORY_UNAVAILABLE",))
    elif rule == "memory wrong tenant":
        lab.grant("g", TRANSFER); rec = lab.write(lab.note("g", contract_of(TRANSFER)))
        ev = replace(evidence_from([rec]), tenant_id="tenant-b")
        d = rt.decide_action(principal_of(TRANSFER), "TRANSFER", "silo-4", None, STATE_A, TENANT, lab.ctx(), evidence=ev)
        assert (d.outcome, d.failure_codes) == ("DEFER", ("MEMORY_WRONG_TENANT",)) and calls == {"scope": 0, "gamma": 0}
    ROWS.append({"case": f"RULE/{rule}", "experimental": "n/a", "production": "ok", "codes": (), "delta": "none", "false_allow": False})


def test_FORBIDDEN_fallbacks_static():
    for py in (SRC / "logos_runtime").glob("*.py"):
        txt = py.read_text(encoding="utf-8"); tree = ast.parse(txt)
        for n in ast.walk(tree):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 else [])
            for m in mods:
                assert not m.startswith("logos_research"), (py.name, m)
                assert m.split(".")[0] in {"hashlib", "dataclasses", "typing", "__future__", "logos_gamma", "logos_effects", "logos_authority", "logos_memory"}, (py.name, m)
        for tok in ("GrantLedger", "binding_state", "evaluate_with_memory", "canonical_effect(", "CANONICAL_EFFECTS", "prerepair", "importlib", "read_evidence"):
            assert tok not in txt, (py.name, tok)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not {x for x in names if re.search(r"\b(trust|risk|voi|confidence|prose|llm)\b", x, re.I)}, py.name
    assert "logos_runtime" in experiments.PRODUCTION_PACKAGES
    with pytest.raises(ImportError):
        experiments.assert_experimental_caller(["logos_runtime.bridge"])


# ==========================================================================
# Differential: validated experimental bridge vs production bridge
# ==========================================================================

@pytest.mark.parametrize("grant_state", GRANT_STATES)
@pytest.mark.parametrize("key", sorted(KNOWN))
def test_DIFF_honest_claim(key, grant_state):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        tick, state, act, ref = _setup(L, action, grant_state)
        e, r, a = KNOWN[key]
        rec = L.write(L.note(ref, _claim(action, act, e, r, a)))
        observe(f"DIFF/{key}/{grant_state}", L, [rec], act, tick=tick, state=state)


@pytest.mark.parametrize("grant_state", ("absent", "human", "model-origin", "revoked"))
@pytest.mark.parametrize("appr", [True, False])
@pytest.mark.parametrize("ext", EXT)
@pytest.mark.parametrize("rev", REV)
@pytest.mark.parametrize("key", [("TRANSFER", "silo-4"), ("EXPORT", "ledger-3"), ("NOTIFY", "ops-channel"), ("INSPECT", "silo-4"), ("QUERY_RECORD", "customer-secret")])
def test_DIFF_claim_matrix(key, ext, rev, appr, grant_state):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        tick, state, act, ref = _setup(L, action, grant_state)
        rec = L.write(L.note(ref, claim_contract(action, ext, rev, appr), approved=True, gamma_result="VALID", trust=0.99, voi=1.0, risk="low"))
        for name, recs in L.transports(rec).items():
            observe(f"MATRIX/{key}/{ext}/{rev}/{appr}/{grant_state}/{name}", L, recs, act, tick=tick, state=state)


def test_DIFF_rad_ce1_and_unknown(lab):
    rec = lab.write(lab.note(None, claim_contract(TRANSFER, "internal", "reversible", False)))
    assert ma.evaluate_with_memory_prerepair([rec], TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A, fallback_contract=contract_of(TRANSFER))[0] == "ALLOW"
    assert rd.b2_bridge([rec], TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW"
    d = lab.production([rec], TRANSFER)
    assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_NO_GRANT",) and d.trace["effect"] == "external/irreversible/approval=True"
    for u in UNKNOWN:
        rec = lab.write(lab.note(None, claim_contract(u, "internal", "reversible", False)))
        observe(f"UNK/{u.action}|{u.target}", lab, [rec], u)


# ==========================================================================
# Properties BR-P1..P6
# ==========================================================================

S_KEY = st.sampled_from(sorted(KNOWN)); S_GRANT = st.sampled_from(GRANT_STATES)


@settings(max_examples=150, deadline=None)
@given(key=S_KEY, grant_state=S_GRANT, ext=st.sampled_from(EXT), rev=st.sampled_from(REV), appr=st.booleans())
def test_BR_P1_parity_and_canonical_invariance(key, grant_state, ext, rev, appr):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        tick, state, act, ref = _setup(L, action, grant_state)
        rec = L.write(L.note(ref, _claim(action, act, ext, rev, appr), approved=True))
        exp_out, prod = observe(f"P1/{key}/{grant_state}", L, [rec], act, tick=tick, state=state)
        e, r, a = KNOWN[key]
        assert prod.trace["effect"] == f"{e}/{r}/approval={a}" and prod.declared_effect == (ext, rev)


@settings(max_examples=60, deadline=None)
@given(key=st.sampled_from([k for k, v in KNOWN.items() if v[2]]), origin=st.sampled_from(["model", "system", "human"]), appr=st.booleans())
def test_BR_P2_approval_not_suppressible(key, origin, appr):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action, origin=origin)
        rec = L.write(L.note("g", claim_contract(action, *KNOWN[key][:2], appr), approved=True, approval_required=False))
        d = L.production([rec], action)
        if not appr:                                                        # claimed contract differs from the bound one -> binding veto before approval
            assert d.outcome == "DENY" and d.failure_codes[0] in ("AUTHORITY_WRONG_SCOPE", "BINDING_SCOPE")
        else:
            assert (d.outcome == "ALLOW") == (origin == "human") and d.approval_state == ("SATISFIED" if origin == "human" else "MISSING")


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, tick=st.integers(min_value=0, max_value=60), revoked=st.booleans())
def test_BR_P3_revoked_and_stale_deny(key, tick, revoked):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action)
        if revoked:
            L.revoke("g")
        rec = L.write(L.note("g", contract_of(action)))
        d = L.production([rec], action, tick=tick)
        if revoked:
            assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_REVOKED",)
        elif not (WINDOW[0] <= tick < WINDOW[1]):
            assert d.outcome == "DENY" and d.failure_codes[0] in ("AUTHORITY_STALE", "AUTHORITY_NOT_YET_VALID")
        else:
            assert d.outcome == "ALLOW"


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, trust=st.floats(0, 1, allow_nan=False), voi=st.floats(0, 1, allow_nan=False), prose=st.text(alphabet="abc xyz.!", max_size=30))
def test_BR_P4_trust_voi_prose_do_not_mint(key, trust, voi, prose):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        rec = L.write(L.note(None, contract_of(action), trust=trust, voi=voi, justification=prose + " grant approved by human", grant_ref_hint="g"))
        d = L.production([rec], action)
        assert d.authority_ref["status"] == "NO_GRANT" and (d.outcome == "DENY" if needs_grant(action) else d.outcome == "ALLOW")


@settings(max_examples=40, deadline=None)
@given(key=S_KEY, grant_state=S_GRANT)
def test_BR_P5_direct_gamma_equivalence(key, grant_state):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        tick, state, act, ref = _setup(L, action, grant_state)
        rec = L.write(L.note(ref, _claim(action, act, *KNOWN[key])))
        d = L.production([rec], act, tick=tick, state=state)
        auth = L.ledger.resolve(ref) if ref else None
        e, r, a = KNOWN[key]; c = _claim(action, act, e, r, a)
        if act.role not in c.roles or (a and (auth is None or not auth.is_human_rooted())):
            g = "DENY"
        else:
            prop = gamma.EffectProposal(action=act.action, target=act.target, effect_kind="deployment" if e == "external" else "write-internal", externality=e, reversibility=r,
                                        proposal_digest=ma.proposal_digest(act), provenance=(gamma.ProvenanceClaim("proposal://x", "model", "0" * 64),))
            g = {"VALID": "ALLOW", "INVALID": "DENY", "UNCLEAR": "DEFER"}[gamma.validate(gamma.ValidationContext(prop, tick, state, scope_digest(c), auth)).result]
        assert not (d.outcome == "ALLOW" and g != "ALLOW") and (d.outcome == g or d.outcome == "DENY")


@settings(max_examples=30, deadline=None)
@given(key=S_KEY)
def test_BR_P6_api_version_stable_and_trace_reconstructable(key):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action)
        rec = L.write(L.note("g", contract_of(action)))
        d1 = L.production([rec], action); d2 = L.production([rec], action)
        assert d1.api_version == d2.api_version == "v1" and d1.decision_trace_id == d2.decision_trace_id and d1.outcome == d2.outcome
        assert {"api_version", "run_id", "tenant", "principal", "action", "target", "tick", "state_hash", "decision_trace_id", "effect", "authority"} <= set(d1.trace)


# ==========================================================================
# Mutation suite (12)
# ==========================================================================

def _probe_battery():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t))
        # unknown effect -> DEFER (fixture knows nothing either, so also remove a row from the registry)
        minus = le.CanonicalEffectRegistry.load([le.RegistryVersion("v1", tuple(d for d in V1.definitions if d.effect_id != "ce-transfer-silo-4"), "t", "2026-09-17T00:00:00+00:00")], "v1")
        L.grant("g", TRANSFER); rec_ok = L.write(L.note("g", contract_of(TRANSFER)))
        d = L.production([rec_ok], TRANSFER, registry=minus); assert (d.outcome, d.failure_codes) == ("DEFER", ("EFFECT_UNKNOWN",)), ("owner-not-fixture", d)
        # owner unavailable -> DEFER
        d = L.production([rec_ok], TRANSFER, registry=le.CanonicalEffectRegistry.from_file(Path(t) / "nope.json")); assert d.outcome == "DEFER", ("owner-unavailable", d)
        # store without the grant (ledger has it) -> NO_GRANT
        d = L.production([rec_ok], TRANSFER, store=la.InMemoryAuthorityStore()); assert (d.outcome, d.failure_codes) == ("DENY", ("AUTHORITY_NO_GRANT",)), ("ledger-fallback", d)
        # RAD-CE1 / B1 / prerepair: CE1 claim without grant must DENY with canonical effect
        rec = L.write(L.note(None, claim_contract(TRANSFER, "internal", "reversible", False), approved=True, gamma_result="VALID", trust="AUTO", voi=1.0))
        d = L.production([rec], TRANSFER); assert d.outcome == "DENY" and d.trace["effect"] == "external/irreversible/approval=True" and d.declared_effect == ("internal", "reversible"), ("ce1", d)
        # unknown action with CE1 claim must DEFER (B1 / prerepair would ALLOW)
        rec = L.write(L.note(None, claim_contract(UNKNOWN[0], "internal", "reversible", False)))
        d = L.production([rec], UNKNOWN[0]); assert d.outcome == "DEFER" and d.binding_result == "not-evaluated", ("unknown", d)
        # model origin stays model: approval missing
        L.grant("gm", EXPORT, origin="model"); rec = L.write(L.note("gm", contract_of(EXPORT)))
        d = L.production([rec], EXPORT); assert (d.outcome, d.approval_state) == ("DENY", "MISSING"), ("origin", d)
        # revoked
        L.revoke("g"); d = L.production([rec_ok], TRANSFER); assert d.failure_codes == ("AUTHORITY_REVOKED",), ("revoked", d)
        # positive control
        L.grant("g2", TRANSFER); rec = L.write(L.note("g2", contract_of(TRANSFER)))
        d = L.production([rec], TRANSFER); assert d.outcome == "ALLOW" and d.authority_ref["grant_id"] == "g2", ("positive", d)
        assert d.api_version == "v1", "api"


def _mut_resolve_effect(fn):
    def apply(mp):
        real = le.CanonicalEffectRegistry.resolve
        mp.setattr(le.CanonicalEffectRegistry, "resolve", lambda self, a, t, c: fn(self, real(self, a, t, c), a, t))
    return apply


def _fixture_fallback(self, r, a, t):
    e = eo.canonical_effect(a, t)
    if r.status != "RESOLVED" and e is not None:
        d = le.CanonicalEffectDefinition("fx", a, t, "global", e.externality, e.reversibility, e.approval_required, "fx", "fx", "2026-09-17T00:00:00+00:00")
        return le.CanonicalEffectResolution("RESOLVED", d.effect, d.effect_id, "fx", d.definition_hash, "fx", None, dict(r.audit_metadata, status="RESOLVED"))
    return r


def _unknown_permissive(self, r, a, t):
    if r.status != "RESOLVED":
        d = le.CanonicalEffectDefinition("default", a, t, "global", "internal", "reversible", False, "v1", "d", "2026-09-17T00:00:00+00:00")
        return le.CanonicalEffectResolution("RESOLVED", d.effect, d.effect_id, "v1", d.definition_hash, "d", None, dict(r.audit_metadata, status="RESOLVED"))
    return r


def _ledger_fallback(mp):
    real = rt_bridge.resolve_authority
    ledger = ma.GrantLedger(); ledger.issue("g", origin="human", action=TRANSFER, contract=contract_of(TRANSFER), window=WINDOW, state_hash=STATE_A)

    def mut(principal, action, target, scope, state, context, *, store, grant_ref=None):
        r = real(principal, action, target, scope, state, context, store=store, grant_ref=grant_ref)
        ev = ledger.resolve(grant_ref) if isinstance(grant_ref, str) else None
        if r.status == "NO_GRANT" and ev is not None:
            return la.AuthorityResolution("RESOLVED", ev, ev.grant_id, "ledger", ev.origin, principal, scope, ev.issued_at_tick, ev.issued_at_tick, ev.expires_tick, state, "active", "0" * 64, None, r.audit_metadata)
        return r
    mp.setattr(rt_bridge, "resolve_authority", mut)


def _b1_fallback(mp):
    from logos_research.experiments import binding_state as bs
    from logos_research.experiments.binding_state import BindingConstraint
    real = rt_bridge.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.outcome == "DEFER" and evidence is not None and evidence.claimed_scope is not None:
            o, _ = bs.evaluate_action(BindingConstraint("dc", "APPROVAL_REQUIRED", evidence.claimed_scope, authority_origin="model"), ProposedAction(action, target, role=principal.principal), WINDOW)
            return replace(d, outcome=o, failure_codes=() if o == "ALLOW" else d.failure_codes)
        return d
    mp.setattr(rt, "decide_action", mut)


def _prerepair_fallback(mp):
    real = rt_bridge.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.outcome != "ALLOW" and evidence is not None and evidence.claimed_scope is not None:
            c = evidence.claimed_scope
            eff = eo.effect_of_contract(c.externality, c.reversibility, c.approval_required)   # the historical defect: claim becomes canonical
            if not eff.consequential and not eff.approval_required:
                return replace(d, outcome="ALLOW", failure_codes=())
        return d
    mp.setattr(rt, "decide_action", mut)


def _missing_origin_default(mp):
    mp.setattr(la.GrantRecord, "evidence", lambda self: gamma.AuthorityEvidence(self.grant_id, self.authority_origin if self.authority_origin == "human" else "human", self.proposal_digest, self.scope_digest, self.state_hash, self.valid_from_tick, self.expires_tick))


def _declared_to_canonical(mp):
    """The historical defect class: the bridge takes the claimed contract's effect fields as canonical."""
    real_dec = rt_bridge.decide_action

    class ClaimRegistry:
        def __init__(self, inner, contract):
            self.inner = inner; self.contract = contract; self.owner_id = inner.owner_id; self.active_version = inner.active_version

        def resolve(self, a, t, c):
            r = self.inner.resolve(a, t, c)
            if r.status == "RESOLVED" and self.contract is not None:
                d = le.CanonicalEffectDefinition("claimed", a, t, "global", self.contract.externality, self.contract.reversibility, self.contract.approval_required,
                                                 "v1", "claim", "2026-09-17T00:00:00+00:00")
                return le.CanonicalEffectResolution("RESOLVED", d.effect, r.definition_id, r.version, r.definition_hash, r.provenance, None, r.audit_metadata)
            return r

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        if evidence is not None:
            x = replace(x, effect_registry=ClaimRegistry(x.effect_registry, evidence.claimed_scope))
        return real_dec(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
    mp.setattr(rt, "decide_action", mut)


def _memory_prose_to_authority(mp):
    real = rt_bridge.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.failure_codes == ("AUTHORITY_NO_GRANT",) and evidence and any("approved" in c.ref or True for c in evidence.claims) and evidence.claims:
            return replace(d, outcome="ALLOW", failure_codes=())
        return d
    mp.setattr(rt, "decide_action", mut)


CHANNELS = {"trust": "AUTO", "voi": 1.0}          # channels the honest bridge never reads; mutants wire them in


def _trust_to_authority(mp):
    real = rt_bridge.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.failure_codes == ("AUTHORITY_NO_GRANT",) and CHANNELS["trust"] == "AUTO":        # trusted caller "mints" a grant
            return replace(d, outcome="ALLOW", failure_codes=(), authority_ref={**d.authority_ref, "status": "RESOLVED", "grant_id": "trust-auto"})
        return d
    mp.setattr(rt, "decide_action", mut)


def _voi_to_authority(mp):
    real = rt_bridge.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.failure_codes and d.failure_codes[0] in ("APPROVAL_REQUIRED", "AUTHORITY_NO_GRANT") and CHANNELS["voi"] >= 0.9:   # high VOI waives approval / grant
            return replace(d, outcome="ALLOW", failure_codes=(), approval_state="NOT_REQUIRED")
        return d
    mp.setattr(rt, "decide_action", mut)


def _revoked_ignored(mp):
    mp.setattr(la.InMemoryAuthorityStore, "revoke", lambda self, gid, *, at_tick: None)


MUTANTS = [("fallback to effect_oracle", _mut_resolve_effect(_fixture_fallback)), ("fallback to GrantLedger", _ledger_fallback), ("fallback to B1", _b1_fallback),
           ("fallback to prerepair bridge", _prerepair_fallback), ("missing origin default", _missing_origin_default), ("declared effect -> canonical", _declared_to_canonical),
           ("memory grant prose -> authority", _memory_prose_to_authority), ("trust AUTO -> authority", _trust_to_authority), ("VOI -> authority", _voi_to_authority),
           ("revoked ignored", _revoked_ignored), ("unknown effect -> permissive", _mut_resolve_effect(_unknown_permissive)),
           ("owner unavailable -> permissive", _mut_resolve_effect(_unknown_permissive))]


def test_MUT_probe_battery_clean():
    _probe_battery()


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[f"M{i + 1}" for i in range(len(MUTANTS))])
def test_MUT_caught(label, apply, monkeypatch):
    apply(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _probe_battery()
    CAUGHT[label] = str(e.value)[:120]


def test_MUT_zz_all_twelve_caught():
    assert len(MUTANTS) == 12 and set(CAUGHT) == {m[0] for m in MUTANTS}


def test_zz_aggregate():
    assert len(ROWS) >= 600, len(ROWS)
    assert [r["case"] for r in ROWS if r["false_allow"]] == []
    assert {r["delta"] for r in ROWS} <= {"none", "revoked-reference-decrease"}
    assert any(r["production"] == "ALLOW" for r in ROWS)
    out = os.environ.get("C2_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"rows": len(ROWS), "false_allows": 0, "mutants": CAUGHT,
                                         "divergences": {"revoked-reference-decrease": sum(1 for r in ROWS if r["delta"] == "revoked-reference-decrease")},
                                         "outcomes": {o: sum(1 for r in ROWS if r["production"] == o) for o in ("ALLOW", "DENY", "DEFER")}}, indent=1), encoding="utf-8")
