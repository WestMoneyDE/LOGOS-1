from hashlib import sha256
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from logos_memory.store import MemoryStore
from test_memory_factory import factory, project_scope
from test_memory_store import record


def test_reopen_preserves_record_order(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record(id="one"))
    store.append(record(id="two"))

    assert tuple(item.id for item in MemoryStore(tmp_path).all()) == ("one", "two")


def test_corrupt_tail_is_quarantined_and_log_is_atomically_repaired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    store = MemoryStore(tmp_path)
    store.append(record())
    valid_prefix = store.path.read_bytes()
    corrupt_tail = b'{"truncated":'
    with store.path.open("ab") as handle:
        handle.write(corrupt_tail)

    replacements = []
    original_replace = Path.replace

    def observed_replace(source: Path, target: Path):
        replacements.append((source.name, Path(target).name, store.path.read_bytes()))
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", observed_replace)
    recovered = MemoryStore(tmp_path)

    assert recovered.fetch("mem-1") is not None
    assert recovered.quarantine_path.read_bytes() == corrupt_tail
    assert replacements == [("memory.jsonl.tmp", "memory.jsonl", valid_prefix + corrupt_tail)]
    assert recovered.path.read_bytes().startswith(valid_prefix)
    assert corrupt_tail not in recovered.path.read_bytes()


def test_recovery_episode_is_deterministic_authority_none_memory(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record())
    corrupt_tail = b'{"truncated":'
    with store.path.open("ab") as handle:
        handle.write(corrupt_tail)

    recovered = MemoryStore(tmp_path)
    recovery = recovered.all()[-1]
    digest = sha256(corrupt_tail).hexdigest()

    assert recovery.id == f"memory-recovery-00000001-{digest}"
    assert recovery.kind == "episodic"
    assert recovery.authority.authority_class == "none"
    assert recovery.authority.admissible_uses == ()
    assert recovery.source.content_digest == digest

    first_bytes = recovered.path.read_bytes()
    assert MemoryStore(tmp_path).path.read_bytes() == first_bytes


def test_identical_corrupt_tails_create_distinct_stable_recovery_occurrences(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record())
    corrupt_tail = b'{"same":'

    with store.path.open("ab") as handle:
        handle.write(corrupt_tail)
    first = MemoryStore(tmp_path)
    with first.path.open("ab") as handle:
        handle.write(corrupt_tail)
    second = MemoryStore(tmp_path)

    recovery_ids = tuple(item.id for item in second.all() if item.id.startswith("memory-recovery-"))
    assert len(recovery_ids) == 2
    assert len(set(recovery_ids)) == 2
    reopened_ids = tuple(item.id for item in MemoryStore(tmp_path).all())
    assert tuple(item.id for item in second.all()) == reopened_ids
    serialized_ids = tuple(
        payload["id"]
        for payload in map(json.loads, second.path.read_text(encoding="utf-8").splitlines())
        if payload["id"].startswith("memory-recovery-")
    )
    assert serialized_ids == recovery_ids

    stable_ids = tuple(item.id for item in MemoryStore(tmp_path).all())
    assert stable_ids == tuple(item.id for item in second.all())


def test_different_corrupt_tails_create_distinct_recovery_occurrences(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record())
    with store.path.open("ab") as handle:
        handle.write(b'{"first":')
    first = MemoryStore(tmp_path)
    with first.path.open("ab") as handle:
        handle.write(b'{"second":')
    second = MemoryStore(tmp_path)

    recovery_ids = tuple(item.id for item in second.all() if item.id.startswith("memory-recovery-"))
    assert len(recovery_ids) == len(set(recovery_ids)) == 2


def test_corrupt_middle_line_raises_without_repair(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record(id="one"))
    store.append(record(id="two"))
    lines = store.path.read_text(encoding="utf-8").splitlines()
    corrupted = (lines[0] + "\n{" + "\n" + lines[1] + "\n").encode()
    store.path.write_bytes(corrupted)

    with pytest.raises(ValueError, match="line 2"):
        MemoryStore(tmp_path)

    assert store.path.read_bytes() == corrupted
    assert not store.quarantine_path.exists()


def test_authority_bearing_final_record_fails_closed_without_quarantine(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record())
    injected = record(id="injected", kind="grant")
    with store.path.open("ab") as handle:
        handle.write((json.dumps(asdict(injected)) + "\n").encode("utf-8"))
    original = store.path.read_bytes()

    with pytest.raises(ValueError, match="line 2"):
        MemoryStore(tmp_path)

    assert store.path.read_bytes() == original
    assert not store.quarantine_path.exists()


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
