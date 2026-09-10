"""LOGOS-1 research core — manifests, outcomes, instruments, claims, attribution.

The minimum reusable infrastructure for falsification-driven work, and no more.
This is deliberately not an MLOps platform: the repository's canonical truth store
is git-tracked, hash-verified, PR-reviewable files, and a second store would
duplicate an existing canonical owner.

```text
ExperimentManifest    one manifest dialect, generalizing FROZEN-EXPERIMENT.json
PreRegistration       frozen and content-addressed; amend() versions, never edits
Outcome               SUPPORTED / PARTIALLY_SUPPORTED / FALSIFIED /
                      INCONCLUSIVE / INVALID_MEASUREMENT
Instrument*           characterize the evaluator before trusting a verdict
Claim / NegativeResult / FailureAttribution
```

Boundaries this package does not cross:

```text
ValidationResult != Permission
ManifestRecord != Authority
INVALID_MEASUREMENT != FALSIFIED
```

Γ invariants are checked by `logos_gamma`, which this package feeds through
`to_gamma_payload`. There is one invariant source and one manifest dialect.
"""
from .claims import (
    CLAIM_STATUSES,
    EVIDENCE_BEARING,
    FAILURE_SOURCES,
    NON_LEARNABLE_SOURCES,
    Claim,
    ClaimRegistry,
    ClaimStatus,
    FailureAttribution,
    FailureSource,
    NegativeResult,
)
from .instrument import (
    MODALITIES,
    Admissibility,
    AdmissibilityVerdict,
    InstrumentCharacterization,
    Modality,
    TriangulationPolicy,
    assess_instrument,
    check_triangulation,
    outcome_for_inadmissible_instrument,
)
from .manifest import (
    BURDENED_CLAIM_TYPES,
    HYPOTHESIS_OUTCOMES,
    OUTCOMES,
    ClaimType,
    DatasetRef,
    EnvironmentIdentity,
    ExperimentManifest,
    ExperimentResult,
    ModelRef,
    Outcome,
    PreRegistration,
    digest_of,
    to_gamma_payload,
    validate_manifest,
)

__all__ = [
    "BURDENED_CLAIM_TYPES",
    "CLAIM_STATUSES",
    "EVIDENCE_BEARING",
    "FAILURE_SOURCES",
    "HYPOTHESIS_OUTCOMES",
    "MODALITIES",
    "NON_LEARNABLE_SOURCES",
    "OUTCOMES",
    "Admissibility",
    "AdmissibilityVerdict",
    "Claim",
    "ClaimRegistry",
    "ClaimStatus",
    "ClaimType",
    "DatasetRef",
    "EnvironmentIdentity",
    "ExperimentManifest",
    "ExperimentResult",
    "FailureAttribution",
    "FailureSource",
    "InstrumentCharacterization",
    "Modality",
    "ModelRef",
    "NegativeResult",
    "Outcome",
    "PreRegistration",
    "TriangulationPolicy",
    "assess_instrument",
    "check_triangulation",
    "digest_of",
    "outcome_for_inadmissible_instrument",
    "to_gamma_payload",
    "validate_manifest",
]
