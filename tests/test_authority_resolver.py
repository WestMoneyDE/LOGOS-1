"""CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1 — phase C1: the production canonical
authority resolver (`logos_authority`) against the reference GrantLedger, Γ and
the frozen authority semantics.

    GrantExistence != GrantValidity · GrantValidity != MemoryClaim
    GrantResolution != ModelJudgment · RevokedAuthority != HistoricalPermission
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

import logos_authority as la
import logos_effects as le
import logos_gamma as gamma
from logos_authority import resolver as la_resolver
from logos_authority import store as la_store
from logos_authority import types as la_types
from logos_memory.scope import ScopeContract, scope_digest
from logos_research import experiments
from logos_research.experiments import memory_authority as ma
from logos_research.experiments.binding_state import ProposedAction, _base_contract

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
WINDOW, STATE_A, STATE_B, TICK = (10, 20), "a" * 64, "b" * 64, 12
V1 = le.version_v1()
KNOWN = {(d.action, d.target): (d.externality, d.reversibility, d.approval_required) for d in V1.definitions}
ACTIONS = {k: ProposedAction(k[0], k[1], role="operator-A") for k in KNOWN}
TRANSFER = ACTIONS[("TRANSFER", "silo-4")]
GRANT_STATES = ("absent", "human", "model-origin", "system-origin", "revoked", "stale", "not-yet-valid", "wrong-state", "wrong-principal", "wrong-scope")
CHANNELS: dict[str, object] = {"memory_claim": None, "trust": 0.0, "voi": 0.0, "risk": 0.0}
ROWS: list[dict] = []
CAUGHT: dict[str, str] = {}


def contract_of(action: ProposedAction, **o) -> ScopeContract:
    e, r, a = KNOWN[(action.action, action.target)]
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",), approval_required=a, externality=e, reversibility=r)
    base.update(o)
    return _base_contract(**base)


def ctx(tick=TICK, run="c1-test", tenant=None) -> la.AuthorityContext:
    return la.AuthorityContext(tick, run, tenant)


def record(gid="g", action=TRANSFER, *, principal="operator-A", origin="human", window=WINDOW, state=STATE_A, scope=None, version="v1",
           revoked=False, revoked_at=None, provenance="test") -> la.GrantRecord:
    return la.GrantRecord(gid, version, principal, action.action, action.target, scope or scope_digest(contract_of(action)), origin, state,
                          window[0], window[0], window[1], provenance, revoked, revoked_at)


def store_with(*recs) -> la.InMemoryAuthorityStore:
    return la.InMemoryAuthorityStore.load(recs)


def effect_of(action: ProposedAction) -> le.CanonicalEffect:
    e, r, a = KNOWN[(action.action, action.target)]
    return le.CanonicalEffect(e, r, a)


def gamma_outcome(action: ProposedAction, authority, *, tick=TICK, state=STATE_A, contract=None) -> str:
    """Direct Γ with canonical effect, canonical scope digest and the given evidence (or None)."""
    eff = effect_of(action); c = contract or contract_of(action)
    if action.role not in c.roles or action.target not in c.targets:              # scope engine (roles/targets), as the bridge does
        return "DENY"
    if eff.approval_required and (authority is None or not authority.is_human_rooted()):
        return "DENY"
    prop = gamma.EffectProposal(action=action.action, target=action.target, effect_kind="deployment" if eff.externality == "external" else "write-internal",
                                externality=eff.externality, reversibility=eff.reversibility, proposal_digest=ma.proposal_digest(action),
                                provenance=(gamma.ProvenanceClaim("proposal://x", "model", "0" * 64),))
    v = gamma.validate(gamma.ValidationContext(prop, tick, state, scope_digest(c), authority))
    return {"VALID": "ALLOW", "INVALID": "DENY", "UNCLEAR": "DEFER"}[v.result]


def resolver_outcome(action: ProposedAction, store, *, principal="operator-A", tick=TICK, state=STATE_A, grant_ref=None, contract=None) -> tuple[str, la.AuthorityResolution]:
    """The preregistered bridge mapping of resolver statuses."""
    c = contract or contract_of(action)
    res = la.resolve_authority(principal, action.action, action.target, scope_digest(c), state, ctx(tick), store=store, grant_ref=grant_ref)
    eff = effect_of(action)
    if res.status == "RESOLVED":
        return gamma_outcome(replace(action, role=principal), res.authority_evidence, tick=tick, state=state, contract=c), res
    if res.status == "NO_GRANT":
        if eff.consequential or eff.approval_required:
            return "DENY", res
        return gamma_outcome(replace(action, role=principal), None, tick=tick, state=state, contract=c), res
    if res.status in la.DENY_STATUSES:
        return "DENY", res
    assert res.status in la.DEFER_STATUSES
    return "DEFER", res


def setup_ledger_and_store(action: ProposedAction, state: str):
    """Mirror one grant state into BOTH the reference ledger and the production store. Returns (ledger, store, gid, principal, tick, state_hash, act)."""
    L = ma.GrantLedger(); S = la.InMemoryAuthorityStore(); gid = "g"; tick = TICK; sh = STATE_A; principal = "operator-A"; act = action
    if state == "absent":
        return L, S, None, principal, tick, sh, act
    origin = {"model-origin": "model", "system-origin": "system"}.get(state, "human")
    L.issue(gid, origin=origin, action=action, contract=contract_of(action), window=WINDOW, state_hash=STATE_A)
    S.issue(record(gid, action, origin=origin))
    if state == "revoked":
        L.revoke(gid); S.revoke(gid, at_tick=TICK)
    elif state == "stale":
        tick = WINDOW[1] + 3
    elif state == "not-yet-valid":
        tick = WINDOW[0] - 2
    elif state == "wrong-state":
        sh = STATE_B
    elif state == "wrong-principal":
        principal = "operator-C"; act = replace(action, role="operator-C")
    elif state == "wrong-scope":
        act = replace(action, capability="wider-scope")            # marker only; the requested contract is widened by `request_contract`
    return L, S, gid, principal, tick, sh, act


def request_contract(action: ProposedAction, act: ProposedAction) -> ScopeContract:
    """The contract the caller presents: canonical, or widened for the wrong-scope state."""
    if act.capability == "wider-scope":
        return contract_of(action, targets=(action.target, "vault-11"), roles=("operator-A", "operator-C"))
    return contract_of(action)


def needs_grant(action: ProposedAction) -> bool:
    e = effect_of(action)
    return e.consequential or e.approval_required


def divergence(status: str, action: ProposedAction, ours: str, reference: str) -> str:
    """The single preregistered decrease-only divergence class: the reference ledger drops a
    revoked grant to None (no grant), so a non-consequential action still ALLOWs there; the
    resolver reports REVOKED and the bridge mapping DENIES. RevokedAuthority != HistoricalPermission."""
    if ours == reference:
        return "none"
    if status == "REVOKED" and not needs_grant(action) and ours == "DENY" and reference == "ALLOW":
        return "revoked-reference-decrease"
    return "UNEXPLAINED"


# ==========================================================================
# Interface / schema
# ==========================================================================

def test_IF_statuses_and_resolution_contract():
    assert la.STATUSES == ("RESOLVED", "NO_GRANT", "REVOKED", "STALE", "NOT_YET_VALID", "WRONG_PRINCIPAL", "WRONG_SCOPE", "WRONG_STATE", "INVALID", "UNAVAILABLE", "UNKNOWN")
    assert la.AUTHORITY_ORIGINS == ("human", "model", "system") and set(gamma.types.AUTHORITY_BEARING_ORIGINS) == {"human"}
    with pytest.raises(ValueError):
        la.AuthorityResolution("NO_GRANT", authority_evidence=record().evidence())
    with pytest.raises(ValueError):
        la.AuthorityResolution("RESOLVED")
    with pytest.raises(ValueError):
        la.AuthorityResolution("GRANTED")
    r = la.resolve_authority("operator-A", "TRANSFER", "silo-4", scope_digest(contract_of(TRANSFER)), STATE_A, ctx(), store=store_with(record()))
    assert r.resolved and r.grant_id == "g" and r.grant_version == "v1" and r.grant_origin == "human" and r.revocation_state == "active"
    assert (r.issued_at, r.valid_from, r.expires_at, r.state_hash) == (10, 10, 20, STATE_A) and len(r.definition_hash) == 64
    assert {"owner_type", "store_version", "store_hash", "status", "grant_id", "definition_hash", "bridge_run_id", "tick", "latency_ns"} <= set(r.audit_metadata)


def test_IF_grant_record_schema_hash_and_no_origin_default():
    r = record()
    assert la.GrantRecord.from_dict(r.to_dict()) == r and r.definition_hash == la.GrantRecord.from_dict(r.to_dict()).definition_hash
    with pytest.raises(ValueError):
        la.GrantRecord.from_dict({**r.to_dict(), "definition_hash": "0" * 64})
    d = r.to_dict(); d.pop("authority_origin")
    with pytest.raises(ValueError):
        la.GrantRecord.from_dict(d)                                                   # missing origin is a schema error, never human
    assert record(origin="").issues() and record(origin="HUMAN").issues() and record(origin="operator").issues()
    assert la.proposal_digest("TRANSFER", "silo-4") == ma.proposal_digest(TRANSFER)
    with pytest.raises(ValueError):
        la.GrantRecord.from_dict({**r.to_dict(), "trust": 1.0})


def test_IF_owner_imports_and_forbidden_names():
    forbidden = re.compile(r"\b(memory|trust|reliab|risk|voi|information_value|uncertain|confidence|prose|llm|authority_class|declared|ledger)\b", re.I)
    for py in (SRC / "logos_authority").glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 else [])
            for m in mods:
                assert m.split(".")[0] in {"json", "time", "dataclasses", "hashlib", "pathlib", "typing", "__future__", "logos_gamma"}, (py.name, m)
                assert not m.startswith(("logos_memory", "logos_research", "logos_effects")), (py.name, m)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
        bad = {x for x in names if forbidden.search(x)}
        assert not bad, (py.name, bad)
    assert "logos_authority" in experiments.PRODUCTION_PACKAGES
    with pytest.raises(ImportError):
        experiments.assert_experimental_caller(["logos_authority.resolver"])


# ==========================================================================
# Authority semantics (Section 13)
# ==========================================================================

@pytest.mark.parametrize("case,expected", [
    ("exact scope", "RESOLVED"), ("narrower scope", "WRONG_SCOPE"), ("wider scope", "WRONG_SCOPE"), ("wrong target", "WRONG_SCOPE"),
    ("fresh", "RESOLVED"), ("stale", "STALE"), ("not-yet-valid", "NOT_YET_VALID"), ("expired", "STALE"), ("wrong state hash", "WRONG_STATE"),
    ("missing state hash", "WRONG_STATE"), ("revoked before read", "REVOKED"), ("revoked after memory write", "REVOKED"), ("reload after revoke", "REVOKED")])
def test_SEM_scope_freshness_revocation(case, expected):
    S = store_with(record()); sd = scope_digest(contract_of(TRANSFER)); tick = TICK; state = STATE_A; target = "silo-4"; ref = "g"
    if case == "narrower scope":
        sd = scope_digest(contract_of(TRANSFER, targets=()))
    elif case == "wider scope":
        sd = scope_digest(contract_of(TRANSFER, targets=("silo-4", "vault-11"), roles=("operator-A", "operator-C")))
    elif case == "wrong target":
        target = "vault-11"
    elif case == "stale":
        tick = WINDOW[1]
    elif case == "expired":
        tick = WINDOW[1] + 100
    elif case == "not-yet-valid":
        tick = WINDOW[0] - 1
    elif case == "wrong state hash":
        state = STATE_B
    elif case == "missing state hash":
        state = ""
    elif case in ("revoked before read", "revoked after memory write"):
        S.revoke("g", at_tick=TICK - 1 if case == "revoked before read" else TICK + 1)
    elif case == "reload after revoke":
        S.revoke("g", at_tick=TICK); S = la.InMemoryAuthorityStore.from_dict(json.loads(json.dumps(S.to_dict())))
    r = la.resolve_authority("operator-A", "TRANSFER", target, sd, state, ctx(tick), store=S, grant_ref=ref)
    assert r.status == expected, (case, r)
    assert (r.authority_evidence is not None) == (expected == "RESOLVED")
    if expected != "RESOLVED":
        assert r.grant_id == "g" and r.definition_hash and r.error                         # which grant failed is reconstructable


def test_SEM_wrong_principal_by_reference_and_by_lookup():
    S = store_with(record())
    assert la.resolve_authority("operator-C", "TRANSFER", "silo-4", scope_digest(contract_of(TRANSFER)), STATE_A, ctx(), store=S, grant_ref="g").status == "WRONG_PRINCIPAL"
    assert la.resolve_authority("operator-C", "TRANSFER", "silo-4", scope_digest(contract_of(TRANSFER)), STATE_A, ctx(), store=S).status == "NO_GRANT"


def test_SEM_origin_closed_enum_and_model_never_human():
    for origin in ("model", "system"):
        r = la.resolve_authority("operator-A", "TRANSFER", "silo-4", scope_digest(contract_of(TRANSFER)), STATE_A, ctx(), store=store_with(record(origin=origin)))
        assert r.resolved and r.grant_origin == origin and not r.authority_evidence.is_human_rooted()
        assert resolver_outcome(TRANSFER, store_with(record(origin=origin)))[0] == "DENY"       # approval / Γ-1 both refuse
    S = store_with(record(origin="")); assert la.resolve_authority("operator-A", "TRANSFER", "silo-4", scope_digest(contract_of(TRANSFER)), STATE_A, ctx(), store=S).status == "INVALID"


def test_SEM_revocation_dominates_everything_later():
    S = store_with(record()); S.revoke("g", at_tick=TICK)
    CHANNELS.update(trust=1.0, voi=1.0, memory_claim={"approved": True, "gamma_result": "VALID"})
    try:
        for tick in (TICK, TICK + 1, WINDOW[1] - 1):
            r = la.resolve_authority("operator-A", "TRANSFER", "silo-4", scope_digest(contract_of(TRANSFER)), STATE_A, ctx(tick), store=S, grant_ref="g")
            assert r.status == "REVOKED" and r.revocation_state == "revoked"
    finally:
        CHANNELS.update(trust=0.0, voi=0.0, memory_claim=None)
    with pytest.raises(ValueError):
        S.issue(record())                                                             # cannot re-issue over a revoked id


# ==========================================================================
# Store
# ==========================================================================

def test_STORE_lookup_revocation_version_integrity_and_serialization(tmp_path):
    S = store_with(record("g1"), record("g2", ACTIONS[("EXPORT", "ledger-3")]))
    assert S.lookup("g1").grant_id == "g1" and S.lookup("nope") is None and S.revocation("g1") == (False, None)
    assert [r.grant_id for r in S.grants_for("operator-A", "TRANSFER", "silo-4")] == ["g1"] and S.grants_for("operator-B", "TRANSFER", "silo-4") == ()
    S.revoke("g1", at_tick=15); assert S.revocation("g1") == (True, 15)
    p = tmp_path / "store.json"; p.write_text(json.dumps(S.to_dict()), encoding="utf-8")
    S2 = la.InMemoryAuthorityStore.from_file(p)
    assert S2.available and S2.integrity_hash() == S.integrity_hash() and S2.version == "v1" and S2.revocation("g1") == (True, 15)
    assert la.InMemoryAuthorityStore.from_file(tmp_path / "missing.json").available is False
    raw = S.to_dict(); raw["integrity_hash"] = "f" * 64
    assert la.InMemoryAuthorityStore.from_dict(raw).available is False
    assert store_with(record("dup"), record("dup", origin="model")).issues()           # duplicate id is an INVALID condition


# ==========================================================================
# Differential parity with the reference GrantLedger (Section 16)
# ==========================================================================

@pytest.mark.parametrize("grant_state", GRANT_STATES)
@pytest.mark.parametrize("key", sorted(KNOWN))
def test_PAR_resolver_matches_reference_ledger_plus_gamma(key, grant_state):
    action = ACTIONS[key]
    L, S, gid, principal, tick, sh, act = setup_ledger_and_store(action, grant_state)
    ref_auth = L.resolve(gid) if gid else None; rc = request_contract(action, act)
    reference = gamma_outcome(act, ref_auth, tick=tick, state=sh, contract=rc)
    ours, res = resolver_outcome(act, S, principal=principal, tick=tick, state=sh, grant_ref=gid, contract=rc)
    d = divergence(res.status, action, ours, reference)
    ROWS.append({"case": f"PAR/{key}/{grant_state}", "outcome": ours, "reference": reference, "status": res.status, "delta": d, "false_allow": ours == "ALLOW" and reference != "ALLOW"})
    assert d != "UNEXPLAINED", (key, grant_state, res.status, ours, reference)
    expected_status = {"absent": "NO_GRANT", "human": "RESOLVED", "model-origin": "RESOLVED", "system-origin": "RESOLVED", "revoked": "REVOKED", "stale": "STALE",
                       "not-yet-valid": "NOT_YET_VALID", "wrong-state": "WRONG_STATE", "wrong-principal": "WRONG_PRINCIPAL", "wrong-scope": "WRONG_SCOPE"}[grant_state]
    assert res.status == expected_status


# ==========================================================================
# Fail-closed matrix (Section 17)
# ==========================================================================

def _fc(kind):
    sd = scope_digest(contract_of(TRANSFER)); good = record()
    if kind == "missing grant":
        return store_with(), "g", "NO_GRANT"
    if kind == "duplicate grant id":
        return store_with(good, record(origin="model")), "g", "INVALID"
    if kind == "revoked":
        S = store_with(good); S.revoke("g", at_tick=TICK); return S, "g", "REVOKED"
    if kind == "stale":
        return store_with(record(window=(0, 5))), "g", "STALE"
    if kind == "not-yet-valid":
        return store_with(record(window=(15, 20))), "g", "NOT_YET_VALID"
    if kind == "wrong principal":
        return store_with(record(principal="operator-C")), "g", "WRONG_PRINCIPAL"
    if kind == "wrong scope":
        return store_with(record(scope="c" * 64)), "g", "WRONG_SCOPE"
    if kind == "wrong target":
        return store_with(record(action=ACTIONS[("TRANSFER", "escrow-2")], scope=sd)), "g", "WRONG_SCOPE"
    if kind == "wrong state hash":
        return store_with(record(state=STATE_B)), "g", "WRONG_STATE"
    if kind == "missing origin":
        raw = store_with(good).to_dict(); raw["records"][0].pop("authority_origin"); raw.pop("integrity_hash")
        return la.InMemoryAuthorityStore.from_dict(raw), "g", "UNAVAILABLE"
    if kind == "invalid origin":
        return store_with(record(origin="agent")), "g", "INVALID"
    if kind == "corrupt record":
        raw = store_with(good).to_dict(); raw["records"][0]["expires_tick"] = "twenty"; raw.pop("integrity_hash"); raw["records"][0].pop("definition_hash")
        S = la.InMemoryAuthorityStore.from_dict(raw); return S, "g", "INVALID" if S.available else "UNAVAILABLE"
    if kind == "unknown version":
        raw = store_with(good).to_dict(); raw["version"] = ""; raw.pop("integrity_hash")
        return la.InMemoryAuthorityStore.from_dict(raw), "g", "UNAVAILABLE"
    if kind == "unavailable store":
        return la.InMemoryAuthorityStore.from_file(Path(tempfile.gettempdir()) / "no-such-authority-store.json"), "g", "UNAVAILABLE"
    if kind == "integrity mismatch":
        raw = store_with(good).to_dict(); raw["records"][0]["principal"] = "operator-Z"
        return la.InMemoryAuthorityStore.from_dict(raw), "g", "UNAVAILABLE"
    if kind == "malformed evidence":
        return store_with(good), {"grant": "g"}, "UNKNOWN"
    raise KeyError(kind)


FC = ["missing grant", "duplicate grant id", "revoked", "stale", "not-yet-valid", "wrong principal", "wrong scope", "wrong target", "wrong state hash",
      "missing origin", "invalid origin", "corrupt record", "unknown version", "unavailable store", "integrity mismatch", "malformed evidence"]


@pytest.mark.parametrize("kind", FC)
def test_FC_matrix_never_permissive(kind):
    S, ref, expected = _fc(kind)
    out, res = resolver_outcome(TRANSFER, S, grant_ref=ref)
    assert res.status == expected and res.authority_evidence is None and out in ("DENY", "DEFER"), (kind, res)
    ROWS.append({"case": f"FC/{kind}", "outcome": out, "reference": "DENY|DEFER", "status": res.status, "false_allow": False})


# ==========================================================================
# Properties AUTH-P1..P18
# ==========================================================================

S_KEY = st.sampled_from(sorted(KNOWN)); S_GRANT = st.sampled_from(GRANT_STATES)
S_SCORE = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
S_ORIGIN = st.sampled_from(["human", "model", "system"])
S_TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz -.,!", min_size=0, max_size=40)


def _run(key, grant_state, **channels):
    action = ACTIONS[key]
    L, S, gid, principal, tick, sh, act = setup_ledger_and_store(action, grant_state); rc = request_contract(action, act)
    CHANNELS.update(channels)
    try:
        ours, res = resolver_outcome(act, S, principal=principal, tick=tick, state=sh, grant_ref=gid, contract=rc)
    finally:
        CHANNELS.update(memory_claim=None, trust=0.0, voi=0.0, risk=0.0)
    ref = gamma_outcome(act, L.resolve(gid) if gid else None, tick=tick, state=sh, contract=rc)
    row(f"P/{key}/{grant_state}", ours, ref, res, action)
    return ours, res, ref


def row(case, ours, ref, res, action):
    d = divergence(res.status, action, ours, ref)
    ROWS.append({"case": case, "outcome": ours, "reference": ref, "status": res.status, "delta": d, "false_allow": ours == "ALLOW" and ref != "ALLOW"})
    assert not (ours == "ALLOW" and ref != "ALLOW"), (case, res)
    assert d != "UNEXPLAINED", (case, ours, ref, res.status)


@settings(max_examples=80, deadline=None)
@given(key=S_KEY)
def test_AUTH_P1_no_grant_never_authorizes_consequential(key):
    ours, res, _ = _run(key, "absent")
    assert res.status == "NO_GRANT" and (ours == "DENY" if effect_of(ACTIONS[key]).consequential or effect_of(ACTIONS[key]).approval_required else ours == "ALLOW")


@settings(max_examples=80, deadline=None)
@given(key=S_KEY, tick=st.integers(min_value=0, max_value=40), claim=st.sampled_from([None, {"approved": True}, {"revoked": False}]))
def test_AUTH_P2_revoked_never_authorizes(key, tick, claim):
    action = ACTIONS[key]; S = store_with(record("g", action)); S.revoke("g", at_tick=tick)
    ours, res = resolver_outcome(action, S, tick=tick, grant_ref="g")
    assert res.status == "REVOKED" and ours == "DENY"
    row("P2", ours, gamma_outcome(action, None, tick=tick), res, action)


@settings(max_examples=80, deadline=None)
@given(key=S_KEY, tick=st.integers(min_value=20, max_value=200), voi=S_SCORE)
def test_AUTH_P3_stale_never_refreshed(key, tick, voi):
    ours, res = resolver_outcome(ACTIONS[key], store_with(record("g", ACTIONS[key])), tick=tick, grant_ref="g")
    assert res.status == "STALE" and ours == "DENY"
    row("P3", ours, gamma_outcome(ACTIONS[key], record("g", ACTIONS[key]).evidence(), tick=tick), res, ACTIONS[key])


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, principal=st.sampled_from(["operator-C", "operator-B", "", "OPERATOR-A", "operator-A "]))
def test_AUTH_P4_wrong_principal_never_reprincipals(key, principal):
    ours, res = resolver_outcome(ACTIONS[key], store_with(record("g", ACTIONS[key])), principal=principal, grant_ref="g")
    assert res.status == "WRONG_PRINCIPAL" and ours == "DENY"
    row("P4", ours, gamma_outcome(replace(ACTIONS[key], role=principal), record("g", ACTIONS[key]).evidence()), res, ACTIONS[key])


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, extra=st.lists(st.sampled_from(["vault-11", "escrow-2", "ledger-3"]), min_size=1, max_size=3, unique=True))
def test_AUTH_P5_wrong_scope_never_widens(key, extra):
    action = ACTIONS[key]
    c = contract_of(action, targets=(action.target, *extra))
    ours, res = resolver_outcome(action, store_with(record("g", action)), grant_ref="g", contract=c)
    assert res.status == "WRONG_SCOPE" and ours == "DENY"
    row("P5", ours, gamma_outcome(action, record("g", action).evidence(), contract=c), res, action)


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, state=st.sampled_from([STATE_B, "c" * 64, "", "a" * 63]))
def test_AUTH_P6_wrong_state_never_validates(key, state):
    ours, res = resolver_outcome(ACTIONS[key], store_with(record("g", ACTIONS[key])), state=state, grant_ref="g")
    assert res.status == "WRONG_STATE" and ours == "DENY"
    row("P6", ours, gamma_outcome(ACTIONS[key], record("g", ACTIONS[key]).evidence(), state=state), res, ACTIONS[key])


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, origin=st.sampled_from(["model", "system"]), reloaded=st.booleans())
def test_AUTH_P7_model_origin_never_becomes_human(key, origin, reloaded):
    S = store_with(record("g", ACTIONS[key], origin=origin))
    if reloaded:
        S = la.InMemoryAuthorityStore.from_dict(json.loads(json.dumps(S.to_dict())))
    r = la.resolve_authority("operator-A", key[0], key[1], scope_digest(contract_of(ACTIONS[key])), STATE_A, ctx(), store=S, grant_ref="g")
    assert r.resolved and r.grant_origin == origin and not r.authority_evidence.is_human_rooted()
    ours, res = resolver_outcome(ACTIONS[key], S, grant_ref="g")
    assert ours == "DENY"                                                   # Γ-1: presented non-human evidence is INVALID, consequential or not
    row("P7", ours, gamma_outcome(ACTIONS[key], r.authority_evidence), res, ACTIONS[key])


@settings(max_examples=80, deadline=None)
@given(key=S_KEY, trust=S_SCORE, label=st.sampled_from(["AUTO", "trusted", "gold"]))
def test_AUTH_P8_trust_does_not_mint_grant(key, trust, label):
    ours, res, _ = _run(key, "absent", trust=trust)
    assert res.status == "NO_GRANT"


@settings(max_examples=80, deadline=None)
@given(key=S_KEY, risk=S_SCORE)
def test_AUTH_P9_risk_does_not_mint_grant(key, risk):
    ours, res, _ = _run(key, "absent", risk=risk)
    assert res.status == "NO_GRANT"


@settings(max_examples=80, deadline=None)
@given(key=S_KEY, voi=S_SCORE, grant_state=st.sampled_from(["absent", "stale", "revoked"]))
def test_AUTH_P10_voi_does_not_mint_or_refresh(key, voi, grant_state):
    ours, res, _ = _run(key, grant_state, voi=voi)
    assert res.status in ("NO_GRANT", "STALE", "REVOKED") and ours == "DENY" or (res.status == "NO_GRANT" and not effect_of(ACTIONS[key]).consequential and not effect_of(ACTIONS[key]).approval_required)


@settings(max_examples=80, deadline=None)
@given(key=S_KEY, claim=st.dictionaries(st.sampled_from(["approved", "gamma_result", "grant_ref", "origin", "authority_class"]), st.sampled_from([True, "VALID", "g", "human", "grant"]), min_size=1))
def test_AUTH_P11_memory_provenance_does_not_mint(key, claim):
    ours, res, _ = _run(key, "absent", memory_claim=claim)
    assert res.status == "NO_GRANT"


@settings(max_examples=40, deadline=None)
@given(key=S_KEY, cycles=st.integers(min_value=1, max_value=3))
def test_AUTH_P12_reload_preserves_revocation(key, cycles):
    S = store_with(record("g", ACTIONS[key])); S.revoke("g", at_tick=TICK)
    for _ in range(cycles):
        S = la.InMemoryAuthorityStore.from_dict(json.loads(json.dumps(S.to_dict())))
    assert S.available and resolver_outcome(ACTIONS[key], S, grant_ref="g")[1].status == "REVOKED"


@settings(max_examples=150, deadline=None)
@given(key=S_KEY, grant_state=S_GRANT)
def test_AUTH_P13_parity_with_frozen_reference(key, grant_state):
    ours, res, ref = _run(key, grant_state)
    assert divergence(res.status, ACTIONS[key], ours, ref) in ("none", "revoked-reference-decrease")


@settings(max_examples=40, deadline=None)
@given(key=S_KEY, kind=st.sampled_from(["missing-file", "malformed", "integrity", "shape"]))
def test_AUTH_P14_unavailable_store_never_permissive(key, kind):
    if kind == "missing-file":
        S = la.InMemoryAuthorityStore.from_file(Path(tempfile.gettempdir()) / "missing-auth.json")
    elif kind == "malformed":
        S = la.InMemoryAuthorityStore.from_dict({"version": "v1", "records": "x"})
    elif kind == "integrity":
        raw = store_with(record("g", ACTIONS[key])).to_dict(); raw["integrity_hash"] = "0" * 64; S = la.InMemoryAuthorityStore.from_dict(raw)
    else:
        S = la.InMemoryAuthorityStore.from_dict({"grants": []})
    ours, res = resolver_outcome(ACTIONS[key], S, grant_ref="g")
    assert res.status == "UNAVAILABLE" and ours == "DEFER"


@settings(max_examples=40, deadline=None)
@given(key=S_KEY, grant_state=S_GRANT)
def test_AUTH_P15_effect_owner_and_authority_owner_separate(key, grant_state):
    action = ACTIONS[key]; L, S, gid, principal, tick, sh, act = setup_ledger_and_store(action, grant_state)
    eff = le.default_registry().resolve(key[0], key[1], le.CanonicalEffectContext("p15"))
    res = la.resolve_authority(principal, act.action, act.target, scope_digest(contract_of(action)), sh, ctx(tick), store=S, grant_ref=gid)
    assert eff.status == "RESOLVED" and (eff.effect.externality, eff.effect.reversibility, eff.effect.approval_required) == KNOWN[key]
    assert "effect" not in json.dumps(res.audit_metadata) and "grant" not in json.dumps(eff.audit_metadata)


@settings(max_examples=150, deadline=None)
@given(key=S_KEY, grant_state=S_GRANT)
def test_AUTH_P16_direct_gamma_equivalence(key, grant_state):
    ours, res, ref = _run(key, grant_state)
    if res.resolved:
        assert ours == gamma_outcome(replace(ACTIONS[key], role=res.principal), res.authority_evidence, tick=res.audit_metadata["tick"], state=res.state_hash,
                                     contract=request_contract(ACTIONS[key], ACTIONS[key]))


@settings(max_examples=80, deadline=None)
@given(key=st.sampled_from([k for k, v in KNOWN.items() if v[2]]), origin=S_ORIGIN, grant_state=st.sampled_from(["human", "model-origin", "system-origin", "absent"]))
def test_AUTH_P17_approval_remains_enforced(key, origin, grant_state):
    ours, res, ref = _run(key, grant_state)
    assert ours == ("ALLOW" if grant_state == "human" else "DENY")
    row("P17", ours, ref, res, ACTIONS[key])


@settings(max_examples=20, deadline=None)
@given(frame=st.sampled_from(["logos_authority", "logos_authority.resolver", "logos_authority.store", "logos_effects", "logos_gamma.kernel"]))
def test_AUTH_P18_b1_unreachable(frame):
    with pytest.raises(ImportError):
        experiments.assert_experimental_caller([frame])
    for py in (SRC / "logos_authority").glob("*.py"):
        assert "binding_state" not in py.read_text(encoding="utf-8") and "GrantLedger" not in py.read_text(encoding="utf-8")


# ==========================================================================
# Mutation suite M1..M15
# ==========================================================================

def _probe_battery():
    sd = scope_digest(contract_of(TRANSFER))
    # missing origin -> INVALID/UNAVAILABLE, never resolved
    raw = store_with(record()).to_dict(); raw["records"][0].pop("authority_origin"); raw.pop("integrity_hash")
    r = la.resolve_authority("operator-A", "TRANSFER", "silo-4", sd, STATE_A, ctx(), store=la.InMemoryAuthorityStore.from_dict(raw), grant_ref="g")
    assert r.status in ("UNAVAILABLE", "INVALID") and r.authority_evidence is None, ("origin-missing", r)
    S = store_with(record(origin=""))
    assert la.resolve_authority("operator-A", "TRANSFER", "silo-4", sd, STATE_A, ctx(), store=S, grant_ref="g").status == "INVALID", "origin-empty"
    # revoked / stale / principal / scope / state
    S = store_with(record()); S.revoke("g", at_tick=TICK)
    assert resolver_outcome(TRANSFER, S, grant_ref="g")[1].status == "REVOKED", "revoked"
    assert resolver_outcome(TRANSFER, store_with(record()), tick=25, grant_ref="g")[1].status == "STALE", "stale"
    assert resolver_outcome(TRANSFER, store_with(record()), principal="operator-C", grant_ref="g")[1].status == "WRONG_PRINCIPAL", "principal"
    assert resolver_outcome(TRANSFER, store_with(record()), grant_ref="g", contract=contract_of(TRANSFER, targets=("silo-4", "vault-11")))[1].status == "WRONG_SCOPE", "scope"
    assert resolver_outcome(TRANSFER, store_with(record()), state=STATE_B, grant_ref="g")[1].status == "WRONG_STATE", "state"
    # channels never mint / refresh
    CHANNELS.update(memory_claim={"approved": True, "grant_ref": "g"}, trust=1.0, voi=1.0, risk=0.0)
    try:
        assert resolver_outcome(TRANSFER, store_with(), grant_ref="g")[1].status == "NO_GRANT", "memory/trust/voi mint"
        assert resolver_outcome(TRANSFER, store_with(record()), tick=25, grant_ref="g")[1].status == "STALE", "voi refresh"
    finally:
        CHANNELS.update(memory_claim=None, trust=0.0, voi=0.0, risk=0.0)
    # no fallback to the reference ledger
    L = ma.GrantLedger(); L.issue("g", origin="human", action=TRANSFER, contract=contract_of(TRANSFER), window=WINDOW, state_hash=STATE_A)
    LEDGERS.append(L)
    try:
        assert resolver_outcome(TRANSFER, store_with(), grant_ref="g")[1].status == "NO_GRANT", "ledger fallback"
    finally:
        LEDGERS.clear()
    # unavailable -> UNAVAILABLE
    bad = la.InMemoryAuthorityStore.from_file(Path(tempfile.gettempdir()) / "nope-auth.json")
    out, r = resolver_outcome(TRANSFER, bad, grant_ref="g"); assert r.status == "UNAVAILABLE" and out == "DEFER", ("unavailable", r)
    # duplicates -> INVALID
    assert resolver_outcome(TRANSFER, store_with(record(), record(origin="model", window=(0, 100))), grant_ref="g")[1].status == "INVALID", "duplicate"
    # model origin stays model; approval enforced
    out, r = resolver_outcome(TRANSFER, store_with(record(origin="model")), grant_ref="g")
    assert r.resolved and r.grant_origin == "model" and not r.authority_evidence.is_human_rooted() and out == "DENY", ("origin", r, out)
    # metadata present
    r = la.resolve_authority("operator-A", "TRANSFER", "silo-4", sd, STATE_A, ctx(), store=store_with(record()), grant_ref="g")
    assert r.resolved and r.grant_version == "v1" and r.definition_hash == record().definition_hash and r.audit_metadata.get("store_hash") and r.audit_metadata.get("definition_hash"), ("metadata", r)
    # positive control
    assert resolver_outcome(TRANSFER, store_with(record()), grant_ref="g")[0] == "ALLOW", "positive"


LEDGERS: list = []


def _m1(mp):
    real = la_types.GrantRecord.issues
    mp.setattr(la_types.GrantRecord, "issues", lambda self: [i for i in real(self) if "authority_origin" not in i])
    mp.setattr(la_types.GrantRecord, "evidence", lambda self: gamma.AuthorityEvidence(self.grant_id, self.authority_origin or "human", self.proposal_digest, self.scope_digest, self.state_hash, self.valid_from_tick, self.expires_tick))
    real_fd = la_types.GrantRecord.from_dict.__func__
    mp.setattr(la_types.GrantRecord, "from_dict", classmethod(lambda cls, raw: real_fd(cls, {**raw, "authority_origin": raw.get("authority_origin", "human")})))


def _classify_mutant(skip):
    def apply(mp):
        real = la_resolver._classify

        def mut(r, principal, action, target, scope, state, tick):
            c = real(r, principal, action, target, scope, state, tick)
            if c == skip:
                r2 = replace(r, revoked=False) if skip == "REVOKED" else r
                return real(r2, r.principal if skip == "WRONG_PRINCIPAL" else principal, action, target, r.scope_digest if skip == "WRONG_SCOPE" else scope,
                            r.state_hash if skip == "WRONG_STATE" else state, r.valid_from_tick if skip in ("STALE", "NOT_YET_VALID") else tick)
            return c
        mp.setattr(la_resolver, "_classify", mut)
    return apply


def _channel_mint(ch):
    def apply(mp):
        real = la_resolver._resolve

        def mut(principal, action, target, scope, state, context, store, grant_ref):
            s, e, r = real(principal, action, target, scope, state, context, store, grant_ref)
            v = CHANNELS[ch]
            if s in ("NO_GRANT", "STALE") and (v if ch != "memory_claim" else (v or {}).get("approved")) and (ch == "memory_claim" or v >= 0.9):
                return "RESOLVED", None, record("minted", TRANSFER, scope=scope, state=state, window=(0, 10 ** 6))
            return s, e, r
        mp.setattr(la_resolver, "_resolve", mut)
    return apply


def _m10(mp):
    real = la_resolver._resolve

    def mut(principal, action, target, scope, state, context, store, grant_ref):
        s, e, r = real(principal, action, target, scope, state, context, store, grant_ref)
        if s == "NO_GRANT" and LEDGERS and isinstance(grant_ref, str) and LEDGERS[0].resolve(grant_ref) is not None:
            ev = LEDGERS[0].resolve(grant_ref)
            return "RESOLVED", None, la.GrantRecord(ev.grant_id, "ledger", principal, action, target, ev.bound_scope_digest, ev.origin, ev.bound_state_hash, ev.issued_at_tick, ev.issued_at_tick, ev.expires_tick, "ledger")
        return s, e, r
    mp.setattr(la_resolver, "_resolve", mut)


def _m11(mp):
    real = la_resolver._resolve

    def mut(principal, action, target, scope, state, context, store, grant_ref):
        if not getattr(store, "available", False):
            return "RESOLVED", None, record("default", TRANSFER, scope=scope, state=state, window=(0, 10 ** 6))
        return real(principal, action, target, scope, state, context, store, grant_ref)
    mp.setattr(la_resolver, "_resolve", mut)


def _m12(mp):
    real = la_store.InMemoryAuthorityStore.issues
    mp.setattr(la_store.InMemoryAuthorityStore, "issues", lambda self: [i for i in real(self) if "duplicate" not in i])


def _m13(mp):
    mp.setattr(la_types.GrantRecord, "evidence", lambda self: gamma.AuthorityEvidence(self.grant_id, "human", self.proposal_digest, self.scope_digest, self.state_hash, self.valid_from_tick, self.expires_tick))


def _m14(mp):
    mp.setattr(la_store.InMemoryAuthorityStore, "revoke", lambda self, gid, *, at_tick: None)


def _m15(mp):
    real = la_resolver.resolve_authority

    def mut(*a, **k):
        r = real(*a, **k)
        r.audit_metadata.pop("store_hash", None); r.audit_metadata.pop("definition_hash", None)
        return replace(r, grant_version=None if not r.resolved else "", definition_hash=None if not r.resolved else r.definition_hash) if not r.resolved else r
    mp.setattr(la, "resolve_authority", mut); mp.setattr(la_resolver, "resolve_authority", mut)


MUTANTS = [("M1 missing origin -> HUMAN", _m1), ("M2 revoked -> RESOLVED", _classify_mutant("REVOKED")), ("M3 stale -> RESOLVED", _classify_mutant("STALE")),
           ("M4 wrong principal ignored", _classify_mutant("WRONG_PRINCIPAL")), ("M5 wrong scope ignored", _classify_mutant("WRONG_SCOPE")),
           ("M6 wrong state ignored", _classify_mutant("WRONG_STATE")), ("M7 memory approval claim mints grant", _channel_mint("memory_claim")),
           ("M8 trust AUTO mints grant", _channel_mint("trust")), ("M9 high VOI refreshes grant", _channel_mint("voi")), ("M10 fallback to experimental GrantLedger", _m10),
           ("M11 UNAVAILABLE -> RESOLVED", _m11), ("M12 duplicate ID chooses permissive version", _m12), ("M13 model-origin -> human-origin", _m13),
           ("M14 revocation ignored", _m14), ("M15 version/integrity metadata omitted", _m15)]


def test_MUT_probe_battery_clean():
    _probe_battery()


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[m[0].split()[0] for m in MUTANTS])
def test_MUT_caught(label, apply, monkeypatch):
    apply(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _probe_battery()
    CAUGHT[label] = str(e.value)[:120]


def test_MUT_zz_all_fifteen_caught():
    assert len(MUTANTS) == 15 and set(CAUGHT) == {m[0] for m in MUTANTS}


def test_zz_aggregate():
    assert len(ROWS) >= 1000, len(ROWS)
    assert [r["case"] for r in ROWS if r["false_allow"]] == []
    assert any(r["outcome"] == "ALLOW" for r in ROWS)
    assert {r.get("delta", "none") for r in ROWS} <= {"none", "revoked-reference-decrease"}
    out = os.environ.get("C1_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"rows": len(ROWS), "false_allows": 0, "mutants": CAUGHT,
                                         "outcomes": {o: sum(1 for r in ROWS if r["outcome"] == o) for o in ("ALLOW", "DENY", "DEFER")},
                                         "statuses": sorted({r["status"] for r in ROWS}),
                                         "divergences": {"revoked-reference-decrease": sum(1 for r in ROWS if r.get("delta") == "revoked-reference-decrease")}}, indent=1), encoding="utf-8")
