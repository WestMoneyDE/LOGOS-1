# Keystone R1 — Laya rescored by question semantics

Scope: the 501 logged Laya decision calls of `docs/research/BROWSE-OBSERVATION/keystone-r1-run/`.
All rows, labels, replays and stop attributions are in `rescore.json` (same directory). The
scripts read the run data from `../keystone-r1-run/` (`dvc pull` restores it). Scripts:
`labels.py` (gold rules), `analyze.py` (sections 1, 2, 4), `replay_rescore.py` (section 3, run in
`jev-ultrafast-laya`), `merge_replay.py`, `tables.py`.

## 0. What was wrong in KEYSTONE-R1 §3–§4

The earlier gold rule marked an option correct when its text contained the goal's quoted target.
34 of the 45 "target offered" questions were `holds` questions ("Which requirement does this form
field hold?") about an empty search textbox. The option `"<what> = <target>"` contains the target,
so the rule scored it as gold. The correct answer is `none of these`, because an empty field holds
no requirement. The replay then rewrote those questions as "which option names `target`?", which
asks a different question.

Rescored with the rules below, the same 45 questions give:

| Kind | n | Old rule: Laya "correct" | New labels: gold present / absent / unlabelled | Laya right (new) |
|---|---:|---:|---:|---:|
| `holds` | 34 | 1 | 0 / 34 / 0 | 33 (chose `none`) |
| `item` | 5 | 2 | 5 / 0 / 0 | 1 |
| `next` | 2 | 2 | 2 / 0 / 0 | 2 |
| `submit` | 2 | 2 | 2 / 0 / 0 | 2 |
| `done` | 2 | 1 | 1 / 0 / 1 | 0 |
| **Total** | **45** | **8 (0.18)** | 10 / 34 / 1 | **38 / 44 (0.86; Wilson 0.73–0.94)** |

The one `done` row labelled here (`fn-role-panel-article`, tick 3) was scored correct by the old
rule. It is wrong under the new label: the URL was `/`, not an article page, and Laya answered
`finish` with p = 0.80.

## 1. Labels per question kind

Deduplication key: (task, qid, criteria). `done` and `met` rows also include the state text in the
key, because their truth depends on the page. This gives 340 distinct rows from 501 calls.

| Kind | Distinct | Labelled | Unlabelled (1 option) | Unlabelled (other) | Gold present | Gold absent |
|---|---:|---:|---:|---:|---:|---:|
| `holds` | 47 | 47 | 0 | 0 | 0 | 47 |
| `item` | 24 | 24 | 0 | 0 | 5 | 19 |
| `next` | 53 | 47 | 0 | 6 | 2 | 45 |
| `submit` | 139 | 138 | 0 | 1 | 8 | 130 |
| `done` | 20 | 9 | 0 | 11 | 9 | 0 |
| `met` | 6 | 3 | 0 | 3 | 3 | 0 |
| `set` | 6 | 4 | 0 | 2 | 0 | 4 |
| `option` | 1 | 1 | 0 | 0 | 0 | 1 |
| `field` | 44 | 6 | 38 | 0 | 0 | 6 |
| **Total** | **340** | **279** | **38** | **23** | **27** | **252** |

61 rows are unlabelled. 38 of them are single-option `field` questions: they have one option,
p = 1.0 by construction, and no choice to score. For `done` and `met`, "gold present" means the
row's truth value is known. It does not mean an option was present.

Rules (all mechanical, in `labels.py`):

- **`holds`**: gold = the requirement whose value equals the field's current value. If the field is
  `(empty)` or has no value (a button), gold = `none`. All 47 fields were empty, valueless, or
  held a value (`Claude Code CLI`) that equals no requirement.
- **`item` / `next`**: gold = an option whose label, after the role prefix, equals the goal's quoted
  click target. A link whose name starts with the target followed by card metadata also counts
  (article cards `X KB-0385 …`, role cards). Textboxes and star buttons never count. If no option
  qualifies, the gold is absent. Six `next` rows are unlabelled because the goal has a
  navigational precondition, or the offered route has been renamed (see `rescore.json`, `reason`).
  Three gold-absent `next` rows are error pages that offered only `Reload`/`Back`. They carry the
  flag `error_page_recovery_offered`; on those pages `Reload` is a defensible action.
- **`submit`**: gold = `Speichern`, `Antwort einreichen` or `Weiter` when offered. If only
  `Toggle theme`, `Assistent öffnen`, `Collapse/Expand sidebar` or `Chat schließen` is offered,
  the gold is absent. A row offering `Später einrichten überspringen` is unlabelled. Three of the
  eight gold-present rows are settings pages where the goal does not name `Speichern`, and the
  field that `Speichern` would save holds jev's mis-fill `Claude Code CLI` (flag
  `submit_not_named_in_goal`). The literal answer is correct; acting on it would be harmful.
- **`done`**: labelled only from direct evidence. For `nav-collapse`, the sidebar button label at
  that tick is used. For `fn-role-test-start`, the state text is used: `Test wird vorbereitet…`
  means not started, and a visible answer box means started. A URL that cannot satisfy the
  finish condition (`/` or `/domains/…` for an article goal) is also used. The `/srs` tasks,
  `fn-role-test-answer`, and article pages whose panel order is not logged are unlabelled.
- **`met`**: `yes` when the current value equals the requirement literally. `no` when a text
  requirement is compared with different text. Unlabelled when the requirement is a state word
  (`checked`, `dark mode`) and the "current value" is an element label.
- **`set` / `option`**: gold = `none` when no offered element carries the value. Unlabelled when a
  sidebar link carries the value's name (`link Platform Architect` for "role = Platform
  Architect"): the logs do not settle whether a navigation link sets the value.
- **`field`**: labelled only when multi-option. None of the offered elements (search box,
  `Anzeigename` box, chat buttons) is the requirement's control, so the gold is absent.

## 2. Laya accuracy on the logged answers

Gate = jev's stop test, `top < 0.40 and gap < 0.15` (`jev_ultrafast/graph.py::is_ambiguous`).

**Gold present:**

| Kind | Correct / n | Wilson 95% | Gate fired | Wrong and gate passed | top min/med/max | gap min/med/max |
|---|---:|---:|---:|---:|---:|---:|
| `item` | 1 / 5 | 0.04–0.62 | 1 | 4 | 0.39 / 0.52 / 0.55 | 0.03 / 0.10 / 0.31 |
| `next` | 2 / 2 | 0.34–1.00 | 0 | 0 | 0.63 / 0.65 / 0.67 | 0.34 / 0.38 / 0.43 |
| `submit` | 7 / 8 | 0.53–0.98 | 2 | 1 | 0.29 / 0.50 / 0.72 | 0.03 / 0.25 / 0.61 |
| `done` | 7 / 9 | 0.45–0.94 | 0 | 2 | 0.60 / 0.80 / 1.00 | 0.35 / 0.64 / 0.99 |
| `met` | 3 / 3 | 0.44–1.00 | 0 | 0 | 0.91 / 0.94 / 0.99 | 0.82 / 0.88 / 0.98 |

Element choice with the target present (`item` + `next`) is **3 / 7 (0.43; Wilson 0.16–0.75)**.
The four `item` errors are the three 2-option sidebar questions (`Enterprise`, `GenAI`,
`Platform Architect` against a `Praktische … Lerntiefe` article link; the wrong option has
p = 0.52–0.55) and `nav-domain-00` (`link Navigation` against six article links whose text
contains "Navigation"). The gate passed all four, so jev clicked the wrong link. The two `done`
errors are one false `finish` (`fn-role-panel-article` tick 3, home page with search results,
p = 0.80) and one missed finish (`nav-collapse` ticks 3/5, sidebar collapsed, `other` p = 0.84).
Eight of the nine labelled `done` rows have truth "not finished", so this figure mostly measures
the rejection of non-finish pages. Counted per call instead of per distinct row: `item` 1/8, `next` 2/2,
`submit` 9/11, `done` 21/24, `met` 7/7.

**Gold absent, `none of these` offered:**

| Kind | n | Chose `none` | Wilson 95% |
|---|---:|---:|---:|
| `holds` | 47 | 44 | 0.83–0.98 |
| `set` | 4 | 1 | 0.05–0.70 |
| `option` | 1 | 1 | 0.21–1.00 |
| **Total** | **52** | **46 (0.88)** | 0.77–0.95 |

The three `holds` misses are `search = Settings` (twice, p = 0.57) and `search = Databases,
storage, search & caching` (p = 0.54). All three are near 0.5. The three `set` misses are
`button Reload` for "Domains = Backend & APIs" (p = 0.73) and two wizard role questions answered
with a different role's sidebar link. The gate stopped one of those two (tick 7, top 0.25).

**Gold absent, no `none` option (no option is correct; a stop is the only safe outcome):**

| Kind | n | Gate fired | Wilson 95% | top ≥ 0.40 | top min/med/max | gap min/med/max |
|---|---:|---:|---:|---:|---:|---:|
| `item` | 19 | 13 | 0.46–0.85 | 6 | 0.11 / 0.33 / 0.62 | 0.00 / 0.09 / 0.46 |
| `next` | 45 | 26 | 0.43–0.71 | 16 | 0.10 / 0.31 / 0.92 | 0.00 / 0.09 / 0.89 |
| `submit` | 130 | 17 | 0.08–0.20 | 113 | 0.35 / 0.57 / 0.77 | 0.00 / 0.20 / 0.60 |
| `field` | 6 | 0 | 0.00–0.39 | 6 | 0.46 / 0.55 / 0.58 | 0.05 / 0.10 / 0.17 |

On `item` and `next`, the distribution was flat when the target was absent in 39 of 64 rows, which
is the appropriate response. On `submit` it was flat in only 17 of 130: Laya picked a chrome
button with top ≥ 0.40 in 113 of them. That is a mis-calibration on an unanswerable question,
and it is how the `Toggle theme` / `Collapse sidebar` loops were executed. jev asked "which button
submits the filled form?" when no form had been filled and gave Laya no `none` option.

## 3. Framing replay, done correctly

**Setup.** A separate process in `jev-ultrafast-laya`, offline (`HF_HUB_OFFLINE=1`), with
`laya.Agent(<snapshot 5e7b2b1b…>)`, subfolders `None` / `multilingual` / `typed-decisions`,
laya 0.3.6, CPU. The logged question id was kept. The container was recreated externally at
08:46:48Z during the first attempt, which killed that process. The replay was re-run in the new
container from the same cache volume. No container was stopped or restarted by this work.

**Reproduction: the earlier 40/45 mismatch is explained.** The Laya service the run used
(jev-ultrafast's `docker/laya-server/app.py`, not LOGOS-1's `infra/laya`) does not call the English checkpoint. It calls `laya.Router(preload=True)`, which routes by the
language of the state text. The Keystone page text is mostly German, so 194 of the 340 distinct
questions went to the **multilingual** checkpoint, including 57 of 77 `item`/`next` and 125 of
139 `submit`.

| Replay of variant (a), as logged | Choice matches logged | Probabilities |
|---|---:|---|
| Checkpoint chosen by `Router.route()` (pinned snapshot) | **340 / 340** (english 146/146, multilingual 194/194) | identical (max abs diff 0.0000) |
| English checkpoint for every question | 239 / 340 (english-routed 146/146, multilingual-routed 93/194) | max abs diff 0.71 |
| English, on the earlier 45 | 40 / 45 | — |

The earlier replays (KEYSTONE-R1 §4) ran the English checkpoint, which never answered the
multilingual-routed questions in the run. That is the 5/45 non-reproduction. Its "as logged"
column did not measure the production model.

**Framing, on element-choice questions with the gold present only (`item`/`next`, n = 7):**

| Variant | English | typed-decisions | Routed (production path) |
|---|---:|---:|---:|
| Logged answers | — | — | 3 / 7 |
| (a) page-text state, original instruction | 6 / 7 | 7 / 7 | 3 / 7 (= logged) |
| (b) `{"target"}` + "Which element opens \`target\`?" | 6 / 7 | 7 / 7 | 6 / 7 |
| (c) `{"target", "page"}` + same | 7 / 7 | 7 / 7 | 7 / 7 |

Wilson 95%: 3/7 = 0.16–0.75; 6/7 = 0.49–0.97; 7/7 = 0.65–1.00. The intervals overlap heavily. On
the English checkpoint, reframing adds at most one question over the logged framing (6 → 6 or 7).
Most of the gain comes from moving the four `item` errors off the multilingual checkpoint, not
from the framing: English and typed-decisions answer all four correctly with the logged page-text
state. With n = 7, neither effect is established.

Contrary evidence on checkpoint choice: on `submit` with the gold present (n = 8), the logged
routed answers score 7/8 and the English checkpoint scores 4/8. Across all 15 gold-present
element choices (`item` + `next` + `submit`), routed and English both score 10/15. The routing
shifts errors between question kinds; on this data it does not change the total.

**Holds control (n = 47):**

| Variant | Chose `none` (correct) | Chose the requirement |
|---|---:|---:|
| As logged: routed / English / typed-decisions | 44 / 44 / 44 | 3 / 3 / 3 |
| Target framing applied: "Which element opens \`target\`?", English | 15 | 32 |
| same, typed-decisions | 3 | 44 |
| "Which option names the same thing as \`target\`?", English | 26 | 21 |
| same, typed-decisions | 9 | 38 |

As logged, Laya answers `holds` correctly on 44 of 47 on every checkpoint. The target framing
turns a correct `none` into the requirement option in up to 44 of 47 cases. It must not be applied
to `holds`, `met`, `set`, `option` or `done` questions. Doing so produced the 44/45 and 45/45
figures in KEYSTONE-R1 §4.

## 4. The 64 `low_confidence` stops

The triggering question was identified by matching the step's `choice_probabilities` to exactly
one entry in `raw_answers` (unique in all 64 stops).

| Trigger kind | Label | Stops |
|---|---|---:|
| `next` | gold absent | 26 |
| `submit` | gold absent | 17 |
| `item` | gold absent | 13 |
| `set` | gold absent (`none` offered; Laya chose a wrong link) | 1 |
| `submit` | gold present (Laya's choice correct) | 3 |
| `item` | gold present (Laya's choice correct) | 1 |
| `next` | unlabelled | 3 |
| **Total** | | **64** |

- **57 of 64 stops (0.89; Wilson 0.79–0.95)** fired on a question with no correct option: the
  target was not among the candidates, or only chrome was offered. In one more (`set`), Laya's
  pick was wrong. On these the stop prevented a wrong click.
- **4 stops fired on a correct answer**: `fn-roles-open` (`link Platform Architect …` card,
  top 0.39) and the three `Speichern` rows on settings pages. Two of those three are the
  `submit_not_named_in_goal` cases, where acting would have saved jev's mis-filled display name.
- 3 stops are on unlabelled `next` rows.
- The per-task list, with top probability and gap, is in `rescore.json` → `stops`. The gold-absent
  submit stops have 3 options and top 0.35–0.40, which is close to uniform (1/3). The item/next
  stops have 4–20 options and top 0.10–0.38.
- Counterfactual from the replay: had every question run on the English checkpoint, 17 of the 64
  stops would not have fired.

## 5. What the corrected numbers say about Laya and jev

- On questions it can answer from what it is given, Laya is mostly right. `holds`: 44/47. `met`:
  3/3. `none` when `none` is offered: 46/52. `done` where the truth is known: 7/9. Real submit
  controls when offered: 7/8.
- It is weak on one category: choosing the target link among similar article/sidebar links with the
  target present, at 3/7 on the multilingual checkpoint that production routed to. n = 7 is too
  small to rank checkpoints or framings.
- Most of the run's questions had no correct answer. 252 of 279 labelled rows have the gold absent,
  and 200 of those offered no `none` option (130 `submit`, 64 `item`/`next`, 6 `field`). Another
  38 `field` questions had a single option. jev generated these questions. It planned `search = X`
  requirements for plain navigation goals, asked for a submit button when no form was filled,
  built candidate lists that left out the target, and offered no abstain option.
- The low-confidence stops are mostly correct abstentions on those unanswerable questions (57/64),
  not Laya failures. The loops happened where Laya was *not* flat on an unanswerable `submit`
  question (113/130 with top ≥ 0.40) and jev executed the chrome click.
- The earlier conclusion that Laya chose the offered target in 8/45 (0.18) and that reframing lifts
  it to 40–45/45 is withdrawn. The 0.18 came from a gold rule that did not match the `holds`
  semantics. The 40–45/45 came from rewriting `holds` questions into a different question.

## Limitations

- All labels are derived mechanically from logs (goal text, option labels, state text, step URL and
  action) by the rules above. No human annotated any row. The rules encode judgement calls,
  including card-link prefixes counting as naming the target, `Reload` on error pages counting as
  gold absent, and literal `Speichern` counting as gold. Each row carries its `reason` and `flags`.
- Gold-present sample sizes are small (`item` 5, `next` 2, `submit` 8, `done` 9, `met` 3), so
  every per-kind accuracy has a wide interval.
- 61 of 340 distinct rows are unlabelled, including 11 of 20 `done` rows. Laya's accuracy on
  finish detection over `/srs` pages is not measured.
- Option labels are truncated (about 75 characters) as jev sent them, so the gold rule can only
  use the visible prefix.
- Deduplicating by (task, qid, criteria) hides state variation within `item`/`next`/`submit`
  groups. Per-call counts are given alongside.
- Replay routing uses the laya 0.3.6 `Router` in the current container. The router code active
  during the run is assumed to be the same; the 340/340 exact reproduction supports this.
- The English-only counterfactuals (section 3, section 4 last bullet) are replays, not runs. They
  do not include the page changes a different click would have caused.
