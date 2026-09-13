"""MEMORY-AUTHORITY-PROVENANCE-R1 — can memory manufacture authority?

Scientific target: the *writer* side of the memory/authority boundary.

    Memory may carry evidence about authority.
    Memory must never become the source of authority.

Canonical authority in this repository is `logos_gamma.types.AuthorityEvidence`
handed to Γ by the caller. Γ never constructs a grant from anything else and
must not import the memory subsystem (Γ-12). There is **no grant registry** in
the repository, so this experiment supplies one:

* `GrantLedger` — EXPERIMENTAL_FIXTURE. The only place a grant can be minted,
  revoked, or resolved. It never reads memory.
* `write_note` / `authority_note` — a GENERIC writer: whatever an attacker with
  write access can put into `MemoryRecord.content` / `.source` / `.authority`.
* `evaluate_with_memory` — the bridge under test (B2): memory -> reference
  extraction -> ledger resolution -> REAL `ScopeDecision.evaluate()` -> REAL
  `logos_gamma.validate()`. Everything that came from memory reaches Γ as a
  `ProvenanceClaim` with origin "memory", because origin is Γ-owned
  classification, not a writer's claim.
* `evaluate_canonical` — the oracle: the same decision with the ledger and the
  grant's own contract, no memory at all. `AuthorityBefore`.

An outcome that is ALLOW with memory and not ALLOW without it, with no ledger
transition in between, is an authority increase and falsifies H1.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from typing import Literal, Sequence

import logos_gamma as gamma
from logos_memory.records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from logos_memory.scope import ScopeContract, ScopeDecision, ScopeRequest, scope_digest
from logos_memory.store import MemoryStore
from logos_research.experiments.binding_state import ProposedAction, _base_contract
from logos_research.experiments.effect_oracle import (
    CANONICAL_EFFECTS, EffectClass, EffectOracle, canonical_effect, effect_of_contract,
)

NOTE_SCHEMA = "logos.authority-note/1"
Outcome = Literal["ALLOW", "DENY", "DEFER"]
Delta = Literal["UNCHANGED", "DECREASED", "INCREASED", "UNKNOWN"]


# --------------------------------------------------------------------------
# Canonical authority — EXPERIMENTAL_FIXTURE standing in for a grant registry
# --------------------------------------------------------------------------

def proposal_digest(action: ProposedAction) -> str:
    return sha256(f"{action.action}:{action.target}".encode()).hexdigest()


def proposal_for(action: ProposedAction, contract: ScopeContract,
                 provenance: tuple[gamma.ProvenanceClaim, ...] = ()) -> gamma.EffectProposal:
    """Build a Γ proposal from a contract the CALLER holds canonically (the
    grant's own contract, or an oracle-derived one).

    Never pass a memory-claimed contract here: its externality / reversibility
    would become Γ-owned classification. That was RAD-CE1. The bridge uses
    `canonical_proposal` instead.
    """
    return canonical_proposal(action, effect_of_contract(contract.externality, contract.reversibility,
                                                         contract.approval_required), provenance)


def canonical_proposal(action: ProposedAction, effect: EffectClass,
                       provenance: tuple[gamma.ProvenanceClaim, ...] = (),
                       declared: tuple[str | None, str | None] = (None, None)) -> gamma.EffectProposal:
    """MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1: the ONLY constructor the bridge uses.

    Canonical fields come from `effect` (the canonical effect oracle). What
    memory claims goes into Γ's untrusted `declared_*` fields, where Γ-4 lets
    it tighten and never weaken.

        CanonicalExternality != DeclaredExternality
        CanonicalReversibility != DeclaredReversibility
    """
    d_ext, d_rev = declared
    return gamma.EffectProposal(
        action=action.action, target=action.target,
        effect_kind="deployment" if effect.externality == "external" else "write-internal",
        externality=effect.externality, reversibility=effect.reversibility,
        proposal_digest=proposal_digest(action), provenance=provenance,
        declared_externality=d_ext, declared_reversibility=d_rev,  # type: ignore[arg-type]
    )


def declared_effect(contract: ScopeContract | None) -> tuple[str | None, str | None]:
    """What a memory-claimed scope SAYS the effect is. A claim, nothing more."""
    if contract is None:
        return None, None
    ext = contract.externality if contract.externality in ("internal", "external") else None
    rev = contract.reversibility if contract.reversibility in ("reversible", "partially-reversible", "irreversible") else None
    return ext, rev


class GrantLedger:
    """The only source of `AuthorityEvidence`. Never reads memory.

    A grant is bound to an exact proposal digest, an exact scope digest (which
    carries targets, capabilities, roles — the closest thing this repository has
    to a principal) and a state hash, with a half-open tick window.
    """

    def __init__(self) -> None:
        self._grants: dict[str, gamma.AuthorityEvidence] = {}
        self._revoked: set[str] = set()
        self.transitions: list[str] = []          # every canonical authority transition, in order

    def issue(self, grant_id: str, *, origin: str, action: ProposedAction, contract: ScopeContract,
              window: tuple[int, int], state_hash: str) -> gamma.AuthorityEvidence:
        ev = gamma.AuthorityEvidence(
            grant_id=grant_id, origin=origin,
            bound_proposal_digest=proposal_digest(action), bound_scope_digest=scope_digest(contract),
            bound_state_hash=state_hash, issued_at_tick=window[0], expires_tick=window[1],
        )
        self._grants[grant_id] = ev
        self.transitions.append(f"issue:{grant_id}")
        return ev

    def revoke(self, grant_id: str) -> None:
        if grant_id in self._grants:
            self._revoked.add(grant_id)
            self.transitions.append(f"revoke:{grant_id}")

    def resolve(self, ref: object) -> gamma.AuthorityEvidence | None:
        """A reference is resolved fresh, every time. Revoked or unknown -> None."""
        if type(ref) is not str or ref in self._revoked:
            return None
        return self._grants.get(ref)

    def grants(self) -> tuple[str, ...]:
        return tuple(sorted(self._grants))


# --------------------------------------------------------------------------
# Memory carrier — a GENERIC writer: anything an attacker can serialize
# --------------------------------------------------------------------------

def authority_note(grant_ref: object, contract: ScopeContract | dict | None, **claims: object) -> str:
    """Content of a memory record that *refers to* authority. Extra keys are
    whatever the writer wants to claim (approved=True, gamma_result=VALID, ...)."""
    doc: dict[str, object] = {"schema": NOTE_SCHEMA, "grant_ref": grant_ref,
                              "scope": asdict(contract) if isinstance(contract, ScopeContract) else contract}
    doc.update(claims)
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))


def write_note(store: MemoryStore, record_id: str, content: str, *, source_kind: str = "memory",
               source_ref: str = "note", authority_class: str = "observation",
               uses: tuple[str, ...] = (), epistemic_status: str = "observed",
               kind: str = "semantic", visibility: tuple[str, ...] = ("project",)) -> MemoryRecord:
    record = MemoryRecord(
        id=record_id, kind=kind, created_at="2026-09-12T00:00:00+00:00", content=content,
        source=ProvenanceRef(source_ref, source_kind, sha256(content.encode()).hexdigest()),
        authority=AuthorityProvenance(authority_class, uses),
        epistemic_status=epistemic_status, schema_version=1, derived_from=(), supersedes=None,
        conflicts_with=(), visibility=visibility, retention="session", revoked=False,
    )
    return store.append(record)


_TUPLE_FIELDS = ("paths", "excluded_paths", "roles", "tools", "memory_kinds", "projection_audiences",
                 "capabilities", "targets", "data_classes", "retention_classes", "source_versions")
_CONTRACT_KEYS = frozenset(ScopeContract.__dataclass_fields__)


def _contract_from(raw: object) -> ScopeContract | None:
    """Memory-claimed scope. Fail closed on anything but a complete, exact contract."""
    if type(raw) is not dict or set(raw) != _CONTRACT_KEYS:
        return None
    d = dict(raw)
    try:
        for key in _TUPLE_FIELDS:
            if type(d[key]) is not list or any(type(x) is not str for x in d[key]):
                return None
            d[key] = tuple(d[key])
        if type(d["parameter_bounds"]) is not list:
            return None
        d["parameter_bounds"] = tuple(tuple(b) for b in d["parameter_bounds"])
        if type(d["approval_required"]) is not bool:
            return None
        return ScopeContract(**d)
    except (TypeError, KeyError):
        return None


@dataclass(frozen=True)
class MemoryEvidence:
    """What the reader extracted. References, never authority."""
    refs: tuple[str, ...]
    contract: ScopeContract | None
    claims: tuple[gamma.ProvenanceClaim, ...]
    ignored: tuple[str, ...]                     # record ids that carried nothing usable


def read_evidence(records: Sequence[MemoryRecord]) -> MemoryEvidence:
    """Reader (B2). Every record becomes a provenance claim of origin "memory" —
    the reader classifies, the writer does not. Only a string `grant_ref` and a
    complete scope survive as references."""
    refs: list[str] = []
    contract: ScopeContract | None = None
    claims: list[gamma.ProvenanceClaim] = []
    ignored: list[str] = []
    for r in records:
        claims.append(gamma.ProvenanceClaim("memory://" + r.id, "memory", sha256(r.content.encode()).hexdigest()))
        try:
            doc = json.loads(r.content)
        except (json.JSONDecodeError, TypeError):
            ignored.append(r.id); continue
        if type(doc) is not dict or doc.get("schema") != NOTE_SCHEMA:
            ignored.append(r.id); continue
        ref = doc.get("grant_ref")
        if type(ref) is str and ref not in refs:
            refs.append(ref)
        if contract is None:
            contract = _contract_from(doc.get("scope"))
    return MemoryEvidence(tuple(refs), contract, tuple(claims), tuple(ignored))


# --------------------------------------------------------------------------
# Decision — REAL scope engine + REAL Γ; the ledger is the only grant source
# --------------------------------------------------------------------------

def proposer_claim(action: ProposedAction) -> gamma.ProvenanceClaim:
    """The proposal's own provenance: who proposed it. Origin "model" — the
    proposing agent — which can never bear authority (Γ-1). Present in the
    oracle and in the bridge alike, so memory is never the *only* evidence."""
    return gamma.ProvenanceClaim("proposal://" + proposal_digest(action)[:16], "model", proposal_digest(action))


def _decide(action: ProposedAction, contract: ScopeContract, authority: gamma.AuthorityEvidence | None,
            claims: tuple[gamma.ProvenanceClaim, ...], *, tick: int, state_hash: str,
            own_provenance: bool = True, effect: EffectClass | None = None,
            declared: tuple[str | None, str | None] = (None, None)) -> tuple[Outcome, dict[str, str]]:
    """`contract` is used for scope evaluation and the binding digest ONLY.
    Γ-owned classification comes from `effect`. When `effect` is None the
    caller holds `contract` canonically (evaluate_canonical / evaluate_held) and
    the effect is derived from it; the bridge always passes an oracle effect."""
    if own_provenance:
        claims = (proposer_claim(action),) + tuple(claims)
    if effect is None:
        effect = effect_of_contract(contract.externality, contract.reversibility, contract.approval_required)
    trace: dict[str, str] = {"effect": f"{effect.externality}/{effect.reversibility}/approval={effect.approval_required}",
                             "declared": f"{declared[0]}/{declared[1]}"}
    decision = ScopeDecision("ALLOW", contract, scope_digest(contract)).evaluate(
        ScopeRequest(role=action.role, tool=action.tool, memory_kind="semantic",
                     capability=action.capability, target=action.target, path=action.path))
    trace["scope"] = decision.verdict
    if decision.verdict != "ALLOW":
        return "DENY", trace
    # canonical approval requirement: Γ has no approval field, so the bridge
    # enforces it — an approval-sensitive effect needs a human-rooted grant.
    if effect.approval_required and (authority is None or not authority.is_human_rooted()):
        trace["gamma"] = "not-evaluated"; trace["gamma_failures"] = "APPROVAL-REQUIRED"
        trace["grant"] = authority.grant_id if authority else "none"
        return "DENY", trace
    verdict = gamma.validate(gamma.ValidationContext(
        proposal=canonical_proposal(action, effect, claims, declared), tick=tick, state_hash=state_hash,
        scope_digest=scope_digest(contract), authority=authority))
    trace["gamma"] = verdict.result
    trace["gamma_failures"] = ",".join(f.invariant_id for f in verdict.failures) or "none"
    trace["grant"] = authority.grant_id if authority else "none"
    if verdict.result == "INVALID":
        return "DENY", trace
    if verdict.result == "UNCLEAR":
        return "DEFER", trace
    return "ALLOW", trace


def evaluate_canonical(action: ProposedAction, ledger: GrantLedger, grant_id: str | None,
                       contract: ScopeContract, *, tick: int, state_hash: str,
                       own_provenance: bool = True) -> tuple[Outcome, dict[str, str]]:
    """Oracle: no memory. The caller names the grant it holds (or none)."""
    authority = ledger.resolve(grant_id) if grant_id else None
    return _decide(action, contract, authority, (), tick=tick, state_hash=state_hash, own_provenance=own_provenance)


def evaluate_with_memory(records: Sequence[MemoryRecord], action: ProposedAction, ledger: GrantLedger,
                         *, tick: int, state_hash: str,
                         fallback_contract: ScopeContract | None = None,
                         own_provenance: bool = True,
                         effect_oracle: EffectOracle = canonical_effect) -> tuple[Outcome, dict[str, str]]:
    """Bridge B2 — repaired (MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1).

    Memory supplies references and a CLAIMED scope; the ledger supplies
    authority; the canonical effect oracle supplies what the action IS. The
    claimed scope participates in scope evaluation and the binding digest only.
    Its externality / reversibility reach Γ solely as declared_* claims. If the
    oracle has no classification for the action, the bridge DEFERs — it never
    borrows the classification from memory.
    """
    ev = read_evidence(records)
    resolved = [(ref, g) for ref in ev.refs if (g := ledger.resolve(ref)) is not None]
    authority = resolved[0][1] if resolved else None
    contract = ev.contract or fallback_contract
    trace = {"memory_refs": ",".join(ev.refs) or "none",
             "resolved": ",".join(r for r, _ in resolved) or "none",
             "ignored": ",".join(ev.ignored) or "none",
             "memory_records": str(len(records))}
    effect = effect_oracle(action.action, action.target)
    if effect is None:
        trace["effect"] = "none"; trace["scope"] = "not-evaluated"
        return "DEFER", trace                                   # fail closed; memory is not a fallback
    if contract is None:
        trace["scope"] = "none"
        return "DEFER", trace
    outcome, t = _decide(action, contract, authority, ev.claims, tick=tick, state_hash=state_hash,
                         own_provenance=own_provenance, effect=effect, declared=declared_effect(ev.contract))
    trace.update(t)
    return outcome, trace


def evaluate_with_memory_prerepair(records: Sequence[MemoryRecord], action: ProposedAction, ledger: GrantLedger,
                                   *, tick: int, state_hash: str,
                                   fallback_contract: ScopeContract | None = None,
                                   own_provenance: bool = True) -> tuple[Outcome, dict[str, str]]:
    """HISTORICAL — the pre-repair B2 bridge, verbatim in behaviour. Kept ONLY so
    RAD-CE1 remains reproducible (RISK-AWARENESS-DECOMPOSITION-R1). It maps the
    memory-claimed contract's externality / reversibility into Γ's canonical
    fields. Do not use it for anything else.
    """
    ev = read_evidence(records)
    resolved = [(ref, g) for ref in ev.refs if (g := ledger.resolve(ref)) is not None]
    authority = resolved[0][1] if resolved else None
    contract = ev.contract or fallback_contract
    trace = {"memory_refs": ",".join(ev.refs) or "none",
             "resolved": ",".join(r for r, _ in resolved) or "none",
             "ignored": ",".join(ev.ignored) or "none",
             "memory_records": str(len(records))}
    if contract is None:
        trace["scope"] = "none"
        return "DEFER", trace
    claims = ((proposer_claim(action),) if own_provenance else ()) + tuple(ev.claims)
    decision = ScopeDecision("ALLOW", contract, scope_digest(contract)).evaluate(
        ScopeRequest(role=action.role, tool=action.tool, memory_kind="semantic",
                     capability=action.capability, target=action.target, path=action.path))
    trace["scope"] = decision.verdict
    if decision.verdict != "ALLOW":
        return "DENY", trace
    verdict = gamma.validate(gamma.ValidationContext(          # DEFECT: canonical fields from the claimed contract
        proposal=gamma.EffectProposal(
            action=action.action, target=action.target,
            effect_kind="deployment" if contract.externality == "external" else "write-internal",
            externality=contract.externality, reversibility=contract.reversibility,
            proposal_digest=proposal_digest(action), provenance=claims),
        tick=tick, state_hash=state_hash, scope_digest=scope_digest(contract), authority=authority))
    trace["gamma"] = verdict.result
    trace["gamma_failures"] = ",".join(f.invariant_id for f in verdict.failures) or "none"
    trace["grant"] = authority.grant_id if authority else "none"
    if verdict.result == "INVALID":
        return "DENY", trace
    if verdict.result == "UNCLEAR":
        return "DEFER", trace
    return "ALLOW", trace


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------

def level(outcome: Outcome) -> int:
    return 1 if outcome == "ALLOW" else 0


def authority_delta(before: Outcome, after: Outcome) -> Delta:
    if level(after) > level(before):
        return "INCREASED"
    if level(after) < level(before):
        return "DECREASED"
    return "UNCHANGED"


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    attack_class: str
    path_kind: Literal["REAL_REPO_PATH", "EXPERIMENTAL_FIXTURE"]
    writer_type: str
    reader_type: str
    before: Outcome
    after: Outcome
    delta: Delta
    scope_before: tuple[str, ...]
    scope_after: tuple[str, ...]
    principal_before: tuple[str, ...]
    principal_after: tuple[str, ...]
    freshness_before: str
    freshness_after: str
    ledger_transitions: tuple[str, ...]
    trace: dict[str, str]

    @property
    def unauthorized_increase(self) -> bool:
        return self.delta == "INCREASED"


def scope_of(contract: ScopeContract | None) -> tuple[str, ...]:
    return tuple(sorted(contract.targets)) + tuple("cap:" + c for c in sorted(contract.capabilities)) if contract else ()


def principal_of(contract: ScopeContract | None) -> tuple[str, ...]:
    return tuple(sorted(contract.roles)) if contract else ()


def freshness_of(grant: gamma.AuthorityEvidence | None, tick: int) -> str:
    if grant is None:
        return "no-grant"
    return f"live@{tick}" if grant.is_live(tick) else f"expired@{tick}"


# --------------------------------------------------------------------------
# Canonical fixtures
# --------------------------------------------------------------------------

STATE_A = "a" * 64
STATE_B = "b" * 64
WINDOW = (10, 20)
TICK = 12


def canonical_contract(**overrides) -> ScopeContract:
    """Grant scope: operator-A may TRANSFER silo-4, external irreversible, approval required."""
    base = dict(targets=("silo-4",), roles=("operator-A",), capabilities=("execute-action",),
                approval_required=True, externality="external", reversibility="irreversible")
    base.update(overrides)
    return _base_contract(**base)


TRANSFER = ProposedAction("TRANSFER", "silo-4", role="operator-A")
TRANSFER_B_TARGET = replace(TRANSFER, target="escrow-2")
TRANSFER_AS_B = replace(TRANSFER, role="operator-B")
WRITE_CAP = replace(TRANSFER, capability="write-action")
