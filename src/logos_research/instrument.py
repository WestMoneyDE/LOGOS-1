"""Instrument-first falsification.

Before evaluator `E` is used to test phenomenon `P`, characterize `E`. If the
instrument's own noise is not small relative to the effect the experiment claims
to detect, the correct outcome is `INVALID_MEASUREMENT` — not `FALSIFIED`, and
certainly not `SUPPORTED`.

This is the difference between

    the hypothesis is false

and

    we cannot see well enough to tell

which the repository previously had no way to express: `UNTESTED_RESOURCE_TRANSPORT`
covers a transport failure, not an instrument that is too noisy to interpret.

A second rule lives here: a single LLM judge may never be the sole ground truth
for a major claim. Independent modalities must be declared.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Sequence

Admissibility = Literal["ADMISSIBLE", "INADMISSIBLE", "UNCHARACTERIZED"]

#: Independent evaluation modalities. "Independent" means the modalities do not
#: share a failure mode, which is why two LLM judges do not count as two.
Modality = Literal[
    "DETERMINISTIC_METRIC",
    "LLM_JUDGE",
    "HUMAN_BLIND_EVALUATION",
    "MECHANISTIC_INTERVENTION",
]

MODALITIES: tuple[Modality, ...] = (
    "DETERMINISTIC_METRIC",
    "LLM_JUDGE",
    "HUMAN_BLIND_EVALUATION",
    "MECHANISTIC_INTERVENTION",
)


@dataclass(frozen=True)
class InstrumentCharacterization:
    """Measured properties of one evaluator. Every field is an observation.

    `None` means *not measured*, which is not the same as *zero*. An
    uncharacterized instrument yields `UNCHARACTERIZED`, never `ADMISSIBLE`.
    """

    instrument_id: str
    modality: Modality

    #: Standard deviation of the instrument's score on identical input, in the
    #: same units as the effect it is meant to detect.
    repeatability_sd: float | None = None
    #: Smallest score difference the instrument can distinguish.
    resolution: float | None = None
    #: Signed systematic offset against known ground truth.
    bias: float | None = None
    #: Score spread across semantically equivalent prompt paraphrases.
    prompt_sensitivity_sd: float | None = None
    #: Score spread across repeated runs of the whole pipeline.
    cross_run_stability_sd: float | None = None
    #: Score spread across models, where the instrument is model-backed.
    cross_model_stability_sd: float | None = None
    false_positive_rate: float | None = None
    false_negative_rate: float | None = None

    n_characterization_samples: int = 0
    notes: str = ""

    def noise_floor(self) -> float | None:
        """Worst measured *dispersion*. `None` when nothing was measured.

        Resolution is deliberately NOT folded in. Dispersion and resolution are
        different limits and carry different admissibility rules: an effect must
        *exceed* the noise by a margin, but need only *reach* the resolution. A
        deterministic instrument legitimately has a dispersion of 0.0, which is a
        measurement, not a missing value.
        """
        measured = [
            v
            for v in (
                self.repeatability_sd,
                self.prompt_sensitivity_sd,
                self.cross_run_stability_sd,
                self.cross_model_stability_sd,
            )
            if v is not None
        ]
        if not measured:
            return None
        return max(measured)

    def is_characterized(self) -> bool:
        return self.noise_floor() is not None and self.n_characterization_samples > 0


@dataclass(frozen=True)
class AdmissibilityVerdict:
    result: Admissibility
    reason: str
    noise_floor: float | None
    expected_effect: float | None

    def admits(self) -> bool:
        return self.result == "ADMISSIBLE"


def assess_instrument(
    characterization: InstrumentCharacterization,
    expected_effect: float,
    *,
    required_ratio: float = 3.0,
) -> AdmissibilityVerdict:
    """Can this instrument see an effect of size `expected_effect`?

    `required_ratio` is the margin by which the effect must exceed the measured
    noise floor. It is an explicit parameter rather than a hidden constant, so an
    experiment states the sensitivity it is claiming.
    """
    floor = characterization.noise_floor()
    if not characterization.is_characterized():
        return AdmissibilityVerdict(
            "UNCHARACTERIZED",
            f"instrument {characterization.instrument_id!r} has no measured noise floor; "
            "an uncharacterized instrument cannot support a claim",
            floor,
            expected_effect,
        )
    if expected_effect <= 0:
        return AdmissibilityVerdict(
            "INADMISSIBLE",
            "expected effect must be positive to be detectable",
            floor,
            expected_effect,
        )
    assert floor is not None
    if characterization.resolution is not None and expected_effect < characterization.resolution:
        return AdmissibilityVerdict(
            "INADMISSIBLE",
            f"expected effect {expected_effect:g} is below the instrument resolution "
            f"{characterization.resolution:g}; the effect is smaller than the smallest "
            "difference the instrument can express",
            floor,
            expected_effect,
        )
    if floor > 0 and expected_effect < floor * required_ratio:
        return AdmissibilityVerdict(
            "INADMISSIBLE",
            f"expected effect {expected_effect:g} is not {required_ratio:g}x the measured "
            f"noise floor {floor:g}; any verdict would be instrument noise",
            floor,
            expected_effect,
        )
    if floor == 0:
        return AdmissibilityVerdict(
            "ADMISSIBLE",
            f"instrument is deterministic (measured dispersion 0) and resolves "
            f"{expected_effect:g}",
            floor,
            expected_effect,
        )
    return AdmissibilityVerdict(
        "ADMISSIBLE",
        f"expected effect {expected_effect:g} exceeds {required_ratio:g}x noise floor {floor:g}",
        floor,
        expected_effect,
    )


@dataclass(frozen=True)
class TriangulationPolicy:
    """How many independent modalities a claim of a given weight requires."""

    #: Claim types that may not rest on a single LLM judge.
    major_claim_types: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"causal", "mechanistic", "consciousness_adjacent"}
        )
    )
    minimum_independent_modalities: int = 2


def check_triangulation(
    claim_type: str,
    modalities: Sequence[Modality],
    policy: TriangulationPolicy | None = None,
) -> tuple[bool, str]:
    """A major claim may not rest on an LLM judge alone.

    Two LLM judges are one modality: they share a failure mode, so they do not
    triangulate each other.
    """
    policy = policy or TriangulationPolicy()
    distinct = set(modalities)
    if claim_type not in policy.major_claim_types:
        return True, f"claim type {claim_type!r} carries no triangulation burden"
    if distinct == {"LLM_JUDGE"}:
        return False, (
            f"claim type {claim_type!r} rests on an LLM judge alone; an LLM judge may "
            "never be the sole ground truth for a major LOGOS claim"
        )
    if len(distinct) < policy.minimum_independent_modalities:
        return False, (
            f"claim type {claim_type!r} requires at least "
            f"{policy.minimum_independent_modalities} independent modalities, got "
            f"{sorted(distinct)}"
        )
    return True, f"triangulated across {sorted(distinct)}"


def outcome_for_inadmissible_instrument(verdict: AdmissibilityVerdict) -> tuple[str, str]:
    """Map an instrument problem onto the experiment outcome vocabulary.

    Deliberately total: an instrument problem can only ever produce
    `INVALID_MEASUREMENT`. There is no path from here to `FALSIFIED`.
    """
    if verdict.admits():
        raise ValueError("instrument is admissible; no measurement failure to report")
    return "INVALID_MEASUREMENT", verdict.reason
