from pathlib import Path

import pytest

from logos_memory import AuthorityProvenance, MemoryFactory, MemoryRecord, MemoryStore, ProvenanceRef


def record(record_id: str, **overrides) -> MemoryRecord:
    values = dict(
        id=record_id,
        kind="episodic",
        created_at="2026-08-21T00:00:00+00:00",
        content=record_id,
        source=ProvenanceRef(f"session:{record_id}", "repository", f"sha256:{record_id}"),
        authority=AuthorityProvenance("observation", ("inform-proposal",)),
        epistemic_status="verified",
        schema_version=1,
        derived_from=(),
        supersedes=None,
        conflicts_with=(),
        visibility=("project",),
        retention="project",
        revoked=False,
    )
    values.update(overrides)
    return MemoryRecord(**values)


@pytest.fixture
def factory(tmp_path: Path) -> MemoryFactory:
    store = MemoryStore(tmp_path)
    inputs = (
        record("a", conflicts_with=("counter",), visibility=("private", "project")),
        record(
            "b",
            authority=AuthorityProvenance("derived", ("inform-proposal", "summarize")),
            visibility=("project", "team"),
        ),
        record("unknown", epistemic_status="unknown"),
        record("private", visibility=("private", "project")),
        record("project", visibility=("project",)),
        record("source"),
    )
    for item in inputs:
        store.append(item)
    return MemoryFactory(store)


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
    assert factory.store.fetch(procedure.id).supersedes is None


def test_revocation_propagates_transitively(factory):
    procedure = factory.derive_procedure(("source",), "proc", ("run test",))
    descendant = factory.consolidate((procedure.id,), "derived guidance", output_id="descendant").record

    revoked = factory.revoke_authority("source", "source authority withdrawn")

    assert revoked == ("source", "proc", "descendant")
    assert factory.store.fetch(descendant.id).revoked is True


def test_missing_source_fails_local_transition_without_append(factory):
    result = factory.consolidate(("missing",), "unsupported", output_id="bad")

    assert result.accepted is False
    assert "local transition" in result.reasons
    assert factory.store.fetch("bad") is None


def test_explicit_empty_authority_intersection_stays_empty(factory):
    result = factory.consolidate(
        ("source",),
        "private summary",
        output_id="no-projection",
        requested_visibility=(),
        requested_uses=(),
    )

    assert result.record.visibility == ()
    assert result.record.authority.admissible_uses == ()


def test_revocation_traverses_an_already_revoked_intermediate(factory):
    procedure = factory.derive_procedure(("source",), "proc", ("run test",))
    factory.revoke_authority(procedure.id, "procedure withdrawn")
    descendant = record("descendant", derived_from=(procedure.id,))
    factory.store.append(descendant)

    factory.revoke_authority("source", "source authority withdrawn")

    assert factory.store.fetch(descendant.id).revoked is True
