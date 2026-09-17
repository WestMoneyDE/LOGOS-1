"""Production canonical effect definitions — version v1.

Governance: CANONICAL-EFFECT-OWNERSHIP-DECISION-R1 (founder decision: Option A,
static registry). Every row is migrated one-to-one from the experimental
reference oracle tables (the research fixtures behind RAD / MBG / MBGV / VOI)
with identical externality / reversibility / approval_required; the migration
mapping with source rows, definition ids and hashes lives in
docs/research/CANONICAL-EFFECT-OWNER.json and is test-compared against both
sources. Nothing here is imported from those fixtures: this file is the owner,
they are the reference.

Semantics are GLOBAL (domain "global"); tenant-specific definitions are
OUT_OF_SCOPE. A new row or a changed row is a new registry version — this
tuple is never edited in place after release.
"""
from __future__ import annotations

from .registry import CanonicalEffectRegistry, RegistryVersion
from .types import CanonicalEffectDefinition

V1 = "v1"
V1_PROVENANCE = "governance:CANONICAL-EFFECT-OWNERSHIP-DECISION-R1; founder-decision:Option-A; base:4795b16"
V1_CREATED_AT = "2026-09-17T00:00:00+00:00"
GLOBAL = "global"

_ROWS: tuple[tuple[str, str, str, str, bool, str], ...] = (
    # effect_id                 action          target             externality  reversibility           approval  source row
    ("ce-transfer-silo-4",      "TRANSFER",     "silo-4",          "external",  "irreversible",         True),   # reference row
    ("ce-transfer-escrow-2",    "TRANSFER",     "escrow-2",        "external",  "irreversible",         True),   # reference row
    ("ce-purge-escrow-2",       "PURGE",        "escrow-2",        "external",  "irreversible",         True),   # reference row
    ("ce-rotate-silo-4",        "ROTATE",       "silo-4",          "internal",  "reversible",           False),  # reference row
    ("ce-inspect-silo-4",       "INSPECT",      "silo-4",          "internal",  "reversible",           False),  # reference row
    ("ce-archive-silo-4",       "ARCHIVE",      "silo-4",          "internal",  "partially-reversible", False),  # reference row
    ("ce-notify-ops-channel",   "NOTIFY",       "ops-channel",     "external",  "reversible",           False),  # reference row (externality-only)
    ("ce-export-ledger-3",      "EXPORT",       "ledger-3",        "internal",  "reversible",           True),   # reference row (approval-only)
    ("ce-query-customer-secret", "QUERY_RECORD", "customer-secret", "internal", "reversible",           True),   # reference row, VOI (protected)
    ("ce-query-public-ledger",  "QUERY_RECORD", "public-ledger",   "internal",  "reversible",           False),  # reference row, VOI
    ("ce-simulate-silo-4",      "SIMULATE",     "silo-4",          "internal",  "reversible",           False),  # reference row, VOI
)


def _definition(row) -> CanonicalEffectDefinition:
    effect_id, action, target, ext, rev, appr = row
    return CanonicalEffectDefinition(effect_id=effect_id, action=action, target=target, domain=GLOBAL,
                                     externality=ext, reversibility=rev, approval_required=appr,  # type: ignore[arg-type]
                                     version=V1, provenance=V1_PROVENANCE, effective_from=V1_CREATED_AT, effective_until=None)


def version_v1() -> RegistryVersion:
    return RegistryVersion(V1, tuple(_definition(r) for r in _ROWS), V1_PROVENANCE, V1_CREATED_AT)


def production_registry(*, sink=None) -> CanonicalEffectRegistry:
    """A fresh registry holding v1, active. Callers that need a shared instance
    use `logos_effects.default_registry()`."""
    return CanonicalEffectRegistry.load([version_v1()], V1, sink=sink)
