# ADR — Canonical Effect Ownership Decision

**Status:** `APPROVED` (ownership option, founder) · companion decisions `EFFECT-ORACLE-SCOPE` and `PRODUCTION-BRIDGE-READINESS` below are `PROPOSED` (evidence-based, pending founder ratification)
**Date:** 2026-09-17
**Work order:** `CANONICAL-EFFECT-OWNERSHIP-DECISION-R1` · base `4795b16` (`DETERMINISTIC_CHAIN_CONSOLIDATED_R1`)
**Supersedes the open question in:** `ADR-PROPOSED-CANONICAL-EFFECT-OWNERSHIP.md` (kept as the option record)
**Machine-checkable record:** `docs/research/CANONICAL-EFFECT-OWNER.json` (test-compared by `tests/test_canonical_effect_owner.py`)

## Founder decision

Presented: decision matrix for Options A–D and `NONE/DEFER` across the fifteen
criteria of the work order, assessed against this repository. The executor
stopped at the gate. The founder answered, verbatim:

> A — static canonical effect registry
> Rationale: Smallest, most deterministic and best-validated fit for the current repository; it preserves the canonical-effect/authority separation without adding unnecessary service or policy complexity.

**Chosen option:** **Option A — static canonical effect registry.**

## Rejected alternatives

| Option | Why not now |
|---|---|
| B — typed registry service | a network dependency on the authority path; nothing to serve and no consumer exist in this repository; a local adapter alone would leave the real owner unvalidated |
| C — authority-domain policy engine | largest trust boundary; couples effect classification to authority — the seam `GI-P6` keeps apart; no policy platform exists |
| D — domain-owned typed providers | governance fragmentation and routing ambiguity; one domain today, no bounded contexts |
| NONE / DEFER | valid outcome; the founder chose to decide, which closes readiness items 3 and 4 instead of leaving them open |

## Decision rationale

Option A is the only option with evidence in this repository: the validated
repair (`MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1`) already runs against
a static table, AST-audited clean of memory/prose/trust/risk inputs, with
unknown → `DEFER`. A static registry is deterministic, content-hashed,
in-process (no availability path on the authority decision), trivially
fail-closed (missing key = `UNKNOWN`) and drop-in testable against Γ with the
existing RAD / MBG / MBGV / VOI suites. Its known costs — table sprawl and
manual governance — are proportional to a surface of one domain and eleven rows.

## Scope

- New production package `src/logos_effects` (stdlib-only imports): typed schema, versioned immutable registry, v1 definitions with governance metadata, fail-closed `resolve`, append-only audit.
- Interface: `resolve_effect(action, target, context) -> CanonicalEffectResolution{status, effect, definition_id, version, definition_hash, provenance, error, audit_metadata}`; statuses `RESOLVED | UNKNOWN | UNAVAILABLE | INVALID`; only `RESOLVED` carries an effect.
- Integration through the repaired bridge only: `logos_research/experiments/canonical_owner_bridge.py` adapts the owner to `evaluate_with_memory(effect_oracle=…)`; `memory_authority.py`, Γ and P7 are unchanged.
- Semantics are **global**; `domain="global"` on every definition; a context in another domain resolves `UNKNOWN`; `tenant` is audit-only.

## Non-goals

No Γ change; no P7 change; no redesign of grant, principal, memory, risk,
trust, VOI or binding models; no B1 repair; no historical verdict change; no
edit of the DCC-F1 historical file; no inference; no policy engine; no
permissive fallback; `effect_oracle.py` is not renamed to production.
**Tenant-specific definitions: `OUT_OF_SCOPE`.**

## Minimum guarantees (all tested)

typed · deterministic · versioned (immutable versions, content hash, explicit
active pointer) · target-aware `(action, target, domain)` · explicit
externality / reversibility / approval requirement · consequentiality derived
exactly as Γ's `is_consequential()` · fail-closed (`UNKNOWN` / `UNAVAILABLE` /
`INVALID` / `VERSION_DRIFT` → bridge `DEFER` before scope and Γ) · observable
and auditable (owner type, version, registry hash, definition id and hash,
status, action, target, domain, tenant, latency, error, bridge run id) ·
rollback-capable (`v1 → v2 → v1` exact and audited) · independent of memory
claims, trust, risk, VOI, uncertainty, declared effect and prose (AST audit +
mutants M2–M5, M7, M8).

## Migration implications

One-to-one from the reference oracles: 8 rows of `effect_oracle.CANONICAL_EFFECTS`
and 3 rows of `value_of_information.INFO_EFFECTS` → 11 v1 definitions with
identical semantics; **semantic diff: none**; unknown rows stay unknown;
approval-only (`EXPORT ledger-3`, `QUERY_RECORD customer-secret`),
externality-only (`NOTIFY ops-channel`) and reversibility-only (`ARCHIVE silo-4`)
rows preserved. The mapping table with definition ids and hashes is in
`CANONICAL-EFFECT-OWNER.json → migration_mapping`. No production caller
migrates: none existed.

## Rollback

Registry versions are immutable; rollback is `activate(previous)`, recorded as
an audited activation event with both content hashes. The bridge adapter pins
the active version when it starts; a mid-run activation makes further
resolutions `INVALID (VERSION_DRIFT)` → `DEFER`, so one execution never mixes
versions. Code rollback: revert the branch; no schema, Γ or P7 migration exists.

## Open risks

- **C1** canonical *authority* still comes from `GrantLedger`, an experimental fixture — no production grant resolver exists.
- **C2** the bridge (`evaluate_with_memory / _decide / canonical_proposal`) lives in `logos_research.experiments` and its API changed twice; not frozen.
- **C3** audit is an in-memory list plus optional sink; no production audit sink.
- **C4** a production memory reader must add VF-2 / VF-3 domain validation and duplicate-key rejection.
- Registry sprawl / drift as domains grow (accepted for one domain; revisit at review date).
- `DCC-F1` (MEDIUM) remains a governance note; historical file untouched.

## Evidence pointers

`09-SESSIONS/2026-09-17-CANONICAL-EFFECT-OWNERSHIP-DECISION-R1/SESSION-REPORT.md` ·
`tests/test_canonical_effect_owner.py` (interface, parity, fail-closed matrix,
RAD/MBG/MBGV regressions, CEO-P1..P15, CEO-MTR1..8, rollback, audit, 14 mutants) ·
predecessor evidence `RAD-CE1`, `MBGV` (`7fa2065`), consolidation (`4795b16`).

## Governance owner

Architecture governance (founder).

**Review date:** 2026-12-17, or earlier when a second domain, a tenant-specific
requirement or a production grant resolver appears.

---

# Decision — `EFFECT-ORACLE-SCOPE`

**Value:** `REFERENCE_TEST_ORACLE` · **State:** `PROPOSED` (recorded by the executor from evidence; the founder stated no preference; ratification: founder)

Rationale: `src/logos_research/experiments/effect_oracle.py` is the differential-
parity source for the production owner (`CEO-MTR8`, `PAR` tests) and the frozen
input of the RAD / MBG / MBGV / VOI evidence. It is not production code, it is
not deleted, and it is not the migration source *only* — it keeps its test role.
`PRODUCTION_OWNER` is explicitly not chosen.

# Decision — `PRODUCTION-BRIDGE-READINESS`

**Value:** `PRODUCTION_BRIDGE_READY_WITH_CONDITIONS` · **State:** `PROPOSED` (recorded by the executor from evidence; ratification: founder)

| Dimension | Assessment |
|---|---|
| owner integration | done — `evaluate_with_owner` routes the production owner through the repaired bridge; fixture never reached (M12) |
| unknown behaviour | validated — `UNKNOWN` → `DEFER`, scope not evaluated, Γ not called (spies) |
| unavailable behaviour | validated — `UNAVAILABLE` / `INVALID` / `VERSION_DRIFT` → `DEFER` (M10) |
| approval gate | validated — bridge-enforced, not suppressible by claim, grant origin or channel (M6, CEO-P6) |
| scope binding | validated — claimed scope only for `ScopeDecision` + digest; mismatch = binding veto (MBGV-F2) |
| B1 isolation | validated — owner is a production package; guard refuses; bridge never calls B1 (M11 + spy) |
| MBGV-F1 guard | validated — adapter never calls `_decide`; `canonical_contract=True` guard intact |
| audit | validated in-memory — every resolution carries owner / version / registry hash / definition id + hash / run id (M14) |
| versioning | validated — immutable versions, content hashes, pinned version per run (M9) |
| observability | validated — trace + audit records; **no production sink (C3)** |
| rollback | validated — `v1 → v2 → v1` exact and audited (CEO-P15, MTR6) |
| regression evidence | RAD / MBG / MBGV / VOI / PETG / RSS / MAP / binding / consolidation green (session report) |
| **conditions** | **C1** production canonical authority resolver · **C2** bridge relocation + API freeze · **C3** audit sink · **C4** production memory reader (VF-2 / VF-3) |

Why not `READY`: every unmet condition is a missing *production* component,
not a failed test. Why not `DEFERRED`: nothing in the evidence is undecided;
the bridge pattern itself passed every attack with the production owner in
place. Why not `REJECTED`: no false ALLOW anywhere.
