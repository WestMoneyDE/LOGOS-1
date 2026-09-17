"""Production memory reader (CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1, C4).

    read_memory(memory_ref, tenant_context, principal_context, *, root) -> MemoryReadResult

A memory record yields EVIDENCE: grant references, a claimed scope, a declared
effect, provenance. It never yields a grant, a canonical effect, an authority
origin, freshness or approval. The reader is strict where the experimental
reader was lenient (VF-2 / VF-3): duplicate JSON keys, NaN / Infinity,
empty strings, negative numbers and wrong types make the record INVALID.

Tenant isolation is structural: every tenant has its own store directory
under `root`, the reference form is ``memory://<tenant_id>/<record_id>``, and
the tenant identity comes only from the typed `TenantContext` — a reference
naming another tenant is WRONG_TENANT before any store is opened.

    MemoryRead != Authorization · DeclaredEffect != CanonicalEffect
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from logos_gamma.types import ProvenanceClaim
from logos_runtime.types import DeclaredEvidence, MemoryReadOutcome, PrincipalContext, TenantContext

from .records import MemoryRecord
from .scope import ScopeContract, scope_digest
from .store import MemoryStore

NOTE_SCHEMA = "logos.authority-note/1"                 # parity-tested against the experiment constant
SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1})
READER_STATUSES: tuple[str, ...] = ("RESOLVED", "NOT_FOUND", "INVALID", "CORRUPT", "UNAVAILABLE", "WRONG_TENANT", "UNSUPPORTED_VERSION")
REF_PREFIX = "memory://"
_EXT = ("internal", "external")
_REV = ("reversible", "partially-reversible", "irreversible")
_TUPLE_FIELDS = ("paths", "excluded_paths", "roles", "tools", "memory_kinds", "projection_audiences", "capabilities", "targets",
                 "data_classes", "retention_classes", "source_versions")
_STR_FIELDS = ("project", "valid_from", "valid_until", "externality", "reversibility")
_INT_FIELDS = ("max_tokens", "max_seconds", "max_attempts", "max_occurrences")
_CONTRACT_KEYS = frozenset(ScopeContract.__dataclass_fields__)


@dataclass(frozen=True)
class MemoryReadResult:
    status: str
    record_id: str | None = None
    tenant_id: str | None = None
    schema_version: int | None = None
    content: str | None = None
    declared_effect: tuple[str | None, str | None] = (None, None)
    claimed_scope: ScopeContract | None = None
    provenance: dict = field(default_factory=dict)
    admissible_uses: tuple[str, ...] = ()
    binding_digest: str | None = None
    record_hash: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    refs: tuple[str, ...] = ()
    claims: tuple[ProvenanceClaim, ...] = ()
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in READER_STATUSES:
            raise ValueError(f"status {self.status!r} not in {READER_STATUSES}")
        if self.status != "RESOLVED" and (self.claimed_scope is not None or self.refs or self.claims):
            raise ValueError(f"{self.status} must not carry evidence")

    def evidence(self) -> DeclaredEvidence:
        return DeclaredEvidence(self.refs, self.claimed_scope, self.declared_effect, self.claims, (), (self.record_hash,) if self.record_hash else (), self.tenant_id)


# -- strict JSON ------------------------------------------------------------

def _no_duplicates(pairs):
    d: dict = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"duplicate key {k!r}")
        d[k] = v
    return d


def _no_constants(name):
    raise ValueError(f"non-finite number {name}")


def strict_loads(text: str):
    """VF-3: duplicate keys rejected pre-parse. VF-2: NaN / Infinity rejected."""
    return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constants)


def _finite(x) -> bool:
    return type(x) in (int, float) and not isinstance(x, bool) and math.isfinite(x)


def contract_from(raw: object) -> tuple[ScopeContract | None, str | None]:
    """Strict, domain-validated claimed scope. (contract, error)."""
    if type(raw) is not dict:
        return None, "scope: object required"
    if set(raw) != _CONTRACT_KEYS:
        return None, f"scope: keys missing={sorted(_CONTRACT_KEYS - set(raw))} extra={sorted(set(raw) - _CONTRACT_KEYS)}"
    d = dict(raw)
    for k in _TUPLE_FIELDS:
        if type(d[k]) is not list or any(type(x) is not str or not x for x in d[k]):
            return None, f"scope.{k}: list of non-empty str required"
        d[k] = tuple(d[k])
    for k in _STR_FIELDS:
        if type(d[k]) is not str or not d[k]:
            return None, f"scope.{k}: non-empty str required"
    if d["externality"] not in _EXT or d["reversibility"] not in _REV:
        return None, "scope.externality/reversibility: enum required"
    for k in _INT_FIELDS:
        if type(d[k]) is not int or isinstance(d[k], bool) or d[k] < 0:
            return None, f"scope.{k}: non-negative int required"
    if not _finite(d["max_cost_usd"]) or d["max_cost_usd"] < 0:
        return None, "scope.max_cost_usd: finite non-negative number required"
    if type(d["approval_required"]) is not bool:
        return None, "scope.approval_required: bool required"
    if type(d["parameter_bounds"]) is not list:
        return None, "scope.parameter_bounds: list required"
    bounds = []
    for b in d["parameter_bounds"]:
        if type(b) is not list or len(b) != 3 or type(b[0]) is not str or not b[0] or not _finite(b[1]) or not _finite(b[2]):
            return None, "scope.parameter_bounds: [name, lo, hi] with finite numbers required"
        bounds.append(tuple(b))
    d["parameter_bounds"] = tuple(bounds)
    try:
        return ScopeContract(**d), None
    except TypeError as e:
        return None, f"scope: {e}"


# -- reference / tenant -------------------------------------------------------

def parse_ref(memory_ref: object) -> tuple[str, str] | None:
    if type(memory_ref) is not str or not memory_ref.startswith(REF_PREFIX):
        return None
    rest = memory_ref[len(REF_PREFIX):]
    if rest.count("/") != 1:
        return None
    tenant, rid = rest.split("/")
    if not tenant or not rid or "/" in tenant or ".." in tenant or ".." in rid:
        return None
    return tenant, rid


def tenant_store_path(root: Path, tenant_id: str) -> Path:
    return Path(root) / tenant_id / "mem"


# -- reader ------------------------------------------------------------------

def read_memory(memory_ref: object, tenant_context: TenantContext, principal_context: PrincipalContext, *, root: str | Path) -> MemoryReadResult:
    parsed = parse_ref(memory_ref)
    if parsed is None:
        return MemoryReadResult("INVALID", error=f"malformed memory reference {memory_ref!r}")
    tenant, rid = parsed
    if type(tenant_context.tenant_id) is not str or not tenant_context.tenant_id:
        return MemoryReadResult("WRONG_TENANT", error="tenant context missing")          # never defaults to a global tenant
    if tenant != tenant_context.tenant_id:
        return MemoryReadResult("WRONG_TENANT", record_id=rid, error=f"reference names tenant {tenant!r}, context is {tenant_context.tenant_id!r}")
    path = tenant_store_path(Path(root), tenant)
    if not path.is_dir():
        return MemoryReadResult("UNAVAILABLE", record_id=rid, tenant_id=tenant, error="tenant store not present")
    try:
        store = MemoryStore(path)
    except ValueError as e:
        return MemoryReadResult("CORRUPT", record_id=rid, tenant_id=tenant, error=f"memory log: {e}")
    except OSError as e:
        return MemoryReadResult("UNAVAILABLE", record_id=rid, tenant_id=tenant, error=f"{type(e).__name__}: {e}")
    record = store.fetch(rid)
    if record is None:
        return MemoryReadResult("NOT_FOUND", record_id=rid, tenant_id=tenant, error="no such record")
    return read_record(record, tenant)


def read_record(record: MemoryRecord, tenant: str) -> MemoryReadResult:
    base = dict(record_id=record.id, tenant_id=tenant, schema_version=record.schema_version, created_at=record.created_at, updated_at=record.created_at,
                record_hash=sha256(record.content.encode()).hexdigest(),
                provenance={"ref": record.source.ref, "source_kind": record.source.source_kind, "content_digest": record.source.content_digest,
                            "authority_class": record.authority.authority_class}, admissible_uses=tuple(record.authority.admissible_uses))
    if record.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        return MemoryReadResult("UNSUPPORTED_VERSION", error=f"schema_version {record.schema_version!r}", **base)
    if record.revoked or record.source.ref == "memory.jsonl:corrupt-tail":
        return MemoryReadResult("INVALID" if record.revoked else "CORRUPT", error="revoked record" if record.revoked else "recovered corrupt tail", **base)
    if base["record_hash"] != record.source.content_digest:
        return MemoryReadResult("CORRUPT", error="content digest mismatch", **base)
    try:
        doc = strict_loads(record.content)
    except (ValueError, TypeError) as e:
        return MemoryReadResult("INVALID", error=f"content: {e}", **base)
    if type(doc) is not dict or doc.get("schema") != NOTE_SCHEMA:
        return MemoryReadResult("INVALID", error="not an authority note", **base)
    ref = doc.get("grant_ref")
    refs = (ref,) if type(ref) is str and ref else ()
    contract, err = contract_from(doc.get("scope")) if doc.get("scope") is not None else (None, None)
    if err is not None:
        return MemoryReadResult("INVALID", error=err, **base)
    declared = (contract.externality, contract.reversibility) if contract is not None else (None, None)
    claim = ProvenanceClaim("memory://" + record.id, "memory", base["record_hash"])
    return MemoryReadResult("RESOLVED", content=record.content, declared_effect=declared, claimed_scope=contract,
                            binding_digest=scope_digest(contract) if contract is not None else None, refs=refs, claims=(claim,), **base)


@dataclass
class ProductionMemoryReader:
    """The bridge's `MemoryReader`: one tenant-partitioned root."""
    root: Path

    def read(self, memory_ref: str, tenant: TenantContext, principal: PrincipalContext) -> MemoryReadOutcome:
        r = read_memory(memory_ref, tenant, principal, root=self.root)
        return MemoryReadOutcome(r.status, r.evidence() if r.status == "RESOLVED" else None, r.error)
