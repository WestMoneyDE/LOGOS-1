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
