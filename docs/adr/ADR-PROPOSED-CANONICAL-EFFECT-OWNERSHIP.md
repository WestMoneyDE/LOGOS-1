# ADR-PROPOSED — Canonical Effect Ownership

**Decision state:** `PROPOSED` (no winner chosen; this work order was not delegated approval)
**Raised by:** `DETERMINISTIC-CHAIN-CONSOLIDATION-R1` (base `46643bd`)
**Evidence:** `RISK-AWARENESS-DECOMPOSITION-R1` (`FALSIFIED`, RAD-CE1), `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1` (`27ef324`), `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1` (`REPAIR_VALIDATED`, `7fa2065`)
**Companion:** `docs/research/DETERMINISTIC-CHAIN-CONSOLIDATION.json`, `GI-P5`, `GI-P6`

## Question

> What component owns canonical effect classification in production, and what
> guarantees are required before the validated experimental bridge pattern can
> be considered production architecture?

## Why it is a question

Γ decides whether a grant is required from the proposal's `externality` and
`reversibility` (`is_consequential()`), and the repaired bridge enforces an
approval flag next to them. RAD-CE1 showed that when those fields are copied
from a memory-claimed scope, a grant-less action can be laundered into a
non-consequential one. The repair fixed *who writes the fields* — but the
canonical source it writes from is `src/logos_research/experiments/effect_oracle.py`,
an `EXPERIMENTAL_FIXTURE` keyed by `(action, target)`. The repository has no
production owner of effect classification. Until it has one, `GI-P5`/`GI-P6`
are validated in fixture only.

## Minimum requirements for any owner (regardless of option)

- typed; deterministic or deterministically auditable
- versioned; provenance of every definition; change review; rollback
- target-aware (`(action, target)` or a documented finer key)
- explicit externality, explicit reversibility, explicit approval requirement
- **no memory / prose fallback; no trust / risk / VOI fallback**
- unknown → `DEFER` / fail-closed (never a permissive default)
- observability and audit trail of lookups
- testable against Γ with the existing validation suites (RAD, MBG, MBGV, VOI)

## Options

### Option A — Static canonical effect registry
A versioned, reviewed table (what `effect_oracle.py` already is, minus the "experimental" label).
- Pros: deterministic, inspectable, trivially testable, fail-closed by construction.
- Cons: update burden; config drift between deployments; no dynamic context (same action may differ by environment).

### Option B — Typed effect registry / policy service
A service that serves the same typed records with versioning and audit.
- Pros: central governance, versioning, audit, independent lifecycle.
- Cons: a service dependency on the authority path (availability, latency); schema coordination; the fail-closed rule must survive outages (unavailable → DEFER).

### Option C — Authority-domain policy engine
Effect classification folded into a unified typed policy engine next to grants/scope.
- Pros: one typed policy surface; centralized control.
- Cons: larger trust boundary; coupling of effect semantics to grant semantics (exactly the coupling GI-P6 keeps apart); migration complexity.

### Option D — Domain-owned typed effect providers
Each domain (payments, storage, messaging) publishes its own typed effect provider under a shared interface.
- Pros: effect knowledge near the domain; extensible.
- Cons: governance fragmentation; cross-domain consistency risk; a weak provider is a weak Γ input.

## What the evidence supports today

Only Option A has been exercised: `effect_oracle.py` is a static table and the
MBGV validation showed it clean under AST audit (no memory/prose/trust/risk
inputs; unknown → `None` → `DEFER`). Options B–D are untested here. No option
is chosen.

## Governance asks

1. Name the production owner of canonical effect classification (`PROPOSED`).
2. Decide whether `effect_oracle.py` stays `EXPERIMENTAL_FIXTURE` (`PROPOSED`: yes, until 1 is decided).
3. Decide the production-bridge question below (`DEFERRED`).

---

# Production-bridge readiness — `canonical_proposal()`

**Decision state:** `DEFERRED` (not production-ready by the evidence available; not rejected)

> Is the validated `canonical_proposal()` bridge pattern ready to become a
> production architectural primitive?

| Dimension | Assessment |
|---|---|
| API stability | experimental; `_decide(effect=…, declared=…, canonical_contract=…)` changed twice in two orders (repair, then MBGV-F1 guard) |
| canonical ownership | depends on this ADR's open question |
| unknown-effect behaviour | validated: `None` → `DEFER` before scope and Γ |
| approval gate placement | lives in the bridge (`_decide`) + oracle flag, not in Γ; Γ has no approval field — a production design must decide where approval belongs |
| scope binding | claimed scope for `ScopeDecision` + digest only; any mismatch with the bound contract is a G3-BINDING veto (MBGV-F2) |
| declared / canonical separation | validated (Γ-input spy 48/48; runtime spies 0 calls) |
| serialization | notes are JSON in `MemoryRecord.content`; duplicate-key and domain gaps VF-2/VF-3 apply to a production reader |
| auditability / observability | trace dict only; no audit sink integration |
| B1 isolation | guarded at the package boundary (`NON_PRODUCTION_FROZEN_RISK_GUARDED`); not repaired |
| failure modes | fail-closed on unknown effect, missing contract, unresolvable reference |
| migration risk | no production caller exists; migration is a green-field decision |
| backward compatibility | n/a (no consumers outside experiments) |
| evidence scope | deterministic fixtures, `GrantLedger` fixture; no real registry, no real model |

**Why deferred, not approved:** fixture validation supports the *rule*
(GI-P6); a production primitive additionally needs a production effect owner
(above), a production grant resolver (none exists — `GrantLedger` is a
fixture), an audit sink and an API freeze. **Why not rejected:** nothing in
the evidence argues against the pattern; every attack on it failed.
