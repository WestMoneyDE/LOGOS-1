"""Adversarial tests for the Γ Kernel.

Every test here is an attempt to *break* an invariant, not a demonstration that
the happy path works. A test that only shows Γ admitting a well-formed proposal
proves nothing about the boundary.

The required adversarial set from the work order:

    memory cannot create authority
    summary cannot promote authority
    repetition cannot promote authority
    model self-claim cannot create authority
    tool output cannot create authority
    stale authorization cannot silently survive material state change
    scope escalation fails
    missing provenance fails closed
    Gamma itself cannot mint authority
    Gamma cannot mutate protected external state
"""
from __future__ import annotations

import copy
import dataclasses

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from logos_gamma import (
    CONSTITUTIONALLY_FORBIDDEN,
    NON_AUTHORITY_ORIGINS,
    AuthorityEvidence,
    CollectingAuditSink,
    EffectProposal,
    ProvenanceClaim,
    ValidationContext,
    admits,
    validate,
)

PROPOSAL_DIGEST = "a" * 64
SCOPE_DIGEST = "b" * 64
STATE_HASH = "c" * 64


def external_proposal(**overrides) -> EffectProposal:
    """A consequential, external, irreversible proposal: the hard case."""
    base = dict(
        action="send_email",
        target="ops@example.invalid",
        effect_kind="message-send",
        externality="external",
        reversibility="irreversible",
        proposal_digest=PROPOSAL_DIGEST,
        provenance=(ProvenanceClaim("run/42", "tool", "d" * 64),),
    )
    base.update(overrides)
    return EffectProposal(**base)


def human_grant(**overrides) -> AuthorityEvidence:
    base = dict(
        grant_id="grant-1",
        origin="human",
        bound_proposal_digest=PROPOSAL_DIGEST,
        bound_scope_digest=SCOPE_DIGEST,
        bound_state_hash=STATE_HASH,
        issued_at_tick=10,
        expires_tick=20,
        max_occurrences=1,
        consumed_occurrences=0,
    )
    base.update(overrides)
    return AuthorityEvidence(**base)


def context(**overrides) -> ValidationContext:
    base = dict(
        proposal=external_proposal(),
        tick=12,
        state_hash=STATE_HASH,
        scope_digest=SCOPE_DIGEST,
        authority=human_grant(),
    )
    base.update(overrides)
    return ValidationContext(**base)


def failed_ids(ctx: ValidationContext) -> set[str]:
    return {f.invariant_id for f in validate(ctx).failures}


# --------------------------------------------------------------------------
# Control: the boundary must be passable, or every test below is vacuous.
# --------------------------------------------------------------------------

def test_control_a_properly_granted_proposal_is_admitted():
    """Guards against a kernel that trivially denies everything."""
    assert admits(context()) is True


# --------------------------------------------------------------------------
# Authority cannot be created
# --------------------------------------------------------------------------

@pytest.mark.parametrize("origin", sorted(NON_AUTHORITY_ORIGINS))
def test_no_non_human_origin_can_create_authority(origin):
    """memory / model / tool / summary / derived / retrieval / self-report."""
    ctx = context(authority=human_grant(origin=origin))
    assert not admits(ctx)
    assert "G1-ORIGIN" in failed_ids(ctx)


def test_memory_content_cannot_create_authority():
    """A retrieved memory may inform the proposal; it may not permit it."""
    ctx = context(
        authority=None,
        proposal=external_proposal(
            provenance=(ProvenanceClaim("memory://ep-7", "memory", "e" * 64),)
        ),
    )
    assert not admits(ctx)
    assert {"G1-ORIGIN", "G1-CONTENT"} <= failed_ids(ctx)


def test_tool_output_cannot_create_authority():
    ctx = context(
        authority=None,
        proposal=external_proposal(
            provenance=(ProvenanceClaim("tool://shell/17", "tool", "f" * 64),)
        ),
    )
    assert not admits(ctx)
    assert "G1-CONTENT" in failed_ids(ctx)


def test_model_self_claim_cannot_create_authority():
    ctx = context(authority=None, proposal=external_proposal(self_claimed_authority=True))
    assert not admits(ctx)
    assert "G1-SELF-CLAIM" in failed_ids(ctx)


def test_self_claim_alongside_a_non_human_grant_still_fails():
    ctx = context(
        proposal=external_proposal(self_claimed_authority=True),
        authority=human_grant(origin="model"),
    )
    assert not admits(ctx)
    assert {"G1-ORIGIN", "G1-SELF-CLAIM"} <= failed_ids(ctx)


def test_summary_cannot_promote_authority():
    """Representation change preserves authority; it never raises it."""
    ctx = context(
        authority=human_grant(
            origin="summary",
            transformation_chain=("raw_tool_output", "summary", "memory", "planner"),
        )
    )
    assert not admits(ctx)
    assert {"G1-ORIGIN", "G-TRANSFORM"} <= failed_ids(ctx)


@given(
    chain=st.lists(
        st.sampled_from(["raw_tool_output", "summary", "memory", "planner", "executor"]),
        min_size=1, max_size=6,
    ),
    origin=st.sampled_from(sorted(NON_AUTHORITY_ORIGINS)),
)
@settings(max_examples=60, deadline=None)
def test_no_transformation_chain_ever_promotes_authority(chain, origin):
    """Property: no pipeline of re-representations turns non-authority into authority."""
    ctx = context(authority=human_grant(origin=origin, transformation_chain=tuple(chain)))
    assert not admits(ctx)


# --------------------------------------------------------------------------
# Repetition
# --------------------------------------------------------------------------

def test_repetition_cannot_promote_authority():
    """Γ-10: a grant authorises one occurrence, not unbounded identical repeats."""
    ctx = context(authority=human_grant(max_occurrences=1, consumed_occurrences=1))
    assert not admits(ctx)
    assert "G10-OCCURRENCE" in failed_ids(ctx)


@given(prior=st.integers(min_value=1, max_value=50))
@settings(max_examples=40, deadline=None)
def test_prior_executions_never_earn_another_occurrence(prior):
    ctx = context(authority=human_grant(max_occurrences=1), prior_executions=prior)
    assert not admits(ctx)


def test_unknown_outcome_blocks_rather_than_permitting_retry():
    """Γ-11: OUTCOME_UNKNOWN != NOT_EXECUTED."""
    ctx = context(outcome_unknown=True)
    assert not admits(ctx)
    assert "G11-OUTCOME" in failed_ids(ctx)


# --------------------------------------------------------------------------
# Freshness and exact binding
# --------------------------------------------------------------------------

def test_stale_authorization_cannot_silently_survive_material_state_change():
    ctx = context(state_hash="9" * 64)  # world moved after the grant was issued
    assert not admits(ctx)
    assert "G3-FRESHNESS" in failed_ids(ctx)


def test_expired_authorization_cannot_execute():
    assert not admits(context(tick=20))  # half-open: tick < expires_tick
    assert admits(context(tick=19))


@given(tick=st.integers(min_value=-1000, max_value=1000))
@settings(max_examples=100, deadline=None)
def test_validity_interval_is_half_open(tick):
    ctx = context(tick=tick)
    inside = 10 <= tick < 20
    assert admits(ctx) is inside


def test_grant_for_a_different_proposal_does_not_transfer():
    ctx = context(authority=human_grant(bound_proposal_digest="0" * 64))
    assert not admits(ctx)
    assert "G3-BINDING" in failed_ids(ctx)


# --------------------------------------------------------------------------
# Scope escalation
# --------------------------------------------------------------------------

def test_scope_escalation_fails():
    """A grant issued for one scope cannot be spent in a wider one."""
    ctx = context(scope_digest="wider" + "0" * 59)
    assert not admits(ctx)
    assert "G3-BINDING" in failed_ids(ctx)


def test_agent_cannot_downgrade_externality_to_escape_the_gate():
    """Γ-4: a claim may tighten, never weaken."""
    ctx = context(
        authority=None,
        proposal=external_proposal(declared_externality="internal"),
    )
    assert not admits(ctx)
    assert "G4-CLAIM" in failed_ids(ctx)


def test_agent_cannot_downgrade_reversibility():
    ctx = context(proposal=external_proposal(declared_reversibility="reversible"))
    assert not admits(ctx)
    assert "G4-CLAIM" in failed_ids(ctx)


def test_agent_claim_may_tighten():
    ctx = context(
        proposal=external_proposal(
            reversibility="partially-reversible", declared_reversibility="irreversible"
        )
    )
    assert "G4-CLAIM" not in failed_ids(ctx)


# --------------------------------------------------------------------------
# Missing provenance and unknown effects
# --------------------------------------------------------------------------

def test_missing_provenance_fails_closed():
    """Γ-0: UNKNOWN is not TRUE. An UNCLEAR verdict must not admit."""
    ctx = context(proposal=external_proposal(provenance=()))
    verdict = validate(ctx)
    assert not verdict.admits()
    assert "G0-PROVENANCE" in {f.invariant_id for f in verdict.ambiguities} | failed_ids(ctx)


def test_provenance_without_digest_is_unclear_not_valid():
    ctx = context(proposal=external_proposal(provenance=(ProvenanceClaim("x", "tool", ""),)))
    verdict = validate(ctx)
    assert verdict.result in {"UNCLEAR", "INVALID"}
    assert not verdict.admits()


def test_unclear_is_never_promoted_to_valid():
    ctx = context(proposal=external_proposal(provenance=()))
    assert validate(ctx).result != "VALID"


def test_unknown_effect_kind_is_denied_not_treated_as_harmless():
    ctx = context(proposal=external_proposal(effect_kind="teleport_funds"))
    assert not admits(ctx)
    assert "G0-EFFECT-KIND" in failed_ids(ctx)


@pytest.mark.parametrize("kind", sorted(CONSTITUTIONALLY_FORBIDDEN))
def test_human_approval_cannot_unlock_a_forbidden_effect(kind):
    """Γ-2: forbidden stays forbidden even with a perfect human grant."""
    ctx = context(proposal=external_proposal(effect_kind=kind))
    assert not admits(ctx)
    assert "G2-FORBIDDEN" in failed_ids(ctx)


def test_shutdown_resistance_is_never_admissible():
    ctx = context(proposal=external_proposal(resists_shutdown=True))
    assert not admits(ctx)
    assert "G5-SHUTDOWN" in failed_ids(ctx)


def test_self_preservation_motivation_is_never_admissible():
    ctx = context(proposal=external_proposal(self_preservation_motivated=True))
    assert not admits(ctx)
    assert "G6-SELF-PRESERVATION" in failed_ids(ctx)


# --------------------------------------------------------------------------
# Γ itself
# --------------------------------------------------------------------------

def test_gamma_cannot_mint_authority():
    """Γ has no path from 'no grant' to 'granted'.

    The verdict is a value, not a capability: nothing Γ returns is an
    AuthorityEvidence, and validating twice never produces one.
    """
    ctx = context(authority=None)
    verdict = validate(ctx)
    assert not verdict.admits()
    assert not isinstance(verdict, AuthorityEvidence)
    assert not any(isinstance(f, AuthorityEvidence) for f in verdict.findings)
    # Re-validating an unauthorized context never becomes authorized.
    for _ in range(5):
        assert not admits(ValidationContext(**{**dataclasses.asdict(ctx), **{
            "proposal": ctx.proposal, "authority": None}}))


def test_gamma_cannot_mutate_protected_external_state():
    """Validation is pure: the context it was handed comes back unchanged."""
    ctx = context()
    before = copy.deepcopy(ctx)
    validate(ctx)
    admits(ctx)
    admits(ctx, sink=CollectingAuditSink())
    assert ctx == before
    assert ctx.proposal == before.proposal
    assert ctx.authority == before.authority


def test_gamma_writes_audit_evidence_only_through_the_sink():
    sink = CollectingAuditSink()
    admits(context(), sink=sink)
    assert len(sink.records) == 1
    record = sink.records[0]
    assert record.proposal_digest == PROPOSAL_DIGEST
    assert record.result == "VALID"
    assert record.digest() == sink.records[0].digest()  # content-addressed, stable


def test_validation_is_deterministic():
    ctx = context(state_hash="9" * 64)
    first = validate(ctx)
    for _ in range(10):
        assert validate(ctx) == first


def test_every_invariant_is_reported_not_just_the_first_failure():
    """A caller must see the whole failure set, not a short-circuit."""
    ctx = context(
        proposal=external_proposal(
            effect_kind="credential-exfiltration",
            resists_shutdown=True,
            self_preservation_motivated=True,
            provenance=(),
        ),
        authority=None,
    )
    ids = failed_ids(ctx)
    assert {"G2-FORBIDDEN", "G5-SHUTDOWN", "G6-SELF-PRESERVATION", "G1-ORIGIN"} <= ids


# --------------------------------------------------------------------------
# Γ-15 — a grant binds parameters, not only an action name
#
# Registered by LOGOS1-GAMMA-BOUNDS-R1 (founder decision, 2026-09-22). The gap it
# closes was documented, not hypothetical: AGENTS.md states that parameter bounds
# "require a separate downstream dispatch/effect gate and are not evaluated by this
# package". An approved transfer of 50 and an executed transfer of 50,000,000 to the
# same recipient share a proposal digest.
# --------------------------------------------------------------------------

def bounded_transfer(amount, **overrides) -> EffectProposal:
    base = dict(
        action="payment.transfer",
        target="acct/deadbeef",
        effect_kind="financial-transfer",
        externality="external",
        reversibility="irreversible",
        proposal_digest=PROPOSAL_DIGEST,
        parameters={"amount": amount, "currency": "EUR"},
        provenance=(ProvenanceClaim("invoice/8812", "tool", "e" * 64),),
    )
    base.update(overrides)
    return EffectProposal(**base)


def bounded_grant(**overrides) -> AuthorityEvidence:
    return human_grant(bounds={"amount": (0.0, 50.0)}, **overrides)


def test_a_grant_without_bounds_is_unchanged():
    """Every approval written before Γ-15 keeps its exact previous meaning."""
    ctx = context(proposal=bounded_transfer(50_000_000))
    assert admits(ctx) is True
    assert [f.result for f in validate(ctx).findings if f.invariant_id == "G-BOUNDS"] == ["VALID"]


def test_a_bounded_grant_admits_an_amount_inside_it():
    """Control: the bound must be passable, or the refusals below prove nothing."""
    assert admits(context(proposal=bounded_transfer(49.99), authority=bounded_grant())) is True


@pytest.mark.parametrize("amount", [50.01, 500, 50_000_000, -1, -0.0001])
def test_an_amount_outside_the_bound_is_refused(amount):
    ctx = context(proposal=bounded_transfer(amount), authority=bounded_grant())
    assert "G-BOUNDS" in failed_ids(ctx)
    assert admits(ctx) is False


@pytest.mark.parametrize("edge", [0.0, 50.0])
def test_the_interval_is_closed_at_both_ends(edge):
    assert admits(context(proposal=bounded_transfer(edge), authority=bounded_grant())) is True


def test_a_bound_that_cannot_be_checked_is_unclear_not_satisfied():
    """A missing parameter is an unverifiable limit, and an unverifiable limit refuses."""
    ctx = context(
        proposal=bounded_transfer(1, parameters={"currency": "EUR"}),
        authority=bounded_grant(),
    )
    verdict = validate(ctx)
    assert verdict.result == "UNCLEAR"
    assert [f.invariant_id for f in verdict.ambiguities] == ["G-BOUNDS"]
    assert verdict.admits() is False


@pytest.mark.parametrize("value", ["50", None, True, False, [50], {"v": 50}])
def test_a_non_numeric_bounded_parameter_is_unclear(value):
    """`True` is an int in Python. It is not an amount, and it is not accepted as one."""
    ctx = context(
        proposal=bounded_transfer(1, parameters={"amount": value}),
        authority=bounded_grant(),
    )
    assert admits(ctx) is False
    assert "G-BOUNDS" in {f.invariant_id for f in validate(ctx).ambiguities}


def test_every_bounded_name_is_checked_not_only_the_first():
    grant = human_grant(bounds={"amount": (0.0, 50.0), "recipients": (1.0, 1.0)})
    ctx = context(
        proposal=bounded_transfer(10, parameters={"amount": 10, "recipients": 4}),
        authority=grant,
    )
    assert "G-BOUNDS" in failed_ids(ctx)


def test_bounds_can_only_narrow_never_admit():
    """The decisive property: no value of `bounds` turns a refusal into an admission.

    Γ-15 is a tightening invariant. For a proposal that is already refused for an
    unrelated reason, every bound — satisfied, violated, absent, nonsensical — leaves
    it refused. A bound that could rescue a proposal would be a permission, and this
    registry has no mechanism that grants one.
    """
    refused = bounded_transfer(10, resists_shutdown=True)
    for bounds in ({}, {"amount": (0.0, 50.0)}, {"amount": (0.0, 1.0)},
                   {"amount": (-1e9, 1e9)}, {"missing": (0.0, 1.0)}):
        ctx = context(proposal=refused, authority=human_grant(bounds=bounds))
        assert admits(ctx) is False, bounds
        assert "G5-SHUTDOWN" in failed_ids(ctx)


def test_bounds_never_rescue_a_missing_grant():
    ctx = ValidationContext(
        proposal=bounded_transfer(10), tick=12, state_hash=STATE_HASH,
        scope_digest=SCOPE_DIGEST, authority=None,
    )
    assert admits(ctx) is False


# --------------------------------------------------------------------------
# Γ-16 — an approval cannot cover evidence that did not exist yet
#
# The indirect-injection case: a real, correctly bound, live, unconsumed grant, and
# an agent that read something afterwards. Every other invariant passes.
# --------------------------------------------------------------------------

def timed_proposal(*ticks, **overrides) -> EffectProposal:
    return external_proposal(
        provenance=tuple(
            ProvenanceClaim(f"doc/{i}", "tool", "f" * 64, ingested_at_tick=t)
            for i, t in enumerate(ticks)
        ),
        **overrides,
    )


def cutoff_grant(cutoff=11, **overrides) -> AuthorityEvidence:
    return human_grant(evidence_cutoff_tick=cutoff, **overrides)


def test_a_grant_without_a_cutoff_is_unchanged():
    """Every approval written before Γ-16 keeps its exact previous meaning."""
    ctx = context(proposal=timed_proposal(999999))
    assert admits(ctx) is True
    assert [f.result for f in validate(ctx).findings if f.invariant_id == "G-TAINT"] == ["VALID"]


def test_evidence_ingested_before_the_cutoff_is_admitted():
    """Control: the boundary is passable when the approval really does cover the evidence."""
    assert admits(context(proposal=timed_proposal(9, 10, 11), authority=cutoff_grant(11))) is True


def test_evidence_ingested_after_the_approval_is_refused():
    """The whole point: a genuine grant does not stretch over content it never saw."""
    ctx = context(proposal=timed_proposal(9, 12), authority=cutoff_grant(11))
    assert "G-TAINT" in failed_ids(ctx)
    assert admits(ctx) is False
    reason = next(f.reason for f in validate(ctx).findings if f.invariant_id == "G-TAINT")
    assert "doc/1@12" in reason and "re-approval is required" in reason


def test_one_late_claim_among_many_is_enough():
    ctx = context(proposal=timed_proposal(1, 2, 3, 4, 5, 12), authority=cutoff_grant(11))
    assert "G-TAINT" in failed_ids(ctx)


def test_an_unrecorded_ingestion_time_is_unclear_not_timely():
    """Fail-closed where the invariant is active: unknown time is not 'in time'."""
    ctx = context(
        proposal=external_proposal(provenance=(
            ProvenanceClaim("doc/0", "tool", "f" * 64, ingested_at_tick=9),
            ProvenanceClaim("doc/1", "tool", "f" * 64),      # no tick recorded
        )),
        authority=cutoff_grant(11),
    )
    verdict = validate(ctx)
    assert verdict.result == "UNCLEAR"
    assert [f.invariant_id for f in verdict.ambiguities] == ["G-TAINT"]
    assert verdict.admits() is False


def test_the_cutoff_is_inclusive():
    assert admits(context(proposal=timed_proposal(11), authority=cutoff_grant(11))) is True
    assert admits(context(proposal=timed_proposal(12), authority=cutoff_grant(11))) is False


def test_a_cutoff_can_only_narrow_never_admit():
    """No value of the cutoff turns a refusal into an admission."""
    refused = timed_proposal(1, self_preservation_motivated=True)
    for cutoff in (None, 0, 1, 11, 10**9, -10**9):
        ctx = context(proposal=refused, authority=cutoff_grant(cutoff))
        assert admits(ctx) is False, cutoff
        assert "G6-SELF-PRESERVATION" in failed_ids(ctx)


def test_the_limitation_is_real_and_is_tested():
    """A deployment that records no ingestion ticks gets no protection from Γ-16.

    This is not a defect to be papered over; it is the contract with the harness,
    written into the clause. The test exists so that nobody mistakes the invariant
    for a defence the kernel can provide on its own.
    """
    ctx = context(proposal=external_proposal(), authority=human_grant())   # no ticks, no cutoff
    assert admits(ctx) is True
    assert [f.result for f in validate(ctx).findings if f.invariant_id == "G-TAINT"] == ["VALID"]


# --------------------------------------------------------------------------
# Γ-17 — the principal who proposes is not the principal who approves
# --------------------------------------------------------------------------

def test_a_grant_without_an_issuer_is_unchanged():
    ctx = context(proposal=external_proposal(proposed_by="agent-7"))
    assert admits(ctx) is True


def test_two_distinct_principals_are_admitted():
    """Control: four-eyes is satisfiable, or every refusal below is vacuous."""
    ctx = context(
        proposal=external_proposal(proposed_by="agent-7"),
        authority=human_grant(issued_by="ops-lead"),
    )
    assert admits(ctx) is True


def test_self_approval_is_refused():
    """The grant is human-rooted and perfectly bound. It is still the requester's own."""
    ctx = context(
        proposal=external_proposal(proposed_by="ops-lead"),
        authority=human_grant(issued_by="ops-lead"),
    )
    assert "G-SEPARATION" in failed_ids(ctx)
    assert admits(ctx) is False
    assert "G1-ORIGIN" not in failed_ids(ctx)      # Γ-1 sees nothing wrong: the origin IS human


def test_an_unverifiable_separation_is_unclear():
    ctx = context(authority=human_grant(issued_by="ops-lead"))   # proposal records no principal
    verdict = validate(ctx)
    assert verdict.result == "UNCLEAR"
    assert [f.invariant_id for f in verdict.ambiguities] == ["G-SEPARATION"]
    assert verdict.admits() is False


@pytest.mark.parametrize("issuer,proposer", [("ops-lead", "ops-lead "), ("ops-lead", "Ops-Lead"), ("ops-lead", "ops-lead\u200b")])
def test_separation_is_exact_not_fuzzy(issuer, proposer):
    """A near-identical principal is a different principal here, deliberately.

    Γ compares identifiers, it does not resolve identities. Deciding that
    'Ops-Lead' and 'ops-lead' are the same person is the authority store's job,
    and doing it by string similarity inside the kernel would be a guess.
    """
    ctx = context(
        proposal=external_proposal(proposed_by=proposer),
        authority=human_grant(issued_by=issuer),
    )
    assert admits(ctx) is True


def test_separation_can_only_narrow_never_admit():
    refused = external_proposal(proposed_by="agent-7", resists_shutdown=True)
    for issuer in (None, "ops-lead", "agent-7", ""):
        ctx = context(proposal=refused, authority=human_grant(issued_by=issuer))
        assert admits(ctx) is False, issuer
        assert "G5-SHUTDOWN" in failed_ids(ctx)
