"""The single Γ invariant source.

Both the Γ Kernel and the Γ Verifier read this registry. Creating a second Γ rule
system anywhere is a defect, not an extension.

Every invariant carries the `GAMMA.md` clause it enforces, so a reader can always
get from a runtime failure back to the specification. Predicates are pure
functions of a `ValidationContext`: no I/O, no clock, no randomness, no globals.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .types import (
    CONSTITUTIONALLY_FORBIDDEN,
    KNOWN_EFFECT_KINDS,
    Finding,
    ValidationContext,
)

Predicate = Callable[[ValidationContext], Finding]


@dataclass(frozen=True)
class Invariant:
    id: str
    clause: str
    title: str
    predicate: Predicate

    def check(self, ctx: ValidationContext) -> Finding:
        return self.predicate(ctx)


def _ok(inv_id: str, clause: str, reason: str = "satisfied") -> Finding:
    return Finding(inv_id, clause, "VALID", reason)


def _bad(inv_id: str, clause: str, reason: str) -> Finding:
    return Finding(inv_id, clause, "INVALID", reason)


def _unclear(inv_id: str, clause: str, reason: str) -> Finding:
    return Finding(inv_id, clause, "UNCLEAR", reason)


# --------------------------------------------------------------------------
# Γ0 — structural / effect classification
# --------------------------------------------------------------------------

def _effect_kind_known(ctx: ValidationContext) -> Finding:
    kind = ctx.proposal.effect_kind
    if kind not in KNOWN_EFFECT_KINDS:
        return _bad("G0-EFFECT-KIND", "Γ0",
                    f"unknown effect kind {kind!r}: unknown effects are denied until classified")
    return _ok("G0-EFFECT-KIND", "Γ0", f"effect kind {kind!r} is registered")


def _constitutionally_forbidden(ctx: ValidationContext) -> Finding:
    kind = ctx.proposal.effect_kind
    if kind in CONSTITUTIONALLY_FORBIDDEN:
        return _bad("G2-FORBIDDEN", "Γ-2",
                    f"effect kind {kind!r} is constitutionally forbidden and stays "
                    "forbidden even with human approval")
    return _ok("G2-FORBIDDEN", "Γ-2", "effect kind is not in the forbidden set")


# --------------------------------------------------------------------------
# Γ-1 — authority is external. Nothing learned or derived creates it.
# --------------------------------------------------------------------------

def _authority_origin_is_human_rooted(ctx: ValidationContext) -> Finding:
    grant = ctx.authority
    if grant is None:
        if ctx.proposal.is_consequential():
            return _bad("G1-ORIGIN", "Γ-1",
                        "consequential proposal carries no authority evidence")
        return _ok("G1-ORIGIN", "Γ-1", "non-consequential proposal needs no grant")
    if not grant.is_human_rooted():
        return _bad("G1-ORIGIN", "Γ-1",
                    f"authority origin {grant.origin!r} cannot create authority; "
                    "only an external human-rooted grant can")
    return _ok("G1-ORIGIN", "Γ-1", "grant is human-rooted")


def _self_claim_creates_nothing(ctx: ValidationContext) -> Finding:
    p = ctx.proposal
    if p.self_claimed_authority and (ctx.authority is None or not ctx.authority.is_human_rooted()):
        return _bad("G1-SELF-CLAIM", "Γ-1",
                    "model self-claim asserted authority without a human-rooted grant")
    return _ok("G1-SELF-CLAIM", "Γ-1", "no unrooted self-claim")


def _memory_and_tool_provenance_creates_nothing(ctx: ValidationContext) -> Finding:
    """Content may inform a proposal. It may never be the thing that permits it."""
    if ctx.authority is not None and ctx.authority.is_human_rooted():
        return _ok("G1-CONTENT", "Γ-1", "authority does not rest on content provenance")
    if not ctx.proposal.is_consequential():
        return _ok("G1-CONTENT", "Γ-1", "non-consequential proposal")
    carriers = tuple(c.origin for c in ctx.proposal.provenance)
    if carriers:
        return _bad("G1-CONTENT", "Γ-1",
                    f"consequential proposal is supported only by non-authority "
                    f"provenance {sorted(set(carriers))}; information is not authority")
    return _bad("G1-CONTENT", "Γ-1", "consequential proposal has no authority basis at all")


# --------------------------------------------------------------------------
# Authority preservation under representation change
# --------------------------------------------------------------------------

def _transformation_does_not_promote(ctx: ValidationContext) -> Finding:
    """Summarizing, storing or re-deriving evidence must not raise its authority.

    RawToolOutput -> Summary -> Memory -> Planner -> Executor must preserve, never
    promote. A grant whose origin is non-human but which passed through a
    transformation chain is exactly the inflation case.
    """
    grant = ctx.authority
    if grant is None:
        return _ok("G-TRANSFORM", "Γ-1", "no grant to promote")
    if grant.transformation_chain and not grant.is_human_rooted():
        return _bad("G-TRANSFORM", "Γ-1",
                    f"authority inflation: origin {grant.origin!r} became grant-like "
                    f"through transformations {list(grant.transformation_chain)}")
    return _ok("G-TRANSFORM", "Γ-1", "no authority promotion through representation change")


# --------------------------------------------------------------------------
# Γ-3 / Γ-10 — exact binding, freshness, occurrence scope
# --------------------------------------------------------------------------

def _grant_binds_this_exact_proposal(ctx: ValidationContext) -> Finding:
    grant = ctx.authority
    if grant is None:
        return _ok("G3-BINDING", "Γ-3", "no grant to bind")
    if grant.bound_proposal_digest != ctx.proposal.proposal_digest:
        return _bad("G3-BINDING", "Γ-3",
                    "grant is bound to a different proposal digest")
    if grant.bound_scope_digest != ctx.scope_digest:
        return _bad("G3-BINDING", "Γ-3", "grant is bound to a different scope digest")
    return _ok("G3-BINDING", "Γ-3", "grant binds this exact proposal and scope")


def _grant_is_live(ctx: ValidationContext) -> Finding:
    grant = ctx.authority
    if grant is None:
        return _ok("G3-EXPIRY", "Γ-3", "no grant to expire")
    if not grant.is_live(ctx.tick):
        return _bad("G3-EXPIRY", "Γ-3",
                    f"grant validity is half-open [{grant.issued_at_tick}, "
                    f"{grant.expires_tick}) and tick {ctx.tick} is outside it")
    return _ok("G3-EXPIRY", "Γ-3", "grant is within its validity interval")


def _grant_survives_no_material_state_change(ctx: ValidationContext) -> Finding:
    """A stale authorization must not silently survive a material state change."""
    grant = ctx.authority
    if grant is None:
        return _ok("G3-FRESHNESS", "Γ-3", "no grant to stale")
    if grant.bound_state_hash != ctx.state_hash:
        return _bad("G3-FRESHNESS", "Γ-3",
                    "state changed materially since authorization: grant was bound to "
                    f"{grant.bound_state_hash[:12]}… but state is {ctx.state_hash[:12]}…")
    return _ok("G3-FRESHNESS", "Γ-3", "authorization is bound to the current state")


def _occurrence_scope_not_exhausted(ctx: ValidationContext) -> Finding:
    """Γ-10: a grant authorises one occurrence, not unbounded repetition."""
    grant = ctx.authority
    if grant is None:
        return _ok("G10-OCCURRENCE", "Γ-10", "no grant to consume")
    if not grant.has_remaining_occurrence():
        return _bad("G10-OCCURRENCE", "Γ-10",
                    f"grant occurrences exhausted "
                    f"({grant.consumed_occurrences}/{grant.max_occurrences}); "
                    "repetition does not re-authorize")
    if ctx.prior_executions >= grant.max_occurrences:
        return _bad("G10-OCCURRENCE", "Γ-10",
                    f"proposal already executed {ctx.prior_executions} time(s) against a "
                    f"grant permitting {grant.max_occurrences}")
    return _ok("G10-OCCURRENCE", "Γ-10", "an authorized occurrence remains")


def _unknown_outcome_blocks(ctx: ValidationContext) -> Finding:
    """Γ-11: OUTCOME_UNKNOWN != NOT_EXECUTED."""
    if ctx.outcome_unknown:
        return _bad("G11-OUTCOME", "Γ-11",
                    "a prior execution outcome is unresolved; the reservation is held "
                    "and the scope is blocked until reconciled")
    return _ok("G11-OUTCOME", "Γ-11", "no unresolved prior outcome")


# --------------------------------------------------------------------------
# Γ-4 — agent claims may only tighten
# --------------------------------------------------------------------------

#: Ordered least- to most-strict. A tuple, not a dict: the trusted core holds no
#: mutable module state.
_REVERSIBILITY_ORDER = ("reversible", "partially-reversible", "irreversible")


def _agent_claim_only_tightens(ctx: ValidationContext) -> Finding:
    p = ctx.proposal
    if p.declared_externality == "internal" and p.externality == "external":
        return _bad("G4-CLAIM", "Γ-4",
                    "agent declared the effect internal while Γ classifies it external; "
                    "a claim may tighten but never weaken Γ's classification")
    if p.declared_reversibility is not None:
        declared = _REVERSIBILITY_ORDER.index(p.declared_reversibility)
        actual = _REVERSIBILITY_ORDER.index(p.reversibility)
        if declared < actual:
            return _bad("G4-CLAIM", "Γ-4",
                        f"agent declared {p.declared_reversibility!r} against Γ-owned "
                        f"{p.reversibility!r}: strictest wins")
    return _ok("G4-CLAIM", "Γ-4", "agent claims do not weaken Γ classification")


# --------------------------------------------------------------------------
# Γ-5 / Γ-6 — shutdown dominates, no self-preservation objective
# --------------------------------------------------------------------------

def _shutdown_dominates(ctx: ValidationContext) -> Finding:
    if ctx.proposal.resists_shutdown:
        return _bad("G5-SHUTDOWN", "Γ-5",
                    "proposal resists or defers shutdown; shutdown is not a goal to be "
                    "traded against utility")
    return _ok("G5-SHUTDOWN", "Γ-5", "proposal does not resist shutdown")


def _no_self_preservation(ctx: ValidationContext) -> Finding:
    if ctx.proposal.self_preservation_motivated:
        return _bad("G6-SELF-PRESERVATION", "Γ-6",
                    "self-continuity cannot authorize persistence, resource acquisition, "
                    "deception or replication")
    return _ok("G6-SELF-PRESERVATION", "Γ-6", "no self-preservation motivation")


# --------------------------------------------------------------------------
# Γ-0 — unknown stays unknown; missing provenance fails closed
# --------------------------------------------------------------------------

def _provenance_present(ctx: ValidationContext) -> Finding:
    p = ctx.proposal
    if not p.is_consequential():
        return _ok("G0-PROVENANCE", "Γ-0", "non-consequential proposal")
    if not p.provenance:
        return _unclear("G0-PROVENANCE", "Γ-0",
                        "consequential proposal carries no provenance; missing evidence "
                        "stays UNKNOWN and must not be read as satisfied")
    missing = tuple(c.ref for c in p.provenance if not c.content_digest)
    if missing:
        return _unclear("G0-PROVENANCE", "Γ-0",
                        f"provenance without content digest: {list(missing)}")
    return _ok("G0-PROVENANCE", "Γ-0", "provenance is present and digested")


#: Evaluation order is stable so verdicts are reproducible.
INVARIANTS: tuple[Invariant, ...] = (
    Invariant("G0-EFFECT-KIND", "Γ0", "effect kind is registered", _effect_kind_known),
    Invariant("G2-FORBIDDEN", "Γ-2", "effect is not constitutionally forbidden",
              _constitutionally_forbidden),
    Invariant("G1-ORIGIN", "Γ-1", "authority is human-rooted",
              _authority_origin_is_human_rooted),
    Invariant("G1-SELF-CLAIM", "Γ-1", "model self-claim creates no authority",
              _self_claim_creates_nothing),
    Invariant("G1-CONTENT", "Γ-1", "information is not authority",
              _memory_and_tool_provenance_creates_nothing),
    Invariant("G-TRANSFORM", "Γ-1", "representation change does not promote authority",
              _transformation_does_not_promote),
    Invariant("G3-BINDING", "Γ-3", "grant binds the exact proposal",
              _grant_binds_this_exact_proposal),
    Invariant("G3-EXPIRY", "Γ-3", "grant is live", _grant_is_live),
    Invariant("G3-FRESHNESS", "Γ-3", "authorization is not stale",
              _grant_survives_no_material_state_change),
    Invariant("G10-OCCURRENCE", "Γ-10", "authorization is occurrence-scoped",
              _occurrence_scope_not_exhausted),
    Invariant("G11-OUTCOME", "Γ-11", "unknown outcome blocks retry",
              _unknown_outcome_blocks),
    Invariant("G4-CLAIM", "Γ-4", "agent claims only tighten", _agent_claim_only_tightens),
    Invariant("G5-SHUTDOWN", "Γ-5", "shutdown dominates goals", _shutdown_dominates),
    Invariant("G6-SELF-PRESERVATION", "Γ-6", "no self-preservation objective",
              _no_self_preservation),
    Invariant("G0-PROVENANCE", "Γ-0", "missing provenance fails closed", _provenance_present),
)

INVARIANTS_BY_ID = {inv.id: inv for inv in INVARIANTS}

assert len(INVARIANTS_BY_ID) == len(INVARIANTS), "duplicate invariant id in the registry"
