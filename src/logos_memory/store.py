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
                _validate_authority(record)
            except (json.JSONDecodeError, KeyError, TypeError, MemoryAuthorityError) as error:
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
        _validate_authority(record)
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
