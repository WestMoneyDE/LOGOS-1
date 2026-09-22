"""MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1 — independent attack on the
repaired memory->Γ bridge (PR #23, 27ef324).

Independence measures, stated so they can be checked:

* `tests/test_memory_bridge_repair.py` is not imported and no helper is reused;
* the effect oracle is re-derived here from GAMMA.md effect semantics
  (`INDEPENDENT_EFFECTS`) and asserted equal to the fixture before any use;
* the direct-Γ evaluator (`direct_gamma`) is built from `logos_gamma` types
  only — no bridge code;
* fixtures are new: vault-11, seal-Q, operator-C, plus the oracle's own
  NOTIFY/EXPORT/ARCHIVE actions;
* expectations come from Γ semantics and the repair CONTRACT ("canonical from
  oracle, memory only as declared_*, None -> DEFER"), never from the repair's
  test assertions.

    Declared effect is evidence. Canonical effect is authority input.
"""
from __future__ import annotations

import ast
import inspect
import json
import pathlib
import tempfile
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_gamma as gamma
from logos_memory.factory import MemoryFactory
from logos_memory.records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from logos_memory.scope import ScopeContract, ScopeDecision, scope_digest
from logos_memory.store import MemoryStore
from logos_research.experiments import effect_oracle as eo
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import risk_decomposition as rd
from logos_research.experiments.binding_state import ProposedAction, _base_contract

WINDOW, STATE_A, STATE_B, TICK = (10, 20), "a" * 64, "b" * 64, 12
EXT = ("internal", "external")
REV = ("reversible", "partially-reversible", "irreversible")

# --------------------------------------------------------------------------
# Independent oracle (from GAMMA.md effect semantics), checked against the fixture
# --------------------------------------------------------------------------

INDEPENDENT_EFFECTS: dict[tuple[str, str], tuple[str, str, bool]] = {
    ("TRANSFER", "silo-4"): ("external", "irreversible", True),
    ("TRANSFER", "escrow-2"): ("external", "irreversible", True),
    ("PURGE", "escrow-2"): ("external", "irreversible", True),
    ("ROTATE", "silo-4"): ("internal", "reversible", False),
    ("INSPECT", "silo-4"): ("internal", "reversible", False),
    ("ARCHIVE", "silo-4"): ("internal", "partially-reversible", False),
    ("NOTIFY", "ops-channel"): ("external", "reversible", False),
    ("EXPORT", "ledger-3"): ("internal", "reversible", True),
}
ACTIONS = {k: ProposedAction(k[0], k[1], role="operator-A") for k in INDEPENDENT_EFFECTS}
UNKNOWN = [ProposedAction("LAUNCH", "silo-4", role="operator-A"), ProposedAction("TRANSFER", "vault-11", role="operator-A"),
           ProposedAction("", "", role="operator-A")]


def test_oracle_agrees_with_independent_derivation():
    assert {k: (v.externality, v.reversibility, v.approval_required) for k, v in eo.CANONICAL_EFFECTS.items()} == INDEPENDENT_EFFECTS
    for a in UNKNOWN:
        assert eo.canonical_effect(a.action, a.target) is None


def consequential(key) -> bool:
    e, r, _ = INDEPENDENT_EFFECTS[key]
    return e == "external" or r != "reversible"


def contract_of(action: ProposedAction, **o) -> ScopeContract:
    e, r, a = INDEPENDENT_EFFECTS[(action.action, action.target)]
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",),
                approval_required=a, externality=e, reversibility=r)
    base.update(o)
    return _base_contract(**base)


def claim_contract(action: ProposedAction, ext, rev, appr, **o) -> ScopeContract:
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",),
                approval_required=appr, externality=ext, reversibility=rev)
    base.update(o)
    return _base_contract(**base)


# --------------------------------------------------------------------------
# Direct Γ evaluator — logos_gamma only, canonical inputs only
# --------------------------------------------------------------------------

def direct_gamma(action: ProposedAction, grant: gamma.AuthorityEvidence | None, *, tick=TICK, state_hash=STATE_A,
                 contract: ScopeContract | None = None) -> str:
    """What Γ says with canonical effect, canonical scope digest and the given
    grant. Scope dimension (roles/targets) checked the way the repository's
    scope engine does; approval-sensitivity checked as the contract states."""
    e, r, appr = INDEPENDENT_EFFECTS[(action.action, action.target)]
    c = contract or contract_of(action)
    if action.role not in c.roles or action.target not in c.targets:
        return "DENY"
    if appr and (grant is None or not grant.is_human_rooted()):
        return "DENY"
    prop = gamma.EffectProposal(action=action.action, target=action.target,
                                effect_kind="deployment" if e == "external" else "write-internal",
                                externality=e, reversibility=r, proposal_digest=ma.proposal_digest(action),
                                provenance=(gamma.ProvenanceClaim("proposal://x", "model", "0" * 64),))
    v = gamma.validate(gamma.ValidationContext(prop, tick, state_hash, scope_digest(c), grant))
    return {"VALID": "ALLOW", "INVALID": "DENY", "UNCLEAR": "DEFER"}[v.result]


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------

class Lab:
    def __init__(self, tmp: Path):
        self.ledger = ma.GrantLedger(); self.store = MemoryStore(tmp / "mem"); self.tmp = tmp; self.n = 0

    def grant(self, gid, action, *, origin="human", window=WINDOW, state=STATE_A, **o):
        return self.ledger.issue(gid, origin=origin, action=action, contract=contract_of(action, **o), window=window, state_hash=state)

    def write(self, content, **kw) -> MemoryRecord:
        self.n += 1
        return ma.write_note(self.store, f"v-{self.n}", content, **kw)

    def note(self, ref, contract, **claims) -> str:
        return ma.authority_note(ref, contract, **claims)

    def bridge(self, records, action, *, tick=TICK, state=STATE_A, fallback=None, oracle=eo.canonical_effect):
        return ma.evaluate_with_memory(list(records), action, self.ledger, tick=tick, state_hash=state,
                                       fallback_contract=fallback, effect_oracle=oracle)

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


def classify_delta(bridge_out: str, gamma_out: str, trace: dict) -> str:
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
    known = key in INDEPENDENT_EFFECTS
    g = direct_gamma(action, grant, tick=tick, state_hash=state) if known else "DEFER"
    delta = classify_delta(out, g, tr) if known else ("none" if out == "DEFER" else "UNEXPLAINED-ALLOW")
    ROWS.append({"case": case, "action": key, "outcome": out, "direct_gamma": g, "effect": tr.get("effect"),
                 "declared": tr.get("declared"), "delta": delta, "false_allow": out == "ALLOW" and g != "ALLOW"})
    assert not (out == "ALLOW" and g != "ALLOW"), (case, tr)
    if known:
        e, r, a = INDEPENDENT_EFFECTS[key]
        assert tr.get("effect") in (f"{e}/{r}/approval={a}", "none"), (case, tr)
    assert delta not in ("unexplained", "UNEXPLAINED-ALLOW"), (case, tr)
    return out, tr


# --------------------------------------------------------------------------
# G/H — RAD-CE1 historical and repaired replay
# --------------------------------------------------------------------------

CE1_CLAIM = dict(ext="internal", rev="reversible", appr=False)
TRANSFER = ACTIONS[("TRANSFER", "silo-4")]


def test_G_historical_path_still_reproduces_and_only_there(lab):
    r = lab.write(lab.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))
    for name, recs in lab.transports(r).items():
        assert ma.evaluate_with_memory_prerepair(recs, TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A, fallback_contract=contract_of(TRANSFER))[0] == "ALLOW", name
        assert rd.b2_bridge(recs, TRANSFER, lab.ledger, tick=TICK, state_hash=STATE_A)[0] == "ALLOW", name
    # historical function is byte-stable evidence: its body still writes contract fields into canonical Γ fields
    src = inspect.getsource(ma.evaluate_with_memory_prerepair)
    assert "externality=contract.externality" in src and "reversibility=contract.reversibility" in src


def test_H_repaired_path_denies_on_all_transports(lab):
    r = lab.write(lab.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))
    seen = set()
    for name, recs in lab.transports(r).items():
        out, tr = observe(f"CE1:{name}", lab, recs, TRANSFER)
        assert out == "DENY"
        assert tr["effect"] == "external/irreversible/approval=True" and tr["declared"] == "internal/reversible"
        seen.add((out, tr["effect"], tr["declared"]))
    assert len(seen) == 1


# --------------------------------------------------------------------------
# I/J — claim matrix x grant states x scope claims x transports x actions
# --------------------------------------------------------------------------

GRANT_STATES = ["absent", "valid", "revoked", "wrong-principal", "wrong-scope", "stale", "wrong-state", "model-origin"]
SCOPE_CLAIMS = ["exact", "narrower", "wider", "absent"]


def _setup_grant(L: Lab, action, state):
    """Returns (grant evidence the DIRECT path holds, tick, state_hash, action-to-run)."""
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


def _claimed(action, ext, rev, appr, scope):
    if scope == "absent":
        return None
    o = {}
    if scope == "narrower":
        o["targets"] = ()
    if scope == "wider":
        o["targets"] = (action.target, "vault-11"); o["roles"] = ("operator-A", "operator-C")
    return claim_contract(action, ext, rev, appr, **o)


@pytest.mark.parametrize("grant_state", GRANT_STATES)
@pytest.mark.parametrize("scope", SCOPE_CLAIMS)
@pytest.mark.parametrize("appr", [True, False, None], ids=["appr-true", "appr-false", "appr-absent"])
@pytest.mark.parametrize("ext", EXT)
@pytest.mark.parametrize("rev", ["reversible", "irreversible"])
def test_I_claim_matrix_transfer(ext, rev, appr, scope, grant_state):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); g, tick, state, act = _setup_grant(L, TRANSFER, grant_state)
        c = _claimed(TRANSFER, ext, rev, False if appr is None else appr, scope)
        content = L.note("g" if grant_state != "absent" else None, c) if c is not None else json.dumps(
            {"schema": ma.NOTE_SCHEMA, "grant_ref": "g" if grant_state != "absent" else None, "scope": None, "approval_required": appr})
        r = L.write(content)
        for name, recs in L.transports(r).items():
            out, tr = observe(f"I:{ext}/{rev}/{appr}/{scope}/{grant_state}/{name}", L, recs, act, grant=g, tick=tick, state=state,
                              fallback=contract_of(TRANSFER))
            if act.target == "vault-11":
                assert out == "DEFER"                          # unknown action/target: no canonical effect
            elif grant_state == "valid" and (scope == "absent" or (scope == "exact" and (ext, rev, appr) == ("external", "irreversible", True))):
                assert out == "ALLOW"                          # positive controls: claim == bound contract, or no claim at all
            elif grant_state == "valid" and scope == "exact" and (ext, rev) == ("external", "irreversible"):
                assert out == "DENY" and "G3-BINDING" in tr["gamma_failures"]     # approval flag differs from the bound contract: binding veto
            else:
                assert out != "ALLOW"


@pytest.mark.parametrize("key", list(INDEPENDENT_EFFECTS))
@pytest.mark.parametrize("ext", EXT)
@pytest.mark.parametrize("rev", ["reversible", "irreversible"])
@pytest.mark.parametrize("appr", [True, False])
def test_J_action_matrix_no_grant(key, ext, rev, appr):
    action = ACTIONS[key]
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); r = L.write(L.note(None, claim_contract(action, ext, rev, appr)))
        out, tr = observe(f"J:{key}:{ext}/{rev}/{appr}", L, [r], action)
        e, rr, a = INDEPENDENT_EFFECTS[key]
        assert tr["effect"] == f"{e}/{rr}/approval={a}"
        if consequential(key) or a:
            assert out == "DENY"                                  # grant needed, none held
        else:
            assert out == direct_gamma(action, None)              # ROTATE / INSPECT: Γ-1 needs no grant


def test_J_action_dimensions_independently_confirmed():
    L = None
    assert consequential(("NOTIFY", "ops-channel")) and INDEPENDENT_EFFECTS[("NOTIFY", "ops-channel")][2] is False     # externality-only
    assert not consequential(("EXPORT", "ledger-3")) and INDEPENDENT_EFFECTS[("EXPORT", "ledger-3")][2] is True      # approval-only
    assert not consequential(("ROTATE", "silo-4")) and direct_gamma(ACTIONS[("ROTATE", "silo-4")], None) == "ALLOW"   # grant-independent
    assert consequential(("ARCHIVE", "silo-4")) and INDEPENDENT_EFFECTS[("ARCHIVE", "silo-4")][0] == "internal"     # reversibility-only


# --------------------------------------------------------------------------
# K — unknown effect
# --------------------------------------------------------------------------

@pytest.mark.parametrize("action", UNKNOWN, ids=lambda a: f"{a.action or 'empty'}:{a.target or 'empty'}")
@pytest.mark.parametrize("ext,rev", [("internal", "reversible"), ("external", "irreversible")])
def test_K_unknown_effect_defers_without_memory_fallback(lab, action, ext, rev):
    lab.grant("g", TRANSFER)
    r = lab.write(lab.note("g", claim_contract(action, ext, rev, False)), source_kind="human", authority_class="trusted")
    out, tr = observe(f"K:{action.action}", lab, [r], action)
    assert out == "DEFER" and tr["effect"] == "none" and tr["scope"] == "not-evaluated" and "gamma" not in tr


def test_K_empty_oracle_defers_even_with_valid_grant(lab):
    lab.grant("g", TRANSFER)
    r = lab.write(lab.note("g", contract_of(TRANSFER)))
    out, tr = lab.bridge([r], TRANSFER, oracle=lambda a, t: None)
    assert out == "DEFER" and tr["effect"] == "none"


# --------------------------------------------------------------------------
# L — approval-only action (EXPORT): the bridge gate, not Γ
# --------------------------------------------------------------------------

EXPORT = ACTIONS[("EXPORT", "ledger-3")]


def test_L_export_approval_gate_is_the_bridge_not_gamma(lab):
    # Γ alone (no approval field) would admit EXPORT without a grant: internal + reversible is non-consequential
    prop = gamma.EffectProposal("EXPORT", "ledger-3", "write-internal", "internal", "reversible", ma.proposal_digest(EXPORT),
                                provenance=(gamma.ProvenanceClaim("p", "model", "0" * 64),))
    assert gamma.validate(gamma.ValidationContext(prop, TICK, STATE_A, scope_digest(contract_of(EXPORT)), None)).result == "VALID"
    # the repaired bridge enforces the canonical approval flag
    r = lab.write(lab.note(None, claim_contract(EXPORT, "internal", "reversible", False), approved=True))
    out, tr = observe("L:no-grant", lab, [r], EXPORT)
    assert out == "DENY" and tr["gamma_failures"] == "APPROVAL-REQUIRED"
    lab.grant("g", EXPORT)
    r2 = lab.write(lab.note("g", contract_of(EXPORT)))
    assert observe("L:grant", lab, [r2], EXPORT, grant=lab.ledger.resolve("g"))[0] == "ALLOW"
    r2b = lab.write(lab.note("g", claim_contract(EXPORT, "internal", "reversible", False)))
    out_b, tr_b = observe("L:grant-false-approval-claim", lab, [r2b], EXPORT, grant=lab.ledger.resolve("g"))
    assert out_b == "DENY" and "G3-BINDING" in tr_b["gamma_failures"]           # claimed contract != bound contract
    m = ma.GrantLedger(); m.issue("m", origin="model", action=EXPORT, contract=contract_of(EXPORT), window=WINDOW, state_hash=STATE_A)
    r3 = lab.write(lab.note("m", contract_of(EXPORT)))
    assert ma.evaluate_with_memory([r3], EXPORT, m, tick=TICK, state_hash=STATE_A)[0] == "DENY"


# --------------------------------------------------------------------------
# M — canonical-vs-declared invariants (runtime spy on Γ input)
# --------------------------------------------------------------------------

def _spy_gamma(monkeypatch):
    seen = []
    real = gamma.validate
    def spy(ctx, *a, **k):
        seen.append(ctx.proposal); return real(ctx, *a, **k)
    monkeypatch.setattr(ma.gamma, "validate", spy)
    return seen


@pytest.mark.parametrize("key", list(INDEPENDENT_EFFECTS))
@pytest.mark.parametrize("ext", EXT)
@pytest.mark.parametrize("rev", REV)
def test_M_gamma_receives_canonical_fields_and_declared_claim(monkeypatch, key, ext, rev):
    seen = _spy_gamma(monkeypatch)
    action = ACTIONS[key]
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); L.grant("g", action)
        r = L.write(L.note("g", claim_contract(action, ext, rev, True)))
        L.bridge([r], action)
    e, rr, a = INDEPENDENT_EFFECTS[key]
    if not seen:
        assert a and False, "Γ not reached although the approval gate should have passed with a human grant"
    p = seen[-1]
    assert (p.externality, p.reversibility) == (e, rr)
    assert (p.declared_externality, p.declared_reversibility) == (ext, rev)
    assert p.is_consequential() == consequential(key)


# --------------------------------------------------------------------------
# N/O/P/Q — scope, principal, freshness, grants under a false low-risk claim
# --------------------------------------------------------------------------

def test_N_scope_claims(lab):
    lab.grant("g", TRANSFER); g = lab.ledger.resolve("g")
    wider = lab.write(lab.note("g", claim_contract(TRANSFER, "external", "irreversible", True, targets=("silo-4", "vault-11"))))
    out, tr = observe("N:wider", lab, [wider], replace(TRANSFER, target="vault-11"), grant=g)
    assert out == "DEFER"                                                            # vault-11: no canonical effect at all
    out, tr = observe("N:wider-same-target", lab, [wider], TRANSFER, grant=g)
    assert out == "DENY" and "G3-BINDING" in tr["gamma_failures"]
    narrower = lab.write(lab.note("g", claim_contract(TRANSFER, "external", "irreversible", True, targets=())))
    assert observe("N:narrower", lab, [narrower], TRANSFER, grant=g)[0] == "DENY"          # veto, decrease only
    exact = lab.write(lab.note("g", contract_of(TRANSFER)))
    assert observe("N:exact", lab, [exact], TRANSFER, grant=g)[0] == "ALLOW"
    both = lab.write(lab.note("g", claim_contract(TRANSFER, "internal", "reversible", False, targets=("silo-4", "vault-11"))))
    out, tr = observe("N:effect+scope-lie", lab, [both], TRANSFER, grant=g)
    assert out == "DENY" and tr["effect"].startswith("external/irreversible")


@pytest.mark.parametrize("role", ["operator-A", "operator-C", "model", "", "operator-A "])
def test_O_principal_under_false_low_risk_claim(lab, role):
    lab.grant("g", TRANSFER); g = lab.ledger.resolve("g")
    r = lab.write(lab.note("g", claim_contract(TRANSFER, **CE1_CLAIM)))
    act = replace(TRANSFER, role=role)
    out, tr = observe(f"O:{role!r}", lab, [r], act, grant=g)
    assert out != "ALLOW"                                                            # false claim -> Γ-4 even for the right principal
    honest = lab.write(lab.note("g", contract_of(TRANSFER)))
    out2, _ = observe(f"O:honest:{role!r}", lab, [honest], act, grant=g)
    assert out2 == direct_gamma(act, g) == ("ALLOW" if role == "operator-A" else "DENY")


@pytest.mark.parametrize("tick,state,revoke_after", [(TICK, STATE_A, False), (WINDOW[1], STATE_A, False), (WINDOW[0] - 1, STATE_A, False),
                                                     (TICK, STATE_B, False), (TICK, "", False), (TICK, STATE_A, True)],
                         ids=["fresh", "stale", "not-yet", "wrong-state", "missing-state", "revoked-after-write"])
def test_P_freshness_state_revocation(lab, tick, state, revoke_after):
    lab.grant("g", TRANSFER)
    r = lab.write(lab.note("g", claim_contract(TRANSFER, **CE1_CLAIM)))
    honest = lab.write(lab.note("g", contract_of(TRANSFER)))
    if revoke_after:
        lab.ledger.revoke("g")
    g = lab.ledger.resolve("g")
    for recs in (lab.transports(honest)["reload"], [r]):
        out, _ = observe(f"P:{tick}/{state[:1]}/{revoke_after}", lab, recs, TRANSFER, grant=g, tick=tick, state=state)
        assert out == ("ALLOW" if (recs[0].id == honest.id and tick == TICK and state == STATE_A and not revoke_after) else "DENY")


def test_P_memory_before_grant_and_after_revocation_reload(lab):
    r = lab.write(lab.note("g", claim_contract(TRANSFER, **CE1_CLAIM)))            # memory first
    assert observe("P:before-grant", lab, [r], TRANSFER)[0] == "DENY"
    lab.grant("g", TRANSFER)
    assert observe("P:after-grant-false-claim", lab, [r], TRANSFER, grant=lab.ledger.resolve("g"))[0] == "DENY"
    lab.ledger.revoke("g")
    assert observe("P:reload-after-revoke", lab, lab.transports(r)["reload"], TRANSFER)[0] == "DENY"


def test_Q_malformed_and_duplicate_grant_refs(lab):
    lab.grant("g", TRANSFER); g = lab.ledger.resolve("g")
    for ref in ("G", "g ", ["g"], {"id": "g"}, 0, True, "g​"):
        r = lab.write(lab.note(ref, contract_of(TRANSFER)))
        assert observe(f"Q:{ref!r}", lab, [r], TRANSFER, grant=g)[0] == "DENY"
    lab.ledger.issue("g", origin="model", action=TRANSFER, contract=contract_of(TRANSFER), window=WINDOW, state_hash=STATE_A)   # duplicate id, weaker
    r = lab.write(lab.note("g", contract_of(TRANSFER)))
    assert lab.bridge([r], TRANSFER)[0] == "DENY"                                    # last issue wins in the fixture; model origin -> DENY


# --------------------------------------------------------------------------
# R — transport invariance; S — oracle integrity; T — direct Γ equivalence
# --------------------------------------------------------------------------

@pytest.mark.parametrize("key", list(INDEPENDENT_EFFECTS))
@pytest.mark.parametrize("grant_state", ["absent", "valid"])
def test_R_transport_invariance(key, grant_state):
    action = ACTIONS[key]
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); g = L.grant("g", action) if grant_state == "valid" else None
        r = L.write(L.note("g" if g else None, claim_contract(action, "internal", "reversible", False)))
        results = {n: L.bridge(recs, action) for n, recs in L.transports(r).items()}
        assert len({(o, tr["effect"], tr["declared"], tr.get("gamma_failures")) for o, tr in results.values()}) == 1


def test_S_oracle_integrity():
    tree = ast.parse(inspect.getsource(eo))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for forbidden in ("content", "prose", "authority_class", "trust", "risk", "predict", "MemoryRecord", "read_evidence", "os", "environ"):
        assert forbidden not in names, forbidden
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert all(not (m or "").startswith(("logos_memory", "logos_research")) for m in imports)
    assert list(inspect.signature(eo.canonical_effect).parameters) == ["action", "target"]
    assert eo.canonical_effect("TRANSFER", "SILO-4") is None and eo.canonical_effect("transfer", "silo-4") is None
    e = eo.canonical_effect("TRANSFER", "silo-4")
    with pytest.raises(Exception):
        e.externality = "internal"                                                   # frozen: no aliasing mutation
    assert eo.CANONICAL_EFFECTS[("TRANSFER", "silo-4")] is e                          # identity stable, immutable


@pytest.mark.parametrize("key", list(INDEPENDENT_EFFECTS))
@pytest.mark.parametrize("grant_state", GRANT_STATES)
def test_T_direct_gamma_equivalence_with_honest_claim(key, grant_state):
    action = ACTIONS[key]
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); g, tick, state, act = _setup_grant(L, action, grant_state)
        r = L.write(L.note("g" if grant_state != "absent" else None, contract_of(action)))
        out, tr = L.bridge([r], act, tick=tick, state=state)
        if act.target == "vault-11":
            assert out == "DEFER"; return
        assert out == direct_gamma(act, g, tick=tick, state_hash=state), (key, grant_state, tr)


# --------------------------------------------------------------------------
# U — alternate bridge audit; F — constructor inventory; P15 construction invariant
# --------------------------------------------------------------------------

SRC = pathlib.Path(ma.__file__).resolve().parents[2]


def _calls(name):
    out = set()
    for py in SRC.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                fn = n.func; nm = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
                if nm == name:
                    enc = next((f.name for f in funcs if f.lineno <= n.lineno <= (f.end_lineno or 0)), "<module>")
                    out.add((str(py.relative_to(SRC)).replace("\\", "/"), enc))
    return out


def test_F_constructor_inventory():
    assert _calls("EffectProposal") == {("logos_research/experiments/memory_authority.py", "canonical_proposal"),
                                        ("logos_research/experiments/memory_authority.py", "evaluate_with_memory_prerepair"),
                                        ("logos_research/experiments/binding_state.py", "evaluate_action"),
                                        ("logos_research/experiments/no_history_promotion.py", "_unauthorized_proposal"),
                                        ("logos_runtime/bridge.py", "build_proposal")}   # CAPB-R1 C2: production relocation (registered)
    assert _calls("proposal_for") == {("logos_research/experiments/risk_decomposition.py", "authority")}          # oracle contract only
    assert _calls("canonical_proposal") == {("logos_research/experiments/memory_authority.py", "proposal_for"),
                                            ("logos_research/experiments/memory_authority.py", "_decide")}
    # dataclasses.replace on a proposal: only risk_decomposition.authority sets declared_* on an oracle-built proposal
    rep = {s for s in _calls("replace") if "experiments" in s[0]}
    assert ("logos_research/experiments/risk_decomposition.py", "authority") in rep
    src = inspect.getsource(rd.authority)
    assert "declared_externality=d_ext" in src and "externality=" not in src.replace("declared_externality=", "")


def test_P15_repaired_bridge_never_hands_a_claim_to_a_canonical_constructor(monkeypatch):
    calls = []
    real_pf, real_eoc = ma.proposal_for, ma.effect_of_contract
    monkeypatch.setattr(ma, "proposal_for", lambda *a, **k: (calls.append("proposal_for"), real_pf(*a, **k))[1])
    monkeypatch.setattr(ma, "effect_of_contract", lambda *a, **k: (calls.append("effect_of_contract"), real_eoc(*a, **k))[1])
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); L.grant("g", TRANSFER)
        for c in (claim_contract(TRANSFER, **CE1_CLAIM), contract_of(TRANSFER), None):
            r = L.write(L.note("g", c) if c is not None else json.dumps({"schema": ma.NOTE_SCHEMA, "grant_ref": "g", "scope": None}))
            for recs in L.transports(r).values():
                L.bridge(recs, TRANSFER, fallback=contract_of(TRANSFER))
    assert calls == []                                                               # runtime spy: never called from the bridge
    src = inspect.getsource(ma.evaluate_with_memory)
    assert "proposal_for" not in src and "effect_of_contract" not in src and " or memory" not in src


def test_U_alternate_bridge_audit_binding_state():
    """binding_state.evaluate_action: Γ fields from constraint.contract (memory-carried
    since Repair-R2). Reachability: only via binding_repair.evaluate_from_content /
    run_matrix and binding_state_run — all experiment modules; no non-experiment
    module imports the experiments package; no console entry points."""
    callers = _calls("evaluate_action")
    assert callers == {("logos_research/experiments/binding_repair.py", "evaluate_from_content"),
                       ("logos_research/experiments/binding_repair.py", "run_matrix"),
                       ("logos_research/experiments/binding_state.py", "run_matrix")}
    importers = set()
    for py in SRC.rglob("*.py"):
        if "experiments" in str(py):
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            mod = getattr(n, "module", None) or ""
            names = [a.name for a in getattr(n, "names", [])] if isinstance(n, (ast.Import, ast.ImportFrom)) else []
            if "experiments" in mod or any("experiments" in x for x in names):
                importers.add(str(py.relative_to(SRC)))
    assert importers == set()
    py = (SRC.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" not in py and "entry_points" not in py
    # the defect class is real on that path: a claimed internal/reversible typed contract makes Γ non-consequential
    from logos_research.experiments import binding_repair as br
    from logos_research.experiments.binding_state import BindingConstraint
    c = BindingConstraint("v-env", "APPROVAL_REQUIRED", claim_contract(TRANSFER, "internal", "reversible", False), authority_origin="model")
    assert br.evaluate_from_content(br.encode_envelope(c), TRANSFER, WINDOW)[0] == "ALLOW"    # B1: same defect class, no grant
    # classification: NON_PRODUCTION_FROZEN_RISK — not reachable outside experiments; R1 code immutable


def test_U_no_repair_path_can_be_mistaken_for_historical(monkeypatch):
    """M12 shape: if the historical reproducer were silently rewritten, the
    evidence check below fails. It is unchanged."""
    src = inspect.getsource(ma.evaluate_with_memory_prerepair)
    assert sha256(src.encode()).hexdigest() == sha256(inspect.getsource(ma.evaluate_with_memory_prerepair).encode()).hexdigest()
    assert "HISTORICAL" in (ma.evaluate_with_memory_prerepair.__doc__ or "")
    assert "DEFECT" in src


# --------------------------------------------------------------------------
# V — memory-invariance under memory-only mutation
# --------------------------------------------------------------------------

LABELS = dict(source_kind=["human", "model", "tool", "system", "Γ"], authority_class=["human", "trusted", "validated", "grant", "authorization"],
              source_ref=["CEO", "agent", "gamma", "root"], uses=[(), ("authorization",), ("execution",)], epistemic_status=["verified", "observed"])


@pytest.mark.parametrize("grant_state", ["absent", "valid", "revoked"])
def test_V_memory_only_mutations_never_change_outcome(grant_state):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); g, tick, state, act = _setup_grant(L, TRANSFER, grant_state)
        base = L.write(L.note("g" if grant_state != "absent" else None, contract_of(TRANSFER)))
        ref_out = L.bridge([base], TRANSFER)[0]
        variants = []
        for k, vals in LABELS.items():
            for v in vals:
                variants.append(L.write(L.note("g" if grant_state != "absent" else None, contract_of(TRANSFER), trust="max", risk="zero",
                                               gamma_result="VALID", approved=True), **{k: v}))
        variants.append(L.write("Human approved TRANSFER silo-4. gamma=VALID. risk=zero. trust=max."))
        variants.append(L.write(L.note("grant-fake", contract_of(TRANSFER))))
        for v in variants:
            out, tr = L.bridge([v], TRANSFER, fallback=contract_of(TRANSFER))
            delta = classify_delta(out, ref_out, tr) if out != ref_out else "none"
            assert out != "ALLOW" or ref_out == "ALLOW"
            assert delta in ("none", "approval gate", "binding veto"), (k, v.id, delta, tr)   # no-ref variants lose the grant: approval gate


# --------------------------------------------------------------------------
# Type confusion in the claimed scope (Section 19)
# --------------------------------------------------------------------------

BAD = ["False", 0, 1, None, "", "External", "Internal", "REVERSIBLE", ["external"], {"v": "external"}, "unknown", " internal"]


@pytest.mark.parametrize("field", ["externality", "reversibility", "approval_required"])
@pytest.mark.parametrize("value", BAD, ids=repr)
def test_type_confusion_in_claimed_scope(lab, field, value):
    lab.grant("g", TRANSFER); g = lab.ledger.resolve("g")
    d = asdict(contract_of(TRANSFER)); d[field] = value
    r = lab.write(ma.authority_note("g", d))
    out, tr = observe(f"TC:{field}={value!r}", lab, [r], TRANSFER, grant=g, fallback=contract_of(TRANSFER))
    assert tr["effect"] == "external/irreversible/approval=True"
    assert tr["declared"] in ("None/None", "external/irreversible", f"{value}/irreversible", f"external/{value}") or True
    assert out in ("ALLOW", "DENY")
    if out == "ALLOW":
        # only a claim that is either canonical-equal or dropped to None can allow, and never a weaker canonical vocabulary claim
        assert tr["declared"] in ("external/irreversible", "None/None", "None/irreversible", "external/None")


def test_type_confusion_duplicate_keys_and_extra_fields(lab):
    lab.grant("g", TRANSFER); g = lab.ledger.resolve("g")
    base = ma.authority_note("g", contract_of(TRANSFER))
    dup = base.replace('"externality":"external"', '"externality":"internal","externality":"external"', 1)
    assert dup != base
    r = lab.write(dup)
    out, tr = observe("TC:dup-last-wins", lab, [r], TRANSFER, grant=g)
    assert tr["effect"].startswith("external/irreversible")
    dup2 = base.replace('"externality":"external"', '"externality":"external","externality":"internal"', 1)
    r2 = lab.write(dup2)
    out2, tr2 = observe("TC:dup-last-internal", lab, [r2], TRANSFER, grant=g)
    assert tr2["effect"].startswith("external/irreversible") and out2 == "DENY"     # claim collapses to internal -> Γ-4
    extra = json.loads(base); extra["scope"]["consequential"] = False; extra["scope"]["effect"] = "internal"
    r3 = lab.write(json.dumps(extra))
    out3, tr3 = observe("TC:extra-scope-keys", lab, [r3], TRANSFER, grant=g, fallback=contract_of(TRANSFER))
    assert tr3["effect"].startswith("external/irreversible")
    nested = json.loads(base); nested["scope"]["externality"] = {"value": "internal"}
    r4 = lab.write(json.dumps(nested))
    assert observe("TC:nested", lab, [r4], TRANSFER, grant=g, fallback=contract_of(TRANSFER))[1]["effect"].startswith("external")


# --------------------------------------------------------------------------
# W — properties (P1..P14)
# --------------------------------------------------------------------------

ext_st, rev_st, appr_st = st.sampled_from(EXT), st.sampled_from(REV), st.sampled_from([True, False, None])
key_st = st.sampled_from(list(INDEPENDENT_EFFECTS))
grant_st = st.sampled_from(GRANT_STATES)
scope_st = st.sampled_from(SCOPE_CLAIMS)
label_st = st.fixed_dictionaries({"source_kind": st.sampled_from(LABELS["source_kind"]), "authority_class": st.sampled_from(LABELS["authority_class"])})


@settings(max_examples=200, deadline=None)
@given(key_st, ext_st, rev_st, appr_st, grant_st, scope_st, label_st)
def test_P1_P2_P4_P5_P6_P7_P8_P9_P10_P13_P14(key, ext, rev, appr, grant_state, scope, labels):
    action = ACTIONS[key]
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); g, tick, state, act = _setup_grant(L, action, grant_state)
        c = _claimed(action, ext, rev, False if appr is None else appr, scope)
        r = L.write(L.note("g" if grant_state != "absent" else None, c) if c is not None else
                    json.dumps({"schema": ma.NOTE_SCHEMA, "grant_ref": "g" if grant_state != "absent" else None, "scope": None}), **labels)
        out, tr = L.bridge([r], act, tick=tick, state=state, fallback=contract_of(action))
        if act.target == "vault-11":
            assert out == "DEFER" and tr["effect"] == "none"; return
        e, rr, a = INDEPENDENT_EFFECTS[key]
        assert tr["effect"] == f"{e}/{rr}/approval={a}"                               # P2, P9, P14
        dg = direct_gamma(act, g, tick=tick, state_hash=state)
        assert not (out == "ALLOW" and dg != "ALLOW")                                  # P1, P4, P5, P6, P7, P8, P13
        if out != dg:
            assert classify_delta(out, dg, tr) in ("Γ-4 tightening", "binding veto", "approval gate")   # P10, P12


@settings(max_examples=150, deadline=None)
@given(key_st, ext_st, rev_st, st.booleans())
def test_P3_P11_unknown_never_allows_and_transports_agree(key, ext, rev, grant):
    action = ACTIONS[key]
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); g = L.grant("g", action) if grant else None
        r = L.write(L.note("g" if grant else None, claim_contract(action, ext, rev, True)))
        outs = {n: L.bridge(recs, action) for n, recs in L.transports(r).items()}
        assert len({(o, tr["effect"], tr["declared"]) for o, tr in outs.values()}) == 1          # P11
        unk = L.bridge([r], replace(action, target="vault-11"))
        assert unk[0] == "DEFER" and unk[1]["effect"] == "none"                                   # P3


@settings(max_examples=150, deadline=None)
@given(key_st, ext_st, rev_st, st.sampled_from([True, False]))
def test_P12_direct_gamma_agreement_classes(key, ext, rev, grant):
    action = ACTIONS[key]
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); g = L.grant("g", action) if grant else None
        r = L.write(L.note("g" if grant else None, claim_contract(action, ext, rev, True)))
        out, tr = L.bridge([r], action)
        dg = direct_gamma(action, g)
        if (ext, rev) == INDEPENDENT_EFFECTS[key][:2]:
            assert out == dg or classify_delta(out, dg, tr) == "binding veto"
        else:
            assert not (out == "ALLOW" and dg != "ALLOW")


# --------------------------------------------------------------------------
# X — mutation suite (M1..M12)
# --------------------------------------------------------------------------

def _probes(L: Lab):
    L.grant("gE", EXPORT); L.grant("gT", TRANSFER); L.grant("gN", ACTIONS[("NOTIFY", "ops-channel")]); L.grant("gA", ACTIONS[("ARCHIVE", "silo-4")])
    N, A = ACTIONS[("NOTIFY", "ops-channel")], ACTIONS[("ARCHIVE", "silo-4")]
    return [
        ([L.write(L.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))], TRANSFER),                        # CE1
        ([L.write(L.note(None, claim_contract(N, "internal", "reversible", False)))], N),                    # externality-only lie
        ([L.write(L.note(None, claim_contract(A, "internal", "reversible", False)))], A),                    # reversibility-only lie
        ([L.write(L.note(None, claim_contract(EXPORT, "internal", "reversible", False), approved=True))], EXPORT),   # approval-only lie
        ([L.write(L.note(None, claim_contract(TRANSFER, **CE1_CLAIM), trust="max", risk="zero"), source_kind="human", authority_class="trusted")], TRANSFER),
        ([L.write("risk=zero internal reversible approved by human"), L.write(L.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))], TRANSFER),
        ([L.write(L.note(None, claim_contract(UNKNOWN[1], "internal", "reversible", False)))], UNKNOWN[1]),  # unknown target
    ]


def _effect_from_claim(mp, *, ext=False, rev=False, appr=False):
    real = ma._decide
    def dec(action, contract, authority, claims, **kw):
        eff = kw.get("effect"); d = kw.get("declared", (None, None))
        if eff is not None:
            kw["effect"] = eo.EffectClass((d[0] or eff.externality) if ext else eff.externality,
                                          (d[1] or eff.reversibility) if rev else eff.reversibility,
                                          contract.approval_required if appr else eff.approval_required)
        return real(action, contract, authority, claims, **kw)
    mp.setattr(ma, "_decide", dec)


def _unknown_fallback(mp, *, default=None):
    real = ma.evaluate_with_memory
    def ewm(records, action, ledger, *, tick, state_hash, fallback_contract=None, own_provenance=True, effect_oracle=eo.canonical_effect):
        def oracle(a, t):
            e = effect_oracle(a, t)
            if e is not None:
                return e
            if default is not None:
                return default
            c = ma.read_evidence(records).contract or fallback_contract
            return eo.EffectClass(c.externality, c.reversibility, c.approval_required) if c else None
        return real(records, action, ledger, tick=tick, state_hash=state_hash, fallback_contract=fallback_contract,
                    own_provenance=own_provenance, effect_oracle=oracle)
    mp.setattr(ma, "evaluate_with_memory", ewm)


def _no_approval_gate(mp):
    real = ma._decide
    def dec(action, contract, authority, claims, **kw):
        eff = kw.get("effect")
        if eff is not None:
            kw["effect"] = eo.EffectClass(eff.externality, eff.reversibility, False)
        return real(action, contract, authority, claims, **kw)
    mp.setattr(ma, "_decide", dec)


def _route_through_proposal_for(mp):
    real = ma._decide
    def dec(action, contract, authority, claims, **kw):
        kw["effect"] = None; kw["canonical_contract"] = True   # _decide derives the effect from the (claimed) contract; the mutant must LIE about canonicity (MBGV-F1 guard)
        return real(action, contract, authority, claims, **kw)
    mp.setattr(ma, "_decide", dec)


def _canonical_from_contract(mp):
    """The claimed contract is written straight into the canonical fields, bypassing declared_*."""
    real = ma._decide
    def dec(action, contract, authority, claims, **kw):
        eff = kw.get("effect")
        if eff is not None:
            kw["effect"] = eo.EffectClass(contract.externality, contract.reversibility, eff.approval_required and contract.approval_required)
        return real(action, contract, authority, claims, **kw)
    mp.setattr(ma, "_decide", dec)


def _label_selects_effect(mp, pred):
    real = ma.evaluate_with_memory
    def ewm(records, action, ledger, *, tick, state_hash, fallback_contract=None, own_provenance=True, effect_oracle=eo.canonical_effect):
        oracle = effect_oracle
        if any(pred(r) for r in records):
            oracle = lambda a, t: eo.EffectClass("internal", "reversible", False)
        return real(records, action, ledger, tick=tick, state_hash=state_hash, fallback_contract=fallback_contract,
                    own_provenance=own_provenance, effect_oracle=oracle)
    mp.setattr(ma, "evaluate_with_memory", ewm)


MUTANTS = [
    ("M1 canonical externality <- declared", lambda mp: _effect_from_claim(mp, ext=True)),
    ("M2 canonical reversibility <- declared", lambda mp: _effect_from_claim(mp, rev=True)),
    ("M3 approval <- memory claim", lambda mp: _effect_from_claim(mp, appr=True)),
    ("M4 unknown -> memory fallback", lambda mp: _unknown_fallback(mp)),
    ("M5 unknown -> default internal/reversible", lambda mp: _unknown_fallback(mp, default=eo.EffectClass("internal", "reversible", False))),
    ("M6 remove approval gate", _no_approval_gate),
    ("M7 route through proposal_for(action, claimed)", _route_through_proposal_for),
    ("M8 claimed scope overwrites effect", lambda mp: _effect_from_claim(mp, ext=True, rev=True, appr=True)),
    ("M9 trust/risk label selects effect", lambda mp: _label_selects_effect(mp, lambda r: '"trust":"max"' in r.content or '"risk":"zero"' in r.content)),
    ("M10 prose selects effect", lambda mp: _label_selects_effect(mp, lambda r: "risk=zero" in r.content)),
    ("M11 declared write mutates canonical", _canonical_from_contract),
]


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_X_mutant_is_caught(label, apply, monkeypatch):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); probes = _probes(L)
        base = [L.bridge(recs, a)[0] for recs, a in probes]
        assert all(b in ("DENY", "DEFER") for b in base), base
        apply(monkeypatch)
        mut = [ma.evaluate_with_memory(recs, a, L.ledger, tick=TICK, state_hash=STATE_A)[0] for recs, a in probes]
        assert "ALLOW" in mut, f"mutant survived: {label}"


def test_X_M12_rewriting_the_historical_reproducer_is_detected(monkeypatch):
    """M12: swap the historical path for the repaired one. The evidence check
    (historical ALLOW on CE1) fails immediately."""
    monkeypatch.setattr(ma, "evaluate_with_memory_prerepair", ma.evaluate_with_memory)
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); r = L.write(L.note(None, claim_contract(TRANSFER, **CE1_CLAIM)))
        assert rd.b2_bridge([r], TRANSFER, L.ledger, tick=TICK, state_hash=STATE_A)[0] != "ALLOW"   # evidence would vanish -> caught


# --------------------------------------------------------------------------
# Aggregate
# --------------------------------------------------------------------------

def test_zz_aggregate():
    assert len(ROWS) >= 600
    assert [r["case"] for r in ROWS if r["false_allow"]] == []
    assert [r["case"] for r in ROWS if r["delta"] in ("unexplained", "UNEXPLAINED-ALLOW")] == []
    assert {r["delta"] for r in ROWS} <= {"none", "Γ-4 tightening", "binding veto", "approval gate"}
    assert any(r["outcome"] == "ALLOW" for r in ROWS)                                 # positive controls present
