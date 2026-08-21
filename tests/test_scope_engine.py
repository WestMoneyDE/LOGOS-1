from dataclasses import replace
import math

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


def test_malformed_include_is_not_discarded_when_valid_pattern_overlaps():
    decision = intersect_contracts([
        contract(paths=("src/**", "bad[")),
        contract(paths=("src/logos_memory/**",)),
    ])
    assert decision.verdict == "DENY"
    assert "paths" in decision.unresolved_dimensions


def test_malformed_exclude_is_not_discarded_when_valid_pattern_exists():
    decision = intersect_contracts([
        contract(excluded_paths=(".state/assurance/**", "bad[")),
        contract(),
    ])
    assert decision.verdict == "DENY"
    assert "excluded_paths" in decision.unresolved_dimensions


@pytest.mark.parametrize(
    "bounds",
    [
        (("changed_files", math.nan, 20.0),),
        (("changed_files", 0.0, math.inf),),
        (("changed_files", True, 20.0),),
        (("changed_files", 10.0, 2.0),),
    ],
)
def test_malformed_parameter_bounds_deny(bounds):
    decision = intersect_contracts([contract(parameter_bounds=bounds)])
    assert decision.verdict == "DENY"
    assert "parameter_bounds" in decision.unresolved_dimensions


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_cost_usd", math.nan),
        ("max_cost_usd", math.inf),
        ("max_tokens", -1),
        ("max_seconds", -1),
        ("max_attempts", 0),
        ("max_occurrences", 0),
        ("max_tokens", True),
    ],
)
def test_malformed_resource_ceiling_denies(field, value):
    decision = intersect_contracts([contract(**{field: value})])
    assert decision.verdict == "DENY"
    assert field in decision.unresolved_dimensions


def test_zero_cost_is_valid():
    decision = intersect_contracts([contract(max_cost_usd=0.0)])
    assert decision.verdict in {"ALLOW", "NARROW"}
    assert decision.effective.max_cost_usd == 0.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("externality", "unknown"),
        ("reversibility", "unknown"),
        ("approval_required", 1),
    ],
)
def test_authority_enum_fields_do_not_coerce(field, value):
    decision = intersect_contracts([contract(**{field: value})])
    assert decision.verdict == "DENY"
    assert field in decision.unresolved_dimensions


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_tokens", 1.5),
        ("max_seconds", "3600"),
        ("max_attempts", True),
        ("max_occurrences", False),
    ],
)
def test_integer_resource_fields_require_actual_integers(field, value):
    decision = intersect_contracts([contract(**{field: value})])
    assert decision.verdict == "DENY"
    assert field in decision.unresolved_dimensions


def test_integer_resource_boundaries_are_valid():
    decision = intersect_contracts([
        contract(max_tokens=0, max_seconds=0, max_attempts=1, max_occurrences=1),
    ])
    assert decision.verdict in {"ALLOW", "NARROW"}
    assert decision.effective.max_tokens == 0
    assert decision.effective.max_seconds == 0
    assert decision.effective.max_attempts == 1
    assert decision.effective.max_occurrences == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("project", 1),
        ("source_versions", ("project-policy@1", 2)),
        ("roles", ("builder", 2)),
    ],
)
def test_scope_contract_collection_and_string_types_are_validated(field, value):
    decision = intersect_contracts([contract(**{field: value})])
    assert decision.verdict == "DENY"
    assert field in decision.unresolved_dimensions
