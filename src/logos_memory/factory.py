from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json

from .consolidation import (
    ConsolidationProposal,
    ConsolidationVerdict,
    validate_authority_preservation,
    validate_global_coherence,
    validate_local_transition,
)
from .records import AuthorityProvenance, MemoryRecord, ProvenanceRef
from .store import MemoryStore


AUTHORITY_CLASS_ORDER = (
    "unknown",
    "observation",
    "derived",
    "validated",
)


def _intersection(values: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    return tuple(sorted(set.intersection(*(set(value) for value in values))))


def _derived_status(sources: tuple[MemoryRecord, ...]) -> str:
    statuses = {source.epistemic_status for source in sources}
    if "contradicted" in statuses:
        return "contradicted"
    if statuses == {"verified"}:
        return "verified"
    return "hypothesis"


def _weakest_authority(sources: tuple[MemoryRecord, ...]) -> str:
    rank = {authority_class: index for index, authority_class in enumerate(AUTHORITY_CLASS_ORDER)}
    return min(
        (source.authority.authority_class for source in sources),
        key=lambda authority_class: (rank.get(authority_class, -1), authority_class),
    )


class MemoryFactory:
    def __init__(self, store: MemoryStore):
        self.store = store

    def consolidate(
        self,
        source_ids: tuple[str, ...],
        content: str,
        *,
        output_id: str,
        kind: str = "semantic",
        requested_status: str | None = None,
        requested_visibility: tuple[str, ...] | None = None,
        requested_uses: tuple[str, ...] | None = None,
    ) -> ConsolidationVerdict:
        sources = tuple(
            source for source_id in source_ids if (source := self.store.fetch(source_id)) is not None
        )
        derived_status = _derived_status(sources) if sources else "hypothesis"
        visibility = requested_visibility if requested_visibility is not None else (
            _intersection(tuple(source.visibility for source in sources)) if sources else ()
        )
        uses = requested_uses if requested_uses is not None else (
            _intersection(tuple(source.authority.admissible_uses for source in sources))
            if sources
            else ()
        )
        proposal = ConsolidationProposal(
            source_ids=source_ids,
            content=content,
            output_id=output_id,
            kind=kind,
            requested_status=requested_status or derived_status,
            requested_visibility=visibility,
            requested_uses=uses,
        )
        reasons = tuple(
            reason
            for validator in (
                validate_local_transition,
                validate_global_coherence,
                validate_authority_preservation,
            )
            for reason in validator(proposal, sources)
        )
        if reasons:
            return ConsolidationVerdict(False, tuple(dict.fromkeys(reasons)))

        lineage_payload = json.dumps(source_ids, separators=(",", ":")).encode("utf-8")
        record = MemoryRecord(
            id=output_id,
            kind=kind,
            created_at=datetime.now(timezone.utc).isoformat(),
            content=content,
            source=ProvenanceRef(
                ref="consolidation:" + ",".join(source_ids),
                source_kind="memory-consolidation",
                content_digest="sha256:" + sha256(lineage_payload).hexdigest(),
            ),
            authority=AuthorityProvenance(_weakest_authority(sources), uses),
            epistemic_status=proposal.requested_status,
            schema_version=max(source.schema_version for source in sources),
            derived_from=source_ids,
            supersedes=None,
            conflicts_with=tuple(
                sorted({conflict for source in sources for conflict in source.conflicts_with})
            ),
            visibility=visibility,
            retention=sources[0].retention,
            revoked=any(source.revoked for source in sources),
        )
        return ConsolidationVerdict(True, (), self.store.append(record))

    def derive_procedure(
        self, source_ids: tuple[str, ...], output_id: str, steps: tuple[str, ...]
    ) -> MemoryRecord:
        content = json.dumps({"steps": steps}, sort_keys=True, separators=(",", ":"))
        verdict = self.consolidate(source_ids, content, output_id=output_id, kind="procedural")
        if not verdict.accepted or verdict.record is None:
            raise ValueError(f"procedure derivation rejected: {verdict.reasons}")
        return verdict.record

    def revoke_authority(self, source_id: str, reason: str) -> tuple[str, ...]:
        if self.store.fetch(source_id) is None:
            raise KeyError(source_id)
        if not reason.strip():
            raise ValueError("revocation reason is required")

        revoked_ids: list[str] = []
        frontier = {source_id}
        visited: set[str] = set()
        while frontier:
            current = frontier.pop()
            if current in visited:
                continue
            visited.add(current)
            current_record = self.store.fetch(current)
            if current_record is not None and not current_record.revoked:
                self.store.append(replace(current_record, revoked=True))
                revoked_ids.append(current)
            frontier.update(
                record.id
                for record in self.store.all()
                if record.id not in visited
                and any(parent == current for parent in record.derived_from)
            )
        order = {record.id: index for index, record in enumerate(self.store.all())}
        return tuple(sorted(revoked_ids, key=order.__getitem__))
