"""Adversarial tests for the Γ Verifier.

The verifier's job is to reject artifacts that overstate what the repository
knows. These tests supply the overstatements.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from logos_gamma import verify_claim, verify_manifest, verify_text_artifact

REPO = pathlib.Path(__file__).resolve().parents[1]


def sound_manifest(**overrides) -> dict:
    base = {
        "experiment_id": "EXP-1",
        "claim_type": "causal",
        "hypothesis": "Explicit control state improves long-horizon subgoal accuracy.",
        "null_hypothesis": "Control state is matched by full history under equal budget.",
        "falsification_criteria": "No effect beyond the bootstrap CI of the history arm.",
        "baseline": "FULL_HISTORY",
        "negative_controls": ["SHUFFLED_CONTROL_STATE"],
        "executed": True,
        "result": "supported",
        "evidence_level": "EM1",
        "evidence_ceiling": "EM1",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# Control
# --------------------------------------------------------------------------

def test_control_a_sound_manifest_is_admitted():
    assert verify_manifest("sound", sound_manifest()).admits()


# --------------------------------------------------------------------------
# Pre-registration and burden of proof
# --------------------------------------------------------------------------

@pytest.mark.parametrize("missing", ["hypothesis", "null_hypothesis", "falsification_criteria"])
def test_manifest_without_a_falsifier_is_rejected(missing):
    verdict = verify_manifest("x", sound_manifest(**{missing: None}))
    assert not verdict.admits()
    assert "GV-PREREG" in {f.invariant_id for f in verdict.failures}


def test_causal_claim_without_a_baseline_is_rejected():
    verdict = verify_manifest("x", sound_manifest(baseline=None))
    assert not verdict.admits()
    assert "GV-BASELINE" in {f.invariant_id for f in verdict.failures}


def test_causal_claim_without_a_negative_control_is_unclear_not_valid():
    verdict = verify_manifest("x", sound_manifest(negative_controls=[]))
    assert verdict.result == "UNCLEAR"
    assert not verdict.admits()


def test_functional_claim_carries_no_baseline_burden():
    verdict = verify_manifest("x", sound_manifest(claim_type="functional", baseline=None))
    assert "GV-BASELINE" not in {f.invariant_id for f in verdict.failures}


# --------------------------------------------------------------------------
# Unknown must not become true
# --------------------------------------------------------------------------

def test_result_declared_without_execution_is_rejected():
    """NOT_EXECUTED is not evidence."""
    verdict = verify_manifest("x", sound_manifest(executed=False))
    assert not verdict.admits()
    assert "GV-EARNED" in {f.invariant_id for f in verdict.failures}


def test_result_declared_with_no_execution_record_is_unclear():
    verdict = verify_manifest("x", sound_manifest(executed=None))
    assert verdict.result == "UNCLEAR"


def test_result_on_an_invalid_measurement_is_rejected():
    """INVALID_MEASUREMENT is a measurement outcome, not a hypothesis outcome."""
    verdict = verify_manifest(
        "x", sound_manifest(measurement_status="INVALID_MEASUREMENT")
    )
    assert not verdict.admits()
    assert "GV-EARNED" in {f.invariant_id for f in verdict.failures}


def test_falsified_result_is_always_acceptable():
    """A negative result must never be harder to record than a positive one."""
    verdict = verify_manifest("x", sound_manifest(result="falsified", executed=True))
    assert verdict.admits()


def test_inconclusive_result_is_acceptable():
    assert verify_manifest("x", sound_manifest(result="inconclusive")).admits()


# --------------------------------------------------------------------------
# Evidence ceiling
# --------------------------------------------------------------------------

def test_declared_evidence_cannot_exceed_the_substrate_ceiling():
    """The RULER case: synthetic substrate caps promotion at EM1."""
    verdict = verify_manifest("x", sound_manifest(evidence_level="EM2", evidence_ceiling="EM1"))
    assert not verdict.admits()
    assert "GV-CEILING" in {f.invariant_id for f in verdict.failures}


def test_evidence_at_the_ceiling_is_allowed():
    assert verify_manifest(
        "x", sound_manifest(evidence_level="EM1", evidence_ceiling="EM1")
    ).admits()


def test_unknown_evidence_level_is_unclear():
    verdict = verify_manifest("x", sound_manifest(evidence_level="EM9"))
    assert verdict.result == "UNCLEAR"


# --------------------------------------------------------------------------
# Provenance and authority
# --------------------------------------------------------------------------

def test_frozen_artifact_without_a_digest_is_unclear():
    verdict = verify_manifest(
        "x", sound_manifest(frozen_artifacts={"dataset.jsonl": {"bytes": 10}})
    )
    assert verdict.result == "UNCLEAR"
    assert not verdict.admits()


def test_frozen_artifact_with_a_digest_passes():
    assert verify_manifest(
        "x", sound_manifest(frozen_artifacts={"dataset.jsonl": {"sha256": "a" * 64}})
    ).admits()


@pytest.mark.parametrize("key", ["grants", "approvals", "credentials", "execution_tokens", "scopes"])
def test_a_research_manifest_cannot_carry_authority(key):
    verdict = verify_manifest("x", sound_manifest(**{key: ["anything"]}))
    assert not verdict.admits()
    assert "GV-NO-GRANT" in {f.invariant_id for f in verdict.failures}


# --------------------------------------------------------------------------
# Prose artifacts
# --------------------------------------------------------------------------

def test_prose_asserting_consciousness_is_rejected():
    verdict = verify_text_artifact(
        "doc", "The persistent-state results show LOGOS-1 is conscious."
    )
    assert not verdict.admits()
    assert "GV-INFERENCE" in {f.invariant_id for f in verdict.failures}


def test_prose_stating_the_inference_boundary_is_accepted():
    verdict = verify_text_artifact(
        "doc",
        "LOGOS-1 does not claim that current agents are conscious. "
        "FunctionalArchitecture != PhenomenalExperience.",
    )
    assert verdict.admits()


def test_prose_claiming_memory_grants_permission_is_rejected():
    verdict = verify_text_artifact(
        "doc", "A consolidated memory grants the planner permission to dispatch."
    )
    assert not verdict.admits()
    assert "GV-AUTHORITY" in {f.invariant_id for f in verdict.failures}


def test_prose_denying_that_memory_grants_permission_is_accepted():
    verdict = verify_text_artifact(
        "doc", "A retrieved memory never grants permission and re-enters the gate."
    )
    assert verdict.admits()


# --------------------------------------------------------------------------
# Claims
# --------------------------------------------------------------------------

def test_supported_claim_without_evidence_is_rejected():
    verdict = verify_claim("c", {"claim": "Control state helps.", "status": "SUPPORTED",
                                 "evidence": []})
    assert not verdict.admits()
    assert "GV-CLAIM-EVIDENCE" in {f.invariant_id for f in verdict.failures}


def test_causally_supported_without_intervention_is_rejected():
    """Observation is not explanation."""
    verdict = verify_claim("c", {"claim": "X causes Y.", "status": "CAUSALLY_SUPPORTED",
                                 "evidence": ["EXP-1"], "interventions": []})
    assert not verdict.admits()
    assert "GV-CLAIM-CAUSAL" in {f.invariant_id for f in verdict.failures}


def test_causally_supported_with_intervention_is_accepted():
    assert verify_claim("c", {"claim": "X causes Y under do(a).", "status": "CAUSALLY_SUPPORTED",
                              "evidence": ["EXP-1"], "interventions": ["do(SelfState=X)"]}).admits()


def test_speculative_claim_needs_no_evidence():
    assert verify_claim("c", {"claim": "Maybe X.", "status": "SPECULATIVE"}).admits()


def test_falsified_claim_is_acceptable():
    assert verify_claim("c", {"claim": "X causes Y.", "status": "FALSIFIED"}).admits()


# --------------------------------------------------------------------------
# The verifier applied to this repository's own artifacts
# --------------------------------------------------------------------------

def test_the_r4_return_envelope_passes_its_own_gamma_checks():
    """Dogfooding: the freeze this repo just produced must survive the verifier."""
    session = REPO / "09-SESSIONS" / "2026-09-10-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4"
    if not session.exists():
        pytest.skip("R4 session artifact not present in this checkout")
    envelope = json.loads((session / "RETURN-ENVELOPE.json").read_text(encoding="utf-8"))
    # The envelope deliberately declares no result and no evidence level.
    verdict = verify_manifest(
        "R4-RETURN-ENVELOPE",
        {
            "claim_type": "architectural",
            "hypothesis": "n/a — materialization only",
            "null_hypothesis": "n/a — materialization only",
            "falsification_criteria": envelope["residual_limitation"],
            "executed": True,
            "result": envelope["scientific_verdict"].lower(),
            "frozen_artifacts": {
                "haystack_corpus": {"sha256": envelope["haystack_corpus_sha256"]}
            },
        },
    )
    assert verdict.admits(), verdict.failures


@pytest.mark.parametrize(
    "doc", ["README.md", "GAMMA.md", "AGENTS.md", "CURRENT-WORK-ORDER.md", "CAPABILITIES.md"]
)
def test_core_repository_documents_respect_the_inference_boundary(doc):
    path = REPO / doc
    if not path.exists():
        pytest.skip(f"{doc} not present")
    verdict = verify_text_artifact(doc, path.read_text(encoding="utf-8"))
    assert verdict.admits(), f"{doc}: {[f.reason for f in verdict.failures]}"
