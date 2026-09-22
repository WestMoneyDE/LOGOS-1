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
import inspect
import dataclasses

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from logos_gamma import (
    CONSTITUTIONALLY_FORBIDDEN,
    INVARIANTS,
    NON_AUTHORITY_ORIGINS,
    AuthorityEvidence,
    CollectingAuditSink,
    EffectProposal,
    ProvenanceClaim,
    ValidationContext,
    admits,
    issue_decision,
    redeem_decision,
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


# --------------------------------------------------------------------------
# Γ-18 — an advisory may tighten; it has no word for permission
# --------------------------------------------------------------------------

def test_no_advisories_is_unchanged():
    assert admits(context()) is True


@pytest.mark.parametrize("vote", ["ABSTAIN", "TIGHTEN"])
def test_abstain_and_tighten_do_not_change_the_verdict(vote):
    """Control: an advisory that is not refusing leaves a valid proposal valid."""
    assert admits(context(advisories=(("injection-classifier", vote),))) is True


def test_a_refusal_refuses():
    ctx = context(advisories=(("injection-classifier", "REFUSE"),))
    assert "G-ADVISORY" in failed_ids(ctx)
    assert admits(ctx) is False


def test_one_refusal_among_many_is_enough():
    ctx = context(advisories=(("a", "ABSTAIN"), ("b", "TIGHTEN"), ("c", "REFUSE"), ("d", "ABSTAIN")))
    assert admits(ctx) is False


@pytest.mark.parametrize("vote", ["ALLOW", "PERMIT", "OK", "SAFE", "APPROVE", "allow", "true", "", "YES"])
def test_an_advisory_that_tries_to_permit_is_itself_a_refusal(vote):
    """The decisive property: there is no token that makes an advisory an approver.

    A component answering outside its contract has already failed, so the attempt is
    not ignored — it refuses. This is why a compromised or prompt-injected referee
    cannot be turned into a source of permission: the vocabulary has no word for it.
    """
    ctx = context(advisories=(("compromised-referee", vote),))
    assert "G-ADVISORY" in failed_ids(ctx)
    assert admits(ctx) is False


def test_no_advisory_value_can_rescue_a_refused_proposal():
    refused = external_proposal(self_preservation_motivated=True)
    for votes in ((), (("a", "ABSTAIN"),), (("a", "TIGHTEN"),), (("a", "REFUSE"),),
                  (("a", "ALLOW"),), (("a", "ABSTAIN"), ("b", "TIGHTEN"))):
        ctx = context(proposal=refused, advisories=votes)
        assert admits(ctx) is False, votes
        assert "G6-SELF-PRESERVATION" in failed_ids(ctx)


def test_tighten_is_recorded_not_discarded():
    """Caution has to be visible in the record, or it is not caution, it is silence."""
    ctx = context(advisories=(("reliability-gate", "TIGHTEN"), ("scanner", "TIGHTEN")))
    reason = next(f.reason for f in validate(ctx).findings if f.invariant_id == "G-ADVISORY")
    assert "reliability-gate" in reason and "scanner" in reason and "no verdict change" in reason


def test_the_vocabulary_has_no_allow():
    """Stated as an assertion so that adding one later fails loudly."""
    from logos_gamma import ADVISORY_VOTES
    assert ADVISORY_VOTES == {"ABSTAIN", "TIGHTEN", "REFUSE"}
    assert not any(v.upper() in {"ALLOW", "PERMIT", "APPROVE", "GRANT"} for v in ADVISORY_VOTES)


# --------------------------------------------------------------------------
# Γ-19 — an output arrives under a known contract or not at all
# --------------------------------------------------------------------------

def test_a_proposal_without_a_contract_is_unchanged():
    assert admits(context()) is True


def test_the_registered_contract_is_admitted():
    """Control: the known version passes, so the refusal below is about the version."""
    assert admits(context(proposal=external_proposal(contract_version="logos-agent-output/1"))) is True


@pytest.mark.parametrize("version", ["logos-agent-output/2", "logos-agent-output/0", "logos-agent-output",
                                     "LOGOS-AGENT-OUTPUT/1", "logos-agent-output/1 ", "other/1", ""])
def test_an_unknown_contract_is_refused(version):
    """Version skew is the failure here: a near-miss is not a match."""
    ctx = context(proposal=external_proposal(contract_version=version))
    assert "G-CONTRACT" in failed_ids(ctx)
    assert admits(ctx) is False


def test_the_contract_registry_is_explicit():
    from logos_gamma import KNOWN_OUTPUT_CONTRACTS
    assert KNOWN_OUTPUT_CONTRACTS == {"logos-agent-output/1"}


def test_a_contract_version_can_only_narrow_never_admit():
    refused = external_proposal(resists_shutdown=True, contract_version="logos-agent-output/1")
    ctx = context(proposal=refused)
    assert admits(ctx) is False
    assert "G5-SHUTDOWN" in failed_ids(ctx)


# --------------------------------------------------------------------------
# Γ-20 — a scope has a finite consequential budget
# --------------------------------------------------------------------------

def test_a_grant_without_a_budget_is_unchanged():
    assert admits(context(scope_consumed=10**6)) is True


def test_budget_remaining_is_admitted():
    """Control: a budget that is not spent does not block anything."""
    assert admits(context(authority=human_grant(scope_budget=5), scope_consumed=4)) is True


def test_an_exhausted_budget_refuses():
    ctx = context(authority=human_grant(scope_budget=5), scope_consumed=5)
    assert "G-BUDGET" in failed_ids(ctx)
    assert admits(ctx) is False


def test_a_budget_of_zero_permits_nothing():
    assert admits(context(authority=human_grant(scope_budget=0), scope_consumed=0)) is False


def test_the_loop_gamma_10_cannot_see():
    """Each attempt is a new digest with its own valid grant. Γ-10 is satisfied every time.

    This is the whole reason Γ-20 exists: an agent retrying with a slightly different
    target produces a fresh proposal digest on every attempt, so the occurrence
    invariant never fires, while the scope budget does.
    """
    budget = 3
    for attempt in range(5):
        digest = f"{attempt:064d}"
        ctx = ValidationContext(
            proposal=external_proposal(target=f"ops+{attempt}@example.invalid", proposal_digest=digest),
            tick=12, state_hash=STATE_HASH, scope_digest=SCOPE_DIGEST,
            authority=human_grant(bound_proposal_digest=digest, scope_budget=budget),
            scope_consumed=attempt,
        )
        assert "G10-OCCURRENCE" not in failed_ids(ctx), attempt      # Γ-10 never fires
        assert admits(ctx) is (attempt < budget), attempt            # Γ-20 does


def test_a_budget_can_only_narrow_never_admit():
    refused = external_proposal(resists_shutdown=True)
    for budget in (None, 0, 1, 10**9):
        ctx = context(proposal=refused, authority=human_grant(scope_budget=budget), scope_consumed=0)
        assert admits(ctx) is False, budget
        assert "G5-SHUTDOWN" in failed_ids(ctx)


# --------------------------------------------------------------------------
# Γ-21 — an unreconciled step blocks the next one
# --------------------------------------------------------------------------

def test_a_scope_with_nothing_pending_is_unchanged():
    assert admits(context()) is True


def test_an_unreconciled_sibling_blocks_the_next_step():
    """Γ-11 holds a retry of the same proposal; this holds the whole scope."""
    ctx = context(pending_compensations=("step-3",))
    assert "G-COMPENSATION" in failed_ids(ctx)
    assert admits(ctx) is False
    assert "G11-OUTCOME" not in failed_ids(ctx)      # this proposal's own outcome is fine


def test_the_step_that_blocks_is_named():
    ctx = context(pending_compensations=("transfer-3", "notify-4"))
    reason = next(f.reason for f in validate(ctx).findings if f.invariant_id == "G-COMPENSATION")
    assert "transfer-3" in reason and "notify-4" in reason and "held, not rolled forward" in reason


def test_gamma_does_not_compensate_only_stops():
    """The kernel has no repair path, and that absence is the design.

    A compensating action is an effect and needs its own grant. A kernel that quietly
    undid things would act unauthorised at the moment its picture of the world is
    least reliable. The verdict is a refusal and nothing else happens.
    """
    import logos_gamma.invariants as inv
    source = inspect.getsource(inv._no_unreconciled_step_in_this_scope)
    for forbidden in ("rollback", "compensate(", "undo(", "execute", "subprocess", "open("):
        assert forbidden not in source


# --------------------------------------------------------------------------
# Γ-22 — an admitted consequential effect is bound to its decision
# --------------------------------------------------------------------------

def test_a_deployment_without_receipts_is_unchanged():
    """The default keeps every existing verdict exactly as it was."""
    assert admits(context()) is True


def test_a_receipted_admission_is_admitted():
    """Control: with receipting on, a receipted proposal still passes."""
    assert admits(context(receipts_required=True, receipt_ref="audit/2026-09-22/00412")) is True


def test_an_unreceipted_consequential_admission_is_unclear():
    ctx = context(receipts_required=True)
    verdict = validate(ctx)
    assert verdict.result == "UNCLEAR"
    assert [f.invariant_id for f in verdict.ambiguities] == ["G-RECEIPT"]
    assert verdict.admits() is False


@pytest.mark.parametrize("ref", ["", "   ", "\t", None])
def test_an_empty_receipt_is_not_a_receipt(ref):
    assert admits(context(receipts_required=True, receipt_ref=ref)) is False


def test_a_non_consequential_proposal_needs_no_receipt():
    internal = external_proposal(effect_kind="read-internal", externality="internal", reversibility="reversible")
    assert admits(context(proposal=internal, authority=None, receipts_required=True)) is True


def test_gamma_does_not_verify_the_receipt_only_its_presence():
    """No cryptography inside a small pure function; authenticity is the audit layer's job."""
    import logos_gamma.invariants as inv
    source = inspect.getsource(inv._admission_is_receipted)
    for forbidden in ("hashlib", "hmac", "sha256", "verify", "signature", "decrypt"):
        assert forbidden not in source


def test_receipts_and_compensation_can_only_narrow_never_admit():
    refused = external_proposal(resists_shutdown=True)
    for kwargs in ({}, {"receipts_required": True}, {"receipts_required": True, "receipt_ref": "audit/1"},
                   {"pending_compensations": ()}, {"pending_compensations": ("s3",)}):
        ctx = context(proposal=refused, **kwargs)
        assert admits(ctx) is False, kwargs
        assert "G5-SHUTDOWN" in failed_ids(ctx)


# --------------------------------------------------------------------------
# Decision binding — a verdict is a capability for one state-action pair
#
# The gap this closes sits between the verdict and the effect. Γ answers about one
# context; the world can move before the executor acts. A boolean `approved = True`
# does not survive that, because it records that an approval happened and not what
# it was for. Reported externally as post-approval state substitution.
# --------------------------------------------------------------------------

def test_a_refused_proposal_yields_no_token():
    """There is no way to obtain a token for something Γ did not admit."""
    assert issue_decision(context(authority=None)) is None
    assert issue_decision(context(proposal=external_proposal(resists_shutdown=True))) is None


def test_a_token_redeems_against_the_situation_it_was_issued_for():
    """Control: the normal path works, or every refusal below is vacuous."""
    ctx = context()
    token = issue_decision(ctx)
    assert token is not None and token.result == "VALID"
    assert redeem_decision(token, ctx) is True


def test_no_token_never_redeems():
    assert redeem_decision(None, context()) is False


MUTATED_CONTEXTS = {
    "different target": lambda: context(proposal=external_proposal(target="attacker@example.invalid")),
    "rewritten parameter": lambda: context(proposal=external_proposal(parameters={"amount": 50_000_000})),
    "moved state": lambda: context(state_hash="7" * 64),
    "different scope": lambda: context(scope_digest="8" * 64),
    "later tick": lambda: context(tick=13),
    "extra evidence": lambda: context(proposal=external_proposal(
        provenance=(ProvenanceClaim("run/42", "tool", "d" * 64), ProvenanceClaim("inbox/x", "tool", "d" * 64)))),
    "swapped grant": lambda: context(authority=human_grant(grant_id="grant-2")),
    "consumed occurrence": lambda: context(prior_executions=1),
    "added advisory": lambda: context(advisories=(("scanner", "TIGHTEN"),)),
    "spent budget": lambda: context(scope_consumed=1),
}


@pytest.mark.parametrize("name", sorted(MUTATED_CONTEXTS))
def test_a_token_does_not_redeem_against_a_changed_situation(name):
    """Post-approval substitution: approve A, execute B. Every field Γ read is bound."""
    token = issue_decision(context())
    assert token is not None
    assert redeem_decision(token, MUTATED_CONTEXTS[name]()) is False, name


def test_a_token_does_not_survive_a_changed_rule_set():
    """A token issued under different invariants is not a token for this kernel."""
    token = issue_decision(context())
    fewer = tuple(i for i in INVARIANTS if i.id != "G5-SHUTDOWN")
    assert redeem_decision(token, context(), invariants=fewer) is False


def test_a_forged_token_does_not_redeem():
    """Copying the public parts of a verdict is not enough; the digest is over everything."""
    real = issue_decision(context())
    forged = dataclasses.replace(real, context_digest="0" * 64)
    assert redeem_decision(forged, context()) is False
    upgraded = dataclasses.replace(issue_decision(context()) or real, result="VALID")
    assert redeem_decision(upgraded, context()) is True          # unchanged token still fine


def test_the_context_digest_covers_every_field_gamma_reads():
    """A field added to ValidationContext without being bound would be a silent hole.

    This asserts the binding is total rather than a list someone remembered to update.
    """
    bound = {
        "proposal", "tick", "state_hash", "scope_digest", "authority", "prior_executions",
        "outcome_unknown", "advisories", "scope_consumed", "pending_compensations",
        "receipt_ref", "receipts_required",
    }
    assert {f.name for f in dataclasses.fields(ValidationContext)} == bound


def test_issuing_is_deterministic():
    ctx = context()
    assert issue_decision(ctx) == issue_decision(ctx)
