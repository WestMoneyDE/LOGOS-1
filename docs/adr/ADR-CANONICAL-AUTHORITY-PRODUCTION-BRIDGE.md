# ADR — Canonical Authority + Production Bridge (C1–C4)

**Master order:** `CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1` · base `ac070e3` (`CANONICAL_EFFECT_OWNER_IMPLEMENTED_AND_VALIDATED_R1`)
**Master verdict:** `PRODUCTION_BRIDGE_VALIDATED_R1` · **Date:** 2026-09-17
**Preregistration:** `17c8f8a959e4eab06e6ea1a679ed871eb32ee8855d2bc2e325b6fde6578f5901` · **Run:** `…-run-2961e252` · artifact `f4630c74836620d1…` `integrity_ok = true`
**Record:** `09-SESSIONS/2026-09-17-CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1/SESSION-REPORT.md`

## 1. Ratified governance (founder, 2026-09-17) — `APPROVED`

| Decision | Value |
|---|---|
| `EFFECT-ORACLE-SCOPE` | `REFERENCE_TEST_ORACLE` — `effect_oracle.py` stays the reference oracle for differential/regression tests; not a production owner |
| `PRODUCTION-BRIDGE-READINESS` (prior) | `PRODUCTION_BRIDGE_READY_WITH_CONDITIONS`, conditions C1–C4 — **all four closed by this order** |

## 2. Target pipeline (implemented, validated)

```text
Production Memory Reader (logos_memory.reader)      C4   PRODUCTION_MEMORY_READER_VALIDATED
        ↓ DeclaredEvidence
Canonical Effect Owner (logos_effects)              —    OWNER_IMPLEMENTATION_VALIDATED (predecessor)
        ↓
Canonical Authority Resolver (logos_authority)      C1   AUTHORITY_RESOLVER_VALIDATED
        ↓
Production Bridge v1 (logos_runtime.decide_action)  C2   PRODUCTION_BRIDGE_API_VALIDATED   BRIDGE_API_VERSION = v1
        ↓
Γ (unchanged)
        ↓
Production Audit Sink (logos_audit)                 C3   AUDIT_SINK_VALIDATED
```

Only canonical, authority-owned state raises authority. Memory yields references and claims; the effect owner yields what an action IS; the resolver yields whether a grant is valid; Γ evaluates; the audit records. None of the four production packages imports `logos_research`; the B1 guard refuses the reverse direction.

## 3. Decision — reference `GrantLedger` scope

**`REFERENCE_TEST_LEDGER`** (`APPROVED` by this order's evidence; founder ratification recorded with the master report). The experimental `GrantLedger` remains the differential-parity source for the resolver and the frozen input of the predecessor evidence. It is not a production fallback (mutants C1-M10, C2 "fallback to GrantLedger", E2E "GrantLedger production fallback" all caught) and is not deleted.

## 4. Schemas (frozen with the preregistration)

- **GrantRecord** — `grant_id, version, principal, action, target, scope_digest, authority_origin (closed enum human|model|system, no default), state_hash, issued_at_tick, valid_from_tick, expires_tick, provenance, revoked, revoked_at_tick, definition_hash`.
- **AuthorityResolution** — `status ∈ {RESOLVED, NO_GRANT, REVOKED, STALE, NOT_YET_VALID, WRONG_PRINCIPAL, WRONG_SCOPE, WRONG_STATE, INVALID, UNAVAILABLE, UNKNOWN}`; only `RESOLVED` carries `authority_evidence`.
- **BridgeDecision** — `outcome, failure_codes, canonical_effect_ref, authority_ref, declared_effect, binding_result, approval_state, decision_trace_id, api_version`.
- **AuditEvent** — the 24 required bridge fields plus `event_id, sequence, timestamp, previous_event_hash, event_hash, schema_version`; append-only, hash-chained, tenant-partitioned queries.
- **MemoryReadResult** — `status ∈ {RESOLVED, NOT_FOUND, INVALID, CORRUPT, UNAVAILABLE, WRONG_TENANT, UNSUPPORTED_VERSION}`; evidence only.

## 5. Authority semantics (bridge mapping, preregistered)

`RESOLVED` → evidence to Γ (Γ re-checks origin/binding/expiry/freshness) · `NO_GRANT` → DENY where a grant is required, otherwise Γ without authority · `REVOKED | STALE | NOT_YET_VALID | WRONG_PRINCIPAL | WRONG_SCOPE | WRONG_STATE` → DENY · `INVALID | UNAVAILABLE | UNKNOWN` → DEFER. Effect owner non-RESOLVED → DEFER. Memory reader non-RESOLVED → DEFER. Audit unavailable → DEFER (never silent). The bridge resolves grants **by explicit reference only** (memory carries references, never authority).

**Classified divergence (decrease-only, CAPB-F2):** a revoked grant presented for a non-consequential, non-approval action is `DENY` in production; the reference ledger drops revoked grants to `None`, so Γ `ALLOW`s there. `RevokedAuthority != HistoricalPermission`. Listed in every differential (C1: 45 rows, C2: 36, E2E: 156); no other divergence class exists.

## 6. Multi-tenant semantics

Tenant identity only from the typed `TenantContext`; memory references are `memory://<tenant>/<id>` over per-tenant store directories; a reference naming another tenant is `WRONG_TENANT` before any store is opened; the bridge re-checks the evidence tenant; audit events carry the tenant and are queried per tenant. Effect definitions remain global (tenant-specific definitions `OUT_OF_SCOPE`).

## 7. Re-evaluated `PRODUCTION-BRIDGE-READINESS`

**Value:** `PRODUCTION_BRIDGE_READY_WITH_CONDITIONS` · **State:** `PROPOSED` (founder ratification requested)

C1–C4 are closed and validated. The remaining conditions are operational, not architectural:

- **R1** deployment topology — authority store, effect registry and audit sink are in-process / file-backed; no backing service, key management or rotation.
- **R2** grant issuance / revocation governance — the store API exists; the human workflow (who may issue or revoke a production grant) does not.
- **R3** tenant provisioning and authentication of `TenantContext` at the caller boundary (typed context is assumed trusted).

Why not `READY`: R1–R3 are missing production components. Why not `DEFERRED`/`REJECTED`: every attack on the pipeline failed (false_allow = 0 over 4 700+ recorded rows; 71/71 mutants caught).

## 8. Residual risks / findings

`CAPB-F1` LOW (predecessor ancestry check strengthened) · `CAPB-F2` INFO (classified divergence) · `CAPB-F3` LOW (empty identity fields also refuse audit → `AUDIT_UNAVAILABLE` added; fail-closed) · `CAPB-F4` INFO (C4 implementation + validation in one commit) · `CAPB-F5` MEDIUM (R1–R3 above) · `DCC-F1` MEDIUM unchanged (governance note; historical file untouched).

## 9. Boundaries

Γ unchanged (bundle hash frozen and re-checked). P7 unchanged. B1 `NON_PRODUCTION_FROZEN_RISK_GUARDED` (guard extended to `logos_authority`, `logos_runtime`, `logos_audit`). MBGV-F1 guard intact. No predecessor verdict changed. Inference prohibition **not lifted** — `ACTIVE`.

**Review date:** 2026-12-17.
