from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path

from .records import AuthorityProvenance, MemoryRecord, ProvenanceRef

ASSURANCE_KINDS = frozenset({"grant", "credential", "scope", "approval", "approval-token", "execution-token", "policy-exception", "assurance"})
MEMORY_KINDS = frozenset({"working", "episodic", "semantic", "procedural", "evidence"})
FORBIDDEN_USES = frozenset({"execute-external-action", "grant-permission", "approve", "mint-token"})


class MemoryAuthorityError(ValueError):
    pass


def _validate_authority(record: MemoryRecord) -> None:
    if record.kind in ASSURANCE_KINDS or record.kind not in MEMORY_KINDS:
        raise MemoryAuthorityError(f"memory kind is not admissible: {record.kind}")
    forbidden = FORBIDDEN_USES.intersection(record.authority.admissible_uses)
    if forbidden:
        raise MemoryAuthorityError(f"memory cannot carry authority uses: {sorted(forbidden)}")


def _decode(payload: dict) -> MemoryRecord:
    return MemoryRecord(
        **{
            **payload,
            "source": ProvenanceRef(**payload["source"]),
            "authority": AuthorityProvenance(
                authority_class=payload["authority"]["authority_class"],
                admissible_uses=tuple(payload["authority"]["admissible_uses"]),
            ),
            "derived_from": tuple(payload["derived_from"]),
            "conflicts_with": tuple(payload["conflicts_with"]),
            "visibility": tuple(payload["visibility"]),
        }
    )


def _encode(record: MemoryRecord) -> bytes:
    return (json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _recovery_record(corrupt_tail: bytes, occurrence_index: int) -> MemoryRecord:
    digest = sha256(corrupt_tail).hexdigest()
    return MemoryRecord(
        id=f"memory-recovery-{occurrence_index:08d}-{digest}",
        kind="episodic",
        created_at="1970-01-01T00:00:00+00:00",
        content=f"Quarantined malformed final memory-log segment sha256:{digest}.",
        source=ProvenanceRef("memory.jsonl:corrupt-tail", "local-recovery", digest),
        authority=AuthorityProvenance("none", ()),
        epistemic_status="observed",
        schema_version=1,
        derived_from=(),
        supersedes=None,
        conflicts_with=(),
        visibility=("project",),
        retention="project",
        revoked=False,
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
        lines = self.path.read_bytes().splitlines(keepends=True)
        for index, line in enumerate(lines):
            try:
                record = _decode(json.loads(line.decode("utf-8")))
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
                if index != len(lines) - 1:
                    raise ValueError(f"memory log corruption at line {index + 1}") from error
                self.quarantine_path.write_bytes(line)
                occurrence_index = 1 + sum(
                    item.source.ref == "memory.jsonl:corrupt-tail"
                    for item in self._records.values()
                )
                recovery = _recovery_record(line, occurrence_index)
                _validate_authority(recovery)
                valid = b"".join(lines[:index])
                temporary = self.path.with_suffix(".jsonl.tmp")
                temporary.write_bytes(valid + _encode(recovery))
                temporary.replace(self.path)
                if recovery.id not in self._records:
                    self._order.append(recovery.id)
                self._records[recovery.id] = recovery
                break
            try:
                _validate_authority(record)
            except MemoryAuthorityError as error:
                raise ValueError(f"memory log corruption at line {index + 1}") from error
            if record.id not in self._records:
                self._order.append(record.id)
            self._records[record.id] = record

    def append(self, record: MemoryRecord) -> MemoryRecord:
        _validate_authority(record)
        with self.path.open("ab") as handle:
            handle.write(_encode(record))
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
