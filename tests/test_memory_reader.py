"""CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1 — phase C4: the production memory
reader (`logos_memory.reader`) — evidence only, tenant-isolated, strict
(VF-2 / VF-3), and the bridge run end to end with it.

    MemoryRead != Authorization · DeclaredEffect != CanonicalEffect · MemoryProvenance != Grant
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_audit as au
import logos_authority as la
import logos_effects as le
import logos_runtime as rt
from logos_memory import reader as mr
from logos_memory.records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from logos_memory.scope import scope_digest
from logos_memory.store import MemoryStore
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import risk_decomposition as rd
from test_production_bridge import ACTIONS, EXPORT, EXT, KNOWN, REV, STATE_A, TICK, TRANSFER, UNKNOWN, WINDOW, claim_contract, contract_of, needs_grant, principal_of

T_A, T_B = rt.TenantContext("tenant-a"), rt.TenantContext("tenant-b")
P = rt.PrincipalContext("operator-A")
ROWS: list[dict] = []
CAUGHT: dict[str, str] = {}


class Lab:
    def __init__(self, tmp: Path):
        self.root = tmp / "memory"; self.stores: dict[str, MemoryStore] = {}; self.n = 0
        self.store = la.InMemoryAuthorityStore(); self.registry = le.production_registry(); self.ledger = ma.GrantLedger()
        self.sink = au.InMemoryAuditSink(clock=lambda: "2026-09-17T00:00:00+00:00")
        self.reader = mr.ProductionMemoryReader(self.root)

    def mem(self, tenant="tenant-a") -> MemoryStore:
        if tenant not in self.stores:
            self.stores[tenant] = MemoryStore(mr.tenant_store_path(self.root, tenant))
        return self.stores[tenant]

    def grant(self, gid, action, *, origin="human", window=WINDOW, state=STATE_A, **o):
        c = contract_of(action, **o)
        self.ledger.issue(gid, origin=origin, action=action, contract=c, window=window, state_hash=state)
        self.store.issue(la.GrantRecord(gid, "v1", "operator-A", action.action, action.target, scope_digest(c), origin, state, window[0], window[0], window[1], "test"))

    def write(self, content, *, tenant="tenant-a", **kw) -> str:
        self.n += 1
        r = ma.write_note(self.mem(tenant), f"m-{self.n}", content, **kw)
        return f"memory://{tenant}/{r.id}"

    def note(self, ref, contract, **claims) -> str:
        return ma.authority_note(ref, contract, **claims)

    def read(self, ref, tenant=T_A) -> mr.MemoryReadResult:
        return mr.read_memory(ref, tenant, P, root=self.root)

    def decide(self, ref, action, *, tenant=T_A, tick=TICK, state=STATE_A, principal=None) -> rt.BridgeDecision:
        x = rt.ExecutionContext(tick, "c4-test", self.registry, self.store, self.reader, self.sink)
        return rt.decide_action(principal or principal_of(action), action.action, action.target, ref, state, tenant, x)


@pytest.fixture
def lab():
    with tempfile.TemporaryDirectory() as t:
        yield Lab(Path(t))


# ==========================================================================
# Statuses / strictness / tenant
# ==========================================================================

def test_STATUS_vocabulary_and_result_contract():
    assert mr.READER_STATUSES == ("RESOLVED", "NOT_FOUND", "INVALID", "CORRUPT", "UNAVAILABLE", "WRONG_TENANT", "UNSUPPORTED_VERSION")
    assert mr.NOTE_SCHEMA == ma.NOTE_SCHEMA == "logos.authority-note/1"
    with pytest.raises(ValueError):
        mr.MemoryReadResult("NOT_FOUND", refs=("g",))
    with pytest.raises(ValueError):
        mr.MemoryReadResult("RESOLVED_MAYBE")


def test_READ_resolved_fields_and_parity_with_experimental_reader(lab):
    ref = lab.write(lab.note("g", claim_contract(TRANSFER, "internal", "reversible", False), approved=True))
    r = lab.read(ref)
    assert r.status == "RESOLVED" and r.refs == ("g",) and r.declared_effect == ("internal", "reversible") and r.claimed_scope.approval_required is False
    assert r.tenant_id == "tenant-a" and r.schema_version == 1 and r.binding_digest == scope_digest(r.claimed_scope) and len(r.record_hash) == 64
    assert r.provenance["source_kind"] == "memory" and r.provenance["authority_class"] == "observation" and r.claims[0].origin == "memory"
    rec = lab.mem().fetch(ref.rsplit("/", 1)[1]); ev = ma.read_evidence([rec])
    assert (ev.refs, ev.contract, ma.declared_effect(ev.contract), ev.claims) == (r.refs, r.claimed_scope, r.declared_effect, r.claims)
    e = r.evidence(); assert isinstance(e, rt.DeclaredEvidence) and e.tenant_id == "tenant-a" and e.record_hashes == (r.record_hash,)
    for name in ("grant", "authority_evidence", "canonical_effect", "origin", "approval_state", "freshness"):
        assert not hasattr(r, name)


@pytest.mark.parametrize("kind,expected", [
    ("not found", "NOT_FOUND"), ("malformed ref", "INVALID"), ("wrong tenant", "WRONG_TENANT"), ("missing tenant", "WRONG_TENANT"), ("tenant store absent", "UNAVAILABLE"),
    ("corrupt log", "CORRUPT"), ("digest mismatch", "CORRUPT"), ("unsupported schema", "UNSUPPORTED_VERSION"), ("revoked record", "INVALID"),
    ("not a note", "INVALID"), ("not json", "INVALID"), ("duplicate keys", "INVALID"), ("nan", "INVALID"), ("empty string in scope", "INVALID"),
    ("negative int", "INVALID"), ("bool as int", "INVALID"), ("scope extra key", "INVALID"), ("scope missing key", "INVALID"), ("bad enum", "INVALID"),
    ("approval not bool", "INVALID"), ("grant_ref non-string", "RESOLVED"), ("scope absent", "RESOLVED")])
def test_STATUS_matrix(lab, kind, expected):
    good = lab.note("g", contract_of(TRANSFER)); ref = lab.write(good); tenant = T_A
    if kind == "not found":
        ref = "memory://tenant-a/none"
    elif kind == "malformed ref":
        ref = "mem:/tenant-a/m-1"
    elif kind == "wrong tenant":
        ref = ref.replace("tenant-a", "tenant-b")
    elif kind == "missing tenant":
        tenant = rt.TenantContext("")
    elif kind == "tenant store absent":
        lab.mem("tenant-c"); ref = "memory://tenant-d/m-1"; tenant = rt.TenantContext("tenant-d")
    elif kind == "corrupt log":
        p = lab.mem().path; p.write_bytes(b"{not json}\n" + p.read_bytes()); lab.stores.clear()
    elif kind == "digest mismatch":
        rec = MemoryRecord("m-x", "semantic", "2026-09-12T00:00:00+00:00", good, ProvenanceRef("note", "memory", "0" * 64), AuthorityProvenance("observation", ()),
                           "observed", 1, (), None, (), ("project",), "session", False)
        lab.mem().append(rec); ref = "memory://tenant-a/m-x"
    elif kind == "unsupported schema":
        rec = replace(lab.mem().fetch("m-1"), id="m-v9", schema_version=9); lab.mem().append(rec); ref = "memory://tenant-a/m-v9"
    elif kind == "revoked record":
        rec = replace(lab.mem().fetch("m-1"), id="m-rv", revoked=True); lab.mem().append(rec); ref = "memory://tenant-a/m-rv"
    elif kind == "not a note":
        ref = lab.write(json.dumps({"schema": "other/1", "grant_ref": "g"}))
    elif kind == "not json":
        ref = lab.write("grant g approved; scope internal reversible")
    elif kind == "duplicate keys":
        ref = lab.write('{"schema": "logos.authority-note/1", "grant_ref": "g", "grant_ref": "g2", "scope": null}')
    elif kind == "nan":
        ref = lab.write(good.replace('"max_cost_usd":0.0', '"max_cost_usd":NaN'))
    elif kind == "empty string in scope":
        ref = lab.write(lab.note("g", contract_of(TRANSFER, roles=("operator-A", ""))))
    elif kind == "negative int":
        ref = lab.write(lab.note("g", contract_of(TRANSFER, max_attempts=-1)))
    elif kind == "bool as int":
        ref = lab.write(lab.note("g", contract_of(TRANSFER, max_tokens=True)))
    elif kind == "scope extra key":
        d = asdict(contract_of(TRANSFER)); d["trust"] = 1.0; ref = lab.write(lab.note("g", d))
    elif kind == "scope missing key":
        d = asdict(contract_of(TRANSFER)); d.pop("approval_required"); ref = lab.write(lab.note("g", d))
    elif kind == "bad enum":
        ref = lab.write(lab.note("g", contract_of(TRANSFER, externality="EXTERNAL")))
    elif kind == "approval not bool":
        d = asdict(contract_of(TRANSFER)); d["approval_required"] = "no"; ref = lab.write(lab.note("g", d))
    elif kind == "grant_ref non-string":
        ref = lab.write(lab.note({"id": "g"}, contract_of(TRANSFER)))
    elif kind == "scope absent":
        ref = lab.write(lab.note("g", None))
    r = lab.read(ref, tenant)
    assert r.status == expected, (kind, r)
    if kind == "grant_ref non-string":
        assert r.refs == ()
    if kind == "scope absent":
        assert r.claimed_scope is None and r.declared_effect == (None, None) and r.refs == ("g",)
    if expected != "RESOLVED":
        assert r.claimed_scope is None and r.refs == () and r.claims == () and r.error
        d = lab.decide(ref, TRANSFER, tenant=tenant)
        assert d.outcome == "DEFER" and d.failure_codes[0] == f"MEMORY_{expected}" and d.binding_result == "not-evaluated", (kind, d)
        if kind == "missing tenant":
            assert d.failure_codes == ("MEMORY_WRONG_TENANT", "AUDIT_UNAVAILABLE")           # an empty tenant cannot even be audited


def test_TENANT_isolation_structural(lab):
    lab.grant("g", TRANSFER)
    ref_a = lab.write(lab.note("g", contract_of(TRANSFER)), tenant="tenant-a")
    ref_b = lab.write(lab.note("g", contract_of(TRANSFER)), tenant="tenant-b")
    assert lab.decide(ref_a, TRANSFER, tenant=T_A).outcome == "ALLOW"
    assert lab.decide(ref_a, TRANSFER, tenant=T_B).failure_codes == ("MEMORY_WRONG_TENANT",)
    assert lab.decide(ref_b, TRANSFER, tenant=T_A).failure_codes == ("MEMORY_WRONG_TENANT",)
    assert lab.read("memory://tenant-a/m-2", T_A).status == "NOT_FOUND"                      # tenant-b's record is not visible through tenant-a's store
    assert lab.read("memory://tenant-b/m-2", T_B).status == "RESOLVED"
    assert mr.parse_ref("memory://../tenant-b/m-2") is None and mr.parse_ref("memory://tenant-a/../m-2") is None


def test_BRIDGE_end_to_end_with_production_reader_rad_ce1(lab):
    ref = lab.write(lab.note(None, claim_contract(TRANSFER, "internal", "reversible", False), approved=True, gamma_result="VALID"))
    rec = lab.mem().fetch("m-1")
    assert ma.evaluate_with_memory_prerepair([rec], TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A, fallback_contract=contract_of(TRANSFER))[0] == "ALLOW"
    assert rd.b2_bridge([rec], TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW"
    d = lab.decide(ref, TRANSFER)
    assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_NO_GRANT",) and d.trace["effect"] == "external/irreversible/approval=True" and d.declared_effect == ("internal", "reversible")
    assert lab.sink.events[-1]["bridge_outcome"] == "DENY" and lab.sink.verify() == []
    lab.grant("g", TRANSFER)
    ref2 = lab.write(lab.note("g", contract_of(TRANSFER)))
    d2 = lab.decide(ref2, TRANSFER); assert d2.outcome == "ALLOW" and d2.trace["memory_status"] == "RESOLVED" and d2.authority_ref["grant_id"] == "g"


# ==========================================================================
# MEM-P1..P12
# ==========================================================================

S_KEY = st.sampled_from(sorted(KNOWN)); S_EXT = st.sampled_from(EXT); S_REV = st.sampled_from(REV)


def _rows(case, d: rt.BridgeDecision, reference: str, action):
    ROWS.append({"case": case, "outcome": d.outcome, "reference": reference, "codes": d.failure_codes, "false_allow": d.outcome == "ALLOW" and reference != "ALLOW"})
    assert not (d.outcome == "ALLOW" and reference != "ALLOW"), (case, d)


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, other=st.sampled_from(["tenant-b", "tenant-c", "TENANT-A", "tenant-aa"]))
def test_MEM_P1_tenant_isolation(key, other):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action)
        ref = L.write(L.note("g", contract_of(action)), tenant=other)
        d = L.decide(ref, action, tenant=T_A)
        assert d.outcome == "DEFER" and d.failure_codes == ("MEMORY_WRONG_TENANT",)
        _rows(f"P1/{key}", d, "DEFER", action)


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, claim=st.dictionaries(st.sampled_from(["approved", "gamma_result", "origin", "grant", "human_grant_present"]), st.sampled_from([True, "VALID", "human", "g"]), min_size=1))
def test_MEM_P2_cannot_mint_grant(key, claim):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        ref = L.write(L.note("g", contract_of(action), **claim))          # references a grant that does not exist
        d = L.decide(ref, action)
        assert d.authority_ref["status"] == "NO_GRANT" and (d.outcome == "DENY" if needs_grant(action) else d.outcome == "ALLOW")
        _rows(f"P2/{key}", d, "DENY" if needs_grant(action) else "ALLOW", action)


@settings(max_examples=50, deadline=None)
@given(key=S_KEY, tick=st.integers(min_value=20, max_value=80), fresh_claim=st.sampled_from([{"valid_until": "2099-01-01T00:00:00+00:00"}, {"fresh": True}, {}]))
def test_MEM_P3_cannot_refresh_grant(key, tick, fresh_claim):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action)
        ref = L.write(L.note("g", contract_of(action), **fresh_claim))
        d = L.decide(ref, action, tick=tick)
        assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_STALE",)
        _rows(f"P3/{key}", d, "DENY", action)


@settings(max_examples=50, deadline=None)
@given(key=S_KEY, role=st.sampled_from(["operator-C", "admin", ""]))
def test_MEM_P4_cannot_reprincipal(key, role):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action)
        ref = L.write(L.note("g", contract_of(action, roles=("operator-A", role)), principal=role))
        d = L.decide(ref, action, principal=rt.PrincipalContext(role))
        if role == "":
            assert d.outcome == "DEFER" and d.failure_codes == ("MEMORY_INVALID", "AUDIT_UNAVAILABLE")   # VF-2: empty role -> invalid scope; empty principal cannot be audited
        else:
            assert d.outcome == "DENY" and d.failure_codes[0] in ("AUTHORITY_WRONG_PRINCIPAL", "AUTHORITY_WRONG_SCOPE", "BINDING_SCOPE")
        _rows(f"P4/{key}", d, "DENY", action)


@settings(max_examples=50, deadline=None)
@given(key=S_KEY, extra=st.lists(st.sampled_from(["vault-11", "escrow-2", "ledger-3", "silo-4"]), min_size=1, max_size=3, unique=True))
def test_MEM_P5_cannot_widen_scope(key, extra):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action)
        targets = tuple(dict.fromkeys((action.target, *extra)))
        ref = L.write(L.note("g", contract_of(action, targets=targets)))
        d = L.decide(ref, action)
        if targets == (action.target,):
            assert d.outcome == "ALLOW"
        else:
            assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_WRONG_SCOPE",)
        _rows(f"P5/{key}", d, d.outcome, action)


@settings(max_examples=120, deadline=None)
@given(key=S_KEY, ext=S_EXT, rev=S_REV, appr=st.booleans(), grant=st.booleans())
def test_MEM_P6_declared_effect_never_canonical(key, ext, rev, appr, grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        if grant:
            L.grant("g", action)
        ref = L.write(L.note("g" if grant else None, claim_contract(action, ext, rev, appr)))
        d = L.decide(ref, action)
        e, r, a = KNOWN[key]
        assert d.trace["effect"] == f"{e}/{r}/approval={a}" and d.declared_effect == (ext, rev) and d.canonical_effect_ref["definition_id"].startswith("ce-")
        ref_out = "ALLOW" if (grant and (ext, rev, appr) == (e, r, a)) or (not grant and not needs_grant(action)) else "DENY"
        _rows(f"P6/{key}", d, ref_out if d.outcome != "DEFER" else "DEFER", action)


@settings(max_examples=50, deadline=None)
@given(key=S_KEY, kind=st.sampled_from(["digest", "nan", "duplicate", "not-json", "revoked"]))
def test_MEM_P7_corrupt_record_cannot_increase_authority(key, kind):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action); good = L.note("g", contract_of(action))
        if kind == "digest":
            L.mem().append(MemoryRecord("m-x", "semantic", "2026-09-12T00:00:00+00:00", good, ProvenanceRef("note", "memory", "1" * 64), AuthorityProvenance("observation", ()),
                                        "observed", 1, (), None, (), ("project",), "session", False)); ref = "memory://tenant-a/m-x"
        elif kind == "nan":
            ref = L.write(good.replace('"max_cost_usd":0.0', '"max_cost_usd":Infinity'))
        elif kind == "duplicate":
            ref = L.write(good[:-1] + ',"grant_ref":"g"}')
        elif kind == "not-json":
            ref = L.write("{" + good)
        else:
            L.write(good); L.mem().append(replace(L.mem().fetch("m-1"), id="m-r", revoked=True)); ref = "memory://tenant-a/m-r"
        d = L.decide(ref, action)
        assert d.outcome == "DEFER" and d.failure_codes[0].startswith("MEMORY_")
        _rows(f"P7/{key}/{kind}", d, "DEFER", action)


@settings(max_examples=50, deadline=None)
@given(key=S_KEY, missing=st.sampled_from(["scope", "grant_ref", "schema"]))
def test_MEM_P8_missing_fields_cannot_increase_authority(key, missing):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action)
        doc = json.loads(L.note("g", contract_of(action))); doc.pop(missing)
        ref = L.write(json.dumps(doc, sort_keys=True, separators=(",", ":")))
        d = L.decide(ref, action)
        if missing == "schema":
            assert d.failure_codes == ("MEMORY_INVALID",)
        elif missing == "scope":
            assert d.failure_codes == ("NO_SCOPE_CONTRACT",)
        else:
            assert d.authority_ref["status"] == "NO_GRANT" and (d.outcome == "DENY" if needs_grant(action) else d.outcome == "ALLOW")
        _rows(f"P8/{key}/{missing}", d, "DEFER" if d.outcome == "DEFER" else ("DENY" if needs_grant(action) else "ALLOW"), action)


@settings(max_examples=40, deadline=None)
@given(key=S_KEY, reloads=st.integers(min_value=1, max_value=3))
def test_MEM_P9_reload_preserves_binding(key, reloads):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; L.grant("g", action)
        ref = L.write(L.note("g", contract_of(action)))
        first = L.read(ref)
        for _ in range(reloads):
            L.stores.clear(); r = L.read(ref)
            assert (r.status, r.refs, r.claimed_scope, r.binding_digest, r.record_hash) == (first.status, first.refs, first.claimed_scope, first.binding_digest, first.record_hash)
        d = L.decide(ref, action); assert d.outcome == "ALLOW"
        _rows(f"P9/{key}", d, "ALLOW", action)


@settings(max_examples=60, deadline=None)
@given(key=S_KEY, grant_state=st.sampled_from(["absent", "human", "model", "revoked", "stale"]))
def test_MEM_P10_direct_canonical_equivalence(key, grant_state):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]; tick = TICK
        if grant_state != "absent":
            L.grant("g", action, origin="model" if grant_state == "model" else "human")
        if grant_state == "revoked":
            L.ledger.revoke("g"); L.store.revoke("g", at_tick=TICK)
        if grant_state == "stale":
            tick = WINDOW[1] + 1
        ref = L.write(L.note("g" if grant_state != "absent" else None, contract_of(action)))
        d = L.decide(ref, action, tick=tick)
        expected = "ALLOW" if grant_state == "human" or (grant_state == "absent" and not needs_grant(action)) else "DENY"
        assert d.outcome == expected, (key, grant_state, d)
        _rows(f"P10/{key}/{grant_state}", d, expected, action)


@settings(max_examples=30, deadline=None)
@given(ext=S_EXT, rev=S_REV, appr=st.booleans())
def test_MEM_P11_rad_ce1_remains_deny(ext, rev, appr):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t))
        ref = L.write(L.note(None, claim_contract(TRANSFER, ext, rev, appr), approved=True))
        d = L.decide(ref, TRANSFER)
        assert d.outcome == "DENY" and d.trace["effect"] == "external/irreversible/approval=True"
        _rows("P11", d, "DENY", TRANSFER)


@settings(max_examples=40, deadline=None)
@given(key=S_KEY, aclass=st.sampled_from(["observation", "instruction", "policy", "grant"]), skind=st.sampled_from(["memory", "human", "system"]),
       trust=st.floats(0, 1, allow_nan=False), voi=st.floats(0, 1, allow_nan=False))
def test_MEM_P12_map_rss_petg_voi_invariants(key, aclass, skind, trust, voi):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = ACTIONS[key]
        ref = L.write(L.note("g", contract_of(action), trust=trust, voi=voi, reliability="gold"), authority_class=aclass, source_kind=skind)
        d = L.decide(ref, action)
        assert d.authority_ref["status"] == "NO_GRANT" and d.trace["effect"].startswith(KNOWN[key][0])
        _rows(f"P12/{key}", d, "DENY" if needs_grant(action) else "ALLOW", action)


# ==========================================================================
# Mutation suite (12)
# ==========================================================================

def _battery():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); L.grant("g", TRANSFER)
        ref_a = L.write(L.note("g", contract_of(TRANSFER)))
        ref_b = L.write(L.note("g", contract_of(TRANSFER)), tenant="tenant-b")
        assert L.decide(ref_b, TRANSFER, tenant=T_A).failure_codes == ("MEMORY_WRONG_TENANT",), "wrong-tenant"
        assert L.read(ref_a, rt.TenantContext("")).status == "WRONG_TENANT", "missing-tenant"
        assert L.read(ref_a, T_B).status == "WRONG_TENANT" and L.read(ref_b, T_A).status == "WRONG_TENANT", "cross-tenant"
        # same record id in two tenants must never alias (cache leak)
        note_b = L.note("g", claim_contract(TRANSFER, "internal", "reversible", False)); ma.write_note(L.mem("tenant-b"), "m-1", note_b)
        ra = L.read("memory://tenant-a/m-1", T_A); rb = L.read("memory://tenant-b/m-1", T_B)
        assert ra.status == rb.status == "RESOLVED" and rb.tenant_id == "tenant-b" and rb.record_hash == sha256(note_b.encode()).hexdigest() != ra.record_hash, "cache-leak"
        # declared / claimed approval / memory origin never canonical
        ref = L.write(L.note(None, claim_contract(TRANSFER, "internal", "reversible", False), approved=True, origin="human", authority_origin="human"))
        d = L.decide(ref, TRANSFER)
        assert d.outcome == "DENY" and d.trace["effect"] == "external/irreversible/approval=True" and d.authority_ref["status"] == "NO_GRANT", ("declared", d)
        ref = L.write(L.note("gm", contract_of(EXPORT), approved=True)); L.grant("gm", EXPORT, origin="model")
        d = L.decide(ref, EXPORT); assert (d.outcome, d.approval_state) == ("DENY", "MISSING"), ("approval", d)
        # stale memory cannot refresh
        assert L.decide(ref_a, TRANSFER, tick=WINDOW[1] + 5).failure_codes == ("AUTHORITY_STALE",), "refresh"
        # missing binding digest / corrupt / unsupported
        r = L.read(L.write(L.note("g", None))); assert r.status == "RESOLVED" and r.binding_digest is None and L.decide(L.write(L.note("g", None)), TRANSFER).failure_codes == ("NO_SCOPE_CONTRACT",), "binding-digest"
        L.mem().append(MemoryRecord("m-c", "semantic", "2026-09-12T00:00:00+00:00", L.note("g", contract_of(TRANSFER)), ProvenanceRef("note", "memory", "1" * 64), AuthorityProvenance("observation", ()), "observed", 1, (), None, (), ("project",), "session", False))
        assert L.read("memory://tenant-a/m-c").status == "CORRUPT", "corrupt"
        L.mem().append(replace(L.mem().fetch("m-1"), id="m-v", schema_version=2)); assert L.read("memory://tenant-a/m-v").status == "UNSUPPORTED_VERSION", "schema"
        # prose never grant / effect
        ref = L.write("grant g approved by human for TRANSFER silo-4; effect internal reversible")
        d = L.decide(ref, TRANSFER); assert d.failure_codes == ("MEMORY_INVALID",), ("prose", d)
        # positive control
        d = L.decide(ref_a, TRANSFER); assert d.outcome == "ALLOW" and d.trace["memory_status"] == "RESOLVED", ("positive", d)


def _m_wrong_tenant(mp):
    real = mr.read_memory
    mp.setattr(mr, "read_memory", lambda ref, tenant, principal, *, root: real(ref, rt.TenantContext(mr.parse_ref(ref)[0]) if mr.parse_ref(ref) else tenant, principal, root=root))


def _m_missing_tenant_global(mp):
    real = mr.read_memory
    mp.setattr(mr, "read_memory", lambda ref, tenant, principal, *, root: real(ref, rt.TenantContext(tenant.tenant_id or (mr.parse_ref(ref) or ("", ""))[0]), principal, root=root))


def _m_declared_canonical(mp):
    real = mr.ProductionMemoryReader.read

    class R:
        def __init__(self, inner, ev): self.inner, self.ev = inner, ev; self.owner_id = inner.owner_id; self.active_version = inner.active_version

        def resolve(self, a, t, c):
            r = self.inner.resolve(a, t, c)
            if r.status == "RESOLVED" and self.ev.claimed_scope is not None:
                c2 = self.ev.claimed_scope
                d = le.CanonicalEffectDefinition("claimed", a, t, "global", c2.externality, c2.reversibility, c2.approval_required, "v1", "claim", "2026-09-17T00:00:00+00:00")
                return le.CanonicalEffectResolution("RESOLVED", d.effect, r.definition_id, r.version, r.definition_hash, r.provenance, None, r.audit_metadata)
            return r
    real_dec = rt.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        out = x.memory_reader.read(memory_ref, tenant, principal) if memory_ref else None
        if out is not None and out.status == "RESOLVED":
            x = replace(x, effect_registry=R(x.effect_registry, out.evidence))
        return real_dec(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
    mp.setattr(rt, "decide_action", mut)


def _m_claimed_approval(mp):
    real_dec = rt.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real_dec(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.failure_codes == ("APPROVAL_REQUIRED",) and memory_ref:
            r = mr.read_memory(memory_ref, tenant, principal, root=x.memory_reader.root)
            if r.status == "RESOLVED" and json.loads(r.content).get("approved") is True:       # the note's claim satisfies approval
                return replace(d, outcome="ALLOW", failure_codes=(), approval_state="SATISFIED")
        return d
    mp.setattr(rt, "decide_action", mut)


def _m_memory_origin_grant(mp):
    real_dec = rt.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real_dec(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.failure_codes == ("AUTHORITY_NO_GRANT",) and memory_ref:
            return replace(d, outcome="ALLOW", failure_codes=(), authority_ref={**d.authority_ref, "status": "RESOLVED", "grant_origin": "memory"})
        return d
    mp.setattr(rt, "decide_action", mut)


def _m_stale_refresh(mp):
    real_dec = rt.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real_dec(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        if d.failure_codes == ("AUTHORITY_STALE",):
            return real_dec(principal, action, target, memory_ref, state, tenant, replace(x, tick=TICK), evidence=evidence)   # memory "refreshes" the window
        return d
    mp.setattr(rt, "decide_action", mut)


def _m_missing_digest(mp):
    real = mr.read_record

    def mut(record, tenant):
        r = real(record, tenant)
        if r.status == "RESOLVED" and r.claimed_scope is None:
            return replace(r, claimed_scope=contract_of(TRANSFER), binding_digest=scope_digest(contract_of(TRANSFER)))   # a default scope for digest-less notes
        return r
    mp.setattr(mr, "read_record", mut)


def _m_corrupt_accepted(mp):
    real = mr.read_record

    def mut(record, tenant):
        r = real(record, tenant)
        if r.status == "CORRUPT":
            return real(replace(record, source=replace(record.source, content_digest=sha256(record.content.encode()).hexdigest())), tenant)
        return r
    mp.setattr(mr, "read_record", mut)


def _m_unsupported_schema(mp):
    mp.setattr(mr, "SUPPORTED_SCHEMA_VERSIONS", frozenset({1, 2, 9}))


def _m_cache_leak(mp):
    real = mr.read_memory
    cache: dict = {}

    def mut(ref, tenant, principal, *, root):
        rid = (mr.parse_ref(ref) or ("", ""))[1]
        if rid in cache:
            return cache[rid]                                       # keyed by record id only: tenant-a's record served to tenant-b
        r = real(ref, tenant, principal, root=root)
        if r.status == "RESOLVED":
            cache[rid] = r
        return r
    mp.setattr(mr, "read_memory", mut)


def _m_prose_grant(mp):
    real = mr.read_record

    def mut(record, tenant):
        r = real(record, tenant)
        if r.status == "INVALID" and "approved" in record.content and "grant g" in record.content:
            return mr.MemoryReadResult("RESOLVED", record_id=record.id, tenant_id=tenant, schema_version=1, content=record.content, refs=("g",),
                                       claimed_scope=contract_of(TRANSFER), binding_digest=scope_digest(contract_of(TRANSFER)), record_hash=r.record_hash,
                                       declared_effect=("internal", "reversible"), claims=(rt.proposer_claim("TRANSFER", "silo-4"),))
        return r
    mp.setattr(mr, "read_record", mut)


def _m_prose_effect(mp):
    real = mr.read_record

    def mut(record, tenant):
        r = real(record, tenant)
        if r.status == "INVALID" and "effect internal reversible" in record.content:
            return mr.MemoryReadResult("RESOLVED", record_id=record.id, tenant_id=tenant, schema_version=1, content=record.content, refs=(),
                                       claimed_scope=claim_contract(TRANSFER, "internal", "reversible", False), binding_digest="0" * 64, record_hash=r.record_hash,
                                       declared_effect=("internal", "reversible"), claims=())
        return r
    mp.setattr(mr, "read_record", mut)


MUTANTS = [("wrong tenant accepted", _m_wrong_tenant), ("missing tenant defaults global", _m_missing_tenant_global), ("declared effect -> canonical", _m_declared_canonical),
           ("claimed approval -> canonical approval", _m_claimed_approval), ("memory origin -> grant origin", _m_memory_origin_grant), ("stale memory refreshes grant", _m_stale_refresh),
           ("missing binding digest accepted", _m_missing_digest), ("corrupt record accepted", _m_corrupt_accepted), ("unsupported schema permissive", _m_unsupported_schema),
           ("cross-tenant cache leak", _m_cache_leak), ("memory prose -> grant", _m_prose_grant), ("memory prose -> canonical effect", _m_prose_effect)]


def test_MUT_battery_clean():
    _battery()


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[f"M{i + 1}" for i in range(len(MUTANTS))])
def test_MUT_caught(label, apply, monkeypatch):
    apply(monkeypatch)
    with pytest.raises(AssertionError) as e:
        _battery()
    CAUGHT[label] = str(e.value)[:120]


def test_MUT_zz_all_twelve_caught():
    assert len(MUTANTS) == 12 and set(CAUGHT) == {m[0] for m in MUTANTS}


def test_zz_aggregate():
    assert len(ROWS) >= 500, len(ROWS)
    assert [r["case"] for r in ROWS if r["false_allow"]] == [] and any(r["outcome"] == "ALLOW" for r in ROWS)
    out = os.environ.get("C4_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"rows": len(ROWS), "false_allows": 0, "mutants": CAUGHT,
                                         "outcomes": {o: sum(1 for r in ROWS if r["outcome"] == o) for o in ("ALLOW", "DENY", "DEFER")}}, indent=1), encoding="utf-8")
