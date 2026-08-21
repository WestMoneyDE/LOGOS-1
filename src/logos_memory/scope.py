from __future__ import annotations

from dataclasses import asdict, dataclass
from fnmatch import fnmatchcase
from hashlib import sha256
import json
from typing import Literal

Verdict = Literal["ALLOW", "NARROW", "DEFER", "DENY"]


@dataclass(frozen=True)
class ScopeRequest:
    role: str
    tool: str
    memory_kind: str
    capability: str
    target: str
    path: str


@dataclass(frozen=True)
class ScopeViolation:
    dimension: str
    requested: str
    allowed: tuple[str, ...]


@dataclass(frozen=True)
class ScopeContract:
    project: str
    paths: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    roles: tuple[str, ...]
    tools: tuple[str, ...]
    memory_kinds: tuple[str, ...]
    projection_audiences: tuple[str, ...]
    capabilities: tuple[str, ...]
    targets: tuple[str, ...]
    parameter_bounds: tuple[tuple[str, float, float], ...]
    max_cost_usd: float
    max_tokens: int
    max_seconds: int
    max_attempts: int
    valid_from: str
    valid_until: str
    max_occurrences: int
    externality: Literal["internal", "external"]
    reversibility: Literal["reversible", "partially-reversible", "irreversible"]
    approval_required: bool
    data_classes: tuple[str, ...]
    retention_classes: tuple[str, ...]
    source_versions: tuple[str, ...]


@dataclass(frozen=True)
class ScopeDecision:
    verdict: Verdict
    effective: ScopeContract | None
    digest: str
    reasons: tuple[str, ...] = ()
    unresolved_dimensions: tuple[str, ...] = ()

    def evaluate(self, request: ScopeRequest) -> ScopeDecision:
        if self.effective is None:
            return self
        pairs = {
            "roles": request.role,
            "tools": request.tool,
            "memory_kinds": request.memory_kind,
            "capabilities": request.capability,
            "targets": request.target,
        }
        violations = tuple(name for name, value in pairs.items() if value not in getattr(self.effective, name))
        if violations:
            return ScopeDecision("DENY", self.effective, self.digest, ("request exceeds effective scope",), violations)
        return ScopeDecision("ALLOW", self.effective, self.digest)


def _canon(contract: ScopeContract | None) -> bytes:
    return json.dumps(asdict(contract) if contract else None, sort_keys=True, separators=(",", ":")).encode()


def scope_digest(contract: ScopeContract | None) -> str:
    return sha256(_canon(contract)).hexdigest()


def _intersection(contracts: list[ScopeContract], field: str) -> tuple[str, ...]:
    values = set(getattr(contracts[0], field))
    for contract in contracts[1:]:
        values.intersection_update(getattr(contract, field))
    return tuple(sorted(values))


def _path_pattern_subset(narrower: str, broader: str) -> bool:
    """Return whether a path pattern is conservatively contained by another."""
    if narrower == broader:
        return True
    if not any(marker in narrower for marker in "*?["):
        return fnmatchcase(narrower, broader)
    if broader == "**":
        return True
    if broader.endswith("/**"):
        return narrower.startswith(broader[:-3])
    return False


def _path_intersection(contracts: list[ScopeContract]) -> tuple[str, ...]:
    patterns = {pattern for contract in contracts for pattern in contract.paths}
    contained = {
        pattern
        for pattern in patterns
        if all(any(_path_pattern_subset(pattern, allowed) for allowed in contract.paths) for contract in contracts)
    }
    return tuple(sorted(contained))


def intersect_contracts(contracts: list[ScopeContract]) -> ScopeDecision:
    if not contracts:
        return ScopeDecision("DEFER", None, scope_digest(None), ("no scope contracts",), ("all",))
    if len({c.project for c in contracts}) != 1:
        return ScopeDecision("DENY", None, scope_digest(None), ("project mismatch",), ("project",))
    set_fields = (
        "paths",
        "roles", "tools", "memory_kinds", "projection_audiences",
        "capabilities", "targets", "data_classes", "retention_classes",
    )
    merged = {field: _intersection(contracts, field) for field in set_fields if field != "paths"}
    merged["paths"] = _path_intersection(contracts)
    empty = tuple(field for field in set_fields if not merged[field])
    if empty:
        return ScopeDecision("DENY", None, scope_digest(None), ("empty restrictive intersection",), empty)
    bounds = {}
    for name in {item[0] for c in contracts for item in c.parameter_bounds}:
        ranges = [item[1:] for c in contracts for item in c.parameter_bounds if item[0] == name]
        lower, upper = max(r[0] for r in ranges), min(r[1] for r in ranges)
        if lower > upper:
            return ScopeDecision("DENY", None, scope_digest(None), (f"parameter bound empty: {name}",), ("parameter_bounds",))
        bounds[name] = (name, lower, upper)
    effective = ScopeContract(
        project=contracts[0].project,
        excluded_paths=tuple(sorted({p for c in contracts for p in c.excluded_paths})),
        parameter_bounds=tuple(bounds[name] for name in sorted(bounds)),
        max_cost_usd=min(c.max_cost_usd for c in contracts),
        max_tokens=min(c.max_tokens for c in contracts),
        max_seconds=min(c.max_seconds for c in contracts),
        max_attempts=min(c.max_attempts for c in contracts),
        valid_from=max(c.valid_from for c in contracts),
        valid_until=min(c.valid_until for c in contracts),
        max_occurrences=min(c.max_occurrences for c in contracts),
        externality="external" if any(c.externality == "external" for c in contracts) else "internal",
        reversibility="irreversible" if any(c.reversibility == "irreversible" for c in contracts) else (
            "partially-reversible" if any(c.reversibility == "partially-reversible" for c in contracts) else "reversible"
        ),
        approval_required=any(c.approval_required for c in contracts),
        source_versions=tuple(sorted({v for c in contracts for v in c.source_versions})),
        **merged,
    )
    narrowed = any(asdict(effective).get(k) != asdict(contracts[0]).get(k) for k in asdict(effective))
    return ScopeDecision("NARROW" if narrowed or len(contracts) > 1 else "ALLOW", effective, scope_digest(effective))
