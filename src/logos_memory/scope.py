from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from hashlib import sha256
import json
import math
from numbers import Real
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

    def validate(self) -> ScopeDecision:
        """Fail closed when a nominally permissive decision is internally inconsistent."""
        if self.verdict not in {"ALLOW", "NARROW"}:
            return self
        if self.effective is None:
            return ScopeDecision(
                "DENY", None, self.digest,
                ("allowed scope has no effective contract",), ("effective",),
            )
        if self.digest != scope_digest(self.effective):
            return ScopeDecision(
                "DENY", self.effective, self.digest,
                ("effective scope digest mismatch",), ("digest",),
            )
        return self

    def evaluate(self, request: ScopeRequest) -> ScopeDecision:
        validated = self.validate()
        if validated.verdict not in {"ALLOW", "NARROW"}:
            return validated
        assert validated.effective is not None
        pairs = {
            "roles": request.role,
            "tools": request.tool,
            "memory_kinds": request.memory_kind,
            "capabilities": request.capability,
            "targets": request.target,
        }
        violations = tuple(name for name, value in pairs.items() if value not in getattr(validated.effective, name))
        path_violation = _request_path_violation(request.path, validated.effective)
        if path_violation:
            violations += ("paths",)
        if violations:
            reason = "request path exceeds effective scope" if path_violation else "request exceeds effective scope"
            return ScopeDecision("DENY", validated.effective, validated.digest, (reason,), violations)
        return ScopeDecision("ALLOW", validated.effective, validated.digest)


def _canon(contract: ScopeContract | None) -> bytes:
    return json.dumps(asdict(contract) if contract else None, sort_keys=True, separators=(",", ":")).encode()


def scope_digest(contract: ScopeContract | None) -> str:
    return sha256(_canon(contract)).hexdigest()


def _intersection(contracts: list[ScopeContract], field: str) -> tuple[str, ...]:
    values = set(getattr(contracts[0], field))
    for contract in contracts[1:]:
        values.intersection_update(getattr(contract, field))
    return tuple(sorted(values))


def _split_path(value: str, *, pattern: bool) -> tuple[str, ...] | None:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        return None
    if value.startswith("/") or (len(value) > 1 and value[1] == ":"):
        return None
    parts = tuple(value.split("/"))
    if any(part in ("", ".", "..") for part in parts):
        return None
    if pattern and any("[" in part or "]" in part for part in parts):
        return None
    return parts


def _valid_scope_pattern(value: str) -> bool:
    parts = _split_path(value, pattern=True)
    if parts is None:
        return False
    for index, part in enumerate(parts):
        if "**" in part and (part != "**" or index != len(parts) - 1):
            return False
    return True


def _finite_real(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(value)
    except (TypeError, ValueError, OverflowError):
        return False


def _invalid_input_dimensions(contracts: list[ScopeContract]) -> tuple[str, ...]:
    if any(not isinstance(contract, ScopeContract) for contract in contracts):
        return ("contracts",)
    invalid: list[str] = []

    if any(not isinstance(contract.project, str) or not contract.project for contract in contracts):
        invalid.append("project")

    for field in ("paths", "excluded_paths"):
        for contract in contracts:
            patterns = getattr(contract, field)
            if not isinstance(patterns, tuple) or any(
                not _valid_scope_pattern(pattern) for pattern in patterns
            ):
                invalid.append(field)
                break

    string_collection_fields = (
        "roles", "tools", "memory_kinds", "projection_audiences", "capabilities",
        "targets", "data_classes", "retention_classes", "source_versions",
    )
    for field in string_collection_fields:
        for contract in contracts:
            values = getattr(contract, field)
            if not isinstance(values, tuple) or any(not isinstance(value, str) or not value for value in values):
                invalid.append(field)
                break

    for contract in contracts:
        bounds = contract.parameter_bounds
        if not isinstance(bounds, tuple):
            invalid.append("parameter_bounds")
            continue
        for bound in bounds:
            if (
                not isinstance(bound, tuple)
                or len(bound) != 3
                or not isinstance(bound[0], str)
                or not bound[0]
                or not _finite_real(bound[1])
                or not _finite_real(bound[2])
                or bound[1] > bound[2]
            ):
                invalid.append("parameter_bounds")
                break

    integer_rules = (
        ("max_tokens", 0, False),
        ("max_seconds", 0, False),
        ("max_attempts", 0, True),
        ("max_occurrences", 0, True),
    )
    for field, minimum, strict in integer_rules:
        for contract in contracts:
            value = getattr(contract, field)
            if type(value) is not int or (value <= minimum if strict else value < minimum):
                invalid.append(field)
                break

    for contract in contracts:
        value = contract.max_cost_usd
        if not _finite_real(value) or value < 0.0:
            invalid.append("max_cost_usd")
            break

    enum_values = (
        ("externality", {"internal", "external"}),
        ("reversibility", {"reversible", "partially-reversible", "irreversible"}),
    )
    for field, allowed in enum_values:
        for contract in contracts:
            value = getattr(contract, field)
            if type(value) is not str or value not in allowed:
                invalid.append(field)
                break
    if any(type(contract.approval_required) is not bool for contract in contracts):
        invalid.append("approval_required")
    if any(
        not isinstance(contract.valid_from, str)
        or not contract.valid_from
        or not isinstance(contract.valid_until, str)
        or not contract.valid_until
        for contract in contracts
    ):
        invalid.append("validity")
    return tuple(dict.fromkeys(invalid))


def _pattern_segment_subset(narrower: str, broader: str) -> bool:
    if narrower == broader:
        return True
    if any(marker in narrower for marker in "*?"):
        return False
    return any(marker in broader for marker in "*?") and fnmatchcase(narrower, broader)


def _path_matches_segments(path: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
    def matches(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern):
            return path_index == len(path)
        segment = pattern[pattern_index]
        if segment == "**":
            return matches(path_index, pattern_index + 1) or (
                path_index < len(path) and matches(path_index + 1, pattern_index)
            )
        return (
            path_index < len(path)
            and fnmatchcase(path[path_index], segment)
            and matches(path_index + 1, pattern_index + 1)
        )

    return matches(0, 0)


def _path_pattern_subset(narrower: str, broader: str) -> bool:
    """Return whether a path pattern is conservatively contained by another."""
    narrower_parts = _split_path(narrower, pattern=True)
    broader_parts = _split_path(broader, pattern=True)
    if narrower_parts is None or broader_parts is None:
        return False
    if narrower_parts == broader_parts:
        return True
    if "**" not in broader_parts:
        return False
    recursive_index = broader_parts.index("**")
    if recursive_index != len(broader_parts) - 1:
        return False
    if len(narrower_parts) < recursive_index:
        return False
    return all(
        _pattern_segment_subset(narrower_parts[index], broader_parts[index])
        for index in range(recursive_index)
    )


def _path_pattern_matches(path: str, pattern: str) -> bool | None:
    path_parts = _split_path(path, pattern=False)
    pattern_parts = _split_path(pattern, pattern=True)
    if path_parts is None or pattern_parts is None:
        return None
    return _path_matches_segments(path_parts, pattern_parts)


def _request_path_violation(path: str, contract: ScopeContract) -> bool:
    if _split_path(path, pattern=False) is None:
        return True
    include_matches = [_path_pattern_matches(path, pattern) for pattern in contract.paths]
    if not include_matches or any(match is None for match in include_matches) or not any(include_matches):
        return True
    excluded_matches = [_path_pattern_matches(path, pattern) for pattern in contract.excluded_paths]
    return any(match is None or match for match in excluded_matches)


def _parse_timestamp(value: str) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


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
    invalid_dimensions = _invalid_input_dimensions(contracts)
    if invalid_dimensions:
        return ScopeDecision(
            "DENY", None, scope_digest(None), ("invalid scope input",), invalid_dimensions,
        )
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

    validity = []
    for contract in contracts:
        valid_from = _parse_timestamp(contract.valid_from)
        valid_until = _parse_timestamp(contract.valid_until)
        if valid_from is None or valid_until is None:
            return ScopeDecision("DENY", None, scope_digest(None), ("invalid validity timestamp",), ("validity",))
        validity.append((valid_from, valid_until, contract.valid_from, contract.valid_until))
    effective_from = max(validity, key=lambda item: (item[0], item[2]))
    effective_until = min(validity, key=lambda item: (item[1], item[3]))
    if effective_from[0] >= effective_until[1]:
        return ScopeDecision("DENY", None, scope_digest(None), ("empty validity window",), ("validity",))

    bounds = {}
    names = sorted({item[0] for c in contracts for item in c.parameter_bounds})
    for name in names:
        ranges = []
        for contract in contracts:
            matching = [item[1:] for item in contract.parameter_bounds if item[0] == name]
            if len(matching) != 1:
                return ScopeDecision(
                    "DENY", None, scope_digest(None),
                    (f"parameter bound missing or ambiguous: {name}",), ("parameter_bounds",),
                )
            ranges.append(matching[0])
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
        valid_from=effective_from[2],
        valid_until=effective_until[3],
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
