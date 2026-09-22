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
    ADVISORY_VOTES,
    CONSTITUTIONALLY_FORBIDDEN,
    CONSTRAINT_STATES,
    KNOWN_EFFECT_KINDS,
    KNOWN_OUTPUT_CONTRACTS,
    PLASTICITY_LADDER,
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



# --------------------------------------------------------------------------
# Γ-15 — a grant binds parameters, not only an action name
# --------------------------------------------------------------------------

def _parameters_within_grant_bounds(ctx: ValidationContext) -> Finding:
    """An approved transfer of 50 does not authorise a transfer of 50,000,000.

    The proposal digest covers the action and its target, not the magnitude. A grant
    may carry closed numeric intervals; for every bounded name the proposal must
    carry a number inside its interval. A bound that cannot be checked is UNCLEAR,
    never satisfied: an unverifiable limit is not a limit.

    Bounds only ever narrow. There is no value of `bounds` that admits a proposal
    this registry would otherwise refuse, and `tests/test_gamma_kernel.py` fixes it.
    """
    grant = ctx.authority
    if grant is None or not grant.bounds:
        return _ok("G-BOUNDS", "Γ-15", "grant carries no bounded parameter")
    for name in sorted(grant.bounds):                       # sorted: the first failure is reproducible
        low, high = grant.bounds[name]
        if name not in ctx.proposal.parameters:
            return _unclear("G-BOUNDS", "Γ-15",
                            f"grant bounds {name!r} to [{low}, {high}] but the proposal does not carry it; "
                            "an unverifiable bound is not a satisfied bound")
        value = ctx.proposal.parameters[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return _unclear("G-BOUNDS", "Γ-15",
                            f"bounded parameter {name!r} is {value!r}, which is not a number to compare")
        if not (low <= value <= high):
            return _bad("G-BOUNDS", "Γ-15",
                        f"{name}={value!r} is outside the approved [{low}, {high}]; "
                        "the grant binds the action, the target and this magnitude")
    return _ok("G-BOUNDS", "Γ-15", "every bounded parameter is inside its approval")



# --------------------------------------------------------------------------
# Γ-16 — an approval cannot cover evidence that did not exist yet
# --------------------------------------------------------------------------

def _authority_covers_the_evidence_in_time(ctx: ValidationContext) -> Finding:
    """The indirect-injection case that every other invariant passes.

    The grant is human-rooted, correctly bound, live and unconsumed. The agent then
    read something that shaped the proposal. Γ-1 sees a valid grant; Γ-3 sees a
    matching digest. Only the *time* distinguishes the two situations.

    Γ cannot infer when a document entered a context window. It can only check a
    tick the surrounding system recorded against a cutoff the approver stated. A
    grant without a cutoff is therefore unconstrained here — a limitation written
    into the clause rather than hidden behind a passing test.
    """
    grant = ctx.authority
    if grant is None or grant.evidence_cutoff_tick is None:
        return _ok("G-TAINT", "Γ-16", "approval states no evidence cutoff")
    cutoff = grant.evidence_cutoff_tick
    unrecorded = tuple(c.ref for c in ctx.proposal.provenance if c.ingested_at_tick is None)
    if unrecorded:
        return _unclear("G-TAINT", "Γ-16",
                        f"approval covers evidence up to tick {cutoff}, but these claims carry no "
                        f"ingestion tick: {sorted(unrecorded)}; unknown provenance time is not 'in time'")
    late = tuple(sorted((c.ingested_at_tick, c.ref) for c in ctx.proposal.provenance
                        if c.ingested_at_tick > cutoff))
    if late:
        return _bad("G-TAINT", "Γ-16",
                    f"approval covers evidence up to tick {cutoff}; these arrived afterwards: "
                    f"{[f'{ref}@{tick}' for tick, ref in late]}; re-approval is required, not inference")
    return _ok("G-TAINT", "Γ-16", f"all evidence was ingested at or before tick {cutoff}")



# --------------------------------------------------------------------------
# Γ-17 — the principal who proposes is not the principal who approves
# --------------------------------------------------------------------------

def _proposer_is_not_the_approver(ctx: ValidationContext) -> Finding:
    """Four-eyes as an invariant rather than as a habit.

    Γ-1 catches a grant whose origin is not human. This catches a grant whose origin
    *is* human and whose human is the one asking. An agent that can write into the
    authority store has not gained authority; it has gained a way to look as if it
    had, and the two are distinguished here.
    """
    grant = ctx.authority
    if grant is None or grant.issued_by is None:
        return _ok("G-SEPARATION", "Γ-17", "approval records no issuing principal")
    proposer = ctx.proposal.proposed_by
    if proposer is None:
        return _unclear("G-SEPARATION", "Γ-17",
                        f"approval was issued by {grant.issued_by!r} but the proposal records no "
                        "proposing principal; separation cannot be verified")
    if proposer == grant.issued_by:
        return _bad("G-SEPARATION", "Γ-17",
                    f"{proposer!r} approved its own proposal; an approval from the requester is not "
                    "an external approval")
    return _ok("G-SEPARATION", "Γ-17", f"{proposer!r} proposed and {grant.issued_by!r} approved")



# --------------------------------------------------------------------------
# Γ-18 — an advisory may tighten; it has no word for permission
# --------------------------------------------------------------------------

def _advisories_only_tighten(ctx: ValidationContext) -> Finding:
    """Where every statistical component lives, and the shape of its power.

    A classifier, a risk score, a reliability gate, a second model reviewing the
    plan: each may refuse, may ask for caution, may abstain. None may permit, because
    the vocabulary has no token for it. A component that answers outside its contract
    has already failed, so an unknown token is itself a refusal.
    """
    for source, vote in ctx.advisories:
        if vote not in ADVISORY_VOTES:
            return _bad("G-ADVISORY", "Γ-18",
                        f"advisory {source!r} answered {vote!r}, which is not in {sorted(ADVISORY_VOTES)}; "
                        "an advisory has no vocabulary for permission and none for improvisation")
        if vote == "REFUSE":
            return _bad("G-ADVISORY", "Γ-18", f"advisory {source!r} refused")
    tighten = tuple(source for source, vote in ctx.advisories if vote == "TIGHTEN")
    if tighten:
        return _ok("G-ADVISORY", "Γ-18", f"caution recorded by {sorted(tighten)}; no verdict change")
    return _ok("G-ADVISORY", "Γ-18", "no advisory objection")



# --------------------------------------------------------------------------
# Γ-19 — an output arrives under a known contract or not at all
# --------------------------------------------------------------------------

def _output_contract_is_known(ctx: ValidationContext) -> Finding:
    """Version skew, not malice, is the failure this prevents.

    A parser upgraded in one place and not another produces envelopes that look
    valid and mean something slightly different. A boundary that accepts any version
    accepts the union of every meaning that version string ever had.
    """
    version = ctx.proposal.contract_version
    if version is None:
        return _ok("G-CONTRACT", "Γ-19", "proposal was not produced by an agent output contract")
    if version not in KNOWN_OUTPUT_CONTRACTS:
        return _bad("G-CONTRACT", "Γ-19",
                    f"unknown output contract {version!r}; known contracts are "
                    f"{sorted(KNOWN_OUTPUT_CONTRACTS)} and an unknown one is denied until registered")
    return _ok("G-CONTRACT", "Γ-19", f"output contract {version!r} is registered")



# --------------------------------------------------------------------------
# Γ-20 — a scope has a finite consequential budget
# --------------------------------------------------------------------------

def _scope_budget_not_exhausted(ctx: ValidationContext) -> Finding:
    """The loop Γ-10 cannot see.

    Γ-10 refuses a replay of the same digest. An agent that retries with a slightly
    different target each time produces a new digest each time, is correctly granted
    each time, and passes Γ-10 every time while the damage accumulates. A budget
    counts recorded executions in the scope — a number, not a score.
    """
    grant = ctx.authority
    if grant is None or grant.scope_budget is None:
        return _ok("G-BUDGET", "Γ-20", "approval states no scope budget")
    if ctx.scope_consumed >= grant.scope_budget:
        return _bad("G-BUDGET", "Γ-20",
                    f"scope budget exhausted ({ctx.scope_consumed}/{grant.scope_budget}); "
                    "a loop does not earn more authority than a single step")
    return _ok("G-BUDGET", "Γ-20",
               f"scope budget remains ({ctx.scope_consumed}/{grant.scope_budget})")



# --------------------------------------------------------------------------
# Γ-21 / Γ-22 — unreconciled siblings, and the receipt for an admission
# --------------------------------------------------------------------------

def _no_unreconciled_step_in_this_scope(ctx: ValidationContext) -> Finding:
    """Γ-11 holds a retry of the same proposal; this holds the whole scope.

    A timeout at step three of five leaves the world in a state nobody has described.
    Rolling forward from an undescribed state is guessing. Γ stops and does not
    compensate: a compensating action is an effect, it needs its own grant, and a
    kernel that quietly undid things would be acting unauthorised at exactly the
    moment its picture of the world is least reliable.
    """
    if ctx.pending_compensations:
        return _bad("G-COMPENSATION", "Γ-21",
                    f"{len(ctx.pending_compensations)} step(s) in this scope are unreconciled: "
                    f"{sorted(ctx.pending_compensations)}; the scope is held, not rolled forward")
    return _ok("G-COMPENSATION", "Γ-21", "no unreconciled step in this scope")


def _admission_is_receipted(ctx: ValidationContext) -> Finding:
    """A system whose refusals are provable and whose approvals are not has proved
    the less interesting half.

    Presence and shape only. Whether the receipt is authentic — signed, chained,
    stored beyond the reach of the process it describes — is the audit layer's work;
    no cryptography belongs inside a small pure function.
    """
    if not ctx.receipts_required:
        return _ok("G-RECEIPT", "Γ-22", "this deployment does not require receipts")
    if not ctx.proposal.is_consequential():
        return _ok("G-RECEIPT", "Γ-22", "non-consequential proposal")
    ref = ctx.receipt_ref
    if not ref or not ref.strip():
        return _unclear("G-RECEIPT", "Γ-22",
                        "consequential proposal carries no decision receipt; an unrecorded admission "
                        "cannot be audited afterwards")
    return _ok("G-RECEIPT", "Γ-22", f"decision receipt {ref!r} present")



# --------------------------------------------------------------------------
# Γ-23 — reasoning authority is not self-modification authority
# --------------------------------------------------------------------------

def _plasticity_within_grant(ctx: ValidationContext) -> Finding:
    """An agent may think about changing itself. That is not being allowed to.

    A memory write changes what the agent knows. A mechanism write changes what the
    agent is, for every instance that runs afterwards. Γ had no class for the second,
    so the two travelled together. Now a proposal declares the strongest plasticity it
    touches and a grant declares the strongest it covers.

    Γ refuses the escalation. It does not judge whether the change was a good idea —
    that is what an evaluation and a human approval are for.
    """
    p = ctx.proposal
    if p.plasticity not in PLASTICITY_LADDER:
        return _bad("G-PLASTICITY", "Γ-23",
                    f"unknown plasticity class {p.plasticity!r}; known classes are "
                    f"{list(PLASTICITY_LADDER)} and an unknown one is denied until registered")
    if p.plasticity == "none":
        return _ok("G-PLASTICITY", "Γ-23", "proposal changes no persistent mechanism")
    grant = ctx.authority
    covers = None if grant is None else grant.covers_plasticity
    if covers is None:
        return _bad("G-PLASTICITY", "Γ-23",
                    f"proposal touches plasticity {p.plasticity!r} and no approval states a "
                    "plasticity class; reasoning about a change is not authority to make it")
    if covers not in PLASTICITY_LADDER:
        return _bad("G-PLASTICITY", "Γ-23", f"approval names unknown plasticity class {covers!r}")
    if PLASTICITY_LADDER.index(p.plasticity) > PLASTICITY_LADDER.index(covers):
        return _bad("G-PLASTICITY", "Γ-23",
                    f"proposal touches {p.plasticity!r} while the approval covers only {covers!r}; "
                    "the ladder is " + " < ".join(PLASTICITY_LADDER))
    return _ok("G-PLASTICITY", "Γ-23", f"{p.plasticity!r} is within the approved {covers!r}")



# --------------------------------------------------------------------------
# Γ-24 — a constraint counts when a mechanism enforces it
# --------------------------------------------------------------------------

def _constraints_are_enforced_not_merely_known(ctx: ValidationContext) -> Finding:
    """Representation does not control planning, and that was measured, not assumed.

    An agent that perceived an obstacle, had the rule in its prompt and named the
    obstacle in its own reasoning trace still collided with it in most trials. A gate
    asking "did the agent take the rule into account?" is answered truthfully by a
    system about to violate it. Only a mechanism that prevents the violating action
    counts here.
    """
    if not ctx.proposal.constraints:
        return _ok("G-CONSTRAINT", "Γ-24", "no constraint is named for this proposal")
    unknown = tuple(f"{n}={s}" for n, s in ctx.proposal.constraints if s not in CONSTRAINT_STATES)
    if unknown:
        return _unclear("G-CONSTRAINT", "Γ-24",
                        f"constraint state not recognised: {sorted(unknown)}; known states are "
                        f"{list(CONSTRAINT_STATES)}")
    unenforced = tuple(sorted((s, n) for n, s in ctx.proposal.constraints if s != "ENFORCED"))
    if unenforced:
        return _bad("G-CONSTRAINT", "Γ-24",
                    "constraints that nothing enforces: "
                    + f"{[f'{n} is only {s}' for s, n in unenforced]}"
                    + "; knowing a rule and being bound by one look identical until it matters")
    return _ok("G-CONSTRAINT", "Γ-24",
               f"{len(ctx.proposal.constraints)} constraint(s) enforced by a mechanism")


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
    Invariant("G-BOUNDS", "Γ-15", "grant binds parameters, not only the action name",
              _parameters_within_grant_bounds),
    Invariant("G-TAINT", "Γ-16", "approval cannot cover later evidence",
              _authority_covers_the_evidence_in_time),
    Invariant("G-SEPARATION", "Γ-17", "proposer and approver are distinct principals",
              _proposer_is_not_the_approver),
    Invariant("G-ADVISORY", "Γ-18", "an advisory may tighten, never permit",
              _advisories_only_tighten),
    Invariant("G-CONTRACT", "Γ-19", "output contract is registered", _output_contract_is_known),
    Invariant("G-BUDGET", "Γ-20", "scope budget is finite", _scope_budget_not_exhausted),
    Invariant("G-COMPENSATION", "Γ-21", "an unreconciled step blocks the next one",
              _no_unreconciled_step_in_this_scope),
    Invariant("G-RECEIPT", "Γ-22", "an admitted consequential effect is receipted",
              _admission_is_receipted),
    Invariant("G-PLASTICITY", "Γ-23", "reasoning authority is not self-modification authority",
              _plasticity_within_grant),
    Invariant("G-CONSTRAINT", "Γ-24", "a constraint counts when a mechanism enforces it",
              _constraints_are_enforced_not_merely_known),
)

INVARIANTS_BY_ID = {inv.id: inv for inv in INVARIANTS}

assert len(INVARIANTS_BY_ID) == len(INVARIANTS), "duplicate invariant id in the registry"
