# jev-ultrafast: stop aborting — design

**Kind:** engineering design for a system outside LOGOS-1, written here and handed to the session
that owns `jev-ultrafast`. No LOGOS claim status changes; Γ is not modified.
**Date:** 2026-09-23
**Evidence:** `docs/research/BROWSE-OBSERVATION/KEYSTONE-R1.md` (72-task run, root causes, Laya
accuracy, validation), three research strands summarised in §8, and the verification of a pasted
advisory text (§9).

## 0. The problem, measured

72 Keystone tasks: 64 `low_confidence`, 5 `blocked`, 3 `done`. Every task that consulted Laya
failed. Root causes of the 69 failures:

| Cause | Tasks | Fix |
|---|---|---|
| B planner misreads a click as a form entry | 24 | F2 |
| A target reached, not recognised | 17 | F1 |
| D target offered, Laya chose wrong | 15 | F4 |
| C target never offered (collapsed / not a candidate) | 13 | F3 |

Laya is the primary cause in 22% of failures. The founder's three points map onto this: the
threshold (F5), Laya deciding better (F4), and not aborting the task (F5 ladder). The largest
causes, A and B, are neither — they are arrival detection and planning.

## 1. Principles

- **The unit of failure is one decision, not the task.** A decision that cannot be made moves one
  rung down a ladder (§F5); only an exhausted ladder ends the task, with a specific status.
- **Reversibility decides how far a guess may go.** A reversible step may be tried, verified and
  undone. A step that writes server state or cannot be undone is never guessed.
- **A flat distribution over wrong options is a correct answer.** When the target is not among the
  options, the right move is to change the options, not to pick one.
- **Every change is measured before and after**, on task success, abort rate, wrong-action rate
  and accepted-decision error together. The abort rate alone is never the success metric.

## F1 — Arrival detection (cause A, 17 tasks)

`goal_reached()` recognises arrival only by the document title (`titled()`) or the last URL
segment equalling the target name (`policy.py`, `goal_reached`). On Keystone the title is always
"Keystone" and role pages have no matching segment; arrival was recognised in 2 tasks — exactly the
two successes.

Add signals, evaluated after every action and before the next decision is chosen:

1. the main heading (`h1`, else the first `h2` of the main region) matches the target with the
   existing word-overlap rule used by `titled()`;
2. an element whose label equals the target carries `aria-current="page"`, `aria-selected="true"`
   or `aria-expanded="true"`;
3. the last executed step clicked an element whose label equals the target **and** the page changed
   (URL, heading or main-region hash), and no signal contradicts arrival.

A final judge re-checks arrival on the current page before `done` is reported.
**Predicted result:** of the 17 cause-A tasks at most 3 still fail; premature stops (done reported
while the target is not open) do not increase.

## F2 — Planner guard (cause B, 24 tasks)

After `plan_goal()`, a deterministic check: if the goal asks to click, open or select a quoted label
(`click`, `open`, `klick`, `öffne`, …) the plan must set `open` to that label and must not contain a
requirement whose value equals it. Otherwise re-plan once with the correction stated; if the second
plan fails the same check, use the deterministic plan `{open: <quoted label>, requirements: []}`.
**Predicted result:** cause B falls from 24 to at most 3; "typed text although the goal was a
click" falls from 41 tasks to 0.

## F3 — Candidate generation (cause C, 13 tasks; sidebar collapsed in 24 tasks)

1. **Interface controls are never candidates** for `submit`, `item` or `next` unless the goal names
   them: sidebar collapse/expand, theme toggle, language switch, assistant/chat launchers. In 24
   tasks the agent collapsed the sidebar holding its own target because only such controls were
   offered for "which button submits the form".
2. **Expand before asking.** If no candidate's label contains the target, expand collapsed
   containers (`aria-expanded="false"`) whose label matches a section the goal names (e.g.
   "Domains"), re-observe, then build candidates.
3. **"None of these" is always an option** in `item`, `next` and `submit` questions, so that an
   absent target produces a ladder step instead of a forced choice.

**Predicted result:** self-collapsed sidebar 24 → 0; cause C 13 → at most 5.

## F4 — Laya decisions (cause D, 15 tasks)

1. **Ask Laya the way its protocol expects — the main fix (validated, §F4-V).** Laya classifies a
   *state of named fields* against a question that references those fields in backticks (the
   vendor's own guard questions: "Does \`prompt\` contain …"). jev sends the whole page text as one
   string and asks "Which element opens Enterprise Architect?" with no field reference, so Laya has
   nothing to compare the options with and ranks them by the page text. Send
   `state = {"target": <plan item>}` and ask **"Which element opens \`target\`?"**; keep each
   candidate's role, label and current value in its option.
2. **Use `laya-typed-decisions` for `choice` questions** — with the framing of item 1 it reached
   45/45 against 40/45 for the English base (§F4-V). Without the framing the checkpoint makes no
   difference.
3. **Exact-label match before Laya.** If exactly one candidate's label equals the target, select it
   deterministically, with no model call.
4. **Not adopted — option-order debiasing.** The measured pattern "correct option first, Laya chose
   the second" was confounded: jev always puts the best candidate first. Reversing the order left
   accuracy unchanged and flipped the choice in 6 of 45 questions (§F4-V). Recorded as negative
   evidence.
5. **Not adopted — shortening the state.** Goal-only or goal-plus-finish states changed nothing
   (§F4-V). The failure was the framing, not the length.
6. **Later, measured:** fine-tune on labelled jev decisions using the vendor's browser recipe, and
   test paraphrased targets (a link named differently from the goal), which §F4-V does not cover.

### F4-V — validation on the logged questions

Replay of the 45 distinct logged `choice` questions whose target was among the options, run in a
separate process inside the Laya container, offline, pinned to revision `5e7b2b1b` (the one that
answered the Keystone run). Correct = Laya's choice names the target.

| Variant | English base | typed-decisions |
|---|---|---|
| As jev sent it (page text as state) | 9/45 (0.20; Wilson 0.11–0.34) | 11/45 (0.24) |
| Same, option order reversed | 8/45 | 9/45 |
| Same, order-averaged | 7/45 | 10/45 |
| State = goal line only | 11/45 | 11/45 |
| State = goal + finish condition | 10/45 | 11/45 |
| **State = {"target"}, "Which option names the same thing as \`target\`?"** | 31/45 (0.69) | 44/45 (0.98) |
| **State = {"target"}, "Which element opens \`target\`?"** | **40/45 (0.89; 0.77–0.95)** | **45/45 (1.00; 0.92–1.00)** |
| Chance level | 0.51 | 0.51 |

The unpinned run on the newer revision `aa8c91ca` gave the same numbers for the first three rows;
40 of 45 of its choices matched the logged ones.

**Limit.** The correct option is identified by the target string itself, so this proves that Laya
maps a named target to the option that names it once asked properly. It does not show robustness to
paraphrase — a link labelled differently from the target — which needs hand labels.

## F5 — Gate and fallback ladder (the founder's point 3)

**Gate.** Keep the working-copy gate (top probability and gap, not Laya's `confidence`). Its
thresholds become per group — (question type, option-count bucket {2, 3–6, 7–10, 11+}) — fitted on
labelled decisions with the selective-risk procedure of Geifman & El-Yaniv (SGR) or Learn-then-Test
once a group has about 200 accepted labelled decisions; until then the current values stand and the
group is reported as uncalibrated.

**Ladder** — replaces the task-level `low_confidence` stop. Each uncertain decision descends:

| Rung | Action | When |
|---|---|---|
| 1 | Re-observe; expand collapsed sections (F3.2) | always first |
| 2 | Re-ask with the named-target framing (F4.1) on `laya-typed-decisions`, narrowed to ≤ 5 options plus "none of these" | if still uncertain |
| 3a | **Reversible step:** act on the best option, verify arrival or the expected change (F1), on failure go back (`history.back` or the stored URL), exclude the candidate, retry | budget: 2 retries per decision |
| 3b | **Irreversible or state-writing step:** never guess → `needs_approval` | see classification below |
| 4 | Skip — only a requirement the plan marks optional, or one verifiably met; reported as "done, n skipped", never as plain "done" | |
| 5 | Stop with a specific status (`target_not_found`, `ambiguous_after_retries`, `needs_approval`) and the evidence | ladder exhausted |

**Reversibility classification.** Deterministic, extending the existing walls: navigation links and
opening an item are reversible; controls that write server state are not — submit/save/send/book,
start test, submit answer, add/remove favourite, delete. Measured: 2 unintended favourites and
started tests came from guessed clicks.

**LLM escalation** is an experiment flag, off by default. The vendor measured escalation to 8B/27B
models as worse than the fine-tuned Laya (27B: 0.603 top-1 at 4.7 s vs 0.623 at 21 ms). It is enabled
only in a measured run that records how often the LLM overturns a correct Laya choice.

**Predicted result:** task-level `low_confidence` aborts disappear as a status; task success rises;
the wrong-action rate (actions later backtracked, or a wrong item left open) is reported next to it
and must not exceed the success gain.

## F6 — Overshoot

Covered by F1: arrival is checked before the next decision, so no click follows a reached target.
Measured on this run: 5 tasks reached the target and continued; 4 left it.

## 7. Measurement

- **MLflow** experiment `jev-abort-fix` (lab stack, `127.0.0.1:55000`). One run per configuration:
  baseline; +F1; +F2; +F3; +F4; +F5; all; and one lesion run per ladder rung. Parameters: fixes on,
  checkpoint, gate thresholds per group, laya version, device. Metrics: task success, abort rate,
  wrong-action rate, accepted-decision error with its Wilson upper bound, overshoot rate,
  human asks per task, latency p50/p95. Artifacts: `calls/steps/tasks.jsonl`.
- **DVC** versions the labelled replay set (`docs/research/BROWSE-OBSERVATION/keystone-r1-run`); its
  hash goes into every threshold record.
- **Replay first.** F4 is evaluated offline on the logged questions before any live run. F1–F3 and
  F5 need live runs, on a local fixture site before Keystone.

## 8. Evidence base (research, 2026-09-23)

- Gate on the calibrated top probability; per-group thresholds from labelled data with a
  finite-sample guarantee (Geifman & El-Yaniv 2017; Learn-then-Test, Angelopoulos et al. 2021;
  Jaeger et al. 2023). Cost-based reject rule (Chow): reversible click acts at p ≥ 0.70 for error
  cost 1 / stop cost 0.3, irreversible at p ≥ 0.95 for 20 / 1.
- No surveyed agent (Operator, Mariner, Claude computer use, browser-use, Agent-E, Skyvern) aborts a
  whole task on low confidence; WebArena measured that an easy "infeasible" exit made GPT-4 declare
  54.9% of feasible tasks infeasible. Humans are asked for irreversible actions, not for ambiguity.
- Two-stage selection (MindAct: 55.1% vs 26.8% element accuracy). Option-order debiasing (PriDe) was tested here and did not help (F4-V).
- Laya vendor: base checkpoints near chance zero-shot; `head_max_len` shared by all options;
  typed-decisions 0.766 vs 0.362; escalation to larger LLMs was worse.

## 9. Not adopted from the pasted advisory text

The founder pasted a long advisory text (≈250k characters). It was verified claim by claim. Not
adopted: advice about verbalised LLM confidence (Laya does not verbalise), any rule that turns low
confidence into continuing (hash or monotony overrides, score boosts), uncalibrated constants
(logit −2.5, fixed 40/70/85% bands, "moving the graph boundaries"), code that reports success
unconditionally, `--workers 4`, the Core ML warm-up for a PyTorch CPU container, and fingerprint
rotation to evade bot protection. Adopted in spirit: evidence-carrying termination (a completion
must point at evidence a deterministic check confirms), which F1's final judge implements.

## 10. Handover

- **Owner:** the session working in `C:\Users\Ömer\Desktop\Freelance\jev-ultrafast`. This design
  does not modify that repository.
- **Order:** F2 and F1 first (41 of 69 failures, no model involved), then F4.1–F4.3 (the framing
  fix is small and validated: 9/45 → 45/45 on replay), then F3, then F5.
- **Keystone clean-up, not executed:** rows created during the run window (2026-09-23 16:04–16:55
  UTC) in `ArticleView`, `SearchLog`, `Test`, `TestAttempt`, `TestAttemptAnswer`, `Conversation`,
  `Message`, `UserRoleSelection` (ENTERPRISE), `FeatureFlags`, and the display name "Observer".
  The pre-run dump is `keystone-before.sql` in the LOGOS session scratchpad.
