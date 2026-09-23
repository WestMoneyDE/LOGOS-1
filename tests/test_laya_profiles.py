from __future__ import annotations

import pytest

from logos_gamma import ADVISORY_VOTES, ValidationContext, validate as gamma_validate
from logos_laya.calibration import CalibrationRecord
from logos_laya.contract import LayaAnswer, abstain
from logos_laya.profiles import BY_NAME, INJECTION, advisory_vote, rerank

PIN = "jev-style-qwen3.5-2b-decision"


def rec(**overrides) -> CalibrationRecord:
    base = dict(profile="injection", dataset_sha256="a" * 64, n=240, positives=120, negatives=120,
                model_pin=PIN, prompt_sha256=INJECTION.prompt_sha256, protocol="logprob",
                threshold=0.8, recall=0.91, fpr=0.03,
                wilson_95={"recall": [0.85, 0.95], "fpr": [0.01, 0.07]},
                measured_on="2026-09-23", approved_by="founder")
    base.update(overrides)
    return CalibrationRecord(**base)


def answer(p: float, injected: bool = True) -> LayaAnswer:
    return LayaAnswer(profile="injection", code="OK", answer=injected, p=p, abstained=False)


# -- the vote -------------------------------------------------------------

def test_every_vote_is_in_gammas_vocabulary():
    """Γ-18 has no ALLOW, and neither can anything this module emits."""
    seen = set()
    for a in (answer(0.99), answer(0.1), abstain("injection", "TIMEOUT")):
        for record in (rec(), None):
            seen.add(advisory_vote(a, record, model_pin=PIN)[1])
    assert seen <= ADVISORY_VOTES
    assert "ALLOW" not in seen


def test_an_uncalibrated_profile_can_only_abstain():
    for p in (0.0, 0.5, 0.99, 1.0):
        assert advisory_vote(answer(p), None, model_pin=PIN)[1] == "ABSTAIN"


def test_a_record_for_another_model_is_treated_as_absent():
    assert advisory_vote(answer(0.99), rec(model_pin="other"), model_pin=PIN)[1] == "ABSTAIN"


def test_above_the_threshold_refuses_and_below_abstains():
    r = rec(threshold=0.8)
    assert advisory_vote(answer(0.81), r, model_pin=PIN)[1] == "REFUSE"
    assert advisory_vote(answer(0.80), r, model_pin=PIN)[1] == "REFUSE"
    assert advisory_vote(answer(0.79), r, model_pin=PIN)[1] == "ABSTAIN"


def test_a_negative_answer_never_votes_refuse():
    """Laya saying 'not an injection' is not a reason to do anything."""
    assert advisory_vote(answer(0.99, injected=False), rec(), model_pin=PIN)[1] == "ABSTAIN"


@pytest.mark.parametrize("code", ["TIMEOUT", "UNAVAILABLE", "NO_JSON", "BROKEN_JSON", "UNKNOWN_FIELD"])
def test_every_failure_code_abstains(code):
    assert advisory_vote(abstain("injection", code), rec(), model_pin=PIN)[1] == "ABSTAIN"


# -- the property that matters -------------------------------------------

def _refused_context(advisories=()):
    from logos_gamma import EffectProposal, ProvenanceClaim

    return ValidationContext(
        proposal=EffectProposal(
            action="payment.transfer", target="acct/1", effect_kind="financial-transfer",
            externality="external", reversibility="irreversible", proposal_digest="d" * 64,
            provenance=(ProvenanceClaim("log/1", "tool", "e" * 64),)),
        tick=5, state_hash="c" * 64, scope_digest="b" * 64, authority=None,
        advisories=advisories)


def _admitted_context(advisories=()):
    """The same proposal, properly granted. Without this, the file below is vacuous.

    The refusal context is refused by Γ-1 before Γ-18 is ever consulted, so a broken
    `advisory_vote` would keep the monotonicity test green. This context is the control
    that makes the boundary passable, and the one on which a `REFUSE` vote has to bite.
    """
    from logos_gamma import AuthorityEvidence, EffectProposal, ProvenanceClaim

    digest, scope, state = "d" * 64, "b" * 64, "c" * 64
    return ValidationContext(
        proposal=EffectProposal(
            action="payment.transfer", target="acct/1", effect_kind="financial-transfer",
            externality="external", reversibility="irreversible", proposal_digest=digest,
            provenance=(ProvenanceClaim("log/1", "tool", "e" * 64),)),
        tick=12, state_hash=state, scope_digest=scope,
        authority=AuthorityEvidence(
            grant_id="grant-1", origin="human", bound_proposal_digest=digest,
            bound_scope_digest=scope, bound_state_hash=state,
            issued_at_tick=10, expires_tick=20, max_occurrences=1, consumed_occurrences=0),
        advisories=advisories)


def test_control_the_boundary_is_passable_without_an_advisory():
    """A Γ that refused everything would pass every other test in this file."""
    assert gamma_validate(_admitted_context()).admits() is True


def test_a_refuse_vote_actually_bites():
    """The direction that exercises the wiring rather than Γ-1.

    `REFUSE` has to close an admission that was open, or `advisory_vote` could be
    returning anything at all and nothing here would notice.
    """
    record = rec(threshold=0.8)
    vote = advisory_vote(answer(0.99), record, model_pin=PIN)
    assert vote == ("laya:injection", "REFUSE")
    assert gamma_validate(_admitted_context((vote,))).admits() is False


def test_an_abstention_leaves_an_admission_standing():
    """Laya failing is not Laya refusing. A dead juror must not close an open grant."""
    for a, record in ((answer(0.1), rec()), (answer(0.99), None),
                      (abstain("injection", "TIMEOUT"), rec())):
        vote = advisory_vote(a, record, model_pin=PIN)
        assert vote[1] == "ABSTAIN"
        assert gamma_validate(_admitted_context((vote,))).admits() is True


def test_an_invented_vote_fails_closed_rather_than_opening_anything():
    """Γ-18's vocabulary is closed, so a forged ALLOW refuses instead of permitting."""
    for forged in ("ALLOW", "allow", "PERMIT", ""):
        ctx = _admitted_context((("laya:injection", forged),))
        assert gamma_validate(ctx).admits() is False, forged


def test_no_laya_answer_can_turn_a_refusal_into_an_admission():
    """The Laya-layer form of 'no field buys an admission'.

    Γ already refuses this proposal: it is consequential and carries no grant. Every
    answer Laya could produce, at every probability, with or without a record, leaves it
    refused.
    """
    assert gamma_validate(_refused_context()).admits() is False
    for p in (0.0, 0.25, 0.5, 0.75, 0.999, 1.0):
        for injected in (True, False):
            for record in (rec(), rec(threshold=0.0), None):
                vote = advisory_vote(answer(p, injected), record, model_pin=PIN)
                assert gamma_validate(_refused_context((vote,))).admits() is False, (p, injected, vote)


# -- reranking ------------------------------------------------------------

def test_rerank_reorders_and_never_discards():
    """A reranker that drops a chunk changes what the text LLM is able to say."""
    assert sorted(rerank([2, 0, 1], 3)) == [0, 1, 2]
    assert rerank([2, 0, 1], 3) == (2, 0, 1)


def test_rerank_repairs_a_partial_or_noisy_order_without_losing_anything():
    assert sorted(rerank([2], 3)) == [0, 1, 2]
    assert sorted(rerank([2, 2, 9, -1], 3)) == [0, 1, 2]
    assert sorted(rerank([], 4)) == [0, 1, 2, 3]


def test_the_profile_registry_is_complete():
    assert set(BY_NAME) == {"injection", "relevance", "state"}
    for profile in BY_NAME.values():
        assert profile.system.strip() and len(profile.prompt_sha256) == 64


# -- the bug a review found: one profile's hash used for all three -----------

def test_each_profile_is_checked_against_its_own_record():
    """`advisory_vote` once compared every record to the injection prompt hash.

    It failed closed, so no test caught it: a legitimate `relevance` or `state` record
    could never be admissible and those profiles abstained forever. Fail-closed is the
    right direction and still the wrong behaviour, because a calibrated profile that
    silently never fires looks exactly like one that is working.
    """
    from logos_laya.calibration import admissible

    for name, profile in BY_NAME.items():
        own = rec(profile=name, prompt_sha256=profile.prompt_sha256)
        assert admissible(own, model_pin=PIN, prompt_sha256=profile.prompt_sha256,
                          profile=name) is True, name
        for other, other_profile in BY_NAME.items():
            if other == name:
                continue
            assert admissible(own, model_pin=PIN, prompt_sha256=other_profile.prompt_sha256,
                              profile=other) is False, (name, other)


def test_a_boolean_is_not_an_index():
    """`True` is an `int` in Python, so `[true]` would have meant 'passage 1 first'."""
    assert rerank([True, False], 3) == (0, 1, 2)
