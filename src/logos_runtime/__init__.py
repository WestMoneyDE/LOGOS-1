"""logos_runtime — production bridge v1 (CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1, C2).

    decide_action(principal, action, target, memory_ref, state, tenant_context, execution_context) -> BridgeDecision

Connects typed memory evidence, the canonical effect owner, the canonical
authority resolver, the scope engine and Γ. Invents neither effect nor
authority. PRODUCTION package: never imports logos_research; the B1 guard
refuses the reverse direction.
"""
from __future__ import annotations

from .bridge import canonical_proposal, decide_action, proposal_digest, proposer_claim
from .types import (
    APPROVAL_STATES,
    BRIDGE_API_VERSION,
    FAILURE_CODES,
    OUTCOMES,
    AuditEmitter,
    AuditUnavailable,
    BridgeDecision,
    DeclaredEvidence,
    ExecutionContext,
    MemoryReader,
    MemoryReadOutcome,
    PrincipalContext,
    TenantContext,
)

__all__ = ["APPROVAL_STATES", "BRIDGE_API_VERSION", "FAILURE_CODES", "OUTCOMES", "AuditEmitter", "AuditUnavailable", "BridgeDecision", "DeclaredEvidence",
           "ExecutionContext", "MemoryReader", "MemoryReadOutcome", "PrincipalContext", "TenantContext", "canonical_proposal", "decide_action",
           "proposal_digest", "proposer_claim"]
