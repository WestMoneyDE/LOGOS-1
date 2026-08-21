from dataclasses import replace

import pytest

from logos_memory.scope import ScopeContract, ScopeRequest, intersect_contracts


def contract(**overrides):
    base = ScopeContract(
        project="logos-1",
        paths=("src/**", "tests/**"),
        excluded_paths=(".state/assurance/**",),
        roles=("builder", "reviewer"),
        tools=("read", "edit", "pytest"),
        memory_kinds=("episodic", "semantic", "procedural"),
        projection_audiences=("project",),
        capabilities=("local-edit", "local-test"),
        targets=("repository",),
        parameter_bounds=(("changed_files", 0.0, 20.0),),
        max_cost_usd=0.0,
        max_tokens=100_000,
        max_seconds=3_600,
        max_attempts=3,
        valid_from="2026-08-21T00:00:00+00:00",
        valid_until="2026-08-22T00:00:00+00:00",
        max_occurrences=1,
        externality="internal",
        reversibility="reversible",
        approval_required=False,
        data_classes=("public", "project"),
        retention_classes=("session", "project"),
        source_versions=("project-policy@1",),
    )
    return replace(base, **overrides)


def test_intersection_can_only_narrow_scope():
    project = contract()
    work_order = contract(
        paths=("src/logos_memory/**", "tests/test_memory_*.py"),
        roles=("builder",),
        tools=("read", "edit", "pytest", "network"),
        max_attempts=2,
        source_versions=("work-order@1",),
    )
    decision = intersect_contracts([project, work_order])
    assert decision.verdict == "NARROW"
    assert decision.effective.roles == ("builder",)
    assert decision.effective.tools == ("edit", "pytest", "read")
    assert "network" not in decision.effective.tools
    assert decision.effective.max_attempts == 2
    assert len(decision.digest) == 64


def test_project_mismatch_denies():
    decision = intersect_contracts([contract(), contract(project="other")])
    assert decision.verdict == "DENY"
    assert "project mismatch" in decision.reasons[0]


def test_empty_high_impact_dimension_denies():
    decision = intersect_contracts([contract(), contract(capabilities=("network-write",))])
    assert decision.verdict == "DENY"
    assert "capabilities" in decision.unresolved_dimensions


def test_request_cannot_widen_effective_scope():
    decision = intersect_contracts([contract()])
    request = ScopeRequest(
        role="builder", tool="network", memory_kind="semantic",
        capability="network-write", target="internet", path="src/x.py",
    )
    checked = decision.evaluate(request)
    assert checked.verdict == "DENY"


def test_request_path_within_includes_is_allowed():
    decision = intersect_contracts([contract()])
    request = ScopeRequest(
        role="builder", tool="edit", memory_kind="semantic",
        capability="local-edit", target="repository", path="src/logos_memory/scope.py",
    )
    assert decision.evaluate(request).verdict == "ALLOW"


@pytest.mark.parametrize(
    "path",
    [
        "docs/readme.md",
        ".state/assurance/grant.json",
        "src/../tests/test_scope_engine.py",
        "/workspace/src/scope.py",
        "C:/workspace/src/scope.py",
        "src\\logos_memory\\scope.py",
    ],
)
def test_request_path_outside_or_ambiguous_is_denied(path):
    decision = intersect_contracts([contract()])
    request = ScopeRequest(
        role="builder", tool="edit", memory_kind="semantic",
        capability="local-edit", target="repository", path=path,
    )
    assert decision.evaluate(request).verdict == "DENY"


def test_request_path_matching_exclusion_is_denied():
    decision = intersect_contracts([contract(paths=("**",), excluded_paths=(".state/assurance/**",))])
    request = ScopeRequest(
        role="builder", tool="edit", memory_kind="semantic",
        capability="local-edit", target="repository", path=".state/assurance/grant.json",
    )
    assert decision.evaluate(request).verdict == "DENY"


def test_recursive_glob_prefix_collision_denies():
    decision = intersect_contracts([
        contract(paths=("src/**",)),
        contract(paths=("src2/**",)),
    ])
    assert decision.verdict == "DENY"
    assert "paths" in decision.unresolved_dimensions


def test_missing_parameter_dimension_denies():
    decision = intersect_contracts([
        contract(),
        contract(parameter_bounds=()),
    ])
    assert decision.verdict == "DENY"
    assert "parameter_bounds" in decision.unresolved_dimensions


def test_empty_validity_window_denies():
    decision = intersect_contracts([
        contract(valid_from="2026-08-23T00:00:00+00:00"),
        contract(valid_until="2026-08-22T00:00:00+00:00"),
    ])
    assert decision.verdict == "DENY"
    assert "validity" in decision.unresolved_dimensions


def test_invalid_timestamp_denies():
    decision = intersect_contracts([contract(valid_from="not-a-timestamp")])
    assert decision.verdict == "DENY"
    assert "validity" in decision.unresolved_dimensions
