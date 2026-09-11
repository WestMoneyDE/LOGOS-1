"""Sandbox policy — L0 enforced, L1/L2 specified only.

`AGENTS.md` states that adding network, shell, browser, robot, financial,
messaging, deployment or other effectful tools "requires a separate safety
review". Provisioning containers or an egress proxy is exactly that class of
change, so this module implements **L0 only** and represents L1/L2 as declared
policy that is not yet authorized.

```text
CapabilityImplemented != CapabilityAvailable != CapabilityAuthorized
NetworkReachable      != ActionAuthorized
```

The default is `DENY`. An unknown tool class fails closed rather than being
treated as harmless — the same rule Γ0 applies to unknown effect kinds.

This module holds no runtime authority. It answers "does policy permit this at
this sandbox level", which is a necessary and never sufficient condition; Γ
validation and human authority remain separate concerns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping

SandboxLevel = Literal["L0", "L1", "L2"]

#: Repository-native maturity vocabulary, reused rather than reinvented.
CapabilityStatus = Literal[
    "NOT_SPECIFIED", "SPECIFIED", "IMPLEMENTED", "TESTED",
    "REVIEW_REQUIRED", "REVIEWED", "AVAILABLE",
]

#: Section 15 tool capability taxonomy.
ToolClass = Literal["PURE", "REVERSIBLE", "MUTATING", "EXTERNAL", "IRREVERSIBLE"]

TOOL_CLASSES: tuple[ToolClass, ...] = (
    "PURE", "REVERSIBLE", "MUTATING", "EXTERNAL", "IRREVERSIBLE",
)

AdapterKind = Literal["MockAdapter", "SandboxAdapter", "RealAdapter"]

#: Typed egress categories. Deliberately not a boolean `internet = true`.
EgressCategory = Literal[
    "RESEARCH_DOWNLOAD_EGRESS", "MODEL_API_EGRESS", "DATA_EGRESS", "GENERAL_WEB_EGRESS",
]

EGRESS_CATEGORIES: tuple[EgressCategory, ...] = (
    "RESEARCH_DOWNLOAD_EGRESS", "MODEL_API_EGRESS", "DATA_EGRESS", "GENERAL_WEB_EGRESS",
)

#: Address ranges an L2 egress proxy must refuse regardless of allowlist. Cloud
#: metadata (169.254.169.254) lives inside link-local and is called out because
#: it is the highest-value target on that list.
BLOCKED_CIDRS: tuple[str, ...] = (
    "127.0.0.0/8",       # loopback
    "10.0.0.0/8",        # private
    "172.16.0.0/12",     # private
    "192.168.0.0/16",    # private
    "169.254.0.0/16",    # link-local, includes cloud metadata
    "::1/128",           # loopback v6
    "fc00::/7",          # unique local v6
    "fe80::/10",         # link-local v6
)

#: Threats an L2 implementation must address before review, not after.
L2_THREATS: tuple[str, ...] = (
    "redirect escape",
    "DNS rebinding",
    "loopback access",
    "private network access",
    "link-local access",
    "cloud metadata endpoint access",
    "unbounded response download",
    "unbounded request rate",
    "credential leakage into logs",
    "proxy bypass",
)


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    tool_class: ToolClass
    adapter: AdapterKind = "MockAdapter"
    egress_category: EgressCategory | None = None


@dataclass(frozen=True)
class SandboxPolicy:
    """What a given level permits. `L0` is the only level implemented here."""

    level: SandboxLevel
    status: CapabilityStatus
    network_allowed: bool = False
    permitted_tool_classes: frozenset[str] = field(default_factory=frozenset)
    permitted_adapters: frozenset[str] = field(
        default_factory=lambda: frozenset({"MockAdapter"})
    )
    allowed_egress_categories: frozenset[str] = field(default_factory=frozenset)
    notes: str = ""

    def is_usable(self) -> bool:
        """Only a reviewed, available level may actually run anything."""
        return self.status == "AVAILABLE"


#: L0 — pure deterministic simulation. No network, fixtures only, mocks only.
L0 = SandboxPolicy(
    level="L0",
    status="AVAILABLE",
    network_allowed=False,
    permitted_tool_classes=frozenset({"PURE", "REVERSIBLE"}),
    permitted_adapters=frozenset({"MockAdapter", "SandboxAdapter"}),
    allowed_egress_categories=frozenset(),
    notes=(
        "Enforced. Every test in this repository runs here: offline, fixture-based, "
        "no production secrets, no external side effects."
    ),
)

#: L1 — container isolation. Specified; provisioning containers is effectful
#: tooling under AGENTS.md and therefore needs the separate safety review.
L1 = SandboxPolicy(
    level="L1",
    status="REVIEW_REQUIRED",
    network_allowed=False,
    permitted_tool_classes=frozenset({"PURE", "REVERSIBLE", "MUTATING"}),
    permitted_adapters=frozenset({"MockAdapter", "SandboxAdapter"}),
    allowed_egress_categories=frozenset(),
    notes=(
        "Target: non-root, read-only root filesystem, ephemeral writable workspace, "
        "CPU/RAM/PID limits, execution timeout, dropped Linux capabilities, "
        "no-new-privileges, seccomp, no host filesystem access beyond declared "
        "fixtures, no network by default. NOT implemented."
    ),
)

#: L2 — controlled egress. Specified as a typed capability, never `internet=true`.
L2 = SandboxPolicy(
    level="L2",
    status="REVIEW_REQUIRED",
    network_allowed=False,  # remains false until reviewed AND authorized
    permitted_tool_classes=frozenset({"PURE", "REVERSIBLE", "MUTATING", "EXTERNAL"}),
    permitted_adapters=frozenset({"MockAdapter", "SandboxAdapter"}),
    allowed_egress_categories=frozenset({"RESEARCH_DOWNLOAD_EGRESS", "MODEL_API_EGRESS"}),
    notes=(
        "Default DENY with an explicit destination allowlist and per-request "
        "recording. GENERAL_WEB_EGRESS and DATA_EGRESS are deliberately excluded: "
        "no current repository need justifies them. NOT implemented."
    ),
)

POLICIES: Mapping[str, SandboxPolicy] = {"L0": L0, "L1": L1, "L2": L2}


@dataclass(frozen=True)
class SandboxDecision:
    permitted: bool
    reason: str
    level: SandboxLevel


def permits(policy: SandboxPolicy, tool: ToolDescriptor) -> SandboxDecision:
    """Fail-closed policy check. Never an authorization.

    A `True` here means "policy does not forbid this at this level". It is not
    permission: Γ validation and human authority are separate and both required.
    """
    if not policy.is_usable():
        return SandboxDecision(
            False,
            f"sandbox level {policy.level} has status {policy.status}; "
            "implementation capability is not authorization",
            policy.level,
        )
    if tool.tool_class not in TOOL_CLASSES:
        return SandboxDecision(
            False,
            f"unknown tool class {tool.tool_class!r}; unknown capability fails closed",
            policy.level,
        )
    if tool.tool_class == "IRREVERSIBLE":
        return SandboxDecision(
            False,
            "IRREVERSIBLE actions require human approval and are never permitted by "
            "sandbox policy alone",
            policy.level,
        )
    if tool.tool_class not in policy.permitted_tool_classes:
        return SandboxDecision(
            False,
            f"tool class {tool.tool_class} is not permitted at {policy.level}",
            policy.level,
        )
    if tool.adapter not in policy.permitted_adapters:
        return SandboxDecision(
            False,
            f"adapter {tool.adapter} is not permitted at {policy.level}; research runs "
            "use mock or sandbox adapters",
            policy.level,
        )
    if tool.egress_category is not None:
        if not policy.network_allowed:
            return SandboxDecision(
                False,
                f"{policy.level} allows no network; egress category "
                f"{tool.egress_category} is refused",
                policy.level,
            )
        if tool.egress_category not in policy.allowed_egress_categories:
            return SandboxDecision(
                False,
                f"egress category {tool.egress_category} is not in the allowlist for "
                f"{policy.level}",
                policy.level,
            )
    return SandboxDecision(True, f"permitted at {policy.level}", policy.level)
