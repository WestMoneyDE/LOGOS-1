# LOGOS-1 Scope Engine — R1 Engineering Contract

**Status:** implemented local scope narrowing and request evaluation; not an
external approval or Γ replacement.

## Interfaces

`ScopeContract` carries project, included/excluded relative path patterns,
roles, tools, memory kinds, projection audiences, capabilities, targets,
parameter bounds, cost/token/time/attempt/occurrence ceilings, half-open
validity inputs, externality, reversibility, approval-required state, data and
retention classes, and source versions.

`intersect_contracts()` returns a `ScopeDecision` with verdict
`ALLOW | NARROW | DEFER | DENY`, the effective contract when one exists, a
canonical SHA-256 digest, reasons, and unresolved dimensions. Inputs are
validated without coercion. Intersections can only retain or narrow authority:
set dimensions intersect, ceilings take minima, exclusions union, validity
windows intersect, risk properties choose the more restrictive value, and
missing, malformed, mismatched, or empty required dimensions fail closed.

`ScopeDecision.evaluate(ScopeRequest)` checks role, tool, memory kind,
capability, target, and a normalized repository-relative path against the
effective contract. Included paths do not override exclusions. Invalid,
absolute, traversal, backslash, ambiguous, or out-of-scope paths are denied.

## Required use

Coding agents must obtain and evaluate a `ScopeDecision` before memory
retrieval, consolidation, file/tool dispatch, or effect proposal. An
`ALLOW`/`NARROW` decision is only a local scope precondition. It does not mint a
grant, consume an approved occurrence, authorize an external effect, or bypass
Γ. External effects still require the separate assurance path.

## Evidence and limits

The exact implementation evidence is `tests/test_scope_engine.py`, with
integration evidence in `tests/test_memory_factory.py` and replay evidence in
`tests/test_memory_recovery.py`. This establishes deterministic behavior for
the tested Python implementation only. It does not establish mediation closure,
OS isolation, approval validity, or scientific evidence for a memory mechanism.

```text
ImplementationPass != ScientificMechanismEvidence
MemoryFactory != AuthoritySource
ScopeDecision != ExternalApproval
PersistentState != PhenomenalConsciousness
```
