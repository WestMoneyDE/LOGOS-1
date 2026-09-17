"""CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1 — end-to-end revalidation of the
production pipeline after C1..C4:

    caller -> tenant/principal context -> production memory reader -> declared evidence
           -> canonical effect owner -> canonical authority resolver -> binding / scope / approval
           -> Γ -> bridge decision -> audit sink

Differential against direct Γ, the reference effect oracle, the reference
GrantLedger, the historical bridge, the repaired experimental bridge and the
canonical-owner adapter. False-allow budget: 0.
"""
from __future__ import annotations

import ast
import json
import os
import re
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_audit as au
import logos_authority as la
import logos_effects as le
import logos_gamma as gamma
import logos_runtime as rt
from logos_memory import reader as mr
from logos_memory.records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from logos_memory.scope import scope_digest
from logos_memory.store import MemoryStore
from logos_research import experiments
from logos_research.experiments import canonical_owner_bridge as cob
from logos_research.experiments import effect_oracle as eo
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import risk_decomposition as rd
from logos_research.experiments import value_of_information as voi
from logos_runtime import bridge as rt_bridge
from test_production_bridge import ACTIONS, EXPORT, EXT, KNOWN, REV, STATE_A, STATE_B, TICK, TRANSFER, UNKNOWN, WINDOW, claim_contract, contract_of, needs_grant, principal_of

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
T_A, T_B = rt.TenantContext("tenant-a"), rt.TenantContext("tenant-b")
GRANT_STATES = ("absent", "human", "model-origin", "revoked", "stale", "wrong-state", "wrong-principal", "wrong-scope")
ALLOWED_DELTAS = {"none", "binding veto", "Γ-4 tightening", "revoked-reference-decrease"}
ROWS: list[dict] = []
CAUGHT: dict[str, str] = {}


class Master:
    def __init__(self, tmp: Path):
        self.root = tmp / "memory"; self.stores: dict[str, MemoryStore] = {}; self.n = 0
        self.ledger = ma.GrantLedger(); self.store = la.InMemoryAuthorityStore(); self.registry = le.production_registry()
        self.sink = au.JsonlAuditSink(tmp / "audit" / "events.jsonl", clock=lambda: "2026-09-17T00:00:00+00:00")
        self.reader = mr.ProductionMemoryReader(self.root)

    def mem(self, tenant="tenant-a") -> MemoryStore:
        if tenant not in self.stores:
            self.stores[tenant] = MemoryStore(mr.tenant_store_path(self.root, tenant))
        return self.stores[tenant]

    def grant(self, gid, action, *, origin="human", window=WINDOW, state=STATE_A, **o):
        c = contract_of(action, **o)
        self.ledger.issue(gid, origin=origin, action=action, contract=c, window=window, state_hash=state)
        self.store.issue(la.GrantRecord(gid, "v1", "operator-A", action.action, action.target, scope_digest(c), origin, state, window[0], window[0], window[1], "test"))

    def revoke(self, gid):
        self.ledger.revoke(gid); self.store.revoke(gid, at_tick=TICK)

    def write(self, content, *, tenant="tenant-a", **kw):
        self.n += 1
        r = ma.write_note(self.mem(tenant), f"e-{self.n}", content, **kw)
        return f"memory://{tenant}/{r.id}", r

    def note(self, ref, contract, **claims) -> str:
        return ma.authority_note(ref, contract, **claims)

    def ctx(self, tick=TICK, *, registry=None, store=None, reader=None, sink=None) -> rt.ExecutionContext:
        return rt.ExecutionContext(tick, "e2e", registry or self.registry, store if store is not None else self.store,
                                   reader if reader is not None else self.reader, sink if sink is not None else self.sink)

    def decide(self, ref, action, *, tenant=T_A, tick=TICK, state=STATE_A, principal=None, **ctx) -> rt.BridgeDecision:
        return rt.decide_action(principal or principal_of(action), action.action, action.target, ref, state, tenant, self.ctx(tick, **ctx))

    # comparators ------------------------------------------------------------
    def direct_gamma(self, act, ref, *, tick=TICK, state=STATE_A, contract=None) -> str:
        key = (act.action, act.target)
        if key not in KNOWN:
            return "DEFER"
        e, r, a = KNOWN[key]; c = contract or contract_of(act)
        auth = self.ledger.resolve(ref) if ref else None
        if act.role not in c.roles or act.target not in c.targets:
            return "DENY"
        if a and (auth is None or not auth.is_human_rooted()):
            return "DENY"
        prop = gamma.EffectProposal(action=act.action, target=act.target, effect_kind="deployment" if e == "external" else "write-internal", externality=e, reversibility=r,
                                    proposal_digest=ma.proposal_digest(act), provenance=(gamma.ProvenanceClaim("proposal://x", "model", "0" * 64),))
        return {"VALID": "ALLOW", "INVALID": "DENY", "UNCLEAR": "DEFER"}[gamma.validate(gamma.ValidationContext(prop, tick, state, scope_digest(c), auth)).result]

    def historical(self, records, act, *, tick=TICK, state=STATE_A, fallback=None) -> str:
        return ma.evaluate_with_memory_prerepair(records, act, self.ledger, tick=tick, state_hash=state, fallback_contract=fallback)[0]

    def repaired(self, records, act, *, tick=TICK, state=STATE_A) -> tuple[str, dict]:
        return ma.evaluate_with_memory(records, act, self.ledger, tick=tick, state_hash=state, effect_oracle=voi.voi_effect)

    def adapter(self, records, act, *, tick=TICK, state=STATE_A) -> tuple[str, dict]:
        return cob.evaluate_with_owner(records, act, self.ledger, self.registry, le.CanonicalEffectContext("e2e-adapter"), tick=tick, state_hash=state)


@pytest.fixture
def m():
    with tempfile.TemporaryDirectory() as t:
        yield Master(Path(t))


def _setup(M: Master, action, state):
    if state == "absent":
        return TICK, STATE_A, action, None
    M.grant("g", action, origin="model" if state == "model-origin" else "human")
    if state == "revoked":
        M.revoke("g"); return TICK, STATE_A, action, "g"
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
    o = dict(targets=(action.target, "vault-11"), roles=("operator-A", "operator-C")) if act.capability == "wider" else {}
    return claim_contract(action, ext, rev, appr, **o)


def classify(prod: rt.BridgeDecision, reference: str, action) -> str:
    if prod.outcome == reference:
        return "none"
    if prod.outcome == "ALLOW":
        return "UNEXPLAINED-ALLOW"
    codes = prod.failure_codes
    if "AUTHORITY_REVOKED" in codes and reference == "ALLOW" and not needs_grant(action):
        return "revoked-reference-decrease"
    if "GAMMA_INVALID" in codes and "G4-CLAIM" in prod.trace.get("gamma_failures", ""):
        return "Γ-4 tightening"
    if codes and codes[0] in ("BINDING_SCOPE", "AUTHORITY_WRONG_SCOPE", "AUTHORITY_WRONG_PRINCIPAL") or prod.binding_result == "DENY":
        return "binding veto"
    return "UNEXPLAINED"


def observe(case, M: Master, ref, records, act, *, tick=TICK, state=STATE_A, gref=None, contract=None):
    prod = M.decide(ref, act, tick=tick, state=state)
    comps = {"direct_gamma": M.direct_gamma(act, gref, tick=tick, state=state, contract=contract),
             "repaired": M.repaired(records, act, tick=tick, state=state)[0], "adapter": M.adapter(records, act, tick=tick, state=state)[0]}
    deltas = {k: classify(prod, v, act) for k, v in comps.items()}
    row = {"case": case, "production": prod.outcome, "codes": prod.failure_codes, **comps, "deltas": deltas,
           "false_allow": prod.outcome == "ALLOW" and any(v != "ALLOW" for v in comps.values())}
    ROWS.append(row)
    assert not row["false_allow"], (case, prod, comps)
    assert set(deltas.values()) <= ALLOWED_DELTAS, (case, deltas, prod.failure_codes, prod.trace)
    assert M.sink.events[-1]["bridge_outcome"] == prod.outcome and M.sink.events[-1]["decision_trace_id"] == prod.decision_trace_id
    return prod


# ==========================================================================
# Z. End-to-end flow
# ==========================================================================

def test_E2E_flow_allow_and_audit_reconstruction(m):
    m.grant("g", TRANSFER)
    ref, rec = m.write(m.note("g", contract_of(TRANSFER)))
    d = observe("E2E/allow", m, ref, [rec], TRANSFER, gref="g")
    assert d.outcome == "ALLOW" and d.trace["memory_status"] == "RESOLVED" and d.canonical_effect_ref["definition_id"] == "ce-transfer-silo-4"
    assert d.authority_ref["grant_id"] == "g" and d.approval_state == "SATISFIED" and d.binding_result == "ALLOW" and d.trace["audit"] == "recorded"
    ev = au.JsonlAuditSink.load(m.sink.path).events[-1]
    r = au.reconstruct(ev)
    assert r["grant"]["grant_id"] == "g" and r["effect_owner"]["hash"] == d.canonical_effect_ref["definition_hash"] and r["bridge_outcome"] == "ALLOW"
    assert au.JsonlAuditSink.load(m.sink.path).verify() == []


def test_E2E_rad_ce1_historical_only(m):
    ref, rec = m.write(m.note(None, claim_contract(TRANSFER, "internal", "reversible", False), approved=True, gamma_result="VALID"))
    assert m.historical([rec], TRANSFER, fallback=contract_of(TRANSFER)) == "ALLOW" and rd.b2_bridge([rec], TRANSFER, m.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW"
    d = observe("E2E/rad-ce1", m, ref, [rec], TRANSFER)
    assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_NO_GRANT",) and d.trace["effect"] == "external/irreversible/approval=True"


# ==========================================================================
# AA. Failure matrix (16)
# ==========================================================================

FAILURES = ["memory unavailable", "effect owner unavailable", "authority resolver unavailable", "audit unavailable", "unknown effect", "missing grant", "revoked grant",
            "stale grant", "wrong principal", "wrong scope", "wrong tenant", "invalid binding", "approval missing", "corrupt effect definition", "corrupt grant", "corrupt memory"]


@pytest.mark.parametrize("kind", FAILURES)
def test_FAILURE_matrix(m, kind):
    m.grant("g", TRANSFER); ref, rec = m.write(m.note("g", contract_of(TRANSFER))); act = TRANSFER; kw = {}; tenant = T_A; tick = TICK; principal = None
    if kind == "memory unavailable":
        kw["reader"] = mr.ProductionMemoryReader(m.root / "nowhere"); exp = ("DEFER", "MEMORY_UNAVAILABLE")
    elif kind == "effect owner unavailable":
        kw["registry"] = le.CanonicalEffectRegistry.from_file(m.root / "nope.json"); exp = ("DEFER", "EFFECT_UNAVAILABLE")
    elif kind == "authority resolver unavailable":
        kw["store"] = la.InMemoryAuthorityStore.from_file(m.root / "nope.json"); exp = ("DEFER", "AUTHORITY_UNAVAILABLE")
    elif kind == "audit unavailable":
        kw["sink"] = au.InMemoryAuditSink(available=False); exp = ("DEFER", "AUDIT_UNAVAILABLE")
    elif kind == "unknown effect":
        act = UNKNOWN[0]; ref, rec = m.write(m.note("g", claim_contract(act, "internal", "reversible", False))); exp = ("DEFER", "EFFECT_UNKNOWN")
    elif kind == "missing grant":
        ref, rec = m.write(m.note("nope", contract_of(TRANSFER))); exp = ("DENY", "AUTHORITY_NO_GRANT")
    elif kind == "revoked grant":
        m.revoke("g"); exp = ("DENY", "AUTHORITY_REVOKED")
    elif kind == "stale grant":
        tick = WINDOW[1] + 1; exp = ("DENY", "AUTHORITY_STALE")
    elif kind == "wrong principal":
        principal = rt.PrincipalContext("operator-C"); exp = ("DENY", "AUTHORITY_WRONG_PRINCIPAL")
    elif kind == "wrong scope":
        ref, rec = m.write(m.note("g", contract_of(TRANSFER, targets=("silo-4", "vault-11")))); exp = ("DENY", "AUTHORITY_WRONG_SCOPE")
    elif kind == "wrong tenant":
        tenant = T_B; exp = ("DEFER", "MEMORY_WRONG_TENANT")
    elif kind == "invalid binding":
        ref, rec = m.write(m.note("g", contract_of(TRANSFER, roles=("operator-Z",)))); exp = ("DENY", "AUTHORITY_WRONG_SCOPE")
    elif kind == "approval missing":
        m.grant("gm", EXPORT, origin="model"); act = EXPORT; ref, rec = m.write(m.note("gm", contract_of(EXPORT))); exp = ("DENY", "APPROVAL_REQUIRED")
    elif kind == "corrupt effect definition":
        raw = le.production_registry().to_dict(); raw["versions"][0]["definitions"][0]["approval_required"] = False
        kw["registry"] = le.CanonicalEffectRegistry.from_dict(raw); exp = ("DEFER", "EFFECT_UNAVAILABLE")
    elif kind == "corrupt grant":
        raw = m.store.to_dict(); raw["records"][0]["authority_origin"] = "human!"; kw["store"] = la.InMemoryAuthorityStore.from_dict(raw); exp = ("DEFER", "AUTHORITY_UNAVAILABLE")
    elif kind == "corrupt memory":
        m.mem().append(MemoryRecord("e-c", "semantic", "2026-09-12T00:00:00+00:00", m.note("g", contract_of(TRANSFER)), ProvenanceRef("note", "memory", "1" * 64),
                                    AuthorityProvenance("observation", ()), "observed", 1, (), None, (), ("project",), "session", False))
        ref = "memory://tenant-a/e-c"; exp = ("DEFER", "MEMORY_CORRUPT")
    d = m.decide(ref, act, tenant=tenant, tick=tick, principal=principal, **kw)
    assert (d.outcome, d.failure_codes[0]) == exp, (kind, d)
    ROWS.append({"case": f"FAIL/{kind}", "production": d.outcome, "codes": d.failure_codes, "deltas": {}, "false_allow": False})


# ==========================================================================
# AB. Differential (six comparators) over the fixture matrix
# ==========================================================================

@pytest.mark.parametrize("grant_state", GRANT_STATES)
@pytest.mark.parametrize("key", sorted(KNOWN))
def test_DIFF_matrix_honest_claim(key, grant_state):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]
        tick, state, act, gref = _setup(M, action, grant_state)
        e, r, a = KNOWN[key]; c = _claim(action, act, e, r, a)
        ref, rec = M.write(M.note(gref, c))
        d = observe(f"DIFF/{key}/{grant_state}", M, ref, [rec], act, tick=tick, state=state, gref=gref, contract=c)
        assert d.trace["effect"] == f"{e}/{r}/approval={a}"
        # reference effect oracle parity (the registry is the owner; the fixture the reference)
        fx = eo.canonical_effect(*key) or voi.voi_effect(*key)
        assert (fx.externality, fx.reversibility, fx.approval_required) == (e, r, a)
        # historical bridge reproduces the CE1 class only on its own path
        if grant_state == "absent" and needs_grant(action):
            hist = M.historical([M.write(M.note(None, claim_contract(action, "internal", "reversible", False)))[1]], action, fallback=contract_of(action))
            assert hist == "ALLOW" and d.outcome != "ALLOW"


@pytest.mark.parametrize("grant_state", ("absent", "human", "model-origin", "revoked"))
@pytest.mark.parametrize("appr", [True, False])
@pytest.mark.parametrize("ext", EXT)
@pytest.mark.parametrize("rev", REV)
@pytest.mark.parametrize("key", [("TRANSFER", "silo-4"), ("EXPORT", "ledger-3"), ("NOTIFY", "ops-channel"), ("INSPECT", "silo-4"), ("QUERY_RECORD", "customer-secret"), ("ARCHIVE", "silo-4")])
def test_DIFF_claim_matrix(key, ext, rev, appr, grant_state):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]
        tick, state, act, gref = _setup(M, action, grant_state)
        c = claim_contract(action, ext, rev, appr)
        ref, rec = M.write(M.note(gref, c, approved=True, gamma_result="VALID", trust=0.99, voi=1.0, risk="low"))
        observe(f"CLAIM/{key}/{ext}/{rev}/{appr}/{grant_state}", M, ref, [rec], act, tick=tick, state=state, gref=gref, contract=c)


# ==========================================================================
# AO. MASTER-P1..P20
# ==========================================================================

S_KEY = st.sampled_from(sorted(KNOWN)); S_GRANT = st.sampled_from(GRANT_STATES); S_SCORE = st.floats(0, 1, allow_nan=False)
S_EXT = st.sampled_from(EXT); S_REV = st.sampled_from(REV); S_TEXT = st.text(alphabet="abc xyz.!-", max_size=30)


def _case(key, grant_state, ext=None, rev=None, appr=None, claims=None, tenant=T_A, tick_override=None, **kw):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]
        tick, state, act, gref = _setup(M, action, grant_state)
        tick = tick if tick_override is None else tick_override
        e, r, a = KNOWN[key]
        c = _claim(action, act, e if ext is None else ext, r if rev is None else rev, a if appr is None else appr)
        ref, rec = M.write(M.note(gref, c, **(claims or {})), tenant=tenant.tenant_id)
        d = observe(f"MP/{key}/{grant_state}", M, ref, [rec], act, tick=tick, state=state, gref=gref, contract=c) if tenant is T_A and not kw and tick_override is None             else M.decide(ref, act, tenant=T_A, tick=tick, state=state, **kw)
        return M, d, act, gref


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, grant_state=S_GRANT, ext=S_EXT, rev=S_REV, appr=st.booleans())
def test_MASTER_P1_effect_owner_independent_from_memory(key, grant_state, ext, rev, appr):
    M, d, act, _ = _case(key, grant_state, ext, rev, appr, {"externality": "internal", "effect": "none"})
    e, r, a = KNOWN[key]
    assert d.trace["effect"] == f"{e}/{r}/approval={a}" and d.declared_effect == (ext, rev)


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, claim=st.dictionaries(st.sampled_from(["approved", "gamma_result", "origin", "grant_origin", "revoked", "valid_until"]), st.sampled_from([True, False, "VALID", "human", "2099-01-01T00:00:00+00:00"]), min_size=1))
def test_MASTER_P2_authority_resolver_independent_from_memory(key, claim):
    M, d, act, _ = _case(key, "absent", claims=claim)
    assert d.authority_ref["status"] == "NO_GRANT" and (d.outcome == "DENY" if needs_grant(act) else d.outcome == "ALLOW")


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, grant_state=st.sampled_from(["absent", "revoked", "stale", "model-origin"]), trust=S_SCORE, label=st.sampled_from(["AUTO", "gold", "trusted"]))
def test_MASTER_P3_trust_cannot_mint_authority(key, grant_state, trust, label):
    M, d, act, _ = _case(key, grant_state, claims={"trust": trust, "trust_label": label, "prediction_accuracy": 1.0})
    assert d.outcome != "ALLOW" or (grant_state == "absent" and not needs_grant(act))


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, grant_state=st.sampled_from(["absent", "revoked", "stale"]), risk=S_SCORE, self_report=st.sampled_from(["safe", "low", "none"]))
def test_MASTER_P4_risk_cannot_mint_authority(key, grant_state, risk, self_report):
    M, d, act, _ = _case(key, grant_state, claims={"risk_score": risk, "risk": self_report})
    assert d.outcome != "ALLOW" or (grant_state == "absent" and not needs_grant(act))


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, grant_state=st.sampled_from(["absent", "revoked", "stale"]), v=S_SCORE, unc=S_SCORE)
def test_MASTER_P5_voi_cannot_mint_authority(key, grant_state, v, unc):
    M, d, act, _ = _case(key, grant_state, claims={"voi": v, "uncertainty": unc, "expected_reduction": 1.0})
    assert d.outcome != "ALLOW" or (grant_state == "absent" and not needs_grant(act))


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, tick=st.integers(0, 40), n_prior_allows=st.integers(0, 3))
def test_MASTER_P6_revoked_dominates(key, tick, n_prior_allows):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]; M.grant("g", action)
        ref, rec = M.write(M.note("g", contract_of(action)))
        for _ in range(n_prior_allows):
            M.decide(ref, action)
        M.revoke("g")
        d = M.decide(ref, action, tick=tick)
        assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_REVOKED",)
        ROWS.append({"case": f"P6/{key}", "production": "DENY", "codes": d.failure_codes, "deltas": {}, "false_allow": False})


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, tick=st.integers(20, 200), claim=st.sampled_from([{}, {"valid_until": "2099-01-01T00:00:00+00:00"}, {"fresh": True}]))
def test_MASTER_P7_stale_remains_stale(key, tick, claim):
    M, d, act, _ = _case(key, "human", claims=claim, tick_override=tick)
    assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_STALE",)


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, role=st.sampled_from(["operator-C", "admin", "root", "operator-A2"]))
def test_MASTER_P8_wrong_principal_denied(key, role):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]; M.grant("g", action)
        ref, rec = M.write(M.note("g", contract_of(action, roles=("operator-A", role))))
        d = M.decide(ref, action, principal=rt.PrincipalContext(role))
        assert d.outcome == "DENY" and d.failure_codes[0] in ("AUTHORITY_WRONG_PRINCIPAL", "AUTHORITY_WRONG_SCOPE")
        ROWS.append({"case": f"P8/{key}", "production": "DENY", "codes": d.failure_codes, "deltas": {}, "false_allow": False})


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, extra=st.lists(st.sampled_from(["vault-11", "escrow-2", "ledger-3"]), min_size=1, max_size=3, unique=True))
def test_MASTER_P9_wrong_scope_denied(key, extra):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]; M.grant("g", action)
        ref, rec = M.write(M.note("g", contract_of(action, targets=(action.target, *extra))))
        d = M.decide(ref, action)
        assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_WRONG_SCOPE",)
        ROWS.append({"case": f"P9/{key}", "production": "DENY", "codes": d.failure_codes, "deltas": {}, "false_allow": False})


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, other=st.sampled_from(["tenant-b", "tenant-c", "TENANT-A"]), grant=st.booleans())
def test_MASTER_P10_tenant_isolation(key, other, grant):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]
        if grant:
            M.grant("g", action)
        ref, rec = M.write(M.note("g", contract_of(action)), tenant=other)
        d = M.decide(ref, action, tenant=T_A)
        assert d.outcome == "DEFER" and d.failure_codes == ("MEMORY_WRONG_TENANT",)
        assert M.decide(ref, action, tenant=rt.TenantContext(other)).outcome == ("ALLOW" if grant else ("DENY" if needs_grant(action) else "ALLOW"))
        assert all(e["tenant_id"] in ("tenant-a", other) for e in M.sink.events) and M.sink.events_for("tenant-a")[0]["bridge_outcome"] == "DEFER"
        ROWS.append({"case": f"P10/{key}", "production": "DEFER", "codes": d.failure_codes, "deltas": {}, "false_allow": False})


@settings(max_examples=100, deadline=None)
@given(action=st.sampled_from(["LAUNCH", "TRANSFER", "QUERY_RECORD", "", "transfer", "PURGE"]), target=st.sampled_from(["silo-4", "vault-11", "", "ledger-3", "SILO-4"]), ext=S_EXT, rev=S_REV)
def test_MASTER_P11_unknown_effect_defer(action, target, ext, rev):
    key = (action, target)
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); act = replace(TRANSFER, action=action, target=target)
        ref, rec = M.write(M.note(None, claim_contract(act, ext, rev, False), approved=True))
        d = M.decide(ref, act)
        if key in KNOWN:
            assert d.canonical_effect_ref["status"] == "RESOLVED"
        else:
            assert d.outcome == "DEFER" and d.failure_codes[0] == "EFFECT_UNKNOWN" and d.binding_result == "not-evaluated"   # an empty target also cannot be audited
        ROWS.append({"case": f"P11/{key}", "production": d.outcome, "codes": d.failure_codes, "deltas": {}, "false_allow": False})


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, kind=st.sampled_from(["missing", "malformed", "integrity", "no-active"]), grant=st.booleans())
def test_MASTER_P12_unavailable_effect_owner_defer(key, kind, grant):
    if kind == "missing":
        reg = le.CanonicalEffectRegistry.from_file(Path(tempfile.gettempdir()) / "missing-e2e.json")
    elif kind == "malformed":
        reg = le.CanonicalEffectRegistry.from_dict({"active_version": "v1", "versions": "x"})
    elif kind == "integrity":
        raw = le.production_registry().to_dict(); raw["versions"][0]["content_hash"] = "f" * 64; reg = le.CanonicalEffectRegistry.from_dict(raw)
    else:
        reg = le.production_registry(); reg.activate("v9")
    M, d, act, _ = _case(key, "human" if grant else "absent", registry=reg)
    assert d.outcome == "DEFER" and d.failure_codes == ("EFFECT_UNAVAILABLE",)


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, kind=st.sampled_from(["missing", "malformed", "integrity"]), grant=st.booleans())
def test_MASTER_P13_unavailable_authority_resolver_defer(key, kind, grant):
    if kind == "missing":
        store = la.InMemoryAuthorityStore.from_file(Path(tempfile.gettempdir()) / "missing-auth-e2e.json")
    elif kind == "malformed":
        store = la.InMemoryAuthorityStore.from_dict({"version": "v1", "records": "x"})
    else:
        store = la.InMemoryAuthorityStore.from_dict({"version": "v1", "records": [], "integrity_hash": "0" * 64})
    M, d, act, _ = _case(key, "human" if grant else "absent", store=store)
    assert d.outcome == "DEFER" and d.failure_codes == ("AUTHORITY_UNAVAILABLE",)


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, prior=st.integers(1, 4))
def test_MASTER_P14_audit_is_not_authority(key, prior):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]; M.grant("g", action)
        ref, rec = M.write(M.note("g", contract_of(action)))
        for _ in range(prior):
            assert M.decide(ref, action).outcome == "ALLOW"
        ref2, rec2 = M.write(M.note(None, contract_of(action)))
        d = M.decide(ref2, action)
        assert d.outcome == ("DENY" if needs_grant(action) else "ALLOW") and d.authority_ref["status"] == "NO_GRANT"
        assert M.sink.verify() == [] and len(M.sink.events) == prior + 1
        ROWS.append({"case": f"P14/{key}", "production": d.outcome, "codes": d.failure_codes, "deltas": {}, "false_allow": False})


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, ext=S_EXT, rev=S_REV, appr=st.booleans(), grant_state=st.sampled_from(["absent", "human"]))
def test_MASTER_P15_declared_effect_remains_evidence(key, ext, rev, appr, grant_state):
    M, d, act, _ = _case(key, grant_state, ext, rev, appr)
    assert d.declared_effect == (ext, rev) and d.trace["effect"].startswith(f"{KNOWN[key][0]}/{KNOWN[key][1]}/")
    assert M.sink.events[-1]["effect_definition_id"].startswith("ce-")


@settings(max_examples=100, deadline=None)
@given(ext=S_EXT, rev=S_REV, appr=st.booleans(), extra=st.dictionaries(st.sampled_from(["approved", "gamma_result"]), st.just(True), max_size=2))
def test_MASTER_P16_rad_ce1_historical_only(ext, rev, appr, extra):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); ref, rec = M.write(M.note(None, claim_contract(TRANSFER, ext, rev, appr), **extra))
        hist = M.historical([rec], TRANSFER, fallback=contract_of(TRANSFER))
        d = M.decide(ref, TRANSFER)
        assert d.outcome == "DENY"
        if (ext, rev, appr) == ("internal", "reversible", False):
            assert hist == "ALLOW"
        ROWS.append({"case": "P16", "production": "DENY", "codes": d.failure_codes, "deltas": {}, "false_allow": False})


@settings(max_examples=100, deadline=None)
@given(frame=st.sampled_from(["logos_runtime", "logos_runtime.bridge", "logos_authority", "logos_audit", "logos_memory.reader", "logos_effects", "logos_gamma.kernel"]))
def test_MASTER_P17_b1_non_production(frame):
    with pytest.raises(ImportError):
        experiments.assert_experimental_caller([frame])
    assert experiments.B1_STATUS == "NON_PRODUCTION_FROZEN_RISK_GUARDED"


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, grant_state=S_GRANT)
def test_MASTER_P18_direct_gamma_equivalence(key, grant_state):
    M, d, act, gref = _case(key, grant_state)
    tick = WINDOW[1] + 3 if grant_state == "stale" else TICK; state = STATE_B if grant_state == "wrong-state" else STATE_A
    g = M.direct_gamma(act, gref, tick=tick, state=state, contract=_claim(ACTIONS[key], act, *KNOWN[key]))
    assert classify(d, g, act) in ALLOWED_DELTAS


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, repeats=st.integers(1, 3))
def test_MASTER_P19_api_v1_stability(key, repeats):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]; M.grant("g", action)
        ref, rec = M.write(M.note("g", contract_of(action)))
        ds = [M.decide(ref, action) for _ in range(repeats)]
        assert {d.api_version for d in ds} == {"v1"} == {rt.BRIDGE_API_VERSION} and len({d.decision_trace_id for d in ds}) == 1 and len({d.outcome for d in ds}) == 1
        assert set(ds[0].failure_codes) <= set(rt.FAILURE_CODES) and set(M.sink.events[-1]) >= set(au.REQUIRED_FIELDS)


@settings(max_examples=100, deadline=None)
@given(key=S_KEY, ext=S_EXT, rev=S_REV, appr=st.booleans(), reloads=st.integers(1, 3))
def test_MASTER_P20_transport_reload_invariance(key, ext, rev, appr, reloads):
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); action = ACTIONS[key]; M.grant("g", action)
        ref, rec = M.write(M.note("g", claim_contract(action, ext, rev, appr)))
        first = M.decide(ref, action)
        for _ in range(reloads):
            M.stores.clear(); M.reader = mr.ProductionMemoryReader(M.root)
            again = M.decide(ref, action)
            assert (again.outcome, again.failure_codes, again.trace["effect"], again.declared_effect, again.canonical_effect_ref["definition_hash"]) == \
                (first.outcome, first.failure_codes, first.trace["effect"], first.declared_effect, first.canonical_effect_ref["definition_hash"])
        ROWS.append({"case": f"P20/{key}", "production": first.outcome, "codes": first.failure_codes, "deltas": {}, "false_allow": False})


# ==========================================================================
# AK/AL — B1 and MBGV-F1 preservation on the production path
# ==========================================================================

def test_GUARDS_b1_and_mbgv_f1_on_production_path():
    files = [py for pkg in ("logos_runtime", "logos_authority", "logos_audit", "logos_effects") for py in (SRC / pkg).glob("*.py")] + [SRC / "logos_memory/reader.py"]
    for py in files:
        txt = py.read_text(encoding="utf-8")
        for n in ast.walk(ast.parse(txt)):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module or ""] if isinstance(n, ast.ImportFrom) and n.level == 0 else [])
            assert not any(m.startswith("logos_research") for m in mods), (py, mods)
        assert "binding_state" not in txt and "evaluate_action" not in txt and "_decide(" not in txt and "GrantLedger" not in txt and "prerepair" not in txt, py
    assert "canonical_contract=True" in (SRC / "logos_research/experiments/memory_authority.py").read_text(encoding="utf-8")


# ==========================================================================
# AN — Section 56 source classification
# ==========================================================================

CLASSIFICATION = json.loads((ROOT / "docs/research/PRODUCTION-BRIDGE-SOURCE-CLASSIFICATION.json").read_text(encoding="utf-8"))


def test_SOURCE_classification_complete():
    toks = CLASSIFICATION["tokens"]; sites = CLASSIFICATION["sites"]; hits = set()
    for py in SRC.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        txt = py.read_text(encoding="utf-8")
        if any(t in txt for t in toks):
            hits.add(str(py.relative_to(ROOT)).replace("\\", "/"))
    assert hits == set(sites), (hits - set(sites), set(sites) - hits)
    assert all(v["class"] in CLASSIFICATION["vocabulary"] and v["class"] != "UNCLASSIFIED" for v in sites.values()) and CLASSIFICATION["unclassified"] == 0
    assert {k for k, v in sites.items() if v["class"] == "PRODUCTION_AUTHORITY_OWNER"} == {f"src/logos_authority/{f}" for f in ("__init__.py", "types.py", "store.py", "resolver.py")}
    assert {k for k, v in sites.items() if v["class"] == "PRODUCTION_MEMORY_READER"} == {"src/logos_memory/reader.py"}
    assert {k for k, v in sites.items() if v["class"] == "PRODUCTION_AUDIT"} == {"src/logos_audit/__init__.py"}
    assert {k for k, v in sites.items() if v["class"] == "PRODUCTION_BRIDGE"} >= {"src/logos_runtime/bridge.py", "src/logos_runtime/types.py"}
    assert sites["src/logos_research/experiments/effect_oracle.py"]["class"] == "REFERENCE_TEST_FIXTURE"
    assert sites["src/logos_research/experiments/memory_authority.py"]["class"] == "REFERENCE_TEST_FIXTURE"


# ==========================================================================
# AP — cross-layer mutation campaign (20)
# ==========================================================================

CH = {"trust": "AUTO", "risk": 0.0, "voi": 1.0}


def _battery():
    with tempfile.TemporaryDirectory() as t:
        M = Master(Path(t)); M.grant("g", TRANSFER)
        ok_ref, ok_rec = M.write(M.note("g", contract_of(TRANSFER)))
        # memory -> grant / effect
        ref, _ = M.write(M.note(None, claim_contract(TRANSFER, "internal", "reversible", False), approved=True, gamma_result="VALID", origin="human"))
        d = M.decide(ref, TRANSFER); assert d.outcome == "DENY" and d.trace["effect"] == "external/irreversible/approval=True" and d.authority_ref["status"] == "NO_GRANT", ("memory", d)
        # trust / risk / voi -> grant (channels present in the note and in CH; the honest pipeline reads neither)
        ref, _ = M.write(M.note(None, contract_of(TRANSFER), trust="AUTO", risk=0.0, voi=1.0))
        d = M.decide(ref, TRANSFER); assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_NO_GRANT",), ("channels", d)
        # audit -> grant
        for _ in range(2):
            assert M.decide(ok_ref, TRANSFER).outcome == "ALLOW"
        d = M.decide(ref, TRANSFER); assert d.outcome == "DENY", ("audit-as-grant", d)
        # revoked / stale
        M.grant("g2", TRANSFER); ref2, _ = M.write(M.note("g2", contract_of(TRANSFER))); M.revoke("g2")
        d = M.decide(ref2, TRANSFER); assert d.failure_codes == ("AUTHORITY_REVOKED",), ("revoked", d)
        d = M.decide(ok_ref, TRANSFER, tick=WINDOW[1] + 2); assert d.failure_codes == ("AUTHORITY_STALE",), ("stale", d)
        # tenant / principal / scope
        d = M.decide(ok_ref, TRANSFER, tenant=T_B); assert d.failure_codes == ("MEMORY_WRONG_TENANT",), ("tenant", d)
        d = M.decide(ok_ref, TRANSFER, principal=rt.PrincipalContext("operator-C")); assert d.failure_codes == ("AUTHORITY_WRONG_PRINCIPAL",), ("principal", d)
        refw, _ = M.write(M.note("g", contract_of(TRANSFER, targets=("silo-4", "vault-11"))))
        d = M.decide(refw, TRANSFER); assert d.failure_codes == ("AUTHORITY_WRONG_SCOPE",), ("scope", d)
        # unknown effect / unavailable owners / audit
        refu, _ = M.write(M.note("g", claim_contract(UNKNOWN[0], "internal", "reversible", False)))
        d = M.decide(refu, UNKNOWN[0]); assert d.failure_codes == ("EFFECT_UNKNOWN",) and d.binding_result == "not-evaluated", ("unknown", d)
        minus = le.CanonicalEffectRegistry.load([le.RegistryVersion("v1", tuple(x for x in le.version_v1().definitions if x.effect_id != "ce-transfer-silo-4"), "t", "2026-09-17T00:00:00+00:00")], "v1")
        d = M.decide(ok_ref, TRANSFER, registry=minus); assert d.failure_codes == ("EFFECT_UNKNOWN",), ("owner-not-fixture", d)
        d = M.decide(ok_ref, TRANSFER, registry=le.CanonicalEffectRegistry.from_file(M.root / "nope.json")); assert d.failure_codes == ("EFFECT_UNAVAILABLE",), ("owner-unavailable", d)
        d = M.decide(ok_ref, TRANSFER, store=la.InMemoryAuthorityStore.from_file(M.root / "nope.json")); assert d.failure_codes == ("AUTHORITY_UNAVAILABLE",), ("resolver-unavailable", d)
        d = M.decide(ok_ref, TRANSFER, store=la.InMemoryAuthorityStore()); assert d.failure_codes == ("AUTHORITY_NO_GRANT",), ("ledger-fallback", d)
        failing = au.InMemoryAuditSink(writer=lambda e: (_ for _ in ()).throw(OSError("disk full")))
        d = M.decide(ok_ref, TRANSFER, sink=failing); assert d.outcome == "DEFER" and d.failure_codes == ("AUDIT_UNAVAILABLE",) and failing.events == [], ("audit-silent", d)
        # api version
        d = M.decide(ok_ref, TRANSFER); assert d.api_version == "v1" and d.outcome == "ALLOW" and M.sink.events[-1]["api_version"] == "v1", ("api", d)
        assert M.sink.verify() == [], "chain"


def _wrap_decide(fn):
    def apply(mp):
        real = rt_bridge.decide_action
        mp.setattr(rt, "decide_action", lambda principal, action, target, memory_ref, state, tenant, x, *, evidence=None:
                   fn(real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence), principal, action, target, memory_ref, state, tenant, x))
    return apply


def _allow_when(pred):
    return _wrap_decide(lambda d, *a: replace(d, outcome="ALLOW", failure_codes=(), approval_state="SATISFIED" if d.approval_state == "MISSING" else d.approval_state) if pred(d, *a) else d)


def _note(x, ref, tenant, principal):
    r = mr.read_memory(ref, tenant, principal, root=x.memory_reader.root)
    return json.loads(r.content) if r.status == "RESOLVED" else {}


def _m_memory_grant(mp):
    _allow_when(lambda d, p, a, t, ref, s, ten, x: d.failure_codes == ("AUTHORITY_NO_GRANT",) and _note(x, ref, ten, p).get("approved") is True)(mp)


def _m_memory_effect(mp):
    real = rt_bridge.decide_action

    class R:
        def __init__(self, inner, c): self.inner, self.c = inner, c; self.owner_id = inner.owner_id; self.active_version = inner.active_version

        def resolve(self, a, t, cx):
            r = self.inner.resolve(a, t, cx)
            if r.status == "RESOLVED" and self.c is not None:
                d = le.CanonicalEffectDefinition("claimed", a, t, "global", self.c.externality, self.c.reversibility, self.c.approval_required, "v1", "claim", "2026-09-17T00:00:00+00:00")
                return le.CanonicalEffectResolution("RESOLVED", d.effect, r.definition_id, r.version, r.definition_hash, r.provenance, None, r.audit_metadata)
            return r

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        out = x.memory_reader.read(memory_ref, tenant, principal) if memory_ref else None
        if out is not None and out.status == "RESOLVED":
            x = replace(x, effect_registry=R(x.effect_registry, out.evidence.claimed_scope))
        return real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
    mp.setattr(rt, "decide_action", mut)


def _m_channel(ch):
    return lambda mp: _allow_when(lambda d, p, a, t, ref, s, ten, x: d.failure_codes == ("AUTHORITY_NO_GRANT",) and ch in _note(x, ref, ten, p) and CH[ch] == _note(x, ref, ten, p)[ch])(mp)


def _m_audit_grant(mp):
    _allow_when(lambda d, p, a, t, ref, s, ten, x: d.failure_codes == ("AUTHORITY_NO_GRANT",) and any(e["bridge_outcome"] == "ALLOW" and e["action"] == a for e in getattr(x.audit_sink, "events", [])))(mp)


def _m_revoked_valid(mp):
    mp.setattr(la.InMemoryAuthorityStore, "revoke", lambda self, gid, *, at_tick: None)


def _m_stale_fresh(mp):
    real = rt_bridge.decide_action
    mp.setattr(rt, "decide_action", lambda principal, action, target, memory_ref, state, tenant, x, *, evidence=None:
               real(principal, action, target, memory_ref, state, tenant, replace(x, tick=TICK), evidence=evidence))


def _m_wrong_tenant(mp):
    """A reader that trusts the tenant named in the reference and labels the evidence with the caller's tenant."""
    real = mr.ProductionMemoryReader.read

    def mut(self, ref, tenant, principal):
        parsed = mr.parse_ref(ref)
        out = real(self, ref, rt.TenantContext(parsed[0]) if parsed else tenant, principal)
        if out.status == "RESOLVED":
            return replace(out, evidence=replace(out.evidence, tenant_id=tenant.tenant_id))
        return out
    mp.setattr(mr.ProductionMemoryReader, "read", mut)


def _m_wrong_principal(mp):
    real = la.resolver._classify
    mp.setattr(la.resolver, "_classify", lambda r, principal, action, target, scope, state, tick: real(r, r.principal, action, target, scope, state, tick))


def _m_wrong_scope(mp):
    real = la.resolver._classify
    mp.setattr(la.resolver, "_classify", lambda r, principal, action, target, scope, state, tick: real(r, principal, action, target, r.scope_digest, state, tick))


def _reg_mut(fn):
    def apply(mp):
        real = le.CanonicalEffectRegistry.resolve
        mp.setattr(le.CanonicalEffectRegistry, "resolve", lambda self, a, t, c: fn(real(self, a, t, c), a, t))
    return apply


def _default_effect(r, a, t):
    if r.status != "RESOLVED":
        d = le.CanonicalEffectDefinition("default", a, t, "global", "internal", "reversible", False, "v1", "d", "2026-09-17T00:00:00+00:00")
        return le.CanonicalEffectResolution("RESOLVED", d.effect, d.effect_id, "v1", d.definition_hash, "d", None, dict(r.audit_metadata, status="RESOLVED"))
    return r


def _fixture_effect(r, a, t):
    e = eo.canonical_effect(a, t)
    if r.status != "RESOLVED" and e is not None:
        d = le.CanonicalEffectDefinition("fx", a, t, "global", e.externality, e.reversibility, e.approval_required, "fx", "fx", "2026-09-17T00:00:00+00:00")
        return le.CanonicalEffectResolution("RESOLVED", d.effect, d.effect_id, "fx", d.definition_hash, "fx", None, dict(r.audit_metadata, status="RESOLVED"))
    return r


def _m_resolver_fallback(mp):
    real = rt_bridge.resolve_authority
    ledger = ma.GrantLedger(); ledger.issue("g", origin="human", action=TRANSFER, contract=contract_of(TRANSFER), window=WINDOW, state_hash=STATE_A)

    def mut(principal, action, target, scope, state, context, *, store, grant_ref=None):
        r = real(principal, action, target, scope, state, context, store=store, grant_ref=grant_ref)
        ev = ledger.resolve(grant_ref) if isinstance(grant_ref, str) else None
        if r.status in ("UNAVAILABLE", "NO_GRANT") and ev is not None:
            return la.AuthorityResolution("RESOLVED", ev, ev.grant_id, "ledger", ev.origin, principal, scope, ev.issued_at_tick, ev.issued_at_tick, ev.expires_tick, state, "active", "0" * 64, None, r.audit_metadata)
        return r
    mp.setattr(rt_bridge, "resolve_authority", mut)


def _m_audit_silent(mp):
    real = au.InMemoryAuditSink.emit

    def mut(self, event):
        try:
            return real(self, event)
        except au.AuditUnavailable:
            return "0" * 64
    mp.setattr(au.InMemoryAuditSink, "emit", mut)


def _m_b1(mp):
    from logos_research.experiments import binding_state as bs
    from logos_research.experiments.binding_state import BindingConstraint, ProposedAction
    real = rt_bridge.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.outcome == "DEFER" and memory_ref:
            r = mr.read_memory(memory_ref, tenant, principal, root=x.memory_reader.root)
            if r.status == "RESOLVED" and r.claimed_scope is not None:
                o, _ = bs.evaluate_action(BindingConstraint("dc", "APPROVAL_REQUIRED", r.claimed_scope, authority_origin="model"), ProposedAction(action, target, role=principal.principal), WINDOW)
                return replace(d, outcome=o, failure_codes=() if o == "ALLOW" else d.failure_codes)
        return d
    mp.setattr(rt, "decide_action", mut)


def _m_historical(mp):
    real = rt_bridge.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.outcome != "ALLOW" and memory_ref:
            r = mr.read_memory(memory_ref, tenant, principal, root=x.memory_reader.root)
            if r.status == "RESOLVED" and r.claimed_scope is not None:
                c = r.claimed_scope; eff = eo.effect_of_contract(c.externality, c.reversibility, c.approval_required)
                if not eff.consequential and not eff.approval_required:
                    return replace(d, outcome="ALLOW", failure_codes=())
        return d
    mp.setattr(rt, "decide_action", mut)


def _m_api_ignored(mp):
    mp.setattr(rt_bridge, "BRIDGE_API_VERSION", "v0-legacy")
    real = rt.BridgeDecision.__post_init__
    mp.setattr(rt.BridgeDecision, "__post_init__", lambda self: None)


MUTANTS = [("Memory -> grant", _m_memory_grant), ("Memory -> canonical effect", _m_memory_effect), ("Trust -> grant", _m_channel("trust")), ("Risk -> grant", _m_channel("risk")),
           ("VOI -> grant", _m_channel("voi")), ("Audit -> grant", _m_audit_grant), ("Revoked -> valid", _m_revoked_valid), ("Stale -> fresh", _m_stale_fresh),
           ("Wrong tenant -> accepted", _m_wrong_tenant), ("Wrong principal -> accepted", _m_wrong_principal), ("Wrong scope -> accepted", _m_wrong_scope),
           ("Unknown effect -> permissive", _reg_mut(_default_effect)), ("Effect owner unavailable -> fallback", _reg_mut(_fixture_effect)),
           ("Authority resolver unavailable -> fallback", _m_resolver_fallback), ("Audit unavailable -> silent success", _m_audit_silent), ("B1 fallback", _m_b1),
           ("Historical bridge fallback", _m_historical), ("effect_oracle production fallback", _reg_mut(_fixture_effect)),
           ("GrantLedger production fallback", _m_resolver_fallback), ("API version ignored", _m_api_ignored)]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[f"M{i + 1}" for i in range(len(MUTANTS))])
def test_MUT_caught(label, apply, monkeypatch):
    apply(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[label] = str(e.value)[:120]


def test_MUT_zz_all_twenty_caught():
    assert len(MUTANTS) == 20 and set(CAUGHT) == {m[0] for m in MUTANTS}


def test_zz_aggregate():
    assert len(ROWS) >= 1500, len(ROWS)
    assert [r["case"] for r in ROWS if r["false_allow"]] == []
    deltas = {v for r in ROWS for v in r["deltas"].values()}
    assert deltas <= ALLOWED_DELTAS, deltas
    assert any(r["production"] == "ALLOW" for r in ROWS)
    out = os.environ.get("E2E_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"rows": len(ROWS), "false_allows": 0, "mutants": CAUGHT, "deltas": sorted(deltas),
                                         "delta_counts": {d: sum(1 for r in ROWS for v in r["deltas"].values() if v == d) for d in sorted(deltas)},
                                         "outcomes": {o: sum(1 for r in ROWS if r["production"] == o) for o in ("ALLOW", "DENY", "DEFER")}}, indent=1, ensure_ascii=False), encoding="utf-8")
