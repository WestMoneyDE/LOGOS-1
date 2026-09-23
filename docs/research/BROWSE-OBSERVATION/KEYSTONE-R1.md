# Browse-use observation on Keystone — R1

**Kind:** measurement record. No claim status changes. Γ is not modified. This record measures a
system outside LOGOS-1 (the browser agent `jev-ultrafast` and the Laya container it calls); it is
kept here because it is the evidence base for the Laya integration and for the fix handed to the
jev-ultrafast owner (`docs/superpowers/specs/2026-09-23-jev-abort-fix-design.md`).

**Date:** 2026-09-23 · **Run:** `jev-observe/runs/20260923-180426-keystone-r1` (72 tasks) ·
**Runner:** `jev-observe/observe.py`, sha256 `75ff6e15d88c965301e379395589b20888cc3693e694abdd19b7d3923226ac54`
(outside both repositories; wraps jev-ultrafast at runtime, modifies nothing) ·
**Run data:** versioned with DVC, see `keystone-r1-run.dvc`.

---

## 1. Result

| Outcome | Tasks | of which Laya was consulted |
|---|---|---|
| `low_confidence` | 64 | 64 |
| `blocked` | 5 | 5 |
| `done` | 3 | 0 |

Every task that consulted Laya failed. The three successes never asked it a question.

**Gate version.** jev-ultrafast's working copy was modified at 17:44 (uncommitted), before this
run started at 18:04. The run used the new gate: stop when the top probability of the executed
question is below 0.4 **and** its gap to the runner-up is below 0.15 — not Laya's `confidence`
field. The earlier finding that `confidence < 0.4` demands a top probability ≥ 0.854 on binary
questions applies to the committed code and to the artefacts in `jev-ultrafast/artifacts/throughput/`,
not to this run.

## 2. Root causes

Each failed task was assigned one primary cause from its plan, history and the questions sent to
Laya. The target of a task is the label the goal quotes (for example `"Chief Architect"`).

| Cause | Tasks | Mechanism |
|---|---|---|
| **B — planner misreads a click as a form entry** | 24 | The text-model planner turns "click *Networking* under *Domains*" into the requirement `{Domains = Networking}`. The agent types into the search box, then asks which button submits the form. |
| **A — target reached, not recognised** | 17 | The correct element was clicked, deterministically and without Laya. `goal_reached()` only recognises arrival by the document title (`titled()`) or by the last URL segment equalling the target name. Keystone's title is always "Keystone"; role pages have no matching URL segment. The agent then asks for the element again, with the clicked one excluded, and Laya must choose among wrong options. |
| **D — target offered, Laya chose wrong** | 15 | See §3. |
| **C — target never offered** | 13 | The target sat in a collapsed sidebar section or outside the candidate list. |

**Laya is the primary cause in 15 of 69 failures (22%).** The other 78% arise in jev-ultrafast's
planner, finish detection and candidate generation.

**Arrival detection, measured.** Of the tasks in which the target was clicked, the URL segment
matched the target name in 2; these 2 are the only two successes of the whole run. Title matching
matched in none, because the title never changes.

**Side effects of forced choices.**
- In 41 tasks whose goal was a click, the agent typed text.
- In 24 tasks the agent collapsed the sidebar that contained its own target: the "submit" question
  offered only interface controls (`Collapse sidebar`, `Toggle theme`, `Assistent öffnen`).
- In 2 tasks a guessed click hit a state-changing control ("zu bevorzugten Rollen hinzufügen").

## 3. Laya's decisions

Measured on the 281 distinct choice questions whose target was identifiable (repeats removed):

| | Questions | Laya correct |
|---|---|---|
| Target not among the options | 236 (84%) | — (no correct answer possible) |
| Target among the options | 45 | 8 (0.178; Wilson 95% 0.093–0.313) |
| Chance level on those 45 | | 0.511 |

Laya is below chance on these questions. On the 36 two-option questions with one correct option:

| | Count |
|---|---|
| Correct option at position 1 (jev pre-ranks the best candidate first) | 36 / 36 |
| Laya chose position 2 | 35 / 36 |

The pattern looks like a position bias and is not one. jev always places the best candidate first,
so any preference against the correct option shows up as "chose position 2". Reversing the option
order leaves accuracy unchanged (§4). The cause is how the question is asked (§4).

## 4. Validation of the proposed corrections

The 45 distinct logged `choice` questions whose target was among the options were replayed in a
separate process inside the Laya container, offline, pinned to revision `5e7b2b1b`, which answered
the Keystone run. Correct means Laya's choice names the target.

| Variant | English base | typed-decisions |
|---|---|---|
| As jev sent it (page text as state) | 9/45 (0.20; Wilson 0.11–0.34) | 11/45 (0.24) |
| Same, option order reversed | 8/45 | 9/45 |
| Same, order-averaged | 7/45 | 10/45 |
| State = goal line only | 11/45 | 11/45 |
| State = goal + finish condition | 10/45 | 11/45 |
| State = `{"target"}`, "Which option names the same thing as \`target\`?" | 31/45 (0.69) | 44/45 (0.98) |
| State = `{"target"}`, "Which element opens \`target\`?" | **40/45 (0.89; 0.77–0.95)** | **45/45 (1.00; 0.92–1.00)** |

**Findings.**

- **Order debiasing: falsified.** Reversing the options changed the choice in 6 of 45 questions and
  did not raise accuracy.
- **Checkpoint alone: no effect.** typed-decisions is no better with page text as the state.
- **State length: no effect.** A state holding only the goal line gave 11/45.
- **Framing: the cause.** Laya classifies a state of named fields against a question that
  references a field in backticks, as the vendor's own guard questions do ("Does \`prompt\`
  contain …"). jev sends page text as one string and asks with no field reference. Asked the
  protocol's way, the English base reaches 40/45 and typed-decisions 45/45.
- **Revision.** An earlier, unpinned replay loaded the newer revision `aa8c91ca` (downloaded from
  Hugging Face during this session into the jev container's cache). It gave the same numbers for
  the first three rows, and 40 of 45 of its choices matched the logged ones.

**Limit.** The correct option is identified by the target string itself. The replay proves that
Laya maps a named target to the option that names it when asked properly. It does not show
robustness to paraphrase, such as a link labelled differently from the goal, and it does not help
in the 236 questions where the target was never offered (causes A–C).

## 5. Changes to the Keystone database

Compared against the `pg_dump` taken before the run (same `COPY` format). 10 of 18 tables changed:

| Table | Added | Cause |
|---|---|---|
| `ArticleView` | 30 | page visits (tested function) |
| `SearchLog` | 69 | searches, including planner-typed text (cause B) |
| `Test` / `TestAttempt` / `TestAttemptAnswer` | 4 / 6 / 120 | role tests started (tested function); 120 empty answers |
| `Conversation` / `Message` | 2 / 2 | two AI summaries — each one `claude -p` call inside Keystone |
| `User` | 1 changed | display name set to "Observer" (task `fn-settings-name`) |
| `UserRoleSelection` | 1 | ENTERPRISE added as favourite — **an unintended guessed click** |
| `FeatureFlags` | 1 | settings page |

No row was removed. The database was **not** restored: a full restore would also remove anything
another session wrote to Keystone during the run window and cannot be undone. A targeted cleanup
of the rows created during the run window is listed in the spec's handover section.

## 6. Limits

- One application. Keystone is a single-page app with a constant title; that is exactly the
  condition that defeats title-based arrival detection, and other sites will differ.
- The target label is taken from the quoted goal text and matched as a substring; a candidate that
  names the target in a longer label counts as the target. This proxy was not checked by hand.
- Causes were assigned by rules over the logs, one primary cause per task. Several tasks show more
  than one failure; the table counts only the first.
- The run was stopped by the founder after the first full pass; there is no repetition, so no
  run-to-run variance is available.
