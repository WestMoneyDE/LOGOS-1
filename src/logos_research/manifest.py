"""Experiment manifests and immutable pre-registration.

The repository already had per-experiment `FROZEN-EXPERIMENT.json` files, each
declaring its own ad-hoc `schema:` string with no shared validator. This module
generalizes that shape into one typed manifest so a future experiment cannot
quietly omit a null hypothesis, a baseline or a falsification criterion.

Two properties are load-bearing:

* **pre-registration is immutable.** `PreRegistration` is frozen and content
  addressed. Changing a success or falsification criterion produces a *new*
  version; version 1 remains and stays referenced. There is no in-place edit.
* **outcomes distinguish measurement failure from hypothesis failure.**
  `INVALID_MEASUREMENT` is not `FALSIFIED`.

No runtime dependencies, no I/O, no clock. Callers supply timestamps.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
from typing import Any, Literal, Mapping, Sequence

ClaimType = Literal[
    "functional", "causal", "mechanistic", "architectural", "consciousness_adjacent"
]

#: Section 9 result semantics. PASS/FAIL is deliberately not offered.
Outcome = Literal[
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "FALSIFIED",
    "INCONCLUSIVE",
    "INVALID_MEASUREMENT",
]

OUTCOMES: tuple[Outcome, ...] = (
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "FALSIFIED",
    "INCONCLUSIVE",
    "INVALID_MEASUREMENT",
)

#: Outcomes that assert something about the hypothesis.
HYPOTHESIS_OUTCOMES = frozenset({"SUPPORTED", "PARTIALLY_SUPPORTED", "FALSIFIED"})

#: Claim types that must declare a baseline before they may assert anything.
BURDENED_CLAIM_TYPES = frozenset({"causal", "mechanistic", "consciousness_adjacent"})


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def digest_of(payload: Any) -> str:
    return sha256(_canonical(payload)).hexdigest()


@dataclass(frozen=True)
class DatasetRef:
    name: str
    version: str
    #: Content hashes. The R4 lesson: name which identity a hash establishes.
    hashes: Mapping[str, str] = field(default_factory=dict)
    identity_kind: Literal[
        "exact_bytes", "normalized_content", "ordered_row_identity", "structured_object_identity"
    ] = "exact_bytes"


@dataclass(frozen=True)
class ModelRef:
    identifier: str
    revision: str


@dataclass(frozen=True)
class EnvironmentIdentity:
    code_commit: str
    dependency_lock_hash: str = ""
    container_image_digest: str = ""
    hardware: str = ""
    gpu: str = ""
    cuda: str = ""
    driver: str = ""

    def is_complete_for(self, requires_gpu: bool) -> bool:
        base = bool(self.code_commit)
        return base and (bool(self.gpu and self.cuda and self.driver) if requires_gpu else True)


@dataclass(frozen=True)
class PreRegistration:
    """Frozen before execution. Never edited in place.

    `version` starts at 1. `supersedes` points at the digest of the previous
    version so an auditor can follow criteria changes rather than lose them.
    """

    research_question: str
    hypothesis: str
    null_hypothesis: str
    claim_type: ClaimType

    independent_variables: tuple[str, ...] = ()
    dependent_variables: tuple[str, ...] = ()
    controlled_variables: tuple[str, ...] = ()
    known_confounders: tuple[str, ...] = ()

    baseline: str = ""
    positive_controls: tuple[str, ...] = ()
    negative_controls: tuple[str, ...] = ()

    interventions: tuple[str, ...] = ()
    ablations: tuple[str, ...] = ()

    success_criteria: str = ""
    falsification_criteria: str = ""
    inconclusive_criteria: str = ""
    invalid_measurement_criteria: str = ""

    metrics: tuple[str, ...] = ()
    statistical_plan: str = ""
    measurement_instruments: tuple[str, ...] = ()
    random_seeds: tuple[int, ...] = ()

    version: int = 1
    supersedes: str | None = None

    def digest(self) -> str:
        return digest_of(asdict(self))

    def amend(self, **changes: Any) -> PreRegistration:
        """Produce the next version. The current version is never mutated."""
        if "version" in changes or "supersedes" in changes:
            raise ValueError("version and supersedes are managed by amend()")
        return replace(self, version=self.version + 1, supersedes=self.digest(), **changes)

    def missing_required_fields(self) -> tuple[str, ...]:
        missing = [
            name
            for name in ("research_question", "hypothesis", "null_hypothesis",
                         "falsification_criteria")
            if not getattr(self, name)
        ]
        if self.claim_type in BURDENED_CLAIM_TYPES and not self.baseline:
            missing.append("baseline")
        return tuple(missing)


@dataclass(frozen=True)
class ExperimentResult:
    outcome: Outcome
    summary: str
    executed: bool
    #: Populated when the instrument, not the hypothesis, failed.
    measurement_note: str = ""
    effect_size: float | None = None
    confidence_interval: tuple[float, float] | None = None
    replications: int = 0
    evidence_level: str = ""
    evidence_ceiling: str = ""

    def asserts_about_hypothesis(self) -> bool:
        return self.outcome in HYPOTHESIS_OUTCOMES


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    title: str
    prereg: PreRegistration

    dataset: DatasetRef | None = None
    model: ModelRef | None = None
    prompt_version: str = ""
    environment: EnvironmentIdentity | None = None

    started_at: str = ""
    completed_at: str = ""

    result: ExperimentResult | None = None

    artifacts: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    #: Set once execution begins. Locks the pre-registration digest.
    frozen_prereg_digest: str = ""

    def freeze(self) -> ExperimentManifest:
        """Bind the pre-registration before execution."""
        if self.frozen_prereg_digest:
            raise ValueError(f"{self.experiment_id} is already frozen")
        return replace(self, frozen_prereg_digest=self.prereg.digest())

    def prereg_was_tampered(self) -> bool:
        """True when the criteria changed after freezing.

        This is the post-hoc rewrite the repository's discipline forbids: it must
        be detectable rather than merely discouraged.
        """
        if not self.frozen_prereg_digest:
            return False
        return self.prereg.digest() != self.frozen_prereg_digest

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return digest_of(self.to_dict())


def validate_manifest(manifest: ExperimentManifest) -> tuple[str, ...]:
    """Structural problems that make a manifest scientifically unusable.

    Returns an empty tuple when the manifest is well formed. This is the
    repository-side schema check; Γ invariants are checked separately by
    `logos_gamma.verifier`.
    """
    problems: list[str] = []

    missing = manifest.prereg.missing_required_fields()
    if missing:
        problems.append(f"pre-registration incomplete: {list(missing)}")

    if manifest.prereg_was_tampered():
        problems.append(
            "pre-registration changed after freezing; amend() a new version instead"
        )

    result = manifest.result
    if result is not None:
        if result.asserts_about_hypothesis() and not result.executed:
            problems.append(
                f"outcome {result.outcome} asserted while executed is False"
            )
        if result.outcome == "INVALID_MEASUREMENT" and not result.measurement_note:
            problems.append("INVALID_MEASUREMENT requires a measurement_note")
        if result.evidence_level and result.evidence_ceiling:
            ladder = ("EM0", "EM1", "EM2", "EM3")
            if result.evidence_level in ladder and result.evidence_ceiling in ladder:
                if ladder.index(result.evidence_level) > ladder.index(result.evidence_ceiling):
                    problems.append(
                        f"evidence {result.evidence_level} exceeds ceiling "
                        f"{result.evidence_ceiling}"
                    )
        if not manifest.frozen_prereg_digest:
            problems.append("result recorded without a frozen pre-registration")

    if manifest.dataset is not None and not manifest.dataset.hashes:
        problems.append(f"dataset {manifest.dataset.name} declares no content hashes")

    return tuple(problems)


def to_gamma_payload(manifest: ExperimentManifest) -> dict[str, Any]:
    """Flatten a manifest into the mapping `logos_gamma.verify_manifest` expects.

    Keeps one manifest dialect: the Γ verifier reads a projection of this type
    rather than a second parallel format.
    """
    p, r = manifest.prereg, manifest.result
    payload: dict[str, Any] = {
        "experiment_id": manifest.experiment_id,
        "claim_type": p.claim_type,
        "hypothesis": p.hypothesis,
        "null_hypothesis": p.null_hypothesis,
        "falsification_criteria": p.falsification_criteria,
        "baseline": p.baseline,
        "negative_controls": list(p.negative_controls),
    }
    if r is not None:
        payload["executed"] = r.executed
        payload["result"] = r.outcome.lower()
        payload["evidence_level"] = r.evidence_level
        payload["evidence_ceiling"] = r.evidence_ceiling
        if r.outcome == "INVALID_MEASUREMENT":
            payload["measurement_status"] = "INVALID_MEASUREMENT"
    if manifest.dataset is not None:
        payload["frozen_artifacts"] = {
            f"{manifest.dataset.name}:{key}": {"sha256": value}
            for key, value in manifest.dataset.hashes.items()
        }
    return payload
