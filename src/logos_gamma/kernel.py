"""Γ Kernel — deterministic runtime invariant validation.

Trusted-core constraints, each enforced by a test in
`tests/test_gamma_trusted_core.py`:

```text
no LLM in trusted core
no network in trusted core
no arbitrary shell in trusted core
no hidden mutable state
fail closed on consequential ambiguity
```

The kernel is a pure function of its `ValidationContext`. It reads state and
authority evidence; it returns a verdict; it mutates nothing. It cannot mint
authority because it has no constructor for one — `AuthorityEvidence` enters only
through the caller-supplied context.
"""
from __future__ import annotations

from .audit import AuditSink, build_record
from .invariants import INVARIANTS
from .types import Finding, GammaVerdict, ValidationContext

#: Bounded evaluation budget (Γ: `T_Γ <= B_Γ`). The registry is finite and every
#: predicate is straight-line, so the bound is structural rather than a timer.
GAMMA_BUDGET = len(INVARIANTS)


def _aggregate(findings: tuple[Finding, ...]) -> str:
    """INVALID dominates UNCLEAR dominates VALID.

    UNCLEAR is never silently promoted to VALID: `Γ-0`, `UNKNOWN != TRUE`.
    """
    if any(f.result == "INVALID" for f in findings):
        return "INVALID"
    if any(f.result == "UNCLEAR" for f in findings):
        return "UNCLEAR"
    return "VALID"


def validate(context: ValidationContext, invariants=INVARIANTS) -> GammaVerdict:
    """Evaluate every Γ invariant against `context`.

    Returns `VALID`, `INVALID` or `UNCLEAR`. Evaluation is total: every invariant
    is checked and reported, so a caller sees all failures rather than only the
    first. Order is fixed, so the verdict is reproducible.
    """
    findings = tuple(inv.check(context) for inv in invariants)
    return GammaVerdict(result=_aggregate(findings), findings=findings)


def admits(context: ValidationContext, sink: AuditSink | None = None) -> bool:
    """Fail-closed admission decision.

    Only an unambiguous `VALID` admits anything. For a consequential proposal an
    `UNCLEAR` verdict is a refusal, not a deferral to the caller's judgement.
    """
    verdict = validate(context)
    if sink is not None:
        sink.emit(
            build_record(
                verdict,
                proposal_digest=context.proposal.proposal_digest,
                scope_digest=context.scope_digest,
                state_hash=context.state_hash,
                tick=context.tick,
            )
        )
    return verdict.admits()


def explain(verdict: GammaVerdict) -> str:
    """Human-readable failure report. Reads the clause ids back to `GAMMA.md`."""
    lines = [f"Γ verdict: {verdict.result}"]
    for finding in verdict.findings:
        if finding.result == "VALID":
            continue
        lines.append(f"  [{finding.result}] {finding.invariant_id} ({finding.clause}): {finding.reason}")
    if len(lines) == 1:
        lines.append("  all invariants satisfied")
    return "\n".join(lines)
