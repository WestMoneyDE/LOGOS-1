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

from dataclasses import fields, is_dataclass
from hashlib import sha256
from typing import Mapping

from .audit import AuditSink, build_record
from .invariants import INVARIANTS
from .types import DecisionToken, Finding, GammaVerdict, ValidationContext

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


# --------------------------------------------------------------------------
# Binding a verdict to the situation that produced it
# --------------------------------------------------------------------------

def invariant_set_digest(invariants=INVARIANTS) -> str:
    """Identity of the rule set. A token issued under different rules is not this one."""
    return sha256("|".join(f"{i.id}:{i.clause}" for i in invariants).encode()).hexdigest()


def _canonical(value) -> str:
    """Order-independent, type-tagged rendering of anything Γ is allowed to read.

    Mappings are sorted, so two contexts that differ only in insertion order produce
    the same digest. Types are tagged, so `1` and `"1"` and `True` never collide.
    """
    if is_dataclass(value):
        return "{" + ";".join(
            f"{f.name}=" + _canonical(getattr(value, f.name)) for f in sorted(fields(value), key=lambda f: f.name)
        ) + "}"
    if isinstance(value, Mapping):
        return "<" + ";".join(f"{_canonical(k)}:{_canonical(v)}" for k, v in sorted(value.items(), key=lambda kv: repr(kv[0]))) + ">"
    if isinstance(value, (list, tuple)):
        return "[" + ";".join(_canonical(v) for v in value) + "]"
    return f"{type(value).__name__}:{value!r}"


def context_digest(context: ValidationContext) -> str:
    """Identity of the judged situation, over every field Γ was allowed to read.

    Derived from the dataclass rather than from a hand-written list, so a field added
    to `ValidationContext` is bound automatically. A list someone has to remember to
    update is a hole waiting to happen, and `tests/test_gamma_kernel.py` checks that
    the binding stays total either way.
    """
    return sha256(_canonical(context).encode()).hexdigest()


def issue_decision(context: ValidationContext, invariants=INVARIANTS) -> DecisionToken | None:
    """Judge, and hand back a token bound to what was judged. `None` when not admitted.

    There is no way to obtain a token for a proposal Γ refused, and no way to build one
    that names a situation other than the one evaluated.
    """
    verdict = validate(context, invariants)
    if not verdict.admits():
        return None
    return DecisionToken(
        proposal_digest=context.proposal.proposal_digest,
        scope_digest=context.scope_digest,
        state_hash=context.state_hash,
        tick=context.tick,
        context_digest=context_digest(context),
        invariant_set_digest=invariant_set_digest(invariants),
        result=verdict.result,
    )


def redeem_decision(token: DecisionToken | None, context: ValidationContext, invariants=INVARIANTS) -> bool:
    """May this token be executed against this situation, right now?

    Fail-closed on every difference: no token, a different proposal, a moved state, a
    rewritten argument, a changed rule set. The executor calls this immediately before
    acting, so the window between the verdict and the effect carries no trust.
    """
    if token is None or token.result != "VALID":
        return False
    if token.invariant_set_digest != invariant_set_digest(invariants):
        return False
    if (token.proposal_digest, token.scope_digest, token.state_hash, token.tick) != (
        context.proposal.proposal_digest, context.scope_digest, context.state_hash, context.tick
    ):
        return False
    return token.context_digest == context_digest(context)
