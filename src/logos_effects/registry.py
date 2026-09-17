"""Static canonical effect registry — the production owner selected by the
founder (Option A, CANONICAL-EFFECT-OWNERSHIP-DECISION-R1).

Shape:

    CanonicalEffectRegistry
    ├── versions        immutable RegistryVersion objects, each content-hashed
    ├── active_version  exactly one, explicit; activation is an audited event
    ├── resolve(action, target, context) -> CanonicalEffectResolution
    └── audit           append-only records of every resolution and activation

Fail-closed by construction:

    no definition                -> UNKNOWN
    outside effective window     -> UNKNOWN
    domain mismatch              -> UNKNOWN
    active version invalid       -> INVALID
    registry not loadable        -> UNAVAILABLE
    deadline exceeded            -> UNAVAILABLE
    no active version            -> UNAVAILABLE

Only RESOLVED carries an effect. There is no default, no fallback and no input
other than ``(action, target, context)`` and the frozen definitions.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Callable, Iterable

from .types import OWNER_TYPE, CanonicalEffectContext, CanonicalEffectDefinition, CanonicalEffectResolution

AuditSink = Callable[[dict], None]


@dataclass(frozen=True)
class RegistryVersion:
    version: str
    definitions: tuple[CanonicalEffectDefinition, ...]
    provenance: str
    created_at: str

    @property
    def content_hash(self) -> str:
        body = json.dumps({"version": self.version, "provenance": self.provenance, "created_at": self.created_at,
                           "definitions": sorted(d.definition_hash for d in self.definitions)}, sort_keys=True, separators=(",", ":"))
        return sha256(body.encode()).hexdigest()

    def issues(self) -> list[str]:
        out: list[str] = []
        if type(self.version) is not str or not self.version:
            out.append("version: non-empty str required")
        keys: dict[tuple[str, str, str], str] = {}
        ids: set[str] = set()
        for d in self.definitions:
            if not isinstance(d, CanonicalEffectDefinition):
                out.append(f"definition of type {type(d).__name__}")
                continue
            out.extend(f"{d.effect_id}: {i}" for i in d.issues())
            if d.version != self.version:
                out.append(f"{d.effect_id}: version {d.version!r} != registry version {self.version!r}")
            if d.effect_id in ids:
                out.append(f"{d.effect_id}: duplicate effect_id")
            ids.add(d.effect_id)
            if d.key in keys:
                out.append(f"{d.effect_id}: duplicate definition for {d.key} (also {keys[d.key]})")
            keys[d.key] = d.effect_id
        return out

    def lookup(self, action: str, target: str, domain: str) -> CanonicalEffectDefinition | None:
        for d in self.definitions:
            if d.key == (action, target, domain):
                return d
        return None

    def to_dict(self) -> dict:
        return {"version": self.version, "provenance": self.provenance, "created_at": self.created_at,
                "content_hash": self.content_hash, "definitions": [d.to_dict() for d in self.definitions]}

    @classmethod
    def from_dict(cls, raw: dict) -> "RegistryVersion":
        if not isinstance(raw, dict) or set(raw) - {"version", "provenance", "created_at", "content_hash", "definitions"}:
            raise ValueError("registry version: unexpected shape")
        defs = raw.get("definitions")
        if not isinstance(defs, list):
            raise ValueError("registry version: definitions must be a list")
        v = cls(raw.get("version"), tuple(CanonicalEffectDefinition.from_dict(d) for d in defs), raw.get("provenance"), raw.get("created_at"))
        if "content_hash" in raw and raw["content_hash"] != v.content_hash:
            raise ValueError(f"integrity mismatch for registry version {raw.get('version')!r}")
        return v


@dataclass
class CanonicalEffectRegistry:
    """See module doc. ``available=False`` models an owner that could not be
    loaded (missing / unreadable / corrupt source); every resolution is then
    UNAVAILABLE. Versions are immutable; only the active pointer moves, and
    every move is audited."""
    versions: dict[str, RegistryVersion] = field(default_factory=dict)
    active_version: str | None = None
    available: bool = True
    load_error: str | None = None
    audit: list[dict] = field(default_factory=list)
    sink: AuditSink | None = None
    owner_id: str = "logos_effects.CanonicalEffectRegistry"

    # -- construction ------------------------------------------------------

    @classmethod
    def load(cls, versions: Iterable[RegistryVersion], active: str, *, sink: AuditSink | None = None) -> "CanonicalEffectRegistry":
        reg = cls(sink=sink)
        for v in versions:
            if v.version in reg.versions:
                raise ValueError(f"duplicate registry version {v.version!r}")
            reg.versions[v.version] = v
        reg.activate(active, reason="load")
        return reg

    @classmethod
    def unavailable(cls, error: str, *, sink: AuditSink | None = None) -> "CanonicalEffectRegistry":
        reg = cls(available=False, load_error=error, sink=sink)
        reg._record({"event": "load-failed", "error": error})
        return reg

    @classmethod
    def from_dict(cls, raw: dict, *, sink: AuditSink | None = None) -> "CanonicalEffectRegistry":
        """Structural failures -> UNAVAILABLE registry (never raises for data problems)."""
        try:
            if not isinstance(raw, dict) or set(raw) - {"active_version", "versions", "owner_id"}:
                raise ValueError("registry: unexpected shape")
            versions = [RegistryVersion.from_dict(v) for v in raw.get("versions", [])]
            return cls.load(versions, raw.get("active_version"), sink=sink)
        except (ValueError, TypeError, KeyError) as e:
            return cls.unavailable(f"{type(e).__name__}: {e}", sink=sink)

    @classmethod
    def from_file(cls, path: str | Path, *, sink: AuditSink | None = None) -> "CanonicalEffectRegistry":
        p = Path(path)
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as e:
            return cls.unavailable(f"{type(e).__name__}: {e}", sink=sink)
        return cls.from_dict(raw, sink=sink)

    def to_dict(self) -> dict:
        return {"owner_id": self.owner_id, "active_version": self.active_version,
                "versions": [self.versions[k].to_dict() for k in sorted(self.versions)]}

    # -- governance --------------------------------------------------------

    def add_version(self, v: RegistryVersion) -> None:
        if v.version in self.versions:
            raise ValueError(f"registry version {v.version!r} already exists (versions are immutable)")
        self.versions[v.version] = v
        self._record({"event": "version-added", "version": v.version, "content_hash": v.content_hash, "issues": v.issues()})

    def activate(self, version: str | None, *, reason: str = "activate") -> None:
        """Move the active pointer. Unknown version -> pointer becomes None
        (UNAVAILABLE), never a silent keep."""
        previous = self.active_version
        self.active_version = version if version in self.versions else None
        self._record({"event": "activated", "reason": reason, "from": previous, "to": self.active_version,
                      "requested": version, "content_hash": self.versions[version].content_hash if version in self.versions else None})

    def active(self) -> RegistryVersion | None:
        return self.versions.get(self.active_version) if self.active_version else None

    def active_issues(self) -> list[str]:
        v = self.active()
        return v.issues() if v else []

    # -- resolution --------------------------------------------------------

    def resolve(self, action: str, target: str, context: CanonicalEffectContext) -> CanonicalEffectResolution:
        t0 = time.perf_counter_ns()
        status, error, d = self._resolve(action, target, context)
        v = self.active()
        meta = {"owner_type": OWNER_TYPE, "owner_id": self.owner_id,
                "owner_version": self.active_version, "registry_hash": v.content_hash if v else None,
                "definition_id": d.effect_id if d else None, "definition_hash": d.definition_hash if d else None,
                "status": status, "action": action, "target": target, "domain": context.domain, "tenant": context.tenant,
                "as_of": context.as_of, "bridge_run_id": context.bridge_run_id, "error": error,
                "latency_ns": time.perf_counter_ns() - t0, "resolved_at_ns": time.time_ns()}
        self._record({"event": "resolve", **meta})
        if status == "RESOLVED":
            assert d is not None
            return CanonicalEffectResolution("RESOLVED", d.effect, d.effect_id, d.version, d.definition_hash, d.provenance, None, meta)
        return CanonicalEffectResolution(status, None, None, self.active_version, None, None, error, meta)

    def _resolve(self, action: str, target: str, context: CanonicalEffectContext):
        if not self.available:
            return "UNAVAILABLE", f"registry not loadable: {self.load_error}", None
        if context.deadline_ns is not None and time.monotonic_ns() > context.deadline_ns:
            return "UNAVAILABLE", "deadline exceeded", None
        v = self.active()
        if v is None:
            return "UNAVAILABLE", "no active version", None
        issues = v.issues()
        if issues:
            return "INVALID", "; ".join(issues), None
        if type(action) is not str or type(target) is not str or type(context.domain) is not str:
            return "INVALID", "action, target and domain must be str", None
        d = v.lookup(action, target, context.domain)
        if d is None:
            return "UNKNOWN", f"no canonical definition for ({action!r}, {target!r}, {context.domain!r}) in {v.version}", None
        if not d.in_effect(context.as_of):
            return "UNKNOWN", f"{d.effect_id} not in effect at {context.as_of!r}", None
        return "RESOLVED", None, d

    # -- audit -------------------------------------------------------------

    def _record(self, rec: dict) -> None:
        self.audit.append(rec)
        if self.sink is not None:
            self.sink(rec)
