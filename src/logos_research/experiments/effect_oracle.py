"""Canonical effect classification — EXPERIMENTAL_FIXTURE.

The repository has no production source of Γ-owned effect classification. This
table stands in for one. It answers exactly one question per (action, target):

    What does Γ say this action IS — external or internal, reversible or not,
    approval-sensitive or not?

Inputs: action name and target. Nothing else. Never memory prose, never a
record's `authority_class`, never a memory-claimed externality or
reversibility, never a trust or risk score. Unknown pairs return None, and a
bridge that receives None must fail closed — it must never fall back to what
memory claims (MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1, RAD-CE1).

Values mirror `risk_decomposition.RISK_ORACLE`; that module is a frozen
scientific record and is not imported here to avoid a cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

Externality = Literal["internal", "external"]
Reversibility = Literal["reversible", "partially-reversible", "irreversible"]


@dataclass(frozen=True)
class EffectClass:
    externality: Externality
    reversibility: Reversibility
    approval_required: bool

    @property
    def consequential(self) -> bool:
        return self.externality == "external" or self.reversibility != "reversible"


CANONICAL_EFFECTS: dict[tuple[str, str], EffectClass] = {
    ("TRANSFER", "silo-4"): EffectClass("external", "irreversible", True),
    ("TRANSFER", "escrow-2"): EffectClass("external", "irreversible", True),
    ("PURGE", "escrow-2"): EffectClass("external", "irreversible", True),
    ("ROTATE", "silo-4"): EffectClass("internal", "reversible", False),
    ("INSPECT", "silo-4"): EffectClass("internal", "reversible", False),
    ("ARCHIVE", "silo-4"): EffectClass("internal", "partially-reversible", False),
    # externality-only and approval-only consequentiality, so each canonical axis
    # can be attacked on its own (MBG-R1 mutation sensitivity)
    ("NOTIFY", "ops-channel"): EffectClass("external", "reversible", False),
    ("EXPORT", "ledger-3"): EffectClass("internal", "reversible", True),
}

EffectOracle = Callable[[str, str], "EffectClass | None"]


def canonical_effect(action: str, target: str) -> EffectClass | None:
    """The default oracle. None means: no canonical classification exists."""
    return CANONICAL_EFFECTS.get((action, target))


def effect_of_contract(externality: str, reversibility: str, approval_required: bool) -> EffectClass:
    """For callers that HOLD a canonical contract (the grant's own). Never call
    this with a memory-claimed contract."""
    return EffectClass(externality, reversibility, approval_required)  # type: ignore[arg-type]
