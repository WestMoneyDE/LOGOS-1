from __future__ import annotations

from dataclasses import dataclass

from .records import MemoryRecord


@dataclass(frozen=True)
class ConsolidationProposal:
    source_ids: tuple[str, ...]
    content: str
    output_id: str
    kind: str
    requested_status: str
    requested_visibility: tuple[str, ...]
    requested_uses: tuple[str, ...]


@dataclass(frozen=True)
class ConsolidationVerdict:
    accepted: bool
    reasons: tuple[str, ...]
    record: MemoryRecord | None = None


def validate_local_transition(
    proposal: ConsolidationProposal, sources: tuple[MemoryRecord, ...]
) -> tuple[str, ...]:
    return (
        ()
        if sources
        and len(sources) == len(proposal.source_ids)
        and all(source.id in proposal.source_ids for source in sources)
        else ("local transition",)
    )


def validate_global_coherence(
    proposal: ConsolidationProposal, sources: tuple[MemoryRecord, ...]
) -> tuple[str, ...]:
    if proposal.requested_status == "verified" and not all(
        source.epistemic_status == "verified" for source in sources
    ):
        return ("global evidence coherence",)
    return ()


def validate_authority_preservation(
    proposal: ConsolidationProposal, sources: tuple[MemoryRecord, ...]
) -> tuple[str, ...]:
    if not sources:
        return ("authority preservation",)
    allowed_visibility = set.intersection(*(set(source.visibility) for source in sources))
    allowed_uses = set.intersection(
        *(set(source.authority.admissible_uses) for source in sources)
    )
    if not set(proposal.requested_visibility) <= allowed_visibility:
        return ("authority preservation",)
    if not set(proposal.requested_uses) <= allowed_uses:
        return ("authority preservation",)
    return ()
