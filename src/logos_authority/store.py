"""Authority store — production-facing abstraction over grant records.

A store answers four questions and nothing else: which record has this id,
which records could bind (principal, action, target), is this id revoked,
and what version / integrity hash is the store at. It never resolves; the
resolver does. Unloadable (missing / unreadable / malformed) -> UNAVAILABLE.
Schema, duplicate or hash-integrity failure -> INVALID. Never a fallback to
any experimental ledger.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Protocol

from .types import GrantRecord


class AuthorityStore(Protocol):
    version: str
    available: bool

    def lookup(self, grant_id: str) -> GrantRecord | None: ...
    def grants_for(self, principal: str, action: str, target: str) -> tuple[GrantRecord, ...]: ...
    def revocation(self, grant_id: str) -> tuple[bool, int | None]: ...
    def integrity_hash(self) -> str: ...
    def issues(self) -> list[str]: ...


@dataclass
class InMemoryAuthorityStore:
    version: str = "v1"
    records: dict[str, GrantRecord] = field(default_factory=dict)
    available: bool = True
    load_error: str | None = None
    _duplicates: list[str] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)

    # -- construction ------------------------------------------------------

    @classmethod
    def load(cls, records: Iterable[GrantRecord], *, version: str = "v1") -> "InMemoryAuthorityStore":
        s = cls(version=version)
        for r in records:
            s._add(r)
        return s

    @classmethod
    def unavailable(cls, error: str) -> "InMemoryAuthorityStore":
        s = cls(available=False, load_error=error)
        s.log.append({"event": "load-failed", "error": error})
        return s

    @classmethod
    def from_dict(cls, raw: dict) -> "InMemoryAuthorityStore":
        try:
            if not isinstance(raw, dict) or set(raw) - {"version", "records", "integrity_hash"}:
                raise ValueError("authority store: unexpected shape")
            recs = raw.get("records")
            if not isinstance(recs, list) or type(raw.get("version")) is not str or not raw.get("version"):
                raise ValueError("authority store: version str and records list required")
            s = cls.load([GrantRecord.from_dict(r) for r in recs], version=raw["version"])
            if "integrity_hash" in raw and raw["integrity_hash"] != s.integrity_hash():
                raise ValueError("authority store: integrity mismatch")
            return s
        except (ValueError, TypeError, KeyError) as e:
            return cls.unavailable(f"{type(e).__name__}: {e}")

    @classmethod
    def from_file(cls, path: str | Path) -> "InMemoryAuthorityStore":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as e:
            return cls.unavailable(f"{type(e).__name__}: {e}")
        return cls.from_dict(raw)

    def to_dict(self) -> dict:
        return {"version": self.version, "integrity_hash": self.integrity_hash(),
                "records": [self.records[k].to_dict() for k in sorted(self.records)]}

    # -- governance --------------------------------------------------------

    def _add(self, r: GrantRecord) -> None:
        if r.grant_id in self.records:
            self._duplicates.append(r.grant_id)                       # kept as an INVALID condition, never "last wins"
        self.records[r.grant_id] = r
        self.log.append({"event": "grant-added", "grant_id": r.grant_id, "definition_hash": r.definition_hash, "issues": r.issues()})

    def issue(self, r: GrantRecord) -> None:
        if r.grant_id in self.records:
            raise ValueError(f"grant {r.grant_id!r} already exists (records are immutable; revoke instead)")
        self._add(r)

    def revoke(self, grant_id: str, *, at_tick: int) -> None:
        r = self.records.get(grant_id)
        if r is None:
            return
        from dataclasses import replace
        self.records[grant_id] = replace(r, revoked=True, revoked_at_tick=at_tick)
        self.log.append({"event": "grant-revoked", "grant_id": grant_id, "at_tick": at_tick})

    # -- AuthorityStore protocol ------------------------------------------

    def lookup(self, grant_id: str) -> GrantRecord | None:
        return self.records.get(grant_id)

    def grants_for(self, principal: str, action: str, target: str) -> tuple[GrantRecord, ...]:
        return tuple(r for k in sorted(self.records) if (r := self.records[k]).principal == principal and r.action == action and r.target == target)

    def revocation(self, grant_id: str) -> tuple[bool, int | None]:
        r = self.records.get(grant_id)
        return (False, None) if r is None else (r.revoked, r.revoked_at_tick)

    def integrity_hash(self) -> str:
        body = json.dumps({"version": self.version, "records": sorted(r.definition_hash for r in self.records.values())}, sort_keys=True, separators=(",", ":"))
        return sha256(body.encode()).hexdigest()

    def issues(self) -> list[str]:
        out = [f"duplicate grant id {g!r}" for g in self._duplicates]
        if type(self.version) is not str or not self.version:
            out.append("version: non-empty str required")
        for r in self.records.values():
            out.extend(f"{r.grant_id}: {i}" for i in r.issues())
        return out
