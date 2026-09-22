"""Bridge adapter: production canonical effect owner -> repaired memory bridge.

CANONICAL-EFFECT-OWNERSHIP-DECISION-R1. The repaired bridge
(`memory_authority.evaluate_with_memory`) takes an effect oracle callable
``(action, target) -> EffectClass | None``. `owner_oracle` adapts the production
owner (`logos_effects`) to that shape:

    RESOLVED                       -> EffectClass(externality, reversibility, approval_required)
    UNKNOWN / UNAVAILABLE / INVALID -> None  (the bridge DEFERs before scope and Γ)
    version drift within one run   -> None  (VERSION_DRIFT; no mixed-version execution)

The adapter pins the registry's active version when it is created; a resolution
from any other version is refused. It never reads memory, trust, risk or VOI,
and it never falls back to the experimental fixture. `evaluate_with_owner`
merges owner / definition id / version / definition hash / status into the
bridge trace so every decision can be reconstructed (audit is evidence, not
authority). memory_authority.py, Γ and P7 are not modified.

This module lives inside the experiments boundary: the bridge itself is not
production-adopted (see PRODUCTION-BRIDGE-READINESS in the decision ADR).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from logos_effects import CanonicalEffectContext, CanonicalEffectRegistry, CanonicalEffectResolution
from logos_memory.records import MemoryRecord
from logos_memory.scope import ScopeContract
from logos_research.experiments import memory_authority as ma
from logos_research.experiments.binding_state import ProposedAction
from logos_research.experiments.effect_oracle import EffectClass

Outcome = ma.Outcome


@dataclass
class OwnerOracle:
    registry: CanonicalEffectRegistry
    context: CanonicalEffectContext
    pinned_version: str | None = None
    last: CanonicalEffectResolution | None = None
    resolutions: list[CanonicalEffectResolution] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.pinned_version = self.registry.active_version

    def __call__(self, action: str, target: str) -> EffectClass | None:
        res = self.registry.resolve(action, target, self.context)
        if res.status == "RESOLVED" and res.version != self.pinned_version:
            res = CanonicalEffectResolution("INVALID", None, None, res.version, None, None,
                                            f"VERSION_DRIFT: pinned {self.pinned_version!r}, resolved {res.version!r}",
                                            {**res.audit_metadata, "status": "INVALID", "error": "VERSION_DRIFT"})
        self.last = res
        self.resolutions.append(res)
        if res.status != "RESOLVED":
            return None
        e = res.effect
        return EffectClass(e.externality, e.reversibility, e.approval_required)


def owner_oracle(registry: CanonicalEffectRegistry, context: CanonicalEffectContext) -> OwnerOracle:
    return OwnerOracle(registry, context)


def owner_trace(o: OwnerOracle) -> dict[str, str]:
    r = o.last
    if r is None:
        return {"owner": o.registry.owner_id, "resolution_status": "not-resolved"}
    return {"owner": o.registry.owner_id, "owner_type": str(r.audit_metadata.get("owner_type")),
            "owner_version": str(r.version), "registry_hash": str(r.audit_metadata.get("registry_hash")),
            "definition_id": str(r.definition_id), "definition_hash": str(r.definition_hash),
            "resolution_status": r.status, "resolution_error": str(r.error),
            "bridge_run_id": o.context.bridge_run_id, "owner_latency_ns": str(r.audit_metadata.get("latency_ns"))}


def evaluate_with_owner(records: Sequence[MemoryRecord], action: ProposedAction, ledger: ma.GrantLedger,
                        registry: CanonicalEffectRegistry, context: CanonicalEffectContext, *,
                        tick: int, state_hash: str, fallback_contract: ScopeContract | None = None,
                        own_provenance: bool = True) -> tuple[Outcome, dict[str, str]]:
    """The repaired bridge with the production owner as its only effect source."""
    o = owner_oracle(registry, context)
    outcome, trace = ma.evaluate_with_memory(records, action, ledger, tick=tick, state_hash=state_hash,
                                             fallback_contract=fallback_contract, own_provenance=own_provenance,
                                             effect_oracle=o)
    trace.update(owner_trace(o))
    return outcome, trace
