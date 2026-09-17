"""Canonical effect ownership — typed schema (CANONICAL-EFFECT-OWNERSHIP-DECISION-R1, Option A).

A canonical effect definition answers exactly one question for one
``(action, target, domain)``: what the action IS — external or internal,
reversible or not, approval-sensitive or not. Consequentiality is DERIVED, not
stored: ``consequential = externality == "external" or reversibility != "reversible"``,
identical to Γ's ``is_consequential()``.

Nothing in this module reads memory, trust, risk, information value, model
confidence or prose. Its only inputs are typed definitions and a typed context.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from hashlib import sha256
from typing import Literal

Externality = Literal["internal", "external"]
Reversibility = Literal["reversible", "partially-reversible", "irreversible"]
ResolutionStatus = Literal["RESOLVED", "UNKNOWN", "UNAVAILABLE", "INVALID"]

EXTERNALITIES: tuple[str, ...] = ("internal", "external")
REVERSIBILITIES: tuple[str, ...] = ("reversible", "partially-reversible", "irreversible")
STATUSES: tuple[str, ...] = ("RESOLVED", "UNKNOWN", "UNAVAILABLE", "INVALID")
OWNER_TYPE = "STATIC_REGISTRY"


@dataclass(frozen=True)
class CanonicalEffect:
    """The three canonical axes. Consequentiality is derived (see module doc)."""
    externality: Externality
    reversibility: Reversibility
    approval_required: bool

    @property
    def consequential(self) -> bool:
        return self.externality == "external" or self.reversibility != "reversible"


@dataclass(frozen=True)
class CanonicalEffectDefinition:
    effect_id: str
    action: str
    target: str
    domain: str
    externality: Externality
    reversibility: Reversibility
    approval_required: bool
    version: str
    provenance: str
    effective_from: str
    effective_until: str | None = None

    HASHED_FIELDS = ("effect_id", "action", "target", "domain", "externality", "reversibility", "approval_required",
                     "version", "provenance", "effective_from", "effective_until")

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.action, self.target, self.domain)

    @property
    def effect(self) -> CanonicalEffect:
        return CanonicalEffect(self.externality, self.reversibility, self.approval_required)

    def canonical_json(self) -> str:
        return json.dumps({f: getattr(self, f) for f in self.HASHED_FIELDS}, sort_keys=True, separators=(",", ":"))

    @property
    def definition_hash(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()

    def to_dict(self) -> dict:
        d = {f: getattr(self, f) for f in self.HASHED_FIELDS}
        d["definition_hash"] = self.definition_hash
        return d

    def issues(self) -> list[str]:
        """Schema problems. An empty list means the definition is well-formed."""
        out: list[str] = []
        for name in ("effect_id", "action", "target", "domain", "version", "provenance", "effective_from"):
            v = getattr(self, name)
            if type(v) is not str or not v:
                out.append(f"{name}: non-empty str required")
        if self.externality not in EXTERNALITIES:
            out.append(f"externality: {self.externality!r} not in {EXTERNALITIES}")
        if self.reversibility not in REVERSIBILITIES:
            out.append(f"reversibility: {self.reversibility!r} not in {REVERSIBILITIES}")
        if type(self.approval_required) is not bool:
            out.append("approval_required: bool required")
        if self.effective_until is not None and (type(self.effective_until) is not str or not self.effective_until):
            out.append("effective_until: str or None required")
        if isinstance(self.effective_from, str) and isinstance(self.effective_until, str) and self.effective_until <= self.effective_from:
            out.append("effective_until must be after effective_from")
        return out

    def in_effect(self, as_of: str | None) -> bool:
        if as_of is None:
            return self.effective_until is None
        return self.effective_from <= as_of and (self.effective_until is None or as_of < self.effective_until)

    @classmethod
    def from_dict(cls, raw: dict) -> "CanonicalEffectDefinition":
        """Strict: every schema field present, no extras. The stored hash (if
        present) must match the recomputed one — an integrity mismatch raises."""
        if not isinstance(raw, dict):
            raise ValueError("definition must be an object")
        allowed = set(cls.HASHED_FIELDS) | {"definition_hash"}
        extra = set(raw) - allowed
        missing = set(cls.HASHED_FIELDS) - set(raw) - {"effective_until"}
        if extra or missing:
            raise ValueError(f"definition fields: missing={sorted(missing)} extra={sorted(extra)}")
        d = cls(**{f: raw.get(f) for f in cls.HASHED_FIELDS})
        if "definition_hash" in raw and raw["definition_hash"] != d.definition_hash:
            raise ValueError(f"integrity mismatch for {raw.get('effect_id')!r}")
        return d


@dataclass(frozen=True)
class CanonicalEffectContext:
    """What a resolution is FOR. Nothing here can change a definition."""
    bridge_run_id: str
    domain: str = "global"
    tenant: str | None = None        # recorded in the audit only; semantics are global
    as_of: str | None = None         # ISO timestamp; None = "current, open-ended definitions only"
    deadline_ns: int | None = None   # monotonic-ns deadline; exceeded -> UNAVAILABLE


@dataclass(frozen=True)
class CanonicalEffectResolution:
    status: ResolutionStatus
    effect: CanonicalEffect | None = None
    definition_id: str | None = None
    version: str | None = None
    definition_hash: str | None = None
    provenance: str | None = None
    error: str | None = None
    audit_metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"status {self.status!r} not in {STATUSES}")
        if self.status == "RESOLVED":
            if self.effect is None or not self.definition_id or not self.version or not self.definition_hash:
                raise ValueError("RESOLVED requires effect, definition_id, version and definition_hash")
        elif self.effect is not None:
            raise ValueError(f"{self.status} must not carry an effect")

    @property
    def resolved(self) -> bool:
        return self.status == "RESOLVED"


def definition_fields() -> tuple[str, ...]:
    return tuple(f.name for f in fields(CanonicalEffectDefinition))
