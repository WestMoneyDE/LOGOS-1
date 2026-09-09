"""Audit emission boundary.

Γ may write validation/audit evidence **only** through the canonical audit owner.
Γ does not own storage, so this module defines the interface and a null default —
it deliberately contains no file, database or network write.

`AuditRecord` is content-addressed so an audit trail can be verified without
trusting the writer.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Protocol, runtime_checkable

from .types import GammaVerdict


@dataclass(frozen=True)
class AuditRecord:
    proposal_digest: str
    scope_digest: str
    state_hash: str
    tick: int
    result: str
    findings: tuple[tuple[str, str, str, str], ...]

    def digest(self) -> str:
        return sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@runtime_checkable
class AuditSink(Protocol):
    """Implemented by the canonical audit owner, never by Γ."""

    def emit(self, record: AuditRecord) -> None: ...


class NullAuditSink:
    """Default sink. Discards records; Γ still works without an audit owner."""

    def emit(self, record: AuditRecord) -> None:  # noqa: D102
        return None


class CollectingAuditSink:
    """In-memory sink for tests and dry runs.

    Mutable by design and therefore *outside* the trusted core: the kernel holds no
    reference to it beyond the call it was passed into.
    """

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def emit(self, record: AuditRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)


def build_record(
    verdict: GammaVerdict, proposal_digest: str, scope_digest: str, state_hash: str, tick: int
) -> AuditRecord:
    return AuditRecord(
        proposal_digest=proposal_digest,
        scope_digest=scope_digest,
        state_hash=state_hash,
        tick=tick,
        result=verdict.result,
        findings=tuple(
            (f.invariant_id, f.clause, f.result, f.reason) for f in verdict.findings
        ),
    )
