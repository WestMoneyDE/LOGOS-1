"""Sandbox policy tests. Default must be DENY; unknown capability fails closed."""
from __future__ import annotations

import pytest

from logos_research.sandbox import (
    BLOCKED_CIDRS,
    EGRESS_CATEGORIES,
    L0,
    L1,
    L2,
    L2_THREATS,
    POLICIES,
    ToolDescriptor,
    permits,
)


def test_l0_is_the_only_available_level():
    assert L0.status == "AVAILABLE"
    assert L1.status == "REVIEW_REQUIRED"
    assert L2.status == "REVIEW_REQUIRED"


def test_no_level_allows_network_today():
    assert not any(p.network_allowed for p in POLICIES.values())


def test_l0_permits_a_pure_mock_tool():
    d = permits(L0, ToolDescriptor("hash", "PURE", "MockAdapter"))
    assert d.permitted


@pytest.mark.parametrize("level", ["L1", "L2"])
def test_an_unreviewed_level_permits_nothing(level):
    d = permits(POLICIES[level], ToolDescriptor("hash", "PURE", "MockAdapter"))
    assert not d.permitted
    assert "is not authorization" in d.reason


def test_unknown_tool_class_fails_closed():
    d = permits(L0, ToolDescriptor("mystery", "TELEPORT", "MockAdapter"))  # type: ignore[arg-type]
    assert not d.permitted
    assert "fails closed" in d.reason


def test_irreversible_is_never_permitted_by_policy_alone():
    d = permits(L0, ToolDescriptor("wipe", "IRREVERSIBLE", "MockAdapter"))
    assert not d.permitted
    assert "human approval" in d.reason


def test_external_tool_is_refused_at_l0():
    assert not permits(L0, ToolDescriptor("send_email", "EXTERNAL", "MockAdapter")).permitted


def test_real_adapter_is_refused_at_l0():
    assert not permits(L0, ToolDescriptor("hash", "PURE", "RealAdapter")).permitted


def test_egress_is_refused_wherever_network_is_off():
    d = permits(L0, ToolDescriptor("fetch", "REVERSIBLE", "MockAdapter",
                                   egress_category="RESEARCH_DOWNLOAD_EGRESS"))
    assert not d.permitted
    assert "no network" in d.reason


def test_egress_is_typed_not_a_boolean():
    assert "GENERAL_WEB_EGRESS" in EGRESS_CATEGORIES
    assert "GENERAL_WEB_EGRESS" not in L2.allowed_egress_categories
    assert "DATA_EGRESS" not in L2.allowed_egress_categories


def test_blocked_ranges_cover_metadata_private_loopback_and_ipv6():
    assert "169.254.0.0/16" in BLOCKED_CIDRS   # cloud metadata lives here
    assert "127.0.0.0/8" in BLOCKED_CIDRS
    assert {"::1/128", "fc00::/7", "fe80::/10"} <= set(BLOCKED_CIDRS)


def test_l2_threat_model_is_recorded_before_implementation():
    for threat in ("DNS rebinding", "cloud metadata endpoint access", "proxy bypass"):
        assert threat in L2_THREATS
