# Γ extension proposal R1 — eight candidate invariants

**Status: DRAFT PROPOSAL. Not implemented. Γ is unchanged.**
`GAMMA.md` and `src/logos_gamma/*` are untouched by this document. Adding an invariant to Γ is a governance act; an AI may draft one and may never approve one. Each candidate below is written so that a founder decision is a yes/no on a precise predicate, not on a paragraph.

**Why these eight and not others.** Every candidate satisfies four conditions, and anything failing one of them is listed at the end under *rejected*:

```text
deterministic   a pure predicate over a typed context — no model, no clock, no network, no randomness
total           it returns a Finding for every context, including the ones it does not constrain
tightening      it can only refuse; no invariant may create an admission
falsifiable     a stated test admits before and refuses after, and a stated case must NOT be refused
```

Current registry: 15 invariants, `GAMMA_BUDGET = len(INVARIANTS)`. This proposal would take it to 23. The budget stays structural — every predicate remains straight-line.

---

## G-TAINT — an approval cannot cover evidence that did not exist yet

**Clause:** Γ-1 (extension) · **Verdict on failure:** INVALID

**The attack.** Indirect prompt injection. The agent holds a legitimate grant. It then reads a file, a web page or a tool result containing instructions, and proposes an action shaped by that content. Every existing invariant passes: the grant is human-rooted, bound, live, fresh and unconsumed. `G1-CONTENT` does not fire, because a valid grant exists. The approval is real — it simply predates the content that actually drove the proposal.

**Predicate.**

```python
def _authority_predates_no_evidence(ctx):
    grant = ctx.authority
    if grant is None or not ctx.proposal.is_consequential():
        return _ok("G-TAINT", "Γ-1", "no grant to outrun")
    late = tuple(c.ref for c in ctx.proposal.provenance
                 if c.ingested_at_tick is not None and c.ingested_at_tick > grant.issued_at_tick)
    if late:
        return _bad("G-TAINT", "Γ-1",
                    f"grant issued at tick {grant.issued_at_tick} cannot cover evidence ingested "
                    f"afterwards: {list(late)}; re-approval is required, not inference")
    unknown = tuple(c.ref for c in ctx.proposal.provenance if c.ingested_at_tick is None)
    if unknown:
        return _unclear("G-TAINT", "Γ-1", f"provenance without an ingestion tick: {list(unknown)}")
    return _ok("G-TAINT", "Γ-1", "all evidence predates the approval")
```

**Type change.** `ProvenanceClaim` gains `ingested_at_tick: int | None = None`. Default `None` keeps every existing construction valid and yields UNCLEAR rather than a silent pass — fail-closed, as `G0-PROVENANCE` already does for a missing digest.

**Must not refuse:** a proposal whose evidence was all ingested before the grant was issued. **Must refuse:** the same proposal with one later item.

**Cost.** This is the strictest candidate. It means an agent that reads anything new after approval must go back for approval. That is the intended consequence and it will be felt.

---

## G-BOUNDS — a grant binds parameters, not only an action name

**Clause:** Γ-3 (extension) · **Verdict on failure:** INVALID

**The gap, already written down.** `AGENTS.md` states plainly that parameter bounds, budgets, time validity, data classes and source versions "require a separate downstream dispatch/effect gate and are not evaluated by this package". Today a grant for `payment.transfer` to a recipient binds the *digest of action and target*. The amount is a parameter. Approving a transfer of 50 and executing 50 000 000 passes every current invariant.

**Predicate.**

```python
def _parameters_within_grant_bounds(ctx):
    grant = ctx.authority
    if grant is None or not grant.bounds:
        return _ok("G-BOUNDS", "Γ-3", "no bounded parameters")
    for name, (low, high) in grant.bounds.items():
        if name not in ctx.proposal.parameters:
            return _unclear("G-BOUNDS", "Γ-3", f"grant bounds {name!r} but the proposal omits it")
        value = ctx.proposal.parameters[name]
        if not isinstance(value, (int, float)) or not (low <= value <= high):
            return _bad("G-BOUNDS", "Γ-3", f"{name}={value!r} outside the approved [{low}, {high}]")
    return _ok("G-BOUNDS", "Γ-3", "every bounded parameter is inside its approval")
```

**Type change.** `AuthorityEvidence` gains `bounds: Mapping[str, tuple[float, float]] = {}` (frozen, empty by default — every existing grant is unaffected).

**Must not refuse:** an unbounded grant, exactly as today. **Must refuse:** amount 50 000 000 against a grant bounded to [0, 50].

---

## G-SEPARATION — the principal who proposes is not the principal who approves

**Clause:** Γ-1 (extension) · **Verdict on failure:** INVALID

Four-eyes, as an invariant rather than as a process. Today nothing prevents a grant whose issuing principal is the same identity that submitted the proposal — the check exists only in the authority store's conventions.

```python
def _proposer_is_not_approver(ctx):
    grant = ctx.authority
    if grant is None:
        return _ok("G-SEPARATION", "Γ-1", "no grant")
    if grant.issued_by is not None and grant.issued_by == ctx.proposal.proposed_by:
        return _bad("G-SEPARATION", "Γ-1",
                    f"{grant.issued_by!r} approved its own proposal; approval is external or it is not approval")
    if grant.issued_by is None or ctx.proposal.proposed_by is None:
        return _unclear("G-SEPARATION", "Γ-1", "principals not recorded on both sides")
    return _ok("G-SEPARATION", "Γ-1", "proposer and approver are distinct principals")
```

**Type change.** `AuthorityEvidence.issued_by: str | None`, `EffectProposal.proposed_by: str | None`.

---

## G-CONTRACT — an output arrives under a known contract or not at all

**Clause:** Γ0 (extension) · **Verdict on failure:** INVALID

Lifts the property `core/output_contract.py` already enforces at the boundary into the kernel, so it holds for every caller rather than for one parser. An unrecognised contract version is refused exactly as an unregistered effect kind is.

```python
KNOWN_CONTRACTS = frozenset({"logos-agent-output/1"})

def _contract_is_known(ctx):
    version = ctx.proposal.contract_version
    if version is None:
        return _ok("G-CONTRACT", "Γ0", "proposal was not produced by an agent contract")
    if version not in KNOWN_CONTRACTS:
        return _bad("G-CONTRACT", "Γ0", f"unknown output contract {version!r}: unknown contracts are denied")
    return _ok("G-CONTRACT", "Γ0", f"contract {version!r} is registered")
```

---

## G-ADVISORY — an advisory input may tighten, never loosen

**Clause:** Γ-4 (extension) · **Verdict on failure:** INVALID

The structural home for every statistical component discussed around this system: an injection classifier, a trust gate, a referee model, a risk score. They are admitted as inputs on one condition — their vote is typed, and the only value that changes anything is a refusal.

```python
def _advisory_only_tightens(ctx):
    for source, vote in ctx.advisories:
        if vote not in ("ABSTAIN", "TIGHTEN", "REFUSE"):
            return _bad("G-ADVISORY", "Γ-4",
                        f"advisory {source!r} returned {vote!r}; an advisory has no vocabulary for permission")
        if vote == "REFUSE":
            return _bad("G-ADVISORY", "Γ-4", f"advisory {source!r} refused")
    return _ok("G-ADVISORY", "Γ-4", "no advisory objection")
```

**Type change.** `ValidationContext.advisories: tuple[tuple[str, str], ...] = ()`.

**The point of the missing value.** There is no `ALLOW`. A referee model cannot vote for an action even if it wants to, and a compromised one cannot be made to. This is the same design as the closed envelope schema: the dangerous option is absent rather than guarded.

---

## G-BUDGET — a scope has a finite consequential budget

**Clause:** Γ-10 (extension) · **Verdict on failure:** INVALID

The deterministic form of the stability-guard idea. Not an energy score from a model: a counter of consequential effects already executed in this scope against a bound carried by the grant.

```python
def _scope_budget_not_exhausted(ctx):
    grant = ctx.authority
    if grant is None or grant.scope_budget is None:
        return _ok("G-BUDGET", "Γ-10", "no scope budget")
    if ctx.scope_consumed >= grant.scope_budget:
        return _bad("G-BUDGET", "Γ-10",
                    f"scope budget exhausted ({ctx.scope_consumed}/{grant.scope_budget}); "
                    "a loop does not earn more authority than a single step")
    return _ok("G-BUDGET", "Γ-10", "scope budget remains")
```

Note what this catches that `G10-OCCURRENCE` does not: a runaway loop issuing *different* proposals, each with its own valid grant, none of them a replay.

---

## G-COMPENSATION — an unreconciled step blocks the next one

**Clause:** Γ-11 (extension) · **Verdict on failure:** INVALID

`G11-OUTCOME` already blocks a retry of the *same* proposal while its outcome is unknown. It does not block *step 4* while step 3 of the same saga is unresolved, which is the multi-step failure mode.

```python
def _no_unreconciled_sibling(ctx):
    if ctx.pending_compensations:
        return _bad("G-COMPENSATION", "Γ-11",
                    f"{len(ctx.pending_compensations)} step(s) in this saga are unreconciled: "
                    f"{list(ctx.pending_compensations)}; the scope is held, not rolled forward")
    return _ok("G-COMPENSATION", "Γ-11", "no unreconciled step in this scope")
```

**Explicitly not proposed:** automatic rollback. Compensation is an *effect*, and an effect needs its own grant. Γ's job here is to stop, not to act.

---

## G-RECEIPT — an admitted consequential effect is reproducibly bound to its decision

**Clause:** Γ-0 (extension) · **Verdict on failure:** UNCLEAR

The auditable half of the governance-receipt idea, without cryptography in the kernel. Γ requires that the caller present a receipt reference binding this proposal to the exact invariant set and policy snapshot that judged it; the kernel checks presence and shape, the audit layer checks the signature.

```python
def _decision_is_receipted(ctx):
    if not ctx.proposal.is_consequential():
        return _ok("G-RECEIPT", "Γ-0", "non-consequential proposal")
    if not ctx.receipt_ref:
        return _unclear("G-RECEIPT", "Γ-0",
                        "consequential proposal carries no decision receipt; an unrecorded admission "
                        "cannot be audited afterwards")
    return _ok("G-RECEIPT", "Γ-0", "decision receipt present")
```

UNCLEAR rather than INVALID, deliberately: a missing receipt is a gap in the record, not proof of a violation — and UNCLEAR already refuses.

---

## What would have to be built alongside

1. A test file in the style of `tests/test_gamma_kernel.py`: for each candidate, one control that must still be admitted and at least one attack that must now be refused. The existing 31 kernel tests and the 22 breaches in `tests/test_escape_prevention.py` must pass **unchanged** — an extension that changes an existing verdict is not an extension.
2. Mutation testing per predicate, as `PREDICTION-ERROR-TRUST-GATE-R1` did (11/11 caught).
3. `GAMMA.md` clauses written before the code, not after.
4. A migration note for every new type field, all defaulting so that existing constructions keep their current verdicts.

## Rejected — and why, so it is not re-proposed

```text
model in the predicate          a referee, a classifier, an entropy check: Γ would stop being a function
entropy / log-prob thresholds   needs logit access; unavailable under subscription-only governance
semantic similarity to policy   not total, not reproducible, not falsifiable as a predicate
"is this plan safe" as a field  a field that can carry permission is the thing this system exists to remove
self-reported confidence        measured: 0.93 mean confidence at floor accuracy (RER-F5)
automatic rollback in Γ         Γ validates; Γ never acts. A compensation is an effect and needs its own grant
memory wipe on anomaly          forbidden by Γ-11: destroying the record of a possibly-executed effect is
                                not a return to the initial state
```

## Decision required

Each candidate is independently approvable. A yes on any of them opens a work order that writes the clause into `GAMMA.md` first, then the predicate, then the tests, against a frozen preregistration — with the existing suites required to pass byte-identically. Nothing here is scheduled, and Γ stays as it is until that decision.
