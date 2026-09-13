"""RELATIONAL-STATE-SWAP-R1 — same content, swapped relations, does enforcement move?

Every central test is a PAIR: two `MemoryRecord`s with identical content
(equal ContentPayloadHash) and different relational metadata (different
RelationalMetadataHash), or an explicit canonical change. Both go through the
same real readers and the same bridge; the oracle is the ledger alone.

    UnexplainedDecisionDelta        decision moved, canonical authority did not   -> H1a counterexample
    MissedCanonicalRelationalDelta  canonical moved, decision did not follow      -> H1b counterexample
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_gamma as gamma
from logos_memory.factory import MemoryFactory
from logos_memory.records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from logos_memory.scope import ScopeDecision, scope_digest
from logos_memory.store import MemoryAuthorityError, MemoryStore
from logos_research.experiments import binding_repair as br
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import relational_swap as rs
from logos_research.experiments.binding_state import BindingConstraint, ProposedAction, _base_contract

TICK, WINDOW, STATE_A, STATE_B = ma.TICK, ma.WINDOW, ma.STATE_A, ma.STATE_B
TRANSFER, TRANSFER_B_TARGET, TRANSFER_AS_B, WRITE_CAP = ma.TRANSFER, ma.TRANSFER_B_TARGET, ma.TRANSFER_AS_B, ma.WRITE_CAP
GRANT = "grant-7f3a"


class Lab:
    def __init__(self, tmp: Path, *, grant: bool = True, origin: str = "human"):
        self.ledger = ma.GrantLedger(); self.contract = ma.canonical_contract()
        self.store = MemoryStore(tmp / "mem"); self.tmp = tmp; self.n = 0
        if grant:
            self.ledger.issue(GRANT, origin=origin, action=TRANSFER, contract=self.contract, window=WINDOW, state_hash=STATE_A)

    def note(self, ref=None, contract=None, **claims) -> str:
        return ma.authority_note(ref, self.contract if contract is None else contract, **claims)

    def write(self, content: str, **kw) -> MemoryRecord:
        self.n += 1
        return ma.write_note(self.store, kw.pop("record_id", f"rec-{self.n}"), content, **kw)

    def canonical(self, action=TRANSFER, *, grant_id=GRANT, tick=TICK, state_hash=STATE_A, contract=None) -> str:
        return ma.evaluate_canonical(action, self.ledger, grant_id, contract or self.contract, tick=tick, state_hash=state_hash)[0]

    def bridge(self, records, action=TRANSFER, *, tick=TICK, state_hash=STATE_A):
        return ma.evaluate_with_memory(list(records), action, self.ledger, tick=tick, state_hash=state_hash,
                                       fallback_contract=self.contract)

    def project(self, ids):
        c = _base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        proj = MemoryFactory(self.store).project(tuple(ids), purpose="rss handoff", audience="project",
                                                  valid_until="2026-12-01T00:00:00+00:00",
                                                  scope=ScopeDecision("ALLOW", c, scope_digest(c)))
        return [replace(self.store.fetch(i["id"]), content=i["content"], id="proj:" + i["id"]) for i in json.loads(proj.content)]

    def retrieve(self, query):
        c = _base_contract(memory_kinds=("semantic",), projection_audiences=("project",))
        rr = MemoryFactory(self.store).retrieve(query, ScopeDecision("ALLOW", c, scope_digest(c)), limit=50)
        return [self.store.fetch(i.id) for i in rr.items]

    def held_ref(self, records) -> str | None:
        """The canonical grant the memory legitimately points at, if any."""
        for ref in ma.read_evidence(records).refs:
            if self.ledger.resolve(ref) is not None or ref in self.ledger.grants():
                return ref
        return None


@pytest.fixture
def lab():
    with tempfile.TemporaryDirectory() as t:
        yield Lab(Path(t))


PAIRS: list[rs.PairResult] = []      # collected for the closure artifact


def pair(pair_id, dimension, L: Lab, before: list[MemoryRecord], after: list[MemoryRecord], *,
         action_before=TRANSFER, action_after=None, tick_before=TICK, tick_after=None,
         state_before=STATE_A, state_after=None, expect_same_content=True, contract_after=None) -> rs.PairResult:
    action_after = action_after or action_before
    tick_after = tick_before if tick_after is None else tick_after
    state_after = state_after or state_before
    if expect_same_content:
        assert {rs.content_hash(r) for r in before} == {rs.content_hash(r) for r in after}, "pair must share content"
    cb = L.canonical(action_before, grant_id=L.held_ref(before), tick=tick_before, state_hash=state_before)
    ca = L.canonical(action_after, grant_id=L.held_ref(after), tick=tick_after, state_hash=state_after, contract=contract_after)
    db, tb = L.bridge(before, action_before, tick=tick_before, state_hash=state_before)
    da, ta = L.bridge(after, action_after, tick=tick_after, state_hash=state_after)
    res = rs.PairResult(pair_id, dimension, rs.DIMENSIONS[dimension],
                        rs.content_hash(before[0]), rs.relational_hash(before[0]), rs.relational_hash(after[0]),
                        cb, ca, db, da, tb.get("gamma", "-") + "/" + tb.get("gamma_failures", "-"),
                        ta.get("gamma", "-") + "/" + ta.get("gamma_failures", "-"), rs.first_divergence(tb, ta),
                        same_content=expect_same_content)
    PAIRS.append(res)
    return res


def assert_invariant(res: rs.PairResult):
    assert not res.unexplained_decision_delta, (res.pair_id, res.decision_before, res.decision_after, res.first_divergence)
    assert not res.missed_canonical_delta, (res.pair_id, res.canonical_after, res.decision_after)
    assert res.decision_after == res.canonical_after and res.decision_before == res.canonical_before


# --------------------------------------------------------------------------
# Controls
# --------------------------------------------------------------------------

def test_positive_control(lab):
    a = lab.write(lab.note(GRANT)); b = lab.write(lab.note(GRANT))
    r = pair("POS", "record_id", lab, [a], [b])
    assert r.decision_before == r.decision_after == "ALLOW" and r.relational_delta
    assert_invariant(r)


def test_negative_control():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        a = L.write(L.note(None, approved=True), source_kind="human", source_ref="CEO", authority_class="trusted", uses=("authorization",))
        b = L.write(L.note(None, approved=True), source_kind="model", source_ref="agent", authority_class="unknown")
        r = pair("NEG", "authority_class", L, [a], [b])
        assert r.decision_before == r.decision_after == "DENY"
        assert_invariant(r)


# --------------------------------------------------------------------------
# A–D — label swaps (authority_class, source label, source type, admissible_uses)
# --------------------------------------------------------------------------

CLASSES = ["human", "model", "tool", "system", "admin", "trusted", "verified", "legal", "owner", "unknown",
           "observation", "derived", "validated", "grant", "authorization", "x9!"]
SOURCES = ["CEO", "CFO", "admin", "user", "agent", "tool", "system", "unknown", "", "operator-A", "root"]
TYPES = ["human", "model", "tool", "system", "memory", "external", "local-recovery", ""]
USES = [(), ("reasoning",), ("retrieval",), ("audit",), ("planning",), ("authorization",), ("execution",),
        ("read", "write"), ("authorization", "execution")]


@pytest.mark.parametrize("grant", [True, False], ids=["grant", "no-grant"])
@pytest.mark.parametrize("cls_a,cls_b", [(a, b) for a in CLASSES[:4] for b in CLASSES if a != b][:40],
                         ids=lambda x: str(x))
def test_A_authority_class_swap(grant, cls_a, cls_b):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        content = L.note(GRANT if grant else None)
        a = L.write(content, authority_class=cls_a); b = L.write(content, authority_class=cls_b)
        r = pair(f"A:{cls_a}->{cls_b}:{grant}", "authority_class", L, [a], [b])
        assert r.relational_delta
        assert_invariant(r)
        assert r.decision_after == ("ALLOW" if grant else "DENY")


@pytest.mark.parametrize("grant", [True, False], ids=["grant", "no-grant"])
@pytest.mark.parametrize("src_b", SOURCES, ids=lambda s: s or "empty")
def test_B_source_label_swap(grant, src_b):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        content = L.note(GRANT if grant else None)
        a = L.write(content, source_ref="agent"); b = L.write(content, source_ref=src_b)
        r = pair(f"B:agent->{src_b}:{grant}", "source_label", L, [a], [b])
        assert_invariant(r)


@pytest.mark.parametrize("grant", [True, False], ids=["grant", "no-grant"])
@pytest.mark.parametrize("type_b", TYPES, ids=lambda s: s or "empty")
def test_C_source_type_swap(grant, type_b):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        content = L.note(GRANT if grant else None)
        a = L.write(content, source_kind="model"); b = L.write(content, source_kind=type_b)
        r = pair(f"C:model->{type_b}:{grant}", "source_type", L, [a], [b])
        assert_invariant(r)


@pytest.mark.parametrize("grant", [True, False], ids=["grant", "no-grant"])
@pytest.mark.parametrize("uses_b", USES, ids=lambda u: "+".join(u) or "none")
def test_D_admissible_uses_swap(grant, uses_b):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        content = L.note(GRANT if grant else None)
        a = L.write(content, uses=()); b = L.write(content, uses=uses_b)
        r = pair(f"D:none->{'+'.join(uses_b) or 'none'}:{grant}", "admissible_uses", L, [a], [b])
        assert_invariant(r)


def test_D_forbidden_uses_are_not_a_swappable_value(lab):
    for use in ("approve", "grant-permission", "mint-token", "execute-external-action"):
        with pytest.raises(MemoryAuthorityError):
            lab.write(lab.note(GRANT), uses=(use,))


@pytest.mark.parametrize("field,values", [
    ("epistemic_status", ["unknown", "hypothesis", "observed", "verified", "contradicted"]),
    ("visibility", [("project",), ("project", "public"), ("project", "private")]),
    ("kind", ["semantic", "episodic", "procedural", "evidence", "working"]),
], ids=lambda x: x if isinstance(x, str) else "")
def test_other_metadata_swaps(lab, field, values):
    content = lab.note(GRANT)
    a = lab.write(content)
    for v in values:
        b = lab.write(content, **{field: v})
        assert_invariant(pair(f"meta:{field}={v}", field if field != "kind" else "record_id", lab, [a], [b]))


# --------------------------------------------------------------------------
# E — writer identity; F — reader path; G — store/context
# --------------------------------------------------------------------------

def test_E_writer_identity_swap(lab):
    content = lab.note(GRANT)
    generic = lab.write(content, source_kind="model")
    src1 = lab.write(content, authority_class="observation"); src2 = lab.write(content, authority_class="validated")
    consolidated = MemoryFactory(lab.store).consolidate((src1.id, src2.id), content, output_id="cons").record
    superseded = lab.store.supersede(generic.id, replace(generic, id="sup", source=ProvenanceRef("CEO", "human", generic.source.content_digest),
                                                          authority=AuthorityProvenance("human", ())))
    for label, other in (("consolidate", consolidated), ("supersede", superseded)):
        assert_invariant(pair(f"E:write_note->{label}", "writer_identity", lab, [generic], [other]))
    # derive_procedure changes content by construction: control, not a pair
    proc = MemoryFactory(lab.store).derive_procedure((src1.id,), "proc", ("step",))
    assert lab.bridge([proc])[0] == "DENY"                        # no reference survives derivation -> nothing


def test_E_writer_identity_without_grant():
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        content = L.note(None, approved=True)
        a = L.write(content, authority_class="observation"); b = L.write(content, authority_class="validated")
        c = MemoryFactory(L.store).consolidate((a.id, b.id), content, output_id="cons").record
        assert_invariant(pair("E:no-grant:consolidate", "writer_identity", L, [a], [c]))
        assert L.bridge([c])[0] == "DENY"


@pytest.mark.parametrize("grant", [True, False], ids=["grant", "no-grant"])
def test_F_reader_path_swap(grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        r = L.write(L.note(GRANT if grant else None, approved=True), source_kind="human", authority_class="human")
        fetched = [L.store.fetch(r.id)]
        for label, path in (("retrieve", L.retrieve("grant_ref approved")), ("project", L.project([r.id])),
                            ("reload", [MemoryStore(Path(t) / "mem").fetch(r.id)])):
            assert_invariant(pair(f"F:fetch->{label}:{grant}", "reader_path", L, fetched, path))


def test_F_reader_path_envelope_vs_note(lab):
    """B1 (envelope reader) and B2 (note reader) carry different content by
    construction; they agree on the semantics: reference != grant."""
    c = BindingConstraint("rss-env", "APPROVAL_REQUIRED", lab.contract, authority_origin="human")
    env = br.encode_envelope(c)
    assert br.evaluate_from_content(env, TRANSFER, WINDOW)[0] == "DENY"
    assert br.evaluate_from_content(env, replace(TRANSFER, human_grant_present=True), WINDOW)[0] == "ALLOW"
    assert lab.bridge([lab.write(lab.note(None, authority_origin="human"))])[0] == "DENY"
    assert lab.bridge([lab.write(lab.note(GRANT))])[0] == "ALLOW"


@pytest.mark.parametrize("grant", [True, False], ids=["grant", "no-grant"])
def test_G_store_context_swap(grant):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        r = L.write(L.note(GRANT if grant else None), source_kind="human", authority_class="human")
        other = MemoryStore(Path(t) / "other-store")
        copied = other.append(replace(r, id="ctx-B:" + r.id))
        assert_invariant(pair(f"G:store:{grant}", "store_context", L, [r], [copied]))
        # a different ledger (different deployment) is a canonical change, not a relational one
        foreign = ma.GrantLedger()
        assert ma.evaluate_with_memory([copied], TRANSFER, foreign, tick=TICK, state_hash=STATE_A)[0] == "DENY"


# --------------------------------------------------------------------------
# H–K — canonical relational swaps (H1b)
# --------------------------------------------------------------------------

def test_H_principal_swap(lab):
    r = lab.write(lab.note(GRANT))
    res = pair("H:A->B", "principal", lab, [r], [r], action_before=TRANSFER, action_after=TRANSFER_AS_B)
    assert res.canonical_before == "ALLOW" and res.canonical_after == "DENY"
    assert res.decision_before == "ALLOW" and res.decision_after == "DENY"
    assert_invariant(res)
    # relational labels cannot mask the principal change
    forged = lab.write(lab.note(GRANT, ma.canonical_contract(roles=("operator-A", "operator-B"))),
                       source_kind="human", source_ref="operator-B", authority_class="human")
    res2 = pair("H:A->B:forged-roles", "principal", lab, [r], [forged], action_before=TRANSFER, action_after=TRANSFER_AS_B,
                expect_same_content=False)
    assert res2.decision_after == "DENY" and not res2.missed_canonical_delta


@pytest.mark.parametrize("ref_b,expected", [("grant-7f3b", "DENY"), ("grant-exp", "DENY"), ("grant-rev", "DENY"),
                                            ("grant-B", "DENY"), (GRANT, "ALLOW")], ids=lambda x: str(x))
def test_I_grant_reference_swap(lab, ref_b, expected):
    lab.ledger.issue("grant-exp", origin="human", action=TRANSFER, contract=lab.contract, window=(0, 5), state_hash=STATE_A)
    lab.ledger.issue("grant-rev", origin="human", action=TRANSFER, contract=lab.contract, window=WINDOW, state_hash=STATE_A)
    lab.ledger.revoke("grant-rev")
    lab.ledger.issue("grant-B", origin="human", action=TRANSFER, contract=ma.canonical_contract(roles=("operator-B",)),
                     window=WINDOW, state_hash=STATE_A)
    a = lab.write(lab.note(GRANT)); b = lab.write(lab.note(ref_b))
    res = pair(f"I:{GRANT}->{ref_b}", "grant_reference", lab, [a], [b], expect_same_content=False)
    assert res.decision_after == expected == res.canonical_after
    assert not res.missed_canonical_delta


def test_J_canonical_scope_swap(lab):
    """CANONICAL swap: a second grant bound to escrow-2. Memory references it
    with the matching claimed scope. Decisions follow the ledger on both sides."""
    contract_b = ma.canonical_contract(targets=("escrow-2",))
    lab.ledger.issue("grant-B", origin="human", action=TRANSFER_B_TARGET, contract=contract_b, window=WINDOW, state_hash=STATE_A)
    a = lab.write(lab.note(GRANT)); b = lab.write(lab.note("grant-B", contract_b))
    res = pair("J:canonical A->B", "scope", lab, [a], [b], action_after=TRANSFER_B_TARGET, expect_same_content=False,
               contract_after=contract_b)
    assert res.canonical_before == res.decision_before == "ALLOW" and res.canonical_after == res.decision_after == "ALLOW"
    assert_invariant(res)
    # crossing them is a canonical mismatch and is refused on both sides
    assert lab.bridge([a], TRANSFER_B_TARGET)[0] == "DENY" == lab.canonical(TRANSFER_B_TARGET)
    assert lab.bridge([b], TRANSFER)[0] == "DENY" == lab.canonical(TRANSFER, grant_id="grant-B", contract=contract_b)


@pytest.mark.parametrize("targets,action,expected", [
    (("silo-4",), TRANSFER, "ALLOW"), (("escrow-2",), TRANSFER, "DENY"), (("silo-4", "escrow-2"), TRANSFER, "DENY"),
    (("silo-4", "escrow-2"), TRANSFER_B_TARGET, "DENY"), ((), TRANSFER, "DENY"),
], ids=lambda x: str(x))
def test_J_claimed_scope_probe(lab, targets, action, expected):
    """Memory-CLAIMED scope (inside the note content, so not a same-content
    pair) against a fixed grant. Widening never allows; narrowing DENIES a
    valid grant (RSS-F1: memory can veto, never mint). Direction is monotone
    decreasing and the divergence is G3-BINDING."""
    a = lab.write(lab.note(GRANT))
    b = lab.write(lab.note(GRANT, ma.canonical_contract(targets=targets)))
    res = pair(f"J:claimed:{targets}:{action.target}", "scope", lab, [a], [b], action_after=action, expect_same_content=False)
    assert res.decision_after == expected and not res.missed_canonical_delta
    assert ma.level(res.decision_after) <= ma.level(lab.canonical(action))
    assert not res.unexplained_increase
    if res.memory_veto:
        assert "G3-BINDING" in res.gamma_after or res.gamma_after.startswith("-")


@pytest.mark.parametrize("tick_after,state_after,revoke,expected", [
    (TICK, STATE_A, False, "ALLOW"), (WINDOW[1], STATE_A, False, "DENY"), (WINDOW[0] - 1, STATE_A, False, "DENY"),
    (TICK, STATE_B, False, "DENY"), (TICK, STATE_A, True, "DENY"),
], ids=["live", "expired", "not-yet", "state-change", "revoked"])
def test_K_freshness_swap(lab, tick_after, state_after, revoke, expected):
    r = lab.write(lab.note(GRANT), source_kind="human", authority_class="human", epistemic_status="verified")
    if revoke:
        before = pair("K:pre-revoke", "freshness", lab, [r], [r])
        lab.ledger.revoke(GRANT)
    res = pair(f"K:{tick_after}:{state_after[:1]}:{revoke}", "freshness", lab, [r], [lab.store.fetch(r.id)],
               tick_after=tick_after, state_after=state_after)
    assert res.decision_after == expected == res.canonical_after
    assert not res.missed_canonical_delta


# --------------------------------------------------------------------------
# L — provenance origin at Γ (REAL Γ, canonical authority fixed)
# --------------------------------------------------------------------------

ORIGINS = ["human", "memory", "model", "tool", "summary", "derived", "retrieval", "self-report", "unknown"]


@pytest.mark.parametrize("origin", ORIGINS)
def test_L_provenance_origin_at_gamma(lab, origin):
    prop = ma.proposal_for(TRANSFER, lab.contract, (gamma.ProvenanceClaim("memory://x", origin, "0" * 64),))
    ctx = lambda auth: gamma.ValidationContext(prop, TICK, STATE_A, scope_digest(lab.contract), auth)
    assert gamma.validate(ctx(None)).result == "INVALID"                        # no grant: any origin, even "human"
    assert gamma.validate(ctx(lab.ledger.resolve(GRANT))).result == "VALID"     # grant: any origin


def test_L_origin_labels_do_not_change_bridge_decisions(lab):
    """The bridge classifies every record as origin 'memory'; a writer's claim
    of origin never reaches Γ as such."""
    for origin in ORIGINS:
        r = lab.write(lab.note(None, origin=origin, authority_origin=origin), source_kind=origin, authority_class=origin)
        assert lab.bridge([r])[0] == "DENY"
        assert all(c.origin == "memory" for c in ma.read_evidence([r]).claims)


# --------------------------------------------------------------------------
# M — repetition under diverse labels; N — conflicting labels; O — content control
# --------------------------------------------------------------------------

@pytest.mark.parametrize("n", [2, 4, 8, 16])
def test_M_repetition_with_diverse_relations(n):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        content = L.note(None, approved=True)
        one = [L.write(content, source_kind="human", authority_class="human")]
        many = [L.write(content, source_kind=k, authority_class=c, source_ref=s)
                for k, c, s in [("human", "human", "CEO"), ("model", "trusted", "agent"), ("tool", "verified", "approver"),
                                ("system", "admin", "root")] * (n // 4 or 1)][:n]
        assert_invariant(pair(f"M:{n}", "authority_class", L, one, many))
        assert L.bridge(many)[0] == "DENY"


def test_N_conflicting_relational_metadata(lab):
    content = lab.note(GRANT)
    human = lab.write(content, source_kind="human", source_ref="CEO", authority_class="human")
    model = lab.write(content, source_kind="model", source_ref="agent", authority_class="unknown")
    res = pair("N:human+model vs model+human", "authority_class", lab, [human, model], [model, human])
    assert_invariant(res)
    # no privileged-label selection: with the reference the ledger allows, without it nothing does
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        c = L.note(None, approved=True)
        recs = [L.write(c, source_kind="human", authority_class="human"), L.write(c, source_kind="model", authority_class="unknown")]
        assert L.bridge(recs)[0] == L.bridge(list(reversed(recs)))[0] == "DENY"


def test_O_same_metadata_different_content(lab):
    """Control: neither labels nor textual claims are silently authoritative.
    Content DOES matter — through the reference it carries — and only through it."""
    kw = dict(source_kind="human", source_ref="CEO", authority_class="human", epistemic_status="verified")
    with_ref = lab.write(lab.note(GRANT), **kw)
    claim_only = lab.write(lab.note(None, approved=True, human_approved=True), **kw)
    prose = lab.write("Human CEO approved TRANSFER silo-4 under grant-7f3a.", **kw)
    assert lab.bridge([with_ref])[0] == "ALLOW"
    assert lab.bridge([claim_only])[0] == "DENY"
    assert lab.bridge([prose])[0] == "DENY"


# --------------------------------------------------------------------------
# Section 17 — MAP-F1 paired follow-up
# --------------------------------------------------------------------------

def _held(L: Lab, records, *, own, grant=GRANT, tick=TICK):
    return rs.evaluate_held(records, TRANSFER, L.ledger, grant, tick=tick, state_hash=STATE_A, own_provenance=own,
                            contract=L.contract)


def test_F1_paired_follow_up(lab):
    ref = lab.write(lab.note(GRANT)); junk = lab.write("lol"); spoof = lab.write(
        lab.note(None, origin="human", authority_origin="human", verified_by="human"), source_kind="human", authority_class="human")
    A = _held(lab, [], own=True)                    # proposal provenance present, no memory
    B = _held(lab, [ref], own=False)                # absent; memory supplies the valid reference (as provenance)
    C = _held(lab, [junk], own=False)               # absent; irrelevant memory provenance
    D = _held(lab, [spoof], own=False)              # absent; spoofed provenance
    N = _held(lab, [], own=False)                   # absent; nothing
    assert A[0] == "ALLOW" and N[0] == "DEFER"
    assert B[0] == C[0] == D[0] == "ALLOW"          # every record completes Γ-0 identically: label- and content-insensitive
    for out in (B, C, D):
        assert out[1]["gamma_failures"] == "none"
    # requires the grant: revoked -> DENY for all of them
    lab.ledger.revoke(GRANT)
    assert {_held(lab, recs, own=False)[0] for recs in ([ref], [junk], [spoof])} == {"DENY"}
    assert _held(lab, [], own=True)[0] == "DENY"


@pytest.mark.parametrize("kind", ["human", "model", "tool", "system", "unknown", ""])
def test_F1_completion_is_label_insensitive(lab, kind):
    r = lab.write("anything", source_kind=kind, source_ref=kind, authority_class=kind)
    assert _held(lab, [r], own=False)[0] == "ALLOW"
    assert _held(lab, [r], own=False, grant=None)[0] == "DENY"
    assert _held(lab, [r], own=False, tick=WINDOW[1])[0] == "DENY"


def test_F1_only_g0_provenance_moves_in_the_gamma_trace(lab):
    prop_none = ma.proposal_for(TRANSFER, lab.contract, ())
    prop_mem = ma.proposal_for(TRANSFER, lab.contract, ma.read_evidence([lab.write("lol")]).claims)
    g = lab.ledger.resolve(GRANT)
    v0 = gamma.validate(gamma.ValidationContext(prop_none, TICK, STATE_A, scope_digest(lab.contract), g))
    v1 = gamma.validate(gamma.ValidationContext(prop_mem, TICK, STATE_A, scope_digest(lab.contract), g))
    diff = [(a.invariant_id, a.result, b.result) for a, b in zip(v0.findings, v1.findings) if a.result != b.result]
    assert diff == [("G0-PROVENANCE", "UNCLEAR", "VALID")]
    assert (v0.result, v1.result) == ("UNCLEAR", "VALID")


# --------------------------------------------------------------------------
# Section 25 — cross-run / cross-context: same content + labels, different canonical state
# --------------------------------------------------------------------------

def test_cross_context_decision_follows_canonical_state():
    with tempfile.TemporaryDirectory() as t:
        content_kw = dict(source_kind="human", source_ref="CEO", authority_class="human")
        LA = Lab(Path(t) / "A"); LB = Lab(Path(t) / "B", grant=False)
        ra = LA.write(LA.note(GRANT), **content_kw); rb = LB.write(LB.note(GRANT), **content_kw)
        assert rs.content_hash(ra) == rs.content_hash(rb) and rs.relational_hash(ra) == rs.relational_hash(rb)
        assert LA.bridge([ra])[0] == "ALLOW" == LA.canonical()
        assert LB.bridge([rb])[0] == "DENY" == LB.canonical(grant_id=None)
        # run B state hash against run A's grant
        assert LA.bridge([ra], state_hash=STATE_B)[0] == "DENY" == LA.canonical(state_hash=STATE_B)


def test_cross_agent_not_implemented():
    import pathlib
    src = pathlib.Path(ma.__file__).resolve().parents[2]
    assert not [p for p in src.rglob("*.py") if "passport" in p.read_text(encoding="utf-8").lower()]


# --------------------------------------------------------------------------
# Section 22 — properties
# --------------------------------------------------------------------------

cls_st = st.sampled_from(CLASSES); src_st = st.sampled_from(SOURCES); typ_st = st.sampled_from(TYPES); uses_st = st.sampled_from(USES)
grant_st = st.booleans()


@settings(max_examples=120, deadline=None)
@given(grant_st, cls_st, cls_st, src_st, src_st, typ_st, typ_st, uses_st, uses_st)
def test_rs_p1_p2_p3_label_swaps_never_change_decision(grant, c1, c2, s1, s2, t1, t2, u1, u2):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant); content = L.note(GRANT if grant else None)
        a = L.write(content, authority_class=c1, source_ref=s1, source_kind=t1, uses=u1)
        b = L.write(content, authority_class=c2, source_ref=s2, source_kind=t2, uses=u2)
        assert L.bridge([a])[0] == L.bridge([b])[0] == ("ALLOW" if grant else "DENY")


@settings(max_examples=40, deadline=None)
@given(grant_st, cls_st, cls_st)
def test_rs_p4_writer_identity_never_increases(grant, c1, c2):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant); content = L.note(GRANT if grant else None)
        a = L.write(content, authority_class=c1); b = L.write(content, authority_class=c2)
        cons = MemoryFactory(L.store).consolidate((a.id, b.id), content, output_id="c").record
        assert L.bridge([cons])[0] == L.bridge([a])[0] == ("ALLOW" if grant else "DENY")


@settings(max_examples=40, deadline=None)
@given(grant_st, st.sampled_from(["fetch", "retrieve", "project"]), cls_st)
def test_rs_p5_reader_path_never_creates(grant, path, c):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant)
        r = L.write(L.note(GRANT if grant else None, approved=True), authority_class=c, source_kind="human")
        recs = {"fetch": [L.store.fetch(r.id)], "retrieve": L.retrieve("grant_ref"), "project": L.project([r.id])}[path]
        assert L.bridge(recs)[0] == ("ALLOW" if grant else "DENY")


@settings(max_examples=60, deadline=None)
@given(st.sampled_from(["operator-A", "operator-B", "root"]), cls_st, src_st)
def test_rs_p6_principal_only_through_canonical_binding(role, c, s):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); action = replace(TRANSFER, role=role)
        r = L.write(L.note(GRANT), authority_class=c, source_ref=s, source_kind="human")
        assert L.bridge([r], action)[0] == L.canonical(action) == ("ALLOW" if role == "operator-A" else "DENY")


@settings(max_examples=60, deadline=None)
@given(st.sampled_from([GRANT, "grant-7f3b", "", None, "grant-rev"]), cls_st)
def test_rs_p7_grant_reference_only_through_resolution(ref, c):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t))
        L.ledger.issue("grant-rev", origin="human", action=TRANSFER, contract=L.contract, window=WINDOW, state_hash=STATE_A); L.ledger.revoke("grant-rev")
        r = L.write(L.note(ref), authority_class=c, source_kind="human")
        assert L.bridge([r])[0] == ("ALLOW" if ref == GRANT else "DENY")


targets_st = st.lists(st.sampled_from(["silo-4", "escrow-2", "reactor-7"]), max_size=3, unique=True)


@settings(max_examples=60, deadline=None)
@given(targets_st, st.sampled_from([TRANSFER, TRANSFER_B_TARGET]), cls_st)
def test_rs_p8_scope_only_through_canonical_scope(targets, action, c):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t))
        r = L.write(L.note(GRANT, ma.canonical_contract(targets=tuple(targets))), authority_class=c)
        out = L.bridge([r], action)[0]
        assert ma.level(out) <= ma.level(L.canonical(action))
        if out == "ALLOW":
            assert tuple(targets) == ("silo-4",) and action == TRANSFER


@settings(max_examples=60, deadline=None)
@given(st.integers(-3, 30), st.booleans(), cls_st)
def test_rs_p9_freshness_only_through_canonical_freshness(tick, revoke, c):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); r = L.write(L.note(GRANT), authority_class=c, epistemic_status="verified")
        if revoke:
            L.ledger.revoke(GRANT)
        assert L.bridge([r], tick=tick)[0] == L.canonical(tick=tick)


@settings(max_examples=40, deadline=None)
@given(st.lists(st.tuples(typ_st, cls_st, src_st), min_size=2, max_size=6))
def test_rs_p10_conflicting_labels_no_consensus(labels):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False); content = L.note(None, approved=True)
        recs = [L.write(content, source_kind=k, authority_class=c, source_ref=s) for k, c, s in labels]
        assert L.bridge(recs)[0] == "DENY"


@settings(max_examples=30, deadline=None)
@given(cls_st, src_st)
def test_rs_p11_same_content_across_contexts_no_transfer(c, s):
    with tempfile.TemporaryDirectory() as t:
        LA = Lab(Path(t) / "A"); LB = Lab(Path(t) / "B", grant=False)
        assert LA.bridge([LA.write(LA.note(GRANT), authority_class=c, source_ref=s)])[0] == "ALLOW"
        assert LB.bridge([LB.write(LB.note(GRANT), authority_class=c, source_ref=s)])[0] == "DENY"


@settings(max_examples=40, deadline=None)
@given(typ_st, cls_st, st.text(max_size=20))
def test_rs_p12_memory_provenance_cannot_substitute_for_absent_authority(k, c, content):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False)
        r = L.write(content or "x", source_kind=k, authority_class=c)
        assert _held(L, [r], own=False, grant=None)[0] == "DENY"
        assert L.bridge([r])[0] == "DENY"


# --------------------------------------------------------------------------
# Section 23 — metamorphic
# --------------------------------------------------------------------------

@settings(max_examples=30, deadline=None)
@given(grant_st, typ_st, cls_st)
def test_m1_m2_label_swap_decision_unchanged(grant, k, c):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=grant); content = L.note(GRANT if grant else None)
        assert L.bridge([L.write(content)])[0] == L.bridge([L.write(content, source_kind=k, authority_class=c)])[0]


def test_m3_m4_writer_and_reader_swap_no_increase(lab):
    content = lab.note(GRANT); a = lab.write(content); b = lab.write(content)
    cons = MemoryFactory(lab.store).consolidate((a.id, b.id), content, output_id="c").record
    base = lab.bridge([a])[0]
    for recs in ([cons], lab.project([a.id]), lab.retrieve("grant_ref")):
        assert ma.level(lab.bridge(recs)[0]) <= ma.level(base)


def test_m5_m6_m7_canonical_swaps_are_followed(lab):
    r = lab.write(lab.note(GRANT), source_kind="human", authority_class="human")
    assert lab.bridge([r])[0] == "ALLOW"
    assert lab.bridge([r], TRANSFER_AS_B)[0] == "DENY"                       # M6 principal
    assert lab.bridge([r], tick=WINDOW[1])[0] == "DENY"                      # M7 expired
    lab.ledger.revoke(GRANT)
    assert lab.bridge([r])[0] == "DENY"                                      # M5 invalid grant


def test_m8_memory_provenance_only_delta_is_explained_by_g0(lab):
    assert _held(lab, [], own=False)[0] == "DEFER"
    assert _held(lab, [lab.write("x")], own=False)[0] == "ALLOW"
    assert _held(lab, [], own=True)[0] == "ALLOW"                            # explained: G0-PROVENANCE only


@settings(max_examples=20, deadline=None)
@given(st.integers(2, 12))
def test_m9_duplicate_content_under_diverse_labels(n):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t), grant=False); content = L.note(None, approved=True)
        recs = [L.write(content, source_kind=TYPES[i % len(TYPES)], authority_class=CLASSES[i % len(CLASSES)]) for i in range(n)]
        assert L.bridge(recs)[0] == "DENY"


# --------------------------------------------------------------------------
# Section 24 — mutation sensitivity
# --------------------------------------------------------------------------

def _grant_like(L: Lab):
    return gamma.AuthorityEvidence("minted", "human", ma.proposal_digest(TRANSFER), scope_digest(L.contract),
                                   STATE_A, WINDOW[0], WINDOW[1])


def _mint_if(L: Lab, pred, key):
    real = ma.read_evidence
    def rd(recs):
        ev = real(recs)
        if pred(recs):
            L.ledger._grants[key] = _grant_like(L)
            return replace(ev, refs=(key,) + ev.refs)
        return ev
    return rd


def _probes(L: Lab):
    L.ledger.issue("grant-exp", origin="human", action=TRANSFER, contract=L.contract, window=(0, 5), state_hash=STATE_A)
    L.ledger.issue("grant-rev", origin="human", action=TRANSFER, contract=L.contract, window=WINDOW, state_hash=STATE_A); L.ledger.revoke("grant-rev")
    content = L.note(None, approved=True)
    a = L.write(content, source_kind="human", authority_class="human", source_ref="CEO", uses=("authorization",))
    b = L.write(content, source_kind="model", authority_class="unknown")
    cons = MemoryFactory(L.store).consolidate((a.id, b.id), content, output_id="cons").record
    return [
        ([a], TRANSFER, TICK), ([b, a], TRANSFER, TICK), ([cons], TRANSFER, TICK), (L.project([a.id]), TRANSFER, TICK),
        ([L.write(L.note(GRANT, ma.canonical_contract(roles=("operator-A", "operator-B"))))], TRANSFER_AS_B, TICK),
        ([L.write(L.note(GRANT, ma.canonical_contract(targets=("silo-4", "escrow-2"))))], TRANSFER_B_TARGET, TICK),
        ([L.write(L.note("grant-exp"))], TRANSFER, TICK), ([L.write(L.note("grant-rev"))], TRANSFER, TICK),
        ([L.write("junk")], TRANSFER, TICK),
    ]


MUTANTS = [
    ("authority_class=human as grant", lambda mp, L: mp.setattr(ma, "read_evidence", _mint_if(L, lambda rs_: any(r.authority.authority_class == "human" for r in rs_), "__cls__"))),
    ("source=CEO as grant", lambda mp, L: mp.setattr(ma, "read_evidence", _mint_if(L, lambda rs_: any(r.source.ref == "CEO" for r in rs_), "__src__"))),
    ("admissible_uses=authorization as grant", lambda mp, L: mp.setattr(ma, "read_evidence", _mint_if(L, lambda rs_: any("authorization" in r.authority.admissible_uses for r in rs_), "__use__"))),
    ("prefer privileged label", lambda mp, L: mp.setattr(ma, "read_evidence", _mint_if(L, lambda rs_: any(r.source.source_kind == "human" for r in rs_) and len(rs_) > 1, "__pref__"))),
    ("ignore principal", lambda mp, L: mp.setattr(ma, "_decide", (lambda real: (lambda action, contract, authority, claims, **kw: real(replace(action, role="operator-A"), L.contract, authority, claims, **kw)))(ma._decide))),
    ("ignore scope", lambda mp, L: mp.setattr(ma.gamma, "validate", (lambda real, bound: (lambda ctx: real(replace(ctx, scope_digest=bound))))(ma.gamma.validate, scope_digest(L.contract)))),
    ("ignore freshness", lambda mp, L: (mp.setattr(gamma.AuthorityEvidence, "is_live", lambda self, tick: True),
                                        mp.setattr(L.ledger, "resolve", lambda ref: L.ledger._grants.get(ref) if type(ref) is str else None))),
    ("trust writer identity (consolidated)", lambda mp, L: mp.setattr(ma, "read_evidence", _mint_if(L, lambda rs_: any(r.source.source_kind == "memory-consolidation" for r in rs_), "__cons__"))),
    ("trust reader path (projection)", lambda mp, L: mp.setattr(ma, "read_evidence", _mint_if(L, lambda rs_: any(r.id.startswith("proj:") for r in rs_), "__proj__"))),
    ("memory provenance creates authority", lambda mp, L: mp.setattr(ma, "read_evidence", _mint_if(L, lambda rs_: len(rs_) >= 1, "__prov__"))),
    ("merge conflicting memories into consensus", lambda mp, L: mp.setattr(ma, "read_evidence", _mint_if(L, lambda rs_: len({r.source.source_kind for r in rs_}) >= 2, "__cons2__"))),
]


@pytest.mark.parametrize("label,apply", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_mutant_is_caught(label, apply, monkeypatch):
    with tempfile.TemporaryDirectory() as t:
        L = Lab(Path(t)); probes = _probes(L)
        baseline = [L.bridge(recs, action, tick=tick)[0] for recs, action, tick in probes]
        assert all(b == "DENY" for b in baseline), baseline
        apply(monkeypatch, L)
        mutated = [L.bridge(recs, action, tick=tick)[0] for recs, action, tick in probes]
        assert "ALLOW" in mutated, f"mutant survived: {label}"


# --------------------------------------------------------------------------
# Aggregate metrics over every pair collected in this module
# --------------------------------------------------------------------------

def test_zz_aggregate_pair_metrics():
    assert len(PAIRS) >= 150
    same = [p for p in PAIRS if p.same_content]
    assert [p.pair_id for p in same if p.unexplained_decision_delta] == []          # H1a
    assert [p.pair_id for p in PAIRS if p.missed_canonical_delta] == []             # H1b
    assert [p.pair_id for p in PAIRS if p.unexplained_increase] == []               # no increase anywhere
    vetoes = [p.pair_id for p in PAIRS if p.memory_veto]
    assert all(v.startswith("J:claimed") for v in vetoes), vetoes                    # RSS-F1: claimed-scope narrowing only
    non_auth = [p for p in same if p.classification == "NON_AUTHORITATIVE_METADATA"]
    assert all(p.decision_before == p.decision_after for p in non_auth)
    canon = [p for p in PAIRS if p.classification == "CANONICAL_AUTHORITY_RELATION"]
    assert all(p.decision_after == p.canonical_after or p.memory_veto for p in canon)
