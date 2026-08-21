from pathlib import Path
from dataclasses import asdict
import json

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


def test_memory_store_quarantines_only_a_corrupt_final_line(tmp_path: Path):
    store = MemoryStore(tmp_path)
    store.append(record())
    with store.path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("{corrupt-tail\n")

    recovered = MemoryStore(tmp_path)

    assert recovered.fetch("mem-1") == record()
    assert recovered.quarantine_path.read_text(encoding="utf-8") == "{corrupt-tail\n"
    assert "{corrupt-tail" not in recovered.path.read_text(encoding="utf-8")


def test_memory_store_fails_on_an_unauthorized_mid_log_record(tmp_path: Path):
    path = tmp_path / "memory.jsonl"
    path.write_text(
        "\n".join((
            json.dumps(asdict(record())),
            json.dumps(asdict(record(kind="grant"))),
            json.dumps(asdict(record(id="mem-2"))),
        )) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="line 2"):
        MemoryStore(tmp_path)
