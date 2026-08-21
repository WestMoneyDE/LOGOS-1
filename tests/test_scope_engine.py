from dataclasses import replace

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
