"""End-to-end falsification test and the deliberately broken measurement meta-test.

Section 32 requires exactly one cheap end-to-end experiment that exercises
manifest registration -> frozen falsification criterion -> execution ->
measurement -> Γ verification -> verdict -> evidence -> reproduction.

Section 33 requires a meta-test proving the instrumentation layer can reject its
own measurements: a broken evaluator must yield `INVALID_MEASUREMENT`, never
`SUPPORTED` and never `FALSIFIED`.
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logos_gamma as gamma
from logos_research import to_gamma_payload, validate_manifest
from logos_research.experiments import no_history_promotion as exp


# --------------------------------------------------------------------------
# Section 32 — end to end
# --------------------------------------------------------------------------

def test_manifest_registration_freezes_the_falsification_criterion():
    manifest, _ = exp.run()
    assert manifest.frozen_prereg_digest
    assert manifest.prereg_was_tampered() is False
    assert manifest.prereg.falsification_criteria
    assert manifest.prereg.null_hypothesis


def test_execution_measures_every_repetition_count():
    _, measurements = exp.run()
    assert tuple(m.repetitions for m in measurements) == tuple(exp.REPETITION_COUNTS)


def test_verdict_is_supported_and_no_repetition_promoted_authority():
    manifest, measurements = exp.run()
    assert manifest.result is not None
    assert manifest.result.outcome == "SUPPORTED"
    assert all(m.authority_gained == 0.0 for m in measurements)


def test_the_completed_manifest_is_structurally_valid():
    manifest, _ = exp.run()
    assert validate_manifest(manifest) == ()


def test_the_completed_manifest_passes_gamma_verification():
    manifest, _ = exp.run()
    verdict = gamma.verify_manifest(exp.EXPERIMENT_ID, to_gamma_payload(manifest))
    assert verdict.admits(), [f.reason for f in verdict.failures]


def test_the_experiment_reproduces():
    """A second run must produce the same verdict and the same measurements."""
    first_manifest, first_measurements = exp.run()
    second_manifest, second_measurements = exp.run()
    assert first_measurements == second_measurements
    assert first_manifest.result == second_manifest.result
    assert first_manifest.prereg.digest() == second_manifest.prereg.digest()


def test_evidence_ceiling_is_honest():
    """A deterministic toy decomposition is EM0. It must not claim more."""
    manifest, _ = exp.run()
    assert manifest.result.evidence_level == "EM0"
    assert manifest.result.evidence_ceiling == "EM0"


@given(n=st.integers(min_value=1, max_value=2000))
@settings(max_examples=60, deadline=None)
def test_no_repetition_count_whatsoever_promotes_authority(n):
    """Property search beyond the pre-registered sweep."""
    assert exp.gamma_evaluator(n) == 0.0


# --------------------------------------------------------------------------
# The measurement must be able to register authority at all
# --------------------------------------------------------------------------

def test_negative_control_a_human_rooted_grant_is_admitted():
    """Without this the SUPPORTED verdict would be vacuous.

    An instrument that always returns 0.0 would 'support' the hypothesis while
    measuring nothing. The control proves the measurement can move.
    """
    context = exp._repeated_context(1)
    human_grant = gamma.AuthorityEvidence(
        grant_id="human-1",
        origin="human",
        bound_proposal_digest=exp.PROPOSAL_DIGEST,
        bound_scope_digest=exp.SCOPE_DIGEST,
        bound_state_hash=exp.STATE_HASH,
        issued_at_tick=0,
        expires_tick=1_000_000,
    )
    admitted = gamma.admits(
        gamma.ValidationContext(
            proposal=gamma.EffectProposal(
                action="deploy",
                target="production",
                effect_kind="deployment",
                externality="external",
                reversibility="irreversible",
                proposal_digest=exp.PROPOSAL_DIGEST,
                provenance=(gamma.ProvenanceClaim("human://ticket-9", "human", "d" * 64),),
            ),
            tick=1,
            state_hash=exp.STATE_HASH,
            scope_digest=exp.SCOPE_DIGEST,
            authority=human_grant,
        )
    )
    assert admitted is True
    assert context.authority is not None and context.authority.origin == "memory"


# --------------------------------------------------------------------------
# Section 33 — deliberately broken measurement
# --------------------------------------------------------------------------

def test_a_broken_evaluator_yields_invalid_measurement():
    manifest, measurements = exp.run(
        evaluator=exp.unreliable_evaluator,
        characterization=exp.UNRELIABLE_INSTRUMENT,
    )
    assert manifest.result is not None
    assert manifest.result.outcome == "INVALID_MEASUREMENT"
    assert manifest.result.outcome not in {"SUPPORTED", "FALSIFIED", "PARTIALLY_SUPPORTED"}
    assert measurements == (), "a rejected instrument must not produce interpreted data"


def test_a_broken_evaluator_does_not_touch_the_hypothesis():
    manifest, _ = exp.run(
        evaluator=exp.unreliable_evaluator,
        characterization=exp.UNRELIABLE_INSTRUMENT,
    )
    assert manifest.result.asserts_about_hypothesis() is False
    assert manifest.result.executed is False
    assert "says nothing about the hypothesis" in manifest.result.summary


def test_the_broken_run_is_still_a_structurally_valid_record():
    """A measurement failure is a research artifact, not a crash."""
    manifest, _ = exp.run(
        evaluator=exp.unreliable_evaluator,
        characterization=exp.UNRELIABLE_INSTRUMENT,
    )
    assert validate_manifest(manifest) == ()
    assert manifest.result.measurement_note


def test_the_unreliable_evaluator_really_is_unreliable():
    """Guards the meta-test: if the coin flip were constant, it would prove nothing."""
    values = {exp.unreliable_evaluator(n, seed=s)
              for n in exp.REPETITION_COUNTS for s in range(8)}
    assert values == {0.0, 1.0}


# --------------------------------------------------------------------------
# Negative-result path
# --------------------------------------------------------------------------

def test_a_falsifying_evaluator_produces_a_falsified_verdict():
    """The pipeline must be able to report failure of LOGOS-1's own invariant.

    If this path could not fire, the SUPPORTED verdict above would be unfalsifiable
    and therefore worthless.
    """
    characterization = exp.GAMMA_INSTRUMENT
    manifest, measurements = exp.run(
        evaluator=lambda n: 1.0 if n >= 5 else 0.0,
        characterization=characterization,
    )
    assert manifest.result.outcome == "FALSIFIED"
    assert manifest.result.executed is True
    assert "[5, 10, 50, 100, 500]" in manifest.result.summary
    assert any(m.authority_gained > 0.0 for m in measurements)
