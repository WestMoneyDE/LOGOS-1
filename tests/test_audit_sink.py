"""CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1 — phase C3: the production audit sink
(`logos_audit`) — schema, hash chain, failure semantics, reconstruction, tenant
partitioning, and the rule that audit evidence is never authority.
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
import logos_runtime as rt
from logos_research import experiments
from logos_runtime import bridge as rt_bridge
from test_production_bridge import ACTIONS, EXPORT, KNOWN, STATE_A, TENANT, TICK, TRANSFER, UNKNOWN, Lab, claim_contract, contract_of, evidence_from, principal_of

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CAUGHT: dict[str, str] = {}
ROWS: list[dict] = []


def lab_with_sink(tmp: Path, sink=None):
    L = Lab(tmp); L.sink = sink if sink is not None else au.InMemoryAuditSink(clock=lambda: "2026-09-17T00:00:00+00:00")
    return L


def run(L: Lab, records, action, *, tenant=TENANT, tick=TICK, sink=None, principal=None):
    ev = evidence_from(records)
    if tenant is not TENANT:
        ev = replace(ev, tenant_id=tenant.tenant_id)
    return rt.decide_action(principal or principal_of(action), action.action, action.target, None, STATE_A, tenant, L.ctx(tick, sink=sink or L.sink), evidence=ev)


# ==========================================================================
# Schema / integrity
# ==========================================================================

def test_EVENT_schema_complete_and_chained(tmp_path):
    L = lab_with_sink(tmp_path); L.grant("g", TRANSFER)
    rec = L.write(L.note("g", contract_of(TRANSFER)))
    d1 = run(L, [rec], TRANSFER); d2 = run(L, [rec], EXPORT)
    ev = L.sink.events
    assert len(ev) == 2 and L.sink.verify() == [] and set(au.REQUIRED_FIELDS) <= set(ev[0])
    assert ev[0]["previous_event_hash"] == au.GENESIS and ev[1]["previous_event_hash"] == ev[0]["event_hash"] and ev[0]["sequence"] == 0
    assert ev[0]["bridge_outcome"] == d1.outcome == "ALLOW" and ev[0]["grant_id"] == "g" and ev[0]["effect_definition_id"] == "ce-transfer-silo-4"
    assert ev[0]["effect_hash"] == d1.canonical_effect_ref["definition_hash"] and ev[0]["scope_digest"] and len(ev[0]["scope_digest"]) == 64
    assert ev[1]["bridge_outcome"] == d2.outcome == "DEFER" and ev[1]["failure_codes"] == list(d2.failure_codes) and ev[1]["authority_resolution_status"] == "NO_GRANT" or ev[1]["bridge_outcome"] == "DENY"
    assert d1.trace["audit"] == "recorded" and d1.trace["audit_event_hash"] == ev[0]["event_hash"]
    for e in ev:
        assert au.validate_event(e) == [] and e["api_version"] == "v1" and e["schema_version"] == au.AUDIT_SCHEMA_VERSION
        assert "grant_ref" not in json.dumps(e) and "content" not in e            # no payloads / secrets


def test_EVENT_reconstruction(tmp_path):
    L = lab_with_sink(tmp_path); L.grant("g", EXPORT, origin="model")
    rec = L.write(L.note("g", claim_contract(EXPORT, "internal", "reversible", False)))
    d = run(L, [rec], EXPORT)
    r = au.reconstruct(L.sink.events[-1])
    assert r["effect_owner"]["definition_id"] == "ce-export-ledger-3" and r["effect_owner"]["version"] == "v1" and len(r["effect_owner"]["hash"]) == 64
    assert r["grant"] == {"grant_id": "g", "version": "v1", "origin": "model", "status": d.authority_ref["status"], "revocation": d.authority_ref["revocation_state"]}
    assert r["principal_scope_state"]["principal"] == "operator-A" and r["principal_scope_state"]["state_hash"] == STATE_A and r["principal_scope_state"]["tenant"] == "tenant-a"
    assert r["binding_approval"] == {"binding": d.binding_result, "approval": d.approval_state} and r["bridge_outcome"] == d.outcome == "DENY"
    assert r["failure_codes"] == list(d.failure_codes) and r["gamma_outcome"] in ("not-evaluated", "INVALID", "VALID", "UNCLEAR")


def test_JSONL_durable_reload_and_unwritable(tmp_path):
    p = tmp_path / "audit" / "events.jsonl"
    L = lab_with_sink(tmp_path, au.JsonlAuditSink(p, clock=lambda: "2026-09-17T00:00:00+00:00")); L.grant("g", TRANSFER)
    rec = L.write(L.note("g", contract_of(TRANSFER)))
    for _ in range(3):
        run(L, [rec], TRANSFER)
    again = au.JsonlAuditSink.load(p)
    assert len(again.events) == 3 and again.verify() == [] and again.events == L.sink.events
    run(L, [rec], TRANSFER); assert au.JsonlAuditSink.load(p).verify() == [] and len(au.JsonlAuditSink.load(p).events) == 4
    broken = au.JsonlAuditSink(tmp_path / "audit" / "events.jsonl" / "not-a-dir" / "x.jsonl")          # parent is a file -> cannot write
    d = run(L, [rec], TRANSFER, sink=broken)
    assert d.outcome == "DEFER" and d.failure_codes == ("AUDIT_UNAVAILABLE",) and d.trace["computed_outcome"] == "ALLOW"


def test_FAILURE_semantics_defer_never_silent(tmp_path):
    L = lab_with_sink(tmp_path); L.grant("g", TRANSFER)
    rec = L.write(L.note("g", contract_of(TRANSFER)))
    for sink in (au.InMemoryAuditSink(available=False), au.InMemoryAuditSink(writer=lambda e: (_ for _ in ()).throw(OSError("disk full")))):
        d = run(L, [rec], TRANSFER, sink=sink)
        assert d.outcome == "DEFER" and d.failure_codes == ("AUDIT_UNAVAILABLE",) and d.trace["audit"] == "unavailable" and sink.events == []
    with pytest.raises(au.AuditUnavailable):
        au.InMemoryAuditSink().emit({"run_id": "r"})                                  # incomplete event is refused, not padded


def test_TENANT_partition(tmp_path):
    L = lab_with_sink(tmp_path); L.grant("g", TRANSFER)
    rec = L.write(L.note("g", contract_of(TRANSFER)))
    run(L, [rec], TRANSFER); run(L, [rec], TRANSFER, tenant=rt.TenantContext("tenant-b"))
    a, b = L.sink.events_for("tenant-a"), L.sink.events_for("tenant-b")
    assert len(a) == 1 and len(b) == 1 and a[0]["tenant_id"] == "tenant-a" and b[0]["tenant_id"] == "tenant-b" and L.sink.verify() == []


def test_AUDIT_is_not_authority_static():
    for py in (SRC / "logos_runtime").glob("*.py"):
        txt = py.read_text(encoding="utf-8")
        assert "events_for" not in txt and "sink.events" not in txt and ".verify(" not in txt and "reconstruct" not in txt, py.name
        for n in ast.walk(ast.parse(txt)):
            if isinstance(n, ast.Attribute) and n.attr == "audit_sink":
                pass
        assert re.findall(r"audit_sink\.(\w+)", txt) in ([], ["emit"]), py.name          # the bridge only ever calls emit()
    for py in (SRC / "logos_audit").glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 else [])
            for m in mods:
                assert m.split(".")[0] in {"json", "dataclasses", "datetime", "hashlib", "pathlib", "typing", "__future__", "logos_runtime"}, (py.name, m)
    assert "logos_audit" in experiments.PRODUCTION_PACKAGES
    with pytest.raises(ImportError):
        experiments.assert_experimental_caller(["logos_audit"])


@settings(max_examples=60, deadline=None)
@given(key=st.sampled_from(sorted(KNOWN)), n=st.integers(min_value=1, max_value=6), grant=st.booleans())
def test_CHAIN_property_every_decision_recorded_and_verifiable(key, n, grant):
    with tempfile.TemporaryDirectory() as t:
        L = lab_with_sink(Path(t)); action = ACTIONS[key]
        if grant:
            L.grant("g", action)
        rec = L.write(L.note("g" if grant else None, contract_of(action)))
        outs = [run(L, [rec], action).outcome for _ in range(n)]
        assert len(L.sink.events) == n and L.sink.verify() == [] and [e["bridge_outcome"] for e in L.sink.events] == outs
        assert all(e["effect_definition_id"] and e["authority_resolution_status"] for e in L.sink.events)
        ROWS.extend({"case": f"chain/{key}", "outcome": o} for o in outs)


# ==========================================================================
# Mutation suite (12)
# ==========================================================================

def _battery():
    with tempfile.TemporaryDirectory() as t:
        L = lab_with_sink(Path(t)); L.grant("g", TRANSFER)
        rec = L.write(L.note("g", contract_of(TRANSFER)))
        d1 = run(L, [rec], TRANSFER); d2 = run(L, [rec], TRANSFER, tenant=rt.TenantContext("tenant-b")); d3 = run(L, [rec], EXPORT)
        ev = L.sink.events
        assert len(ev) == 3, ("drop", len(ev))
        assert L.sink.verify() == [], ("chain", L.sink.verify())
        assert ev[0]["grant_id"] == d1.authority_ref["grant_id"] == "g", ("grant-id", ev[0]["grant_id"])
        assert ev[0]["effect_hash"] == d1.canonical_effect_ref["definition_hash"], "effect-hash"
        assert ev[0]["run_id"] == d1.trace["run_id"], "run-id"
        assert ev[0]["bridge_outcome"] == d1.outcome and ev[2]["bridge_outcome"] == d3.outcome, "outcome"
        assert len({e["event_id"] for e in ev}) == 3, "duplicate-id"
        assert [e["sequence"] for e in ev] == [0, 1, 2], "order"
        assert [e["tenant_id"] for e in L.sink.events_for("tenant-a")] == ["tenant-a", "tenant-a"] and [e["tenant_id"] for e in L.sink.events_for("tenant-b")] == ["tenant-b"], "tenant"
        assert d1.outcome == "ALLOW" and d1.trace["audit"] == "recorded", "positive"
        # audit is not authority: a grant-less consequential action stays DENY however many ALLOW events exist
        rec2 = L.write(L.note(None, contract_of(TRANSFER)))
        d = run(L, [rec2], TRANSFER); assert d.outcome == "DENY" and d.failure_codes == ("AUTHORITY_NO_GRANT",), ("audit-as-authority", d)
        # failing backend must surface as DEFER, never as a recorded-looking success
        failing = au.InMemoryAuditSink(writer=lambda e: (_ for _ in ()).throw(OSError("disk full")))
        d = run(L, [rec], TRANSFER, sink=failing)
        assert d.outcome == "DEFER" and d.failure_codes == ("AUDIT_UNAVAILABLE",) and failing.events == [], ("silent-failure", d, len(failing.events))


def _m_drop(mp):
    real = au.InMemoryAuditSink.emit

    def mut(self, event):
        if len(self.events) == 1:
            return "deadbeef" * 8                                  # second event silently dropped
        return real(self, event)
    mp.setattr(au.InMemoryAuditSink, "emit", mut)


def _m_manipulate(mp):
    real = au.InMemoryAuditSink.emit

    def mut(self, event):
        h = real(self, event); self.events[-1]["bridge_outcome"] = "ALLOW"; self.events[-1]["failure_codes"] = []; return h
    mp.setattr(au.InMemoryAuditSink, "emit", mut)


def _m_chain(mp):
    real = au.InMemoryAuditSink._seal

    def mut(self, event):
        e = real(self, event); e["previous_event_hash"] = au.GENESIS; e["event_hash"] = au.event_hash(e); return e
    mp.setattr(au.InMemoryAuditSink, "_seal", mut)


def _m_field(name, value):
    def apply(mp):
        real = au.InMemoryAuditSink._seal

        def mut(self, event):
            e = real(self, dict(event, **{name: value})); return e
        mp.setattr(au.InMemoryAuditSink, "_seal", mut)
    return apply


def _m_missing_outcome(mp):
    real = au.InMemoryAuditSink._seal
    mp.setattr(au, "validate_event", lambda e: [])                  # validation disabled ...

    def mut(self, event):
        ev = dict(event); ev.pop("bridge_outcome"); e = real(self, ev); return e   # ... and the outcome is dropped
    mp.setattr(au.InMemoryAuditSink, "_seal", mut)


def _m_dup_id(mp):
    real = au.InMemoryAuditSink._seal

    def mut(self, event):
        e = real(self, event); e["event_id"] = "evt-fixed"; e["event_hash"] = au.event_hash(e); return e
    mp.setattr(au.InMemoryAuditSink, "_seal", mut)


def _m_out_of_order(mp):
    real = au.InMemoryAuditSink.emit

    def mut(self, event):
        h = real(self, event)
        if len(self.events) == 3:
            self.events[0], self.events[1] = self.events[1], self.events[0]
        return h
    mp.setattr(au.InMemoryAuditSink, "emit", mut)


def _m_audit_as_authority(mp):
    real = rt_bridge.decide_action

    def mut(principal, action, target, memory_ref, state, tenant, x, *, evidence=None):
        d = real(principal, action, target, memory_ref, state, tenant, x, evidence=evidence)
        sink = x.audit_sink
        if d.failure_codes == ("AUTHORITY_NO_GRANT",) and sink is not None and any(e["bridge_outcome"] == "ALLOW" and e["action"] == action for e in getattr(sink, "events", [])):
            return replace(d, outcome="ALLOW", failure_codes=())                    # "it was allowed before" — audit used as authority
        return d
    mp.setattr(rt, "decide_action", mut)


def _m_silent_failure(mp):
    real = au.InMemoryAuditSink.emit

    def mut(self, event):
        try:
            return real(self, event)
        except au.AuditUnavailable:
            return "0" * 64                                         # failure swallowed
    mp.setattr(au.InMemoryAuditSink, "emit", mut)


def _m_cross_tenant(mp):
    mp.setattr(au.InMemoryAuditSink, "events_for", lambda self, tenant_id: list(self.events))


MUTANTS = [("event drop", _m_drop), ("event manipulation", _m_manipulate), ("broken hash chain", _m_chain), ("wrong grant id", _m_field("grant_id", "g-other")),
           ("wrong effect hash", _m_field("effect_hash", "f" * 64)), ("wrong run id", _m_field("run_id", "other-run")), ("missing outcome", _m_missing_outcome),
           ("duplicate event id", _m_dup_id), ("out-of-order event", _m_out_of_order), ("audit evidence used as authority", _m_audit_as_authority),
           ("audit sink failure silently ignored", _m_silent_failure), ("cross-tenant audit mixup", _m_cross_tenant)]


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
    out = os.environ.get("C3_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"mutants": CAUGHT, "chain_rows": len(ROWS)}, indent=1), encoding="utf-8")
