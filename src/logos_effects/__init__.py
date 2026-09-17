"""logos_effects — production owner of canonical effect classification.

Decision: CANONICAL-EFFECT-OWNERSHIP-DECISION-R1, founder-selected Option A
(static canonical effect registry). See docs/adr/ADR-CANONICAL-EFFECT-OWNERSHIP-DECISION.md.

Interface (Section 6 of the work order):

    resolve_effect(action, target, context) -> CanonicalEffectResolution
        status ∈ {RESOLVED, UNKNOWN, UNAVAILABLE, INVALID}; only RESOLVED carries
        an effect; everything else must be treated as DEFER by the caller.

Boundary: this package imports the standard library only. It never reads
memory, memory authority classes, source labels, trust, reliability, prediction
accuracy, model confidence, risk, VOI, uncertainty, declared effect, retrieved
text or prose. It is a PRODUCTION package: `logos_research.experiments` refuses
to be imported from it (B1 guard).
"""
from __future__ import annotations

from .definitions import V1, production_registry, version_v1
from .registry import CanonicalEffectRegistry, RegistryVersion
from .types import (
    OWNER_TYPE,
    STATUSES,
    CanonicalEffect,
    CanonicalEffectContext,
    CanonicalEffectDefinition,
    CanonicalEffectResolution,
)

__all__ = ["OWNER_TYPE", "STATUSES", "V1", "CanonicalEffect", "CanonicalEffectContext", "CanonicalEffectDefinition",
           "CanonicalEffectResolution", "CanonicalEffectRegistry", "RegistryVersion", "default_registry",
           "production_registry", "resolve_effect", "version_v1"]

_DEFAULT: CanonicalEffectRegistry | None = None


def default_registry() -> CanonicalEffectRegistry:
    """Process-wide production registry (v1 active). Built once; versions are
    immutable, so sharing it is safe. Activation changes on it are audited."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = production_registry()
    return _DEFAULT


def resolve_effect(action: str, target: str, context: CanonicalEffectContext, *,
                   registry: CanonicalEffectRegistry | None = None) -> CanonicalEffectResolution:
    return (registry if registry is not None else default_registry()).resolve(action, target, context)
