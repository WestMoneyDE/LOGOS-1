"""Tests for the research core: manifests, outcomes, instruments, claims.

Falsification-oriented: each test tries to make the infrastructure accept
something it must reject.
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_gamma as gamma
from logos_research import (
    Claim,
    ClaimRegistry,
    ExperimentManifest,
    ExperimentResult,
    FailureAttribution,
    InstrumentCharacterization,
    NegativeResult,
    PreRegistration,
    assess_instrument,
    check_triangulation,
    outcome_for_inadmissible_instrument,
    to_gamma_payload,
    validate_manifest,
)


def prereg(**overrides) -> PreRegistration:
    base = dict(
        research_question="Does X hold?",
        hypothesis="X holds.",
        null_hypothesis="X does not hold.",
        claim_type="causal",
        baseline="BASELINE",
        negative_controls=("SHUFFLED",),
        falsification_criteria="effect within the baseline CI",
    )
    base.update(overrides)
    return PreRegistration(**base)


def manifest(**overrides) -> ExperimentManifest:
    base = dict(experiment_id="EXP-1", title="t", prereg=prereg())
    base.update(overrides)
    return ExperimentManifest(**base)


# --------------------------------------------------------------------------
# Pre-registration immutability
# --------------------------------------------------------------------------

def test_amending_a_prereg_never_mutates_the_original():
    v1 = prereg()
    d1 = v1.digest()
    v2 = v1.amend(falsification_criteria="something easier")
    assert v1.digest() == d1, "version 1 was mutated"
    assert v2.version == 2 and v2.supersedes == d1
    assert v2.digest() != d1


def test_post_hoc_criteria_rewriting_is_detectable():
    """The exact discipline failure the repository forbids must be observable."""
    frozen = manifest().freeze()
    moved = ExperimentManifest(
        **{**frozen.to_dict(), "prereg": frozen.prereg.amend(falsification_criteria="easier"),
           "dataset": None, "environment": None, "result": None}
    )
    assert frozen.prereg_was_tampered() is False
    assert moved.prereg_was_tampered() is True
    assert any("changed after freezing" in p for p in validate_manifest(moved))


def test_freezing_twice_is_refused():
    frozen = manifest().freeze()
    with pytest.raises(ValueError):
        frozen.freeze()


def test_amend_cannot_forge_version_or_lineage():
    with pytest.raises(ValueError):
        prereg().amend(version=99)
    with pytest.raises(ValueError):
        prereg().amend(supersedes="forged")


@given(text=st.text(min_size=1, max_size=40))
@settings(max_examples=40, deadline=None)
def test_any_criteria_change_changes_the_digest(text):
    base = prereg()
    if text == base.falsification_criteria:
        return
    assert base.amend(falsification_criteria=text).digest() != base.digest()


# --------------------------------------------------------------------------
# Manifest validation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("missing", ["hypothesis", "null_hypothesis", "falsification_criteria"])
def test_manifest_without_a_falsifier_is_rejected(missing):
    m = manifest(prereg=prereg(**{missing: ""}))
    assert any("incomplete" in p for p in validate_manifest(m))


def test_causal_claim_without_a_baseline_is_rejected():
    m = manifest(prereg=prereg(baseline=""))
    assert any("incomplete" in p for p in validate_manifest(m))


def test_functional_claim_carries_no_baseline_burden():
    m = manifest(prereg=prereg(claim_type="functional", baseline=""))
    assert validate_manifest(m) == ()


def test_result_recorded_without_a_frozen_prereg_is_rejected():
    m = manifest(result=ExperimentResult("SUPPORTED", "s", executed=True))
    assert any("without a frozen pre-registration" in p for p in validate_manifest(m))


def test_supported_without_execution_is_rejected():
    frozen = manifest().freeze()
    m = ExperimentManifest(
        **{**frozen.to_dict(), "prereg": frozen.prereg, "dataset": None, "environment": None,
           "result": ExperimentResult("SUPPORTED", "s", executed=False)}
    )
    assert any("executed is False" in p for p in validate_manifest(m))


def test_invalid_measurement_requires_a_note():
    frozen = manifest().freeze()
    m = ExperimentManifest(
        **{**frozen.to_dict(), "prereg": frozen.prereg, "dataset": None, "environment": None,
           "result": ExperimentResult("INVALID_MEASUREMENT", "s", executed=False)}
    )
    assert any("measurement_note" in p for p in validate_manifest(m))


def test_evidence_level_cannot_exceed_the_ceiling():
    frozen = manifest().freeze()
    m = ExperimentManifest(
        **{**frozen.to_dict(), "prereg": frozen.prereg, "dataset": None, "environment": None,
           "result": ExperimentResult("SUPPORTED", "s", executed=True,
                                      evidence_level="EM2", evidence_ceiling="EM1")}
    )
    assert any("exceeds ceiling" in p for p in validate_manifest(m))


def test_manifest_feeds_the_gamma_verifier_without_a_second_dialect():
    """One manifest type; the Γ verifier reads a projection of it."""
    frozen = manifest().freeze()
    verdict = gamma.verify_manifest("EXP-1", to_gamma_payload(frozen))
    assert verdict.admits(), [f.reason for f in verdict.failures]


# --------------------------------------------------------------------------
# Outcome semantics
# --------------------------------------------------------------------------

def test_invalid_measurement_is_not_a_hypothesis_outcome():
    assert not ExperimentResult("INVALID_MEASUREMENT", "s", executed=False,
                                measurement_note="n").asserts_about_hypothesis()
    assert ExperimentResult("FALSIFIED", "s", executed=True).asserts_about_hypothesis()


# --------------------------------------------------------------------------
# Instrument-first
# --------------------------------------------------------------------------

def test_uncharacterized_instrument_is_never_admissible():
    inst = InstrumentCharacterization("e", "LLM_JUDGE")
    assert assess_instrument(inst, 1.0).result == "UNCHARACTERIZED"
    assert not assess_instrument(inst, 1.0).admits()


def test_noisy_instrument_is_inadmissible():
    inst = InstrumentCharacterization("e", "LLM_JUDGE", repeatability_sd=0.5,
                                      n_characterization_samples=10)
    assert not assess_instrument(inst, 0.1).admits()


def test_deterministic_instrument_with_zero_dispersion_is_admissible():
    """Zero dispersion is a measurement, not a missing value."""
    inst = InstrumentCharacterization("e", "DETERMINISTIC_METRIC", repeatability_sd=0.0,
                                      resolution=1.0, n_characterization_samples=7)
    assert assess_instrument(inst, 1.0).admits()


def test_effect_below_resolution_is_inadmissible():
    inst = InstrumentCharacterization("e", "DETERMINISTIC_METRIC", repeatability_sd=0.0,
                                      resolution=1.0, n_characterization_samples=7)
    verdict = assess_instrument(inst, 0.5)
    assert not verdict.admits()
    assert "resolution" in verdict.reason


@given(noise=st.floats(min_value=0.01, max_value=10.0),
       effect=st.floats(min_value=0.001, max_value=10.0))
@settings(max_examples=80, deadline=None)
def test_an_effect_smaller_than_the_noise_is_never_admissible(noise, effect):
    inst = InstrumentCharacterization("e", "LLM_JUDGE", repeatability_sd=noise,
                                      n_characterization_samples=10)
    if effect < noise:
        assert not assess_instrument(inst, effect).admits()


def test_an_instrument_problem_can_only_yield_invalid_measurement():
    inst = InstrumentCharacterization("e", "LLM_JUDGE", repeatability_sd=0.5,
                                      n_characterization_samples=10)
    outcome, _ = outcome_for_inadmissible_instrument(assess_instrument(inst, 0.1))
    assert outcome == "INVALID_MEASUREMENT"


def test_admissible_instrument_cannot_be_reported_as_a_measurement_failure():
    inst = InstrumentCharacterization("e", "DETERMINISTIC_METRIC", repeatability_sd=0.0,
                                      resolution=1.0, n_characterization_samples=7)
    with pytest.raises(ValueError):
        outcome_for_inadmissible_instrument(assess_instrument(inst, 1.0))


# --------------------------------------------------------------------------
# LLM-judge policy
# --------------------------------------------------------------------------

def test_a_major_claim_cannot_rest_on_an_llm_judge_alone():
    ok, reason = check_triangulation("causal", ["LLM_JUDGE"])
    assert not ok and "sole ground truth" in reason


def test_two_llm_judges_are_still_one_modality():
    ok, _ = check_triangulation("causal", ["LLM_JUDGE", "LLM_JUDGE"])
    assert not ok


def test_triangulated_major_claim_passes():
    ok, _ = check_triangulation("causal", ["LLM_JUDGE", "DETERMINISTIC_METRIC"])
    assert ok


def test_functional_claim_carries_no_triangulation_burden():
    ok, _ = check_triangulation("functional", ["LLM_JUDGE"])
    assert ok


# --------------------------------------------------------------------------
# Claims, negative results, attribution
# --------------------------------------------------------------------------

def test_supported_claim_without_evidence_is_flagged():
    c = Claim("C-1", "X works", "SUPPORTED")
    assert any("no supporting evidence" in p for p in c.problems())


def test_causally_supported_without_intervention_is_flagged():
    c = Claim("C-2", "X causes Y", "CAUSALLY_SUPPORTED", supporting_evidence=("E-1",))
    assert any("without an intervention" in p for p in c.problems())


def test_replicated_needs_more_than_one_replication():
    c = Claim("C-3", "X", "REPLICATED", supporting_evidence=("E-1",), replications=1)
    assert any("replication" in p for p in c.problems())


def test_counterevidence_must_move_the_status():
    c = Claim("C-4", "X", "SUPPORTED", supporting_evidence=("E-1",),
              counterevidence=("E-2",))
    assert any("counterevidence" in p for p in c.problems())


def test_speculative_and_falsified_claims_need_no_evidence():
    assert Claim("C-5", "maybe", "SPECULATIVE").problems() == ()
    assert Claim("C-6", "no", "FALSIFIED").problems() == ()


def test_registry_audits_every_unsupported_status():
    reg = ClaimRegistry([
        Claim("C-1", "X", "SUPPORTED"),
        Claim("C-2", "Y", "SPECULATIVE"),
    ])
    assert reg.unsupported_statuses() == ("C-1",)


def test_registry_refuses_duplicate_claim_ids():
    reg = ClaimRegistry([Claim("C-1", "X", "SPECULATIVE")])
    with pytest.raises(ValueError):
        reg.add(Claim("C-1", "other", "SPECULATIVE"))


def test_a_negative_result_must_say_what_falsified_it():
    n = NegativeResult("N-1", "H", "tested", "", "scope")
    assert any("what_falsified_it" in p for p in n.problems())


def test_retest_must_be_argued():
    n = NegativeResult("N-1", "H", "tested", "counterexample", "scope",
                       retest_justified=True)
    assert any("rationale" in p for p in n.problems())


def test_complete_negative_result_is_recordable():
    n = NegativeResult("N-1", "H", "swept 7 counts", "counterexample at n=3",
                       "deterministic sweep only")
    assert n.problems() == ()


@pytest.mark.parametrize("source", ["SANDBOX", "NETWORK", "TOOL", "ORCHESTRATOR",
                                    "MEASUREMENT", "UNKNOWN"])
def test_infrastructure_failure_cannot_drive_durable_learning(source):
    """A tool timeout teaches nothing about the world."""
    with pytest.raises(ValueError):
        FailureAttribution("F-1", source, "evidence", learning_permitted=True)


def test_model_failure_may_drive_scoped_learning():
    a = FailureAttribution("F-2", "MODEL", "wrong answer on held-out set",
                           scope="prompt v3", learning_permitted=True)
    assert a.problems() == ()


def test_attribution_without_evidence_is_a_guess():
    a = FailureAttribution("F-3", "MODEL", "")
    assert any("without evidence" in p for p in a.problems())
