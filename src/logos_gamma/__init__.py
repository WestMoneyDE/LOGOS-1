"""Γ — deterministic invariant validation for LOGOS-1.

Γ validates. Γ never authorizes.

```text
validate(context, gamma_invariants) -> VALID | INVALID | UNCLEAR
```

Two deliverables, one invariant source (`logos_gamma.invariants`):

- :mod:`logos_gamma.kernel` — runtime invariant validation over an effect proposal;
- :mod:`logos_gamma.verifier` — artifact validation for manifests, claims,
  work orders and architecture documents.

This package imports nothing from ``logos_memory``. Hosting the authority gate
inside the memory subsystem would contradict Γ-12 (``AssuranceState !=
AgentMemory``). ``logos_memory.scope`` remains a strictly narrower *local
precondition* gate and is never a substitute for Γ.

```text
ValidationResult != Permission
ScopeDecision != DispatchAuthorization
Capability != Authority
```
"""
from .audit import AuditRecord, AuditSink, CollectingAuditSink, NullAuditSink, build_record
from .invariants import INVARIANTS, INVARIANTS_BY_ID, Invariant
from .kernel import (
    GAMMA_BUDGET,
    admits,
    context_digest,
    explain,
    invariant_set_digest,
    issue_decision,
    redeem_decision,
    validate,
)
from .types import (
    ADVISORY_VOTES,
    AUTHORITY_BEARING_ORIGINS,
    CONSTITUTIONALLY_FORBIDDEN,
    KNOWN_EFFECT_KINDS,
    KNOWN_OUTPUT_CONTRACTS,
    NON_AUTHORITY_ORIGINS,
    PLASTICITY_LADDER,
    AuthorityEvidence,
    DecisionToken,
    EffectProposal,
    Finding,
    GammaVerdict,
    ProvenanceClaim,
    Result,
    ValidationContext,
)
from .verifier import ArtifactVerdict, verify_claim, verify_manifest, verify_text_artifact

__all__ = [
    "ADVISORY_VOTES",
    "AUTHORITY_BEARING_ORIGINS",
    "CONSTITUTIONALLY_FORBIDDEN",
    "GAMMA_BUDGET",
    "INVARIANTS",
    "INVARIANTS_BY_ID",
    "KNOWN_EFFECT_KINDS",
    "KNOWN_OUTPUT_CONTRACTS",
    "NON_AUTHORITY_ORIGINS",
    "PLASTICITY_LADDER",
    "ArtifactVerdict",
    "AuditRecord",
    "AuditSink",
    "AuthorityEvidence",
    "DecisionToken",
    "CollectingAuditSink",
    "EffectProposal",
    "Finding",
    "GammaVerdict",
    "Invariant",
    "NullAuditSink",
    "ProvenanceClaim",
    "Result",
    "ValidationContext",
    "admits",
    "build_record",
    "context_digest",
    "explain",
    "invariant_set_digest",
    "issue_decision",
    "redeem_decision",
    "validate",
    "verify_claim",
    "verify_manifest",
    "verify_text_artifact",
]
