"""Hash-freeze utilities for RULER JSONL generated before model execution."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_sha256(obj: Any) -> str:
    data = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class DatasetFreezeManifest:
    schema: str
    file: str
    file_sha256: str
    row_count: int
    row_canonical_sha256: tuple[str, ...]
    source_repo: str
    source_commit: str
    task: str
    seed: int
    max_seq_length: int
    num_samples: int
    tokenizer_repo: str
    tokenizer_revision: str
    exact_command: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def freeze_jsonl(
    path: str | Path,
    *,
    source_repo: str,
    source_commit: str,
    task: str,
    seed: int,
    max_seq_length: int,
    num_samples: int,
    tokenizer_repo: str,
    tokenizer_revision: str,
    exact_command: str,
) -> DatasetFreezeManifest:
    path = Path(path)
    raw = path.read_bytes()
    rows: list[Any] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL row {lineno}: {exc}") from exc
    if len(rows) != num_samples:
        raise ValueError(f"expected {num_samples} rows, found {len(rows)}")
    return DatasetFreezeManifest(
        schema="logos-ruler-dataset-freeze-v1",
        file=path.name,
        file_sha256=hashlib.sha256(raw).hexdigest(),
        row_count=len(rows),
        row_canonical_sha256=tuple(canonical_json_sha256(r) for r in rows),
        source_repo=source_repo,
        source_commit=source_commit,
        task=task,
        seed=int(seed),
        max_seq_length=int(max_seq_length),
        num_samples=int(num_samples),
        tokenizer_repo=tokenizer_repo,
        tokenizer_revision=tokenizer_revision,
        exact_command=exact_command,
    )
