# LOGOS-1 Memory Factory and Scope Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement deterministic, research-only Memory Factory and Scope Engine primitives without changing LOGOS-1's active scientific queue or authority boundary.

**Architecture:** Add a dependency-light `logos_memory` Python package beside the existing persistent-state adapters. The package owns typed records, JSONL persistence, scope intersection, consolidation checks, scoped retrieval and minimum-context projections; assurance remains an external interface with no Memory Factory write path.

**Tech Stack:** Python 3.11+, standard library dataclasses/JSON/hashlib/pathlib, pytest, existing setuptools configuration.

## Global Constraints

- `AdaptiveState != Authority`
- `AgentMemory != AssuranceState`
- `RememberedContent != ExecutionAuthority`
- `ScopeProposal != EffectiveScope`
- `OUTCOME_UNKNOWN != NOT_EXECUTED`
- `RetrievalScore != EvidenceStrength`
- Active work order `READY_PERSISTENT_STATE_DATASET_MATERIALIZATION_R4` remains unchanged.
- No network, shell, browser, financial, messaging or deployment connector is added.
- No scientific Γ, memory-mechanism or consciousness verdict is promoted.
- No SIP application code, patent text or SIP-specific workflow is added.

---

## File map

- `src/logos_memory/scope.py` — typed scope contracts, intersection, decisions and digest.
- `src/logos_memory/records.py` — memory/provenance/consolidation/projection dataclasses.
- `src/logos_memory/store.py` — append-only JSONL memory store and authority firewall.
- `src/logos_memory/consolidation.py` — local, global and authority-preservation checks.
- `src/logos_memory/retrieval.py` — scope-first deterministic BM25 retrieval.
- `src/logos_memory/factory.py` — ingest, consolidate, derive procedure, revoke and project orchestration.
- `src/logos_memory/__init__.py` — explicit public interface.
- `tests/test_scope_engine.py`, `tests/test_memory_store.py`, `tests/test_memory_factory.py`, `tests/test_memory_recovery.py` — negative and recovery contracts.
- `docs/architecture/MEMORY-SYSTEM.md`, `docs/architecture/SCOPE-ENGINE.md` — implementation-aligned architecture.
- `05-WORK-ORDERS/ENGINEERING-MEMORY-SYSTEM-CODING-AGENTS-R1.md`, `CAPABILITIES.md`, `AGENTS.md`, `CLAUDE.md` — propagation.
- `09-SESSIONS/2026-08-21-MEMORY-FACTORY-SCOPE-ENGINE-R1/SESSION-REPORT.md` — durable checkpoint.

### Task 1: Define and test deterministic scope intersection

**Files:**
- Create: `src/logos_memory/__init__.py`
- Create: `src/logos_memory/scope.py`
- Create: `tests/test_scope_engine.py`

**Interfaces:**
- Produces: `ScopeContract`, `ScopeRequest`, `ScopeDecision`, `ScopeViolation`, `intersect_contracts()` and `scope_digest()`.
- Consumes: standard-library values only.

- [ ] **Step 1: Write the failing scope tests**

Create `tests/test_scope_engine.py`:

```python
from dataclasses import replace

from logos_memory.scope import ScopeContract, ScopeRequest, intersect_contracts


def contract(**overrides):
    base = ScopeContract(
        project="logos-1",
        paths=("src/**", "tests/**"),
        excluded_paths=(".state/assurance/**",),
        roles=("builder", "reviewer"),
        tools=("read", "edit", "pytest"),
        memory_kinds=("episodic", "semantic", "procedural"),
        projection_audiences=("project",),
        capabilities=("local-edit", "local-test"),
        targets=("repository",),
        parameter_bounds=(("changed_files", 0.0, 20.0),),
        max_cost_usd=0.0,
        max_tokens=100_000,
        max_seconds=3_600,
        max_attempts=3,
        valid_from="2026-08-21T00:00:00+00:00",
        valid_until="2026-08-22T00:00:00+00:00",
        max_occurrences=1,
        externality="internal",
        reversibility="reversible",
        approval_required=False,
        data_classes=("public", "project"),
        retention_classes=("session", "project"),
        source_versions=("project-policy@1",),
    )
    return replace(base, **overrides)


def test_intersection_can_only_narrow_scope():
    project = contract()
    work_order = contract(
        paths=("src/logos_memory/**", "tests/test_memory_*.py"),
        roles=("builder",),
        tools=("read", "edit", "pytest", "network"),
        max_attempts=2,
        source_versions=("work-order@1",),
    )
    decision = intersect_contracts([project, work_order])
    assert decision.verdict == "NARROW"
    assert decision.effective.roles == ("builder",)
    assert decision.effective.tools == ("edit", "pytest", "read")
    assert "network" not in decision.effective.tools
    assert decision.effective.max_attempts == 2
    assert len(decision.digest) == 64


def test_project_mismatch_denies():
    decision = intersect_contracts([contract(), contract(project="other")])
    assert decision.verdict == "DENY"
    assert "project mismatch" in decision.reasons[0]


def test_empty_high_impact_dimension_denies():
    decision = intersect_contracts([contract(), contract(capabilities=("network-write",))])
    assert decision.verdict == "DENY"
    assert "capabilities" in decision.unresolved_dimensions


def test_request_cannot_widen_effective_scope():
    decision = intersect_contracts([contract()])
    request = ScopeRequest(
        role="builder", tool="network", memory_kind="semantic",
        capability="network-write", target="internet", path="src/x.py",
    )
    checked = decision.evaluate(request)
    assert checked.verdict == "DENY"
```

- [ ] **Step 2: Run the test and verify RED**

```powershell
pytest tests/test_scope_engine.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'logos_memory'`.

- [ ] **Step 3: Implement the scope types and restrictive intersection**

Create `src/logos_memory/scope.py` with these public types and rules:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
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


def intersect_contracts(contracts: list[ScopeContract]) -> ScopeDecision:
    if not contracts:
        return ScopeDecision("DEFER", None, scope_digest(None), ("no scope contracts",), ("all",))
    if len({c.project for c in contracts}) != 1:
        return ScopeDecision("DENY", None, scope_digest(None), ("project mismatch",), ("project",))
    set_fields = (
        "paths", "roles", "tools", "memory_kinds", "projection_audiences",
        "capabilities", "targets", "data_classes", "retention_classes",
    )
    merged = {field: _intersection(contracts, field) for field in set_fields}
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
```

Create `src/logos_memory/__init__.py`:

```python
from .scope import ScopeContract, ScopeDecision, ScopeRequest, ScopeViolation, intersect_contracts, scope_digest

__all__ = ["ScopeContract", "ScopeDecision", "ScopeRequest", "ScopeViolation", "intersect_contracts", "scope_digest"]
```

- [ ] **Step 4: Run the scope tests and verify GREEN**

```powershell
pytest tests/test_scope_engine.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```powershell
git add -- src/logos_memory/__init__.py src/logos_memory/scope.py tests/test_scope_engine.py
git commit -m "feat: add restrictive scope engine"
```

### Task 2: Add typed memory records and append-only storage

**Files:**
- Create: `src/logos_memory/records.py`
- Create: `src/logos_memory/store.py`
- Create: `tests/test_memory_store.py`
- Modify: `src/logos_memory/__init__.py`

**Interfaces:**
- Consumes: `ScopeContract` visibility and retention values.
- Produces: `MemoryRecord`, `ProvenanceRef`, `AuthorityProvenance`, `MemoryStore`, `MemoryAuthorityError`.

- [ ] **Step 1: Write failing authority-firewall and persistence tests**

Create `tests/test_memory_store.py`:

```python
from pathlib import Path
import pytest

from logos_memory.records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from logos_memory.store import MemoryAuthorityError, MemoryStore


def record(kind="episodic", **overrides):
    values = dict(
        id="mem-1", kind=kind, created_at="2026-08-21T00:00:00+00:00",
        content="provider failure remained WAIT", source=ProvenanceRef("session-1", "repository", "sha256:a"),
        authority=AuthorityProvenance("observation", ("inform-proposal",)),
        epistemic_status="observed", schema_version=1, derived_from=(), supersedes=None,
        conflicts_with=(), visibility=("project",), retention="project", revoked=False,
    )
    values.update(overrides)
    return MemoryRecord(**values)


def test_memory_store_round_trips_provenance(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record())
    recovered = MemoryStore(tmp_path).fetch("mem-1")
    assert recovered.source.ref == "session-1"
    assert recovered.authority.admissible_uses == ("inform-proposal",)


@pytest.mark.parametrize("kind", ["grant", "credential", "scope", "approval", "execution-token", "policy-exception", "assurance"])
def test_memory_cannot_mint_assurance(kind: str, tmp_path: Path):
    with pytest.raises(MemoryAuthorityError):
        MemoryStore(tmp_path).append(record(kind=kind))


def test_memory_rejects_execution_use(tmp_path: Path):
    rec = record(authority=AuthorityProvenance("user-authorization", ("execute-external-action",)))
    with pytest.raises(MemoryAuthorityError):
        MemoryStore(tmp_path).append(rec)
```

- [ ] **Step 2: Run and verify RED**

```powershell
pytest tests/test_memory_store.py -q
```

Expected: collection fails because `logos_memory.records` and `logos_memory.store` do not exist.

- [ ] **Step 3: Implement exact immutable record types**

Create `src/logos_memory/records.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Literal

MemoryKind = Literal["working", "episodic", "semantic", "procedural", "evidence"]


@dataclass(frozen=True)
class ProvenanceRef:
    ref: str
    source_kind: str
    content_digest: str


@dataclass(frozen=True)
class AuthorityProvenance:
    authority_class: str
    admissible_uses: tuple[str, ...]


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    kind: str
    created_at: str
    content: str
    source: ProvenanceRef
    authority: AuthorityProvenance
    epistemic_status: str
    schema_version: int
    derived_from: tuple[str, ...]
    supersedes: str | None
    conflicts_with: tuple[str, ...]
    visibility: tuple[str, ...]
    retention: str
    revoked: bool

    def tombstone(self) -> MemoryRecord:
        return replace(self, content="[deleted]")
```

Create `src/logos_memory/store.py` with JSONL encoding/decoding using `dataclasses.asdict()`, atomic tail recovery and these invariants:

```python
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path

from .records import AuthorityProvenance, MemoryRecord, ProvenanceRef

ASSURANCE_KINDS = frozenset({"grant", "credential", "scope", "approval", "approval-token", "execution-token", "policy-exception", "assurance"})
MEMORY_KINDS = frozenset({"working", "episodic", "semantic", "procedural", "evidence"})
FORBIDDEN_USES = frozenset({"execute-external-action", "grant-permission", "approve", "mint-token"})

class MemoryAuthorityError(ValueError):
    pass


def _decode(payload: dict) -> MemoryRecord:
    return MemoryRecord(
        **{
            **payload,
            "source": ProvenanceRef(**payload["source"]),
            "authority": AuthorityProvenance(**payload["authority"]),
            "derived_from": tuple(payload["derived_from"]),
            "conflicts_with": tuple(payload["conflicts_with"]),
            "visibility": tuple(payload["visibility"]),
        }
    )


class MemoryStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "memory.jsonl"
        self.quarantine_path = directory / "memory.quarantine.jsonl"
        self.path.touch(exist_ok=True)
        self._records: dict[str, MemoryRecord] = {}
        self._order: list[str] = []
        self._load()

    def _load(self) -> None:
        lines = self.path.read_text(encoding="utf-8").splitlines(keepends=True)
        for index, line in enumerate(lines):
            try:
                record = _decode(json.loads(line))
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                if index != len(lines) - 1:
                    raise ValueError(f"memory log corruption at line {index + 1}") from error
                self.quarantine_path.write_text(line, encoding="utf-8")
                valid = "".join(lines[:index])
                temporary = self.path.with_suffix(".jsonl.tmp")
                temporary.write_text(valid, encoding="utf-8")
                temporary.replace(self.path)
                break
            if record.id not in self._records:
                self._order.append(record.id)
            self._records[record.id] = record

    def append(self, record: MemoryRecord) -> MemoryRecord:
        if record.kind in ASSURANCE_KINDS or record.kind not in MEMORY_KINDS:
            raise MemoryAuthorityError(f"memory kind is not admissible: {record.kind}")
        forbidden = FORBIDDEN_USES.intersection(record.authority.admissible_uses)
        if forbidden:
            raise MemoryAuthorityError(f"memory cannot carry authority uses: {sorted(forbidden)}")
        encoded = json.dumps(asdict(record), sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded + "\n")
        if record.id not in self._records:
            self._order.append(record.id)
        self._records[record.id] = record
        return record

    def fetch(self, record_id: str) -> MemoryRecord | None:
        return self._records.get(record_id)

    def all(self) -> tuple[MemoryRecord, ...]:
        return tuple(self._records[record_id] for record_id in self._order)

    def supersede(self, old_id: str, replacement: MemoryRecord) -> MemoryRecord:
        if old_id not in self._records:
            raise KeyError(old_id)
        return self.append(replace(replacement, supersedes=old_id))

    def record_conflict(self, left_id: str, right_id: str) -> tuple[MemoryRecord, MemoryRecord]:
        left, right = self._records[left_id], self._records[right_id]
        left = replace(left, conflicts_with=tuple(sorted(set(left.conflicts_with) | {right_id})))
        right = replace(right, conflicts_with=tuple(sorted(set(right.conflicts_with) | {left_id})))
        return self.append(left), self.append(right)

    def delete_content(self, record_id: str) -> MemoryRecord:
        record = self._records[record_id]
        return self.append(record.tombstone())
```

The full implementation must reject assurance kinds before writing, reject every forbidden admissible use, append one canonical JSON object per line, rebuild the latest record by ID on load and quarantine only a corrupt final line to `memory.quarantine.jsonl`. Mid-log corruption raises `ValueError`.

- [ ] **Step 4: Export the public types and verify GREEN**

Add imports to `src/logos_memory/__init__.py`, then run:

```powershell
pytest tests/test_memory_store.py -q
```

Expected: `9 passed`.

- [ ] **Step 5: Commit**

```powershell
git add -- src/logos_memory/__init__.py src/logos_memory/records.py src/logos_memory/store.py tests/test_memory_store.py
git commit -m "feat: add provenance-aware memory store"
```

### Task 3: Implement three-gate consolidation and revocation

**Files:**
- Create: `src/logos_memory/consolidation.py`
- Create: `src/logos_memory/factory.py`
- Create: `tests/test_memory_factory.py`
- Modify: `src/logos_memory/__init__.py`

**Interfaces:**
- Consumes: `MemoryStore`, `MemoryRecord`.
- Produces: `ConsolidationProposal`, `ConsolidationVerdict`, `MemoryFactory.consolidate()`, `.derive_procedure()`, `.revoke_authority()`.

- [ ] **Step 1: Write failing consolidation tests**

Create tests for these exact behaviors in `tests/test_memory_factory.py`:

```python
def test_consolidation_preserves_conflict_and_weakest_authority(factory):
    result = factory.consolidate(("a", "b"), "supplier rule", output_id="summary")
    assert result.accepted is True
    assert result.record.conflicts_with == ("counter",)
    assert result.record.authority.authority_class == "observation"
    assert result.record.authority.admissible_uses == ("inform-proposal",)

def test_consolidation_cannot_convert_unknown_to_verified(factory):
    result = factory.consolidate(("unknown",), "certain fact", output_id="bad", requested_status="verified")
    assert result.accepted is False
    assert "global evidence coherence" in result.reasons

def test_consolidation_cannot_widen_visibility_or_uses(factory):
    result = factory.consolidate(("private", "project"), "wide", output_id="bad", requested_visibility=("public",))
    assert result.accepted is False
    assert "authority preservation" in result.reasons

def test_revocation_propagates_but_deletion_does_not(factory):
    procedure = factory.derive_procedure(("source",), "proc", ("run test",))
    factory.store.delete_content("source")
    assert factory.store.fetch(procedure.id).revoked is False
    assert procedure.id in factory.revoke_authority("source", "source authority withdrawn")
    assert factory.store.fetch(procedure.id).revoked is True
```

- [ ] **Step 2: Run and verify RED**

```powershell
pytest tests/test_memory_factory.py -q
```

Expected: import or attribute failures because consolidation/factory types are absent.

- [ ] **Step 3: Implement the three validators**

Create `src/logos_memory/consolidation.py` with frozen `ConsolidationProposal` and `ConsolidationVerdict`. Implement:

```python
def validate_local_transition(proposal, sources):
    return () if sources and all(source.id in proposal.source_ids for source in sources) else ("local transition",)

def validate_global_coherence(proposal, sources):
    if proposal.requested_status == "verified" and not all(s.epistemic_status == "verified" for s in sources):
        return ("global evidence coherence",)
    return ()

def validate_authority_preservation(proposal, sources):
    allowed_visibility = set.intersection(*(set(s.visibility) for s in sources))
    allowed_uses = set.intersection(*(set(s.authority.admissible_uses) for s in sources))
    if not set(proposal.requested_visibility) <= allowed_visibility:
        return ("authority preservation",)
    if not set(proposal.requested_uses) <= allowed_uses:
        return ("authority preservation",)
    return ()
```

`MemoryFactory.consolidate()` runs all three validators before append. It derives epistemic status conservatively (`contradicted` dominates, `verified` only when all are verified, otherwise `hypothesis`), unions unresolved conflicts, intersects visibility/uses and selects the weakest authority class from a constant order.

`derive_procedure()` calls `consolidate(kind="procedural")` and stores the explicit steps. `revoke_authority()` traverses `derived_from` transitively and appends revoked replacements; it does not call content deletion.

- [ ] **Step 4: Run and verify GREEN**

```powershell
pytest tests/test_memory_factory.py -q
```

Expected: all new tests pass.

- [ ] **Step 5: Commit**

```powershell
git add -- src/logos_memory/__init__.py src/logos_memory/consolidation.py src/logos_memory/factory.py tests/test_memory_factory.py
git commit -m "feat: add guarded memory consolidation"
```

### Task 4: Add scope-first retrieval and minimum-context projections

**Files:**
- Create: `src/logos_memory/retrieval.py`
- Modify: `src/logos_memory/factory.py`
- Modify: `tests/test_memory_factory.py`

**Interfaces:**
- Consumes: `ScopeDecision`, `MemoryStore.all()`.
- Produces: `RetrievalRecord`, `ProjectionRecord`, `MemoryFactory.retrieve()` and `.project()`.

- [ ] **Step 1: Add failing tests**

```python
def test_retrieval_filters_visibility_before_ranking(factory, project_scope):
    result = factory.retrieve("supplier", project_scope, limit=5)
    assert [item.id for item in result.items] == ["project-record"]
    assert "private-record" in result.excluded_ids
    assert len(result.context_digest) == 64

def test_projection_is_minimum_context_and_has_expiry(factory, project_scope):
    projection = factory.project(
        ids=("project-record",), purpose="review", audience="project",
        valid_until="2026-08-22T00:00:00+00:00", scope=project_scope,
    )
    assert projection.source_ids == ("project-record",)
    assert projection.audience == "project"
    assert "private" not in projection.content.lower()
    assert len(projection.digest) == 64
```

- [ ] **Step 2: Run and verify RED**

```powershell
pytest tests/test_memory_factory.py -q
```

Expected: `MemoryFactory` lacks `retrieve` and `project`.

- [ ] **Step 3: Implement deterministic BM25 after scope filtering**

Create `src/logos_memory/retrieval.py` using the existing LOGOS BM25 constants `k1=1.5`, `b=0.75`, stable ID ties and SHA-256 digests. Define:

```python
@dataclass(frozen=True)
class RetrievalItem:
    id: str
    score: float
    content_digest: str
    epistemic_status: str
    conflicts_with: tuple[str, ...]

@dataclass(frozen=True)
class RetrievalRecord:
    query_digest: str
    candidate_ids: tuple[str, ...]
    excluded_ids: tuple[str, ...]
    items: tuple[RetrievalItem, ...]
    scope_digest: str
    context_digest: str
```

`MemoryFactory.retrieve()` first excludes records whose visibility has no intersection with `scope.effective.projection_audiences`, then ranks. `project()` accepts only selected records within scope and stores purpose, audience, validity, sources, content and digest in a frozen `ProjectionRecord`. Neither method accepts or returns an assurance record.

- [ ] **Step 4: Run and verify GREEN**

```powershell
pytest tests/test_memory_factory.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add -- src/logos_memory/retrieval.py src/logos_memory/factory.py tests/test_memory_factory.py
git commit -m "feat: add scoped retrieval and projections"
```

### Task 5: Prove recovery and scientific-queue non-interference

**Files:**
- Create: `tests/test_memory_recovery.py`
- Modify: `src/logos_memory/store.py`

**Interfaces:**
- Consumes: persisted JSONL and canonical scope inputs.
- Produces: deterministic recovery evidence and corruption semantics.

- [ ] **Step 1: Write failing recovery tests**

Create `tests/test_memory_recovery.py` with the following tests, reusing the `record` helper from `tests/test_memory_store.py` and the `factory`/`project_scope` fixtures from `tests/test_memory_factory.py`:

```python
from pathlib import Path

import pytest

from logos_memory.store import MemoryStore
from test_memory_store import record


def test_reopen_preserves_record_order(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record(id="one"))
    store.append(record(id="two"))
    assert tuple(item.id for item in MemoryStore(tmp_path).all()) == ("one", "two")


def test_corrupt_tail_is_quarantined(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record())
    with store.path.open("a", encoding="utf-8") as handle:
        handle.write('{"truncated":')
    recovered = MemoryStore(tmp_path)
    assert recovered.fetch("mem-1") is not None
    assert recovered.quarantine_path.read_text(encoding="utf-8") == '{"truncated":'


def test_corrupt_middle_line_raises(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record(id="one"))
    store.append(record(id="two"))
    lines = store.path.read_text(encoding="utf-8").splitlines()
    store.path.write_text(lines[0] + "\n{" + "\n" + lines[1] + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        MemoryStore(tmp_path)


def test_serialized_memory_has_no_assurance_fields(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record())
    serialized = store.path.read_text(encoding="utf-8")
    for forbidden in ('"grant"', '"credential"', '"occurrence_token"', '"policy_exception"'):
        assert forbidden not in serialized


def test_replay_preserves_scope_and_projection_digests(factory, project_scope):
    before = factory.project(
        ids=("project-record",), purpose="review", audience="project",
        valid_until="2026-08-22T00:00:00+00:00", scope=project_scope,
    )
    replayed = type(factory)(MemoryStore(factory.store.path.parent))
    after = replayed.project(
        ids=("project-record",), purpose="review", audience="project",
        valid_until="2026-08-22T00:00:00+00:00", scope=project_scope,
    )
    assert after.scope_digest == before.scope_digest
    assert after.digest == before.digest
```

- [ ] **Step 2: Run and verify RED**

```powershell
pytest tests/test_memory_recovery.py -q
```

Expected: at least the tail-recovery assertion fails before recovery logic is complete.

- [ ] **Step 3: Complete tail quarantine and deterministic replay**

Implement atomic rewrite through `memory.jsonl.tmp` followed by `Path.replace()`. Preserve valid lines byte-for-byte, write the corrupt tail to `memory.quarantine.jsonl`, then append a normal episodic recovery record with authority class `none` and no admissible uses.

- [ ] **Step 4: Run targeted and existing tests**

```powershell
pytest tests/test_memory_recovery.py tests/test_memory_store.py tests/test_memory_factory.py tests/test_scope_engine.py -q
pytest -q
python -m compileall -q src
```

Expected: all commands pass; existing persistent-state adapter tests remain green.

- [ ] **Step 5: Commit**

```powershell
git add -- src/logos_memory/store.py tests/test_memory_recovery.py
git commit -m "test: prove memory and scope recovery"
```

### Task 6: Propagate architecture, work order, capabilities and session evidence

**Files:**
- Modify: `docs/architecture/MEMORY-SYSTEM.md`
- Create: `docs/architecture/SCOPE-ENGINE.md`
- Modify: `05-WORK-ORDERS/ENGINEERING-MEMORY-SYSTEM-CODING-AGENTS-R1.md`
- Modify: `CAPABILITIES.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Create: `09-SESSIONS/2026-08-21-MEMORY-FACTORY-SCOPE-ENGINE-R1/SESSION-REPORT.md`

**Interfaces:**
- Consumes: implemented types and fresh test evidence.
- Produces: durable, internally consistent engineering state without scientific promotion.

- [ ] **Step 1: Update architecture docs with exact implemented interfaces**

Document `MemoryFactory`, `MemoryStore`, `ScopeContract`, `ScopeDecision`, consolidation gates, scoped retrieval, projections, JSONL recovery and the separate assurance interface. Include these explicit non-claims:

```text
ImplementationPass != ScientificMechanismEvidence
MemoryFactory != AuthoritySource
ScopeDecision != ExternalApproval
PersistentState != PhenomenalConsciousness
```

- [ ] **Step 2: Update operating contracts and capability inventory**

Add the rule that agents must obtain a `ScopeDecision` before memory retrieval, consolidation, file/tool dispatch or effect proposal. Rate capabilities `IMPLEMENTED` only with the exact pytest files as evidence. Keep R4 as the canonical scientific gate and Γ-v0.3 as `HOLD`.

- [ ] **Step 3: Write the session checkpoint**

The session report must record objective, independent variable/mechanism toggles, dependent measures, negative controls, predicted results, disconfirming results, provenance, safety class, exact test output, scientific non-promotion, blockers and next action. State that no model benchmark, network action or SIP change occurred.

- [ ] **Step 4: Verify active work order preservation**

```powershell
git diff d3686ffb6616b2696405a61be9f97b187abf4be5 -- CURRENT-WORK-ORDER.md
```

Expected: no output.

- [ ] **Step 5: Run the full LOGOS push protocol gate**

```powershell
pytest -q
python -m compileall -q src
git diff --check origin/main...HEAD
git status --short --branch
```

Expected: tests and compile pass, diff check is clean, and only reviewed files are present before the documentation commit.

- [x] **Step 6: Commit propagation artifacts**

```powershell
git add -- docs/architecture/MEMORY-SYSTEM.md docs/architecture/SCOPE-ENGINE.md 05-WORK-ORDERS/ENGINEERING-MEMORY-SYSTEM-CODING-AGENTS-R1.md CAPABILITIES.md AGENTS.md CLAUDE.md 09-SESSIONS/2026-08-21-MEMORY-FACTORY-SCOPE-ENGINE-R1/SESSION-REPORT.md
git commit -m "docs: record memory factory and scope engine"
```

### Task 7: Final local delivery gate

**Files:**
- Modify: `docs/superpowers/plans/2026-08-21-memory-factory-scope-engine.md` only to check completed boxes during execution.

- [x] **Step 1: Re-run fresh verification**

```powershell
pytest -q
python -m compileall -q src
git diff --check origin/main...HEAD
git log --oneline --decorate origin/main..HEAD
git status --short --branch
```

Expected: zero failures, clean diff, expected commits only and clean working tree.

- [x] **Step 2: Prepare but do not execute the external push**

Record branch, commit list, test counts, active-work-order byte-preservation result and capability delta for the final coordinated one-shot multi-repository push gate.
