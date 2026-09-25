# Browse-use observation on Keystone — R1

**Kind:** measurement record, corrected 2026-09-25 (§0). No claim status changes. Γ is not modified. This record measures a
system outside LOGOS-1 (the browser agent `jev-ultrafast` and the Laya container it calls); it is
kept here because it is the evidence base for the Laya integration and for the fix handed to the
jev-ultrafast owner (`docs/superpowers/specs/2026-09-23-jev-abort-fix-design.md`).

**Date:** 2026-09-23 · **Run:** `jev-observe/runs/20260923-180426-keystone-r1` (72 tasks) ·
**Runner:** `jev-observe/observe.py`, sha256 `75ff6e15d88c965301e379395589b20888cc3693e694abdd19b7d3923226ac54`
(outside both repositories; wraps jev-ultrafast at runtime, modifies nothing) ·
**Run data:** versioned with DVC, see `keystone-r1-run.dvc`.

---

## 0. Correction (2026-09-25)

The first version of this record (commit `c0c6eca`) reported that Laya chose the offered target in
8 of 45 questions, below chance; that a reframed question lifted this to 40–45/45; and a root-cause
table (planner 24, arrival 17, Laya 15, never offered 13; "Laya is the primary cause in 22%").
An audit of every number and a rescoring by question semantics withdrew these claims:

- 34 of the 45 "target offered" questions were `holds` questions ("Which requirement does this
  form field hold?") about an empty search box. The correct answer is "none of these"; Laya gave it
  in 33 of 34. The gold rule (the option contains the goal's target) scored those as wrong.
- The framing replay rewrote those `holds` questions into a different question, and it ran the
  English checkpoint, although the run's Laya service routed 194 of 340 distinct questions to the
  multilingual checkpoint. That is why only 40 of 45 logged choices were reproduced.
- The cause table was assigned by rules that were not committed and could not be reproduced.

Sections 1–4 below are rebuilt from committed, rerunnable scripts. The rescoring is in
`keystone-r1-rescore/` (`RESCORE.md`, `labels.py`, `analyze.py`, `replay_rescore.py`,
`merge_replay.py`; rerunning them reproduces `rescore.json` byte for byte). A replay on the
checkpoint the router chose reproduces **340 of 340** logged choices with identical probabilities.

## 1. Result

| Outcome | Tasks | of which Laya was consulted |
|---|---|---|
| `low_confidence` | 64 | 64 |
| `blocked` | 5 | 5 |
| `done` | 3 | 0 |

Two of the three `done` are verified by the URL (`nav-domain-01`, `nav-domain-02`). The third,
`nav-home`, ended on `/domains`, not on the home page: a false `done`.

**Gate version.** jev-ultrafast's working copy was modified at 17:44 (uncommitted), before this
run started at 18:04. The run used the new gate: stop when the top probability of the executed
question is below 0.4 **and** its gap to the runner-up is below 0.15 — not Laya's `confidence`
field.

## 2. Where the failures arise (reproducible measurements)

| Mechanism | Measured | Source |
|---|---|---|
| The planner turns "click X" into a form requirement | 30 of 72 logged plans rejected by a plan validator; 28 of them type a quoted click target into a field | `jev-ultrafast/tests/data/keystone_r1_plans.json`, `tests/test_planner_guard.py` |
| Arrival not recognised | 6 tasks reached the target URL (23 steps on a target page). The old `goal_reached` recognised 2 of the 23 steps; the page title is always "Keystone" and `aria-current` does not exist in the app | offline replay over `steps.jsonl` and live page headings |
| Target never offered | the snapshot drops every element outside the viewport, and `scroll_down` scrolls the window, never the sidebar: 24 of 53 link targets were offered | live DOM measurement, 53 link targets |
| Interface buttons chosen as a step | 180 executed clicks on `Collapse sidebar`, `Expand sidebar`, `Toggle theme`, `Assistent öffnen` in 30 tasks | `steps.jsonl` |
| Questions with no correct option | 252 of 279 labelled distinct questions; 200 of them offered no "none of these" | §3 |

**Side effects of forced choices.** In 1 task (`nav-roles-all`) a guessed click hit a
state-changing control ("… zu bevorzugten Rollen hinzufügen"; see §5).

## 3. Laya's decisions, scored by what each question asks

340 distinct questions from 501 calls; 279 labelled by mechanical rules (`labels.py`), 61 not
(38 of them single-option questions with nothing to choose).

| Situation | Laya | 95% Wilson |
|---|---|---|
| "none of these" offered and correct (`holds`, `set`, `option`) | chose it in 46 of 52 | 0.77–0.95 |
| `holds` alone | 44 of 47 | 0.83–0.98 |
| Target element offered (`item` + `next`) | chose it in 3 of 7 | 0.16–0.75 |
| Real submit control offered | 7 of 8 | 0.53–0.98 |
| Finish question with known truth (`done`) | 7 of 9 (8 of the 9 are "not finished") | 0.45–0.94 |
| No correct option and no "none": `item` / `next` | answer flat (stop fired) in 39 of 64 | — |
| No correct option and no "none": `submit` | answer flat in 17 of 130; top ≥ 0.40 on an interface button in 113 | — |

**The 64 stops.** 57 of 64 (0.89; Wilson 0.79–0.95) fired on a question with no correct option;
each prevented a wrong click. 1 more stopped a wrong pick. 4 stopped a correct answer — two of
them `Speichern` clicks that would have saved a wrong value jev had typed into the display-name
field. 3 are on unlabelled questions.

**Reading.** Laya answers most questions it can answer from what it is given. Its measured
weakness is choosing the target among similar links (3/7; n too small to rank checkpoints).
The run failed mainly because jev asked questions without a correct option and without a way to
say so, and executed the answer when Laya was not flat.

## 4. Replays

| Replay | Result |
|---|---|
| Logged questions on the checkpoint the router chose (pinned `5e7b2b1b`) | 340 / 340 choices, probabilities identical |
| Same questions all on the English checkpoint | 239 / 340 |
| Target framing (`{"target"}` + "Which element opens \`target\`?"), element questions with the target present | routed 3/7 → 6/7 (b) and 7/7 (c); English 6/7 → 6–7/7; typed-decisions 7/7 throughout. n = 7: no effect established |
| Target framing applied to `holds` | turns a correct "none" into a wrong requirement in up to 44 of 47 |

The framing change is therefore not adopted as a correction. It must never be applied to `holds`,
`met`, `set`, `option` or `done` questions. The corrections adopted in jev-ultrafast are listed in
the spec (`docs/superpowers/specs/2026-09-23-jev-abort-fix-design.md`, §11).

## 5. Changes to the Keystone database

Compared against the `pg_dump` taken before the run (same `COPY` format). 10 of 18 tables changed:

| Table | Added | Cause |
|---|---|---|
| `ArticleView` | 30 | page visits (tested function) |
| `SearchLog` | 69 | searches, including text the planner typed for click goals (§2) |
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
- Every label is derived mechanically from the logs by the rules in `keystone-r1-rescore/labels.py`;
  no human checked a row. Some rules are judgement calls (card links count as naming the target,
  `Reload` on an error page counts as no correct option, a literal `Speichern` counts as correct).
- Gold-present samples are small (`item` 5, `next` 2, `submit` 8, `done` 9); every per-kind
  accuracy has a wide interval.
- Offline replays of the arrival rule use page headings fetched from the live app afterwards, not
  recorded during the run.
- The run was stopped by the founder after the first full pass; there is no repetition, so no
  run-to-run variance is available.
