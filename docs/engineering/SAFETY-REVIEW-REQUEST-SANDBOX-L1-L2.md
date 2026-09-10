# Safety Review Request — Sandbox L1 / L2

**Status:** `L1 REVIEW_GRANTED` / `L2 REVIEW_REQUIRED` — see Decision record
**Raised by:** `NEXT-SESSION-RESEARCH-FALSIFICATION-INFRASTRUCTURE-R1`
**Governing rule:** `AGENTS.md`, External-action boundary
**Decision owner:** human reviewer. Not Γ, not this document, not the agent.

## Why this request exists

`AGENTS.md` states:

> Adding network, shell, browser, robot, financial, messaging, deployment or
> other effectful tools requires a separate safety review. The learned agent must
> not become the authority gate for its own tools.

Sandbox L1 provisions containers. Sandbox L2 opens controlled network egress.
Both fall squarely inside that rule. This request exists so the boundary is
crossed by a human decision rather than by an implementation landing.

```text
ImplementationCapability != Authorization
SafetyReviewPASS != UserMandate
```

**The Γ Verifier does not issue this approval.** Γ may verify that a Safety
Review artifact is internally consistent with Γ invariants; it cannot be the
entity that grants the review. Making Γ the approver would be precisely the
"learned agent as authority gate for its own tools" failure the rule forbids.

## What has been implemented

Only L0, and only as policy:

```text
src/logos_research/sandbox.py     policy objects and a fail-closed permits()
tests/test_sandbox_policy.py      13 tests
```

`network_allowed` is `False` at every level, **including L2**. L1 and L2 carry
status `REVIEW_REQUIRED`, and `permits()` refuses everything at a level whose
status is not `AVAILABLE`. Nothing in this repository can currently open a socket
through the sandbox layer, and the Γ trusted core is AST-tested to import no
network module at all.

## What is being requested

Not approval to run anything. Approval to **proceed to implementation** of:

1. **L1 container isolation** — non-root, read-only root filesystem, ephemeral
   writable workspace, CPU/RAM/PID limits, execution timeout, dropped Linux
   capabilities, `no-new-privileges`, seccomp, no host filesystem access beyond
   declared fixtures, no network.
2. **L2 controlled egress** — default `DENY`, explicit destination allowlist,
   typed categories, per-request recording.

Requested egress categories, and only these:

```text
RESEARCH_DOWNLOAD_EGRESS   pinned sources and dataset material
MODEL_API_EGRESS           declared model endpoints
```

Explicitly **not** requested: `DATA_EGRESS`, `GENERAL_WEB_EGRESS`. No current
repository need justifies either, and a category that is not requested cannot be
quietly used later.

## Threat model the implementation must address

```text
redirect escape              DNS rebinding
loopback access              private network access
link-local access            cloud metadata endpoint access
unbounded response download  unbounded request rate
credential leakage in logs   proxy bypass
```

Blocked regardless of allowlist:

```text
127.0.0.0/8      10.0.0.0/8       172.16.0.0/12    192.168.0.0/16
169.254.0.0/16   ::1/128          fc00::/7         fe80::/10
```

IPv6 included deliberately — a v4-only blocklist is a bypass. Cloud metadata
(`169.254.169.254`) is called out because it is the highest-value target present.

This list is a floor, not a complete policy.

## Residual risk if approved

- an egress proxy is a new trust boundary and a new bypass surface;
- request/response recording is an exfiltration surface if it captures payloads,
  so recording is metadata and hashes only;
- container escape remains possible in principle; stronger isolation (gVisor,
  Firecracker, Kata) is **not** requested here and would be a separate review;
- an allowlist entry is a standing capability and should carry an expiry.

## Residual risk if declined

- experiments needing pinned external material stay manual, as R4 was;
- model-backed evaluators cannot be characterized in-repo, so instrument-first
  falsification stays limited to deterministic instruments.

Neither risk is a reason to approve. Both are recorded so the decision is made on
the actual trade-off.

## What must not happen

```text
this document is not an approval
an implementation landing is not an approval
a passing test suite is not an approval
a Γ VALID verdict is not an approval
```

Until a human reviewer records a decision here, L1 and L2 remain
`REVIEW_REQUIRED` and `permits()` continues to refuse them.

## Decision record

```text
decision:            L1 GRANTED, L2 NOT GRANTED
reviewer:            repository owner / founder (WestMoneyDE)
date:                2026-09-10
granted verbatim:    "die sandboxen auch installieren damit wir die instanzen
                      isoliert laufen lassen koennen"
L1 container isolation:   GRANTED
                          non-root, read-only root fs, ephemeral workspace,
                          CPU/RAM/PID limits, timeout, dropped capabilities,
                          no-new-privileges, seccomp, no network by default
L2 controlled egress:     NOT GRANTED
                          The grant names container isolation for running
                          instances. It does not mention experimental agent
                          network egress, and that is a separate capability.
                          L2 stays REVIEW_REQUIRED and network_allowed stays
                          False until explicitly granted.
```

```text
InfrastructureHasNetwork != AgentHasNetwork
ServiceReachability      != ExperimentAuthority
```
