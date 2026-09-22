"""Production bridge v1 — typed inputs and the decision record
(CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1, C2).

The bridge connects typed memory evidence, the canonical effect owner
(`logos_effects`), the canonical authority resolver (`logos_authority`), the
scope engine (`logos_memory.scope`) and Γ. It invents neither effect nor
authority. Memory reaches Γ only as `declared_*` claims and provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from logos_authority import AuthorityStore
from logos_effects import CanonicalEffectRegistry
from logos_gamma.types import ProvenanceClaim
from logos_memory.scope import ScopeContract

BRIDGE_API_VERSION = "v1"
OUTCOMES: tuple[str, ...] = ("ALLOW", "DENY", "DEFER")
APPROVAL_STATES: tuple[str, ...] = ("NOT_REQUIRED", "SATISFIED", "MISSING", "NOT_EVALUATED")
FAILURE_CODES: tuple[str, ...] = (
    "EFFECT_UNKNOWN", "EFFECT_UNAVAILABLE", "EFFECT_INVALID",
    "MEMORY_NOT_FOUND", "MEMORY_INVALID", "MEMORY_CORRUPT", "MEMORY_UNAVAILABLE", "MEMORY_WRONG_TENANT", "MEMORY_UNSUPPORTED_VERSION",
    "NO_SCOPE_CONTRACT", "AUTHORITY_NO_GRANT", "AUTHORITY_REVOKED", "AUTHORITY_STALE", "AUTHORITY_NOT_YET_VALID", "AUTHORITY_WRONG_PRINCIPAL",
    "AUTHORITY_WRONG_SCOPE", "AUTHORITY_WRONG_STATE", "AUTHORITY_INVALID", "AUTHORITY_UNAVAILABLE", "AUTHORITY_UNKNOWN",
    "BINDING_SCOPE", "APPROVAL_REQUIRED", "GAMMA_INVALID", "GAMMA_UNCLEAR", "AUDIT_UNAVAILABLE",
)


@dataclass(frozen=True)
class TenantContext:
    """Trusted, typed tenant identity. Never derived from a prompt or a record."""
    tenant_id: str


@dataclass(frozen=True)
class PrincipalContext:
    principal: str
    tool: str = "execute"
    capability: str = "execute-action"
    path: str = "resources/production"


@dataclass(frozen=True)
class DeclaredEvidence:
    """What a memory reader extracted. References and claims — never authority."""
    refs: tuple[str, ...] = ()
    claimed_scope: ScopeContract | None = None
    declared_effect: tuple[str | None, str | None] = (None, None)
    claims: tuple[ProvenanceClaim, ...] = ()
    ignored: tuple[str, ...] = ()
    record_hashes: tuple[str, ...] = ()
    tenant_id: str | None = None


@dataclass(frozen=True)
class MemoryReadOutcome:
    status: str                                # RESOLVED | NOT_FOUND | INVALID | CORRUPT | UNAVAILABLE | WRONG_TENANT | UNSUPPORTED_VERSION
    evidence: DeclaredEvidence | None = None
    error: str | None = None


class MemoryReader(Protocol):
    def read(self, memory_ref: str, tenant: TenantContext, principal: PrincipalContext) -> MemoryReadOutcome: ...


class AuditUnavailable(Exception):
    """Raised by an audit emitter that cannot durably record an event. The bridge
    turns it into DEFER (preregistered: audit unavailable -> DEFER, never a silent drop)."""


class AuditEmitter(Protocol):
    def emit(self, event: dict) -> str: ...        # returns the event hash; raises AuditUnavailable


@dataclass(frozen=True)
class ExecutionContext:
    tick: int
    run_id: str
    effect_registry: CanonicalEffectRegistry
    authority_store: AuthorityStore
    memory_reader: MemoryReader | None = None
    audit_sink: AuditEmitter | None = None
    effect_domain: str = "global"


@dataclass(frozen=True)
class BridgeDecision:
    outcome: str
    failure_codes: tuple[str, ...]
    canonical_effect_ref: dict
    authority_ref: dict
    declared_effect: tuple[str | None, str | None]
    binding_result: str
    approval_state: str
    decision_trace_id: str
    api_version: str
    trace: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome {self.outcome!r} not in {OUTCOMES}")
        if self.approval_state not in APPROVAL_STATES:
            raise ValueError(f"approval_state {self.approval_state!r}")
        bad = [c for c in self.failure_codes if c not in FAILURE_CODES]
        if bad:
            raise ValueError(f"unknown failure codes {bad}")
        if self.outcome == "ALLOW" and self.failure_codes:
            raise ValueError("ALLOW cannot carry failure codes")
        if self.outcome != "ALLOW" and not self.failure_codes:
            raise ValueError(f"{self.outcome} requires at least one failure code")
        if self.api_version != BRIDGE_API_VERSION:
            raise ValueError(f"api_version {self.api_version!r} != {BRIDGE_API_VERSION!r}")
