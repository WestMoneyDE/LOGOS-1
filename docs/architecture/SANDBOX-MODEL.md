# Sandbox Model — L0 enforced, L1/L2 specified

```text
CapabilityImplemented != CapabilityAvailable != CapabilityAuthorized
NetworkReachable != ActionAuthorized
SandboxPermits != Authorized
```

Owner: `src/logos_research/sandbox.py`. Tests: `tests/test_sandbox_policy.py`.

## Governing rule

`AGENTS.md`, External-action boundary:

> Phase-0 code is research-only. Adding network, shell, browser, robot,
> financial, messaging, deployment or other effectful tools requires a separate
> safety review. The learned agent must not become the authority gate for its own
> tools.

Provisioning containers (L1) and an egress proxy (L2) are effectful tooling under
that rule. They are therefore **specified and not implemented**, and both carry
status `REVIEW_REQUIRED`. See `docs/engineering/SAFETY-REVIEW-REQUEST-SANDBOX-L1-L2.md`.

## Status

Repository-native maturity vocabulary; the levels are not conflated.

| Level | Status | Network | Adapters | Tool classes |
|---|---|---|---|---|
| **L0** pure deterministic simulation | `AVAILABLE` | none | `MockAdapter`, `SandboxAdapter` | `PURE`, `REVERSIBLE` |
| **L1** container isolation | `REVIEW_REQUIRED` | none | `MockAdapter`, `SandboxAdapter` | + `MUTATING` |
| **L2** controlled egress | `REVIEW_REQUIRED` | typed allowlist | `MockAdapter`, `SandboxAdapter` | + `EXTERNAL` |

`network_allowed` is `False` at **every** level today, including L2. It stays
false until the level is both reviewed and authorized. A level whose status is not
`AVAILABLE` permits nothing at all — implementation capability is not
authorization.

## Fail-closed rules

Enforced by `permits()`:

- unknown tool class is refused (the Γ0 rule applied to tooling);
- `IRREVERSIBLE` is never permitted by sandbox policy alone — it requires human
  approval;
- `RealAdapter` is refused wherever research runs; experiments use mocks or the
  sandbox adapter;
- any egress request is refused where `network_allowed` is false, and refused
  again if its category is outside the allowlist.

`permits() == True` means *policy does not forbid this here*. It is not
permission. Γ validation and human authority remain separate and are both
required.

## L1 target (not implemented)

```text
non-root user                     read-only root filesystem
ephemeral writable workspace      CPU / RAM / PID limits
execution timeout                 dropped Linux capabilities
no-new-privileges                 seccomp profile
no host filesystem access beyond declared fixtures
no network by default
```

## L2 target (not implemented)

Egress is a **typed capability**, never `internet = true`:

```text
RESEARCH_DOWNLOAD_EGRESS   allow-listed  (pinned sources, dataset material)
MODEL_API_EGRESS           allow-listed  (declared model endpoints)
DATA_EGRESS                excluded      (no current repository need)
GENERAL_WEB_EGRESS         excluded      (no current repository need)
```

Default `DENY`. Allowed destinations explicit. Per request, record where
technically possible: `experiment_id`, `run_id`, destination, resolved address,
method/protocol, timestamp, request metadata, response metadata/hash, latency,
failure. Never secrets, never full sensitive payloads.

### Threat model — to be addressed before review, not after

```text
redirect escape              DNS rebinding
loopback access              private network access
link-local access            cloud metadata endpoint access
unbounded response download  unbounded request rate
credential leakage in logs   proxy bypass
```

Ranges an implementation must refuse regardless of allowlist:

```text
127.0.0.0/8      10.0.0.0/8       172.16.0.0/12    192.168.0.0/16
169.254.0.0/16   ::1/128          fc00::/7         fe80::/10
```

`169.254.169.254` (cloud metadata) lives inside link-local and is the
highest-value target on that list. IPv6 is included deliberately: a v4-only
blocklist is a bypass.

This list is a floor, not a complete policy. A concrete runtime may require more.

## Tool capability model

```text
PURE          allowed
REVERSIBLE    sandbox only
MUTATING      explicit experiment policy
EXTERNAL      blocked by default
IRREVERSIBLE  human approval required
```

Each logical tool may have three adapters — `MockAdapter`, `SandboxAdapter`,
`RealAdapter`. Research and falsification runs use the first two.

## Relationship to Γ

Sandbox policy and Γ are separate gates that must both pass:

```text
sandbox policy   may this class of action run at this isolation level?
Γ                is this specific proposal compatible with the invariants?
human authority  is it permitted at all?
```

Neither substitutes for another, and none of them creates authority.
