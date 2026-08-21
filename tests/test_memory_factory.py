from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from logos_memory import (
    AuthorityProvenance,
    MemoryFactory,
    MemoryRecord,
    MemoryStore,
    ProvenanceRef,
    ScopeContract,
    ScopeDecision,
    intersect_contracts,
)


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
        record(
            "project-record",
            content="supplier obligation is disputed",
            epistemic_status="contradicted",
            conflicts_with=("counter-record",),
        ),
        record("private-record", content="supplier confidential confidential", visibility=("private",)),
        record("project-tie-a", content="supplier neutral"),
        record("project-tie-b", content="supplier neutral"),
    )
    for item in inputs:
        store.append(item)
    return MemoryFactory(store)


@pytest.fixture
def project_scope() -> ScopeDecision:
    contract = ScopeContract(
        project="logos-1",
        paths=("src/**", "tests/**"),
        excluded_paths=(".state/assurance/**",),
        roles=("builder",),
        tools=("read",),
        memory_kinds=("episodic", "semantic", "procedural"),
        projection_audiences=("project",),
        capabilities=("local-read",),
        targets=("repository",),
        parameter_bounds=(),
        max_cost_usd=0.0,
        max_tokens=10_000,
        max_seconds=3_600,
        max_attempts=1,
        valid_from="2026-08-21T00:00:00+00:00",
        valid_until="2026-08-23T00:00:00+00:00",
        max_occurrences=1,
        externality="internal",
        reversibility="reversible",
        approval_required=False,
        data_classes=("project",),
        retention_classes=("project",),
        source_versions=("project-policy@1",),
    )
    return intersect_contracts([contract])


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


@pytest.mark.parametrize(
    ("source_status", "requested_status"),
    (("contradicted", "hypothesis"), ("unknown", "hypothesis")),
)
def test_consolidation_rejects_less_conservative_epistemic_transition(
    factory, source_status, requested_status
):
    factory.store.append(record("epistemic", epistemic_status=source_status))

    result = factory.consolidate(
        ("epistemic",), "unsupported", output_id="bad-state", requested_status=requested_status
    )

    assert result.accepted is False
    assert "global evidence coherence" in result.reasons
    assert factory.store.fetch("bad-state") is None


def test_consolidation_rejects_invalid_epistemic_status(factory):
    result = factory.consolidate(
        ("source",), "invalid", output_id="bad-state", requested_status="certain"
    )

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


def test_consolidation_digest_changes_when_same_source_id_gets_new_version(factory):
    first = factory.consolidate(("source",), "first", output_id="summary-1").record
    factory.store.append(replace(factory.store.fetch("source"), content="changed source content"))

    second = factory.consolidate(("source",), "second", output_id="summary-2").record

    assert first.source.content_digest != second.source.content_digest
    assert first.derived_from == second.derived_from == ("source",)


def test_consolidation_digest_is_deterministic_across_source_order(factory):
    forward = factory.consolidate(("a", "b"), "forward", output_id="forward").record
    reverse = factory.consolidate(("b", "a"), "reverse", output_id="reverse").record

    assert forward.source.content_digest == reverse.source.content_digest
    assert forward.derived_from == ("a", "b")
    assert reverse.derived_from == ("b", "a")


def test_retrieval_filters_visibility_before_ranking(factory, project_scope):
    result = factory.retrieve("confidential", project_scope, limit=5)

    assert result.items == ()
    assert "private-record" in result.excluded_ids
    assert "private-record" not in result.candidate_ids
    assert len(result.context_digest) == 64


def test_retrieval_is_deterministic_with_stable_id_ties(factory, project_scope):
    first = factory.retrieve("neutral", project_scope, limit=5)
    second = factory.retrieve("neutral", project_scope, limit=5)

    assert [item.id for item in first.items[:2]] == ["project-tie-a", "project-tie-b"]
    assert first == second


@pytest.mark.parametrize("verdict", ["DENY", "DEFER"])
def test_retrieval_returns_no_content_for_denied_or_deferred_scope(factory, project_scope, verdict):
    scope = ScopeDecision(verdict, project_scope.effective, project_scope.digest, ("blocked",))

    result = factory.retrieve("supplier", scope, limit=5)

    assert result.candidate_ids == ()
    assert result.items == ()
    assert result.context_digest == sha256(b"[]").hexdigest()


@pytest.mark.parametrize(
    "scope,reason_dimension",
    [
        (ScopeDecision("ALLOW", None, "0" * 64), "effective"),
        (ScopeDecision("ALLOW", None, "bad-digest"), "effective"),
    ],
)
def test_retrieval_fails_closed_for_missing_allowed_effective_scope(
    factory, scope, reason_dimension
):
    result = factory.retrieve("supplier", scope, limit=5)

    assert result.candidate_ids == ()
    assert result.items == ()
    assert result.context_digest == sha256(b"[]").hexdigest()
    assert result.scope_unresolved_dimensions == (reason_dimension,)
    assert result.scope_reasons == ("allowed scope has no effective contract",)


def test_retrieval_fails_closed_for_effective_scope_digest_mismatch(factory, project_scope):
    scope = replace(project_scope, digest="0" * 64)

    result = factory.retrieve("supplier", scope, limit=5)

    assert result.candidate_ids == ()
    assert result.items == ()
    assert result.scope_unresolved_dimensions == ("digest",)
    assert result.scope_reasons == ("effective scope digest mismatch",)


def test_projection_is_minimum_context_and_has_expiry(factory, project_scope):
    projection = factory.project(
        ids=("project-record",),
        purpose="review",
        audience="project",
        valid_until="2026-08-22T00:00:00+00:00",
        scope=project_scope,
    )

    assert projection.source_ids == ("project-record",)
    assert projection.purpose == "review"
    assert projection.audience == "project"
    assert projection.valid_until == "2026-08-22T00:00:00+00:00"
    assert projection.scope_digest == project_scope.digest
    assert len(projection.source_digests) == 1
    assert "private-record" not in projection.content
    assert "contradicted" in projection.content
    assert "counter-record" in projection.content
    assert "authority" not in projection.content.lower()
    assert len(projection.digest) == 64


@pytest.mark.parametrize(
    ("ids", "audience", "valid_until"),
    [
        (("private-record",), "project", "2026-08-22T00:00:00+00:00"),
        (("project-record",), "private", "2026-08-22T00:00:00+00:00"),
        (("project-record",), "project", "2026-08-24T00:00:00+00:00"),
    ],
)
def test_projection_rejects_scope_or_expiry_widening(
    factory, project_scope, ids, audience, valid_until
):
    with pytest.raises(ValueError):
        factory.project(
            ids=ids,
            purpose="review",
            audience=audience,
            valid_until=valid_until,
            scope=project_scope,
        )


@pytest.mark.parametrize("verdict", ["DENY", "DEFER"])
def test_projection_rejects_denied_or_deferred_scope(factory, project_scope, verdict):
    scope = ScopeDecision(verdict, project_scope.effective, project_scope.digest, ("blocked",))

    with pytest.raises(ValueError):
        factory.project(
            ids=("project-record",),
            purpose="review",
            audience="project",
            valid_until="2026-08-22T00:00:00+00:00",
            scope=scope,
        )


@pytest.mark.parametrize(
    "scope,reason",
    [
        (ScopeDecision("ALLOW", None, "0" * 64), "allowed scope has no effective contract"),
        (None, "effective scope digest mismatch"),
    ],
)
def test_projection_fails_closed_for_inconsistent_allowed_scope(
    factory, project_scope, scope, reason
):
    scope = replace(project_scope, digest="0" * 64) if scope is None else scope

    with pytest.raises(ValueError, match=reason):
        factory.project(
            ids=("project-record",),
            purpose="review",
            audience="project",
            valid_until="2026-08-22T00:00:00+00:00",
            scope=scope,
        )
