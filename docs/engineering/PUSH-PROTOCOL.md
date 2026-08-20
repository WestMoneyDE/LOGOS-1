# LOGOS-1 Push Protocol

Every substantive push should leave the repository more internally consistent than it found it.

## 1. Implementation

- code/config/artifacts reflect the requested change;
- no unrelated authority expansion;
- failures remain visible rather than narrated as success.

## 2. Validation

- run the smallest relevant tests/diagnostics **before** the repository write where possible;
- add regression coverage for newly fixed failure modes;
- record blockers instead of replacing unavailable real evidence with synthetic substitutes.

## 3. One-shot external execution

For GitHub Actions and other external-evidence runs:

- finish the frozen contract, hashes, resource gate and persistence path before the content push;
- make **one coherent prepared content push** for the session;
- execute the frozen scientific run at most once in that session;
- do **not** automatically retry failed, cancelled, timed-out, blocked or resource-incomplete runs;
- classify infrastructure/model/data/provider failures as transport/runtime outcomes, not scientific nulls;
- a state-persistence/bot commit must be guarded so it cannot retrigger the scientific job;
- a later rerun requires an explicit new work order/user instruction and a materially changed prerequisite or protocol.

A failure is information about the execution path. Repetition is not a substitute for diagnosis.

## 4. Architecture propagation

If subsystem meaning changed, update the relevant architecture document. Do not leave README, docs and code describing different systems.

## 5. Capability propagation

Update `CAPABILITIES.md` when the push adds, removes, promotes, demotes or materially changes an operational/research capability. If there is no capability delta, say so in the session/PR summary.

## 6. Evidence propagation

If a scientific claim changes, update:

- raw evidence location;
- verdict;
- evidence maturity;
- falsifier/assumption boundary;
- what remains unproven.

Do not promote from a transport failure or partial return.

## 7. Session persistence

A substantive LOGOS session should leave a checkpoint under `09-SESSIONS/` containing enough context for another human or coding agent to resume without the chat transcript.

Minimum session checkpoint:

- objective;
- files/areas changed;
- tests/evidence;
- decisions/verdicts;
- blockers/open questions;
- next action;
- commit/PR reference where applicable.

## 8. Coding-agent memory

Persistent project knowledge belongs in versioned repo files. Machine-local agent auto-memory may help ergonomics but must not become the sole copy of an architectural decision or safety invariant.

## 9. Final consistency check

Before merge/push completion ask:

- does `CURRENT-WORK-ORDER.md` still mean what it says?
- does `CAPABILITIES.md` match reality?
- do `AGENTS.md`/`CLAUDE.md` still guide agents correctly?
- did the change weaken `AdaptiveState != Authority` or `OUTCOME_UNKNOWN != NOT_EXECUTED`?
- did any failed external run get retried without a new explicit work order?
- can a fresh agent understand what changed without this chat?
