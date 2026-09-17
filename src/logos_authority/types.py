"""Canonical authority ownership — typed schema (CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1, C1).

A grant record is the only thing that can become canonical authority
evidence, and only through `resolve_authority`. Nothing in this package reads
memory, prose, trust, risk, information value, model confidence or declared
effect. `authority_origin` is a closed enum with NO default: a record without
an origin is INVALID, never human.

    GrantExistence != GrantValidity · GrantValidity != MemoryClaim
    GrantResolution != ModelJudgment · RevokedAuthority != HistoricalPermission
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256

from logos_gamma.types import AUTHORITY_BEARING_ORIGINS, AuthorityEvidence

AUTHORITY_ORIGINS: tuple[str, ...] = ("human", "model", "system")
assert set(AUTHORITY_BEARING_ORIGINS) <= set(AUTHORITY_ORIGINS)
STATUSES: tuple[str, ...] = ("RESOLVED", "NO_GRANT", "REVOKED", "STALE", "NOT_YET_VALID", "WRONG_PRINCIPAL", "WRONG_SCOPE",
                             "WRONG_STATE", "INVALID", "UNAVAILABLE", "UNKNOWN")
DENY_STATUSES: frozenset[str] = frozenset({"REVOKED", "STALE", "NOT_YET_VALID", "WRONG_PRINCIPAL", "WRONG_SCOPE", "WRONG_STATE"})
DEFER_STATUSES: frozenset[str] = frozenset({"INVALID", "UNAVAILABLE", "UNKNOWN"})
OWNER_TYPE = "STATIC_AUTHORITY_STORE"
_HEX64 = 64


def proposal_digest(action: str, target: str) -> str:
    """Identical to the reference ledger's binding digest (parity-tested)."""
    return sha256(f"{action}:{target}".encode()).hexdigest()


@dataclass(frozen=True)
class GrantRecord:
    grant_id: str
    version: str
    principal: str
    action: str
    target: str
    scope_digest: str
    authority_origin: str
    state_hash: str
    issued_at_tick: int
    valid_from_tick: int
    expires_tick: int
    provenance: str
    revoked: bool = False
    revoked_at_tick: int | None = None

    HASHED_FIELDS = ("grant_id", "version", "principal", "action", "target", "scope_digest", "authority_origin", "state_hash",
                     "issued_at_tick", "valid_from_tick", "expires_tick", "provenance", "revoked", "revoked_at_tick")

    @property
    def proposal_digest(self) -> str:
        return proposal_digest(self.action, self.target)

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
        out: list[str] = []
        for name in ("grant_id", "version", "principal", "action", "target", "provenance"):
            v = getattr(self, name)
            if type(v) is not str or not v:
                out.append(f"{name}: non-empty str required")
        for name in ("scope_digest", "state_hash"):
            v = getattr(self, name)
            if type(v) is not str or len(v) != _HEX64 or any(c not in "0123456789abcdef" for c in v):
                out.append(f"{name}: 64-hex digest required")
        if self.authority_origin not in AUTHORITY_ORIGINS:                      # missing / unknown origin is INVALID, never human
            out.append(f"authority_origin: {self.authority_origin!r} not in {AUTHORITY_ORIGINS}")
        for name in ("issued_at_tick", "valid_from_tick", "expires_tick"):
            v = getattr(self, name)
            if type(v) is not int or v < 0:
                out.append(f"{name}: non-negative int required")
        if type(self.revoked) is not bool:
            out.append("revoked: bool required")
        if self.revoked_at_tick is not None and (type(self.revoked_at_tick) is not int or self.revoked_at_tick < 0):
            out.append("revoked_at_tick: int or None required")
        if not out and not (self.issued_at_tick <= self.valid_from_tick < self.expires_tick):
            out.append("ticks: issued_at <= valid_from < expires required")
        return out

    def evidence(self) -> AuthorityEvidence:
        """Γ-facing evidence. Only the resolver calls this, only for RESOLVED."""
        return AuthorityEvidence(grant_id=self.grant_id, origin=self.authority_origin, bound_proposal_digest=self.proposal_digest,
                                 bound_scope_digest=self.scope_digest, bound_state_hash=self.state_hash,
                                 issued_at_tick=self.valid_from_tick, expires_tick=self.expires_tick)

    @classmethod
    def from_dict(cls, raw: dict) -> "GrantRecord":
        if not isinstance(raw, dict):
            raise ValueError("grant record must be an object")
        allowed = set(cls.HASHED_FIELDS) | {"definition_hash"}
        required = set(cls.HASHED_FIELDS) - {"revoked", "revoked_at_tick"}
        extra = set(raw) - allowed; missing = required - set(raw)
        if extra or missing:
            raise ValueError(f"grant record fields: missing={sorted(missing)} extra={sorted(extra)}")
        r = cls(**{f: raw.get(f, False if f == "revoked" else None) for f in cls.HASHED_FIELDS})
        if "definition_hash" in raw and raw["definition_hash"] != r.definition_hash:
            raise ValueError(f"integrity mismatch for grant {raw.get('grant_id')!r}")
        return r


@dataclass(frozen=True)
class AuthorityContext:
    tick: int
    bridge_run_id: str
    tenant: str | None = None


@dataclass(frozen=True)
class AuthorityResolution:
    status: str
    authority_evidence: AuthorityEvidence | None = None
    grant_id: str | None = None
    grant_version: str | None = None
    grant_origin: str | None = None
    principal: str | None = None
    scope: str | None = None
    issued_at: int | None = None
    valid_from: int | None = None
    expires_at: int | None = None
    state_hash: str | None = None
    revocation_state: str | None = None
    definition_hash: str | None = None
    error: str | None = None
    audit_metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"status {self.status!r} not in {STATUSES}")
        if self.status == "RESOLVED":
            if self.authority_evidence is None or not self.grant_id or not self.grant_version or not self.definition_hash \
                    or self.grant_origin not in AUTHORITY_ORIGINS:
                raise ValueError("RESOLVED requires evidence, grant_id, grant_version, grant_origin and definition_hash")
        elif self.authority_evidence is not None:
            raise ValueError(f"{self.status} must not carry authority evidence")

    @property
    def resolved(self) -> bool:
        return self.status == "RESOLVED"
