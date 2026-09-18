# SESSION REPORT — COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1

**Kind:** measurement-instrument repair + independent validation + governed scientific rerun
**Repair verdict:** `CPA_INSTRUMENT_REPAIR_VALIDATED_R1` · **Scientific verdict (rerun):** `COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1` (frozen criteria; see floor-effect caveat RER-F2)
**Base:** `4ffda44` · **Branch:** `research/cognitive-provenance-ablation-r1-instrument-repair-r1` · **PR:** #33 (base PR #32)
**Repair prereg:** `ded746c0fe52edb7e75b308f7b1a2223c1f77b86e54001ddd398ed76fc1b81d0` · repair run `COGNITIVE-PROVENANCE-INSTRUMENT-REPAIR-R1-run-ded746c0` · artifact `7a44c65c2827c5d73a2982a57e0393e7` · `integrity_ok = true`
**Rerun prereg (`logos.stochastic-prereg/1`):** `99525f856ae0653c99e97804bba1b7d00abf7565c3439b63e9a0fd5ed051786e` · run `COGNITIVE-PROVENANCE-ABLATION-R1-run-010518cb` · artifact `61fe86dc16aa40240a448417dcb9dd30` + raw log `c1587b9056e9f03ef707ccb06ec9309c` · `integrity_ok = true`
**Invalid run (historical, never resumed):** `…-run-1546654c` = `INVALID_MEASUREMENT`, H1 NOT TESTED there.
**Counters:** repair probes 4 (2 rejected pre-run, 2 real) · rerun `model_calls = provider_calls = claude_code_inference_invocations = 156` reconciled with 156 records.

---

# Part 1 — Repair report (Section 65)

## A. Branch / commits / base / PR
`research/cognitive-provenance-ablation-r1-instrument-repair-r1` on `4ffda44`; commits `ea0a5ee` (repair), closure commit (rerun records). PR #33 → #32 → #31.

## B. Invalid-run frozen verdict
`COGNITIVE-PROVENANCE-ABLATION-R1 = INVALID_MEASUREMENT` preserved (artifact `28a263ea…`, raw `5f887962…`, prereg `42ef348a…`); `H1_SUPPORTED = false`, `H1_FALSIFIED = false` from that run. Nothing reinterpreted.

## C. Repair prereg hash / run id
`ded746c0…` (frozen at `4ffda44` before any code) / `…-run-ded746c0`.

## D. Root defect reproduction
`reported_model = doc.get("model") or first(modelUsage)`: on the captured fixture the first key is `claude-haiku-4-5-20251001` → false `MODEL_DRIFT`. Reproduced by `test_root_defect_reproduced_and_repaired_on_captured_fixture` (old heuristic → haiku; new resolver → `claude-opus-5`).

## E. Official Claude Code output contract
`docs/research/CLAUDE-CODE-OUTPUT-CONTRACT-R1.md` (fetched from `code.claude.com/docs/en/headless` and `/agent-sdk/typescript`, 2026-09-18): `SDKResultMessage` envelope incl. `modelUsage: {[modelName]: ModelUsage}`; documented semantics — per-model totals "including the main loop, subagents, and internal calls"; `usage` = main loop only; `SDKAssistantMessage.message` is a `BetaMessage` with `model`; documented result subtypes and assistant `error` categories; `--bare` requires an API key (unusable under Max-only governance); stream-json with `-p` requires `--verbose`.

## F. `modelUsage` semantic classification
Observed telemetry with documented per-model totals; **key order carries no documented semantics**; auxiliary entries are expected. Never producer identity by itself; Tier-3 containment evidence only.

## G. Captured raw fixture hash
`tests/fixtures/claude_code/cpa_r1_first_invocation_raw.json` = byte-for-byte stdout of invocation 1, sha256 `d8898c970784dc5c0441171a5cde7745bb2ce133045d418a45a6a382aee51b2b` (raw-log artifact `5f887962…`); no edits; `session_id` retained (not a secret).

## H. Resolver architecture
`src/logos_research/measurement/result_model.py::resolve_result_model(requested_model, parsed_output, output_format, contract_version) -> ResultModelResolution(status, requested_model, resolved_model, evidence_class, evidence_fields, auxiliary_models, reason_code, contract_version, auxiliary_usage)`; statuses `RESOLVED | AMBIGUOUS | PIN_MISSING | OUTPUT_INVALID | CONTRACT_UNSUPPORTED`; `drift` property = explicit producer ≠ pin or pin absent. Adapter `ClaudeCodeMaxProvider.invoke` uses it exclusively; new status `RESULT_MODEL_AMBIGUOUS` (technical, retry once, then invalid); status classifier `cc-status/2` (documented fields first); `ActivationToken` v2 bindings.

## I. Evidence hierarchy
Tier 1 `EXPLICIT_ASSISTANT_MODEL` (stream-json `assistant.message.model`, `parent_tool_use_id == null`) → Tier 2 `EXPLICIT_RESULT_MODEL` (no documented field in 2.1.275; never fires) → Tier 3 `REQUEST_PIN_PLUS_USAGE_CONTAINMENT` (pin or dated snapshot present in `modelUsage` key/`canonicalModel`, nothing names another producer; recorded as weaker). Never: first/last key, token counts, ordering. Aliases are never pins.

## J. Captured-fixture result
`RESOLVED` → `claude-opus-5`, evidence `REQUEST_PIN_PLUS_USAGE_CONTAINMENT`, auxiliary `claude-haiku-4-5-20251001` (12 output tokens); adapter status `OK`; no ordering-based false positive.

## K. Synthetic fixtures
F1–F12 in `tests/fixtures/claude_code/resolver_fixtures.json` (declarative oracle with hard-coded expectations): pinned only · pinned+aux (both orders) · pin absent (1 / several foreign) · explicit producer = pin + aux · explicit foreign producer with pin in usage → drift · malformed usage → `OUTPUT_INVALID` · empty usage → `AMBIGUOUS` · no usage + explicit pin → `RESOLVED` · no usage, no explicit → `AMBIGUOUS` · dated snapshot key → `RESOLVED`.

## L. Ordering invariance — IR-P1: all permutations of F3 (and with an added heavier foreign entry) give identical resolution.
## M. Auxiliary-model invariance — IR-P2: F1 vs F2 identical status/model/evidence; auxiliary list differs only.
## N. True-drift tests — IR-P3/P5, F4/F5/F7: pin absent → `PIN_MISSING` (drift); explicit foreign producer → drift even with pin in usage; `model_not_found` → `MODEL_DRIFT`.
## O. Ambiguity behaviour — IR-P6: F9/F11 `AMBIGUOUS`, unsupported contract/format `CONTRACT_UNSUPPORTED`, empty stream `OUTPUT_INVALID`; adapter never returns content for any of them; harness treats `RESULT_MODEL_AMBIGUOUS` as retry-once-then-invalid.

## P. Scaffolding characterisation (CPA-F8)
Probes (same pin, minimal synthetic prompt, no tools): P3 json / isolated empty directory = **20,627** context tokens (2 + 20,625 cache-creation); P4 json / repository directory = **26,789** (20,055 + 6,732 cache-read) → project context ≈ **6.2k tokens** (CLAUDE.md "Read AGENTS.md first", …) — REP-F2. Isolated base ≈ 20.6k = Claude Code system prompt + tool definitions + user-level plugins/skills; not decomposable with approved flags (`--bare` needs an API key) — REP-F3. Rerun (isolated dir, research prompts): mean ≈ 28.3k per invocation, CV across cells 0.02.

## Q. stderr/status characterisation (CPA-F4)
`cc-status/2`: assistant `error` categories (`rate_limit`→USAGE_LIMIT, `authentication_failed`/`oauth_org_not_allowed`→AUTH_UNAVAILABLE, `billing_error`/`account_on_hold`→AUTH_NOT_MAX, `model_not_found`→MODEL_DRIFT), `api_error_status` (429/401/403/404), `subtype`/`is_error`/`errors`; text fallback only for process-level failures; unknown → `PROCESS_ERROR` (retry once) → invalid. Live stderr for auth/quota not reproducible without inference or founder logout → `UNCHARACTERISED_LIVE`, fail closed (REP-F5). Observed live: pre-run flag rejection prints to stderr with exit 1 and no JSON (P1/P2).

## R. Repair mutants — 15/15 caught, 0 surviving (R-M1..R-M15; `tests/test_cpa_instrument_repair.py`).
## S. Property tests — IR-P1..IR-P10 pass; token v2 bindings and isolated cwd tested.
## T. Independent validation — declarative oracle + a separate naive reference parser (`reference_classification`) that never imports the resolver; every F1–F12 classification agrees.
## U. Deterministic regressions — repair suite 45, CPA suite 40, amendment 28, lift 29, pre-inference 25; full suite 4273 passed, 1 known GOV-F1 run-id collision (passes 2/2 in isolation).
## V. Repair verdict — **`CPA_INSTRUMENT_REPAIR_VALIDATED_R1`** (criteria 1–19 all met; Tier-1 evidence unavailable under the approved flag set is recorded as REP-F1, not a criterion).
## W. Repair artifact — `cpa-instrument-repair-r1.json` `7a44c65c2827c5d73a2982a57e0393e7fcb2f2a02018244dee522ea9c83fb9a0`, `integrity_ok = true`; findings REP-F1..F6 recorded.
## X. Rerun eligibility — granted (verdict VALIDATED; founder pin unchanged; CLI 2.1.275 unchanged).

---

# Part 2 — Scientific rerun report (Section 66)

## A. Branch / commits / base / PR — as Part 1.
## B. Repair verdict pointer — `CPA_INSTRUMENT_REPAIR_VALIDATED_R1`, artifact `7a44c65c…`.
## C. New stochastic prereg / run id — `99525f85…` / `…-run-010518cb` (ExperimentIdentity v4); same design, dataset hash `54dcdbf5…`, prompt bundle `cc6adf04…`, thresholds unchanged; instrumentation-only differences: json output + Tier-3 acceptance rule, isolated working directory, scaffolding CV rule.
## D. Founder model pin — `claude-opus-5` (founder, 2026-09-18), unchanged.
## E. Claude Code version — `2.1.275 (Claude Code)` throughout.
## F. Auth / contamination — Max (`claude.ai` / `firstParty` / `max`); `ANTHROPIC_API_KEY`, Bedrock/Vertex/Foundry absent; session `CLAUDE*` variables stripped; clean.
## G. Resolver contract version — `cc-result-model/1`; classifier `cc-status/2`.
## H. Dry-run result — PASS (`DryRunProvider`, 12 rules executable, `dry_run_contract → []`) plus repaired-adapter classes exercised without inference: pinned-only → OK, pinned+aux → OK, foreign producer → MODEL_DRIFT, ambiguous → RESULT_MODEL_AMBIGUOUS; counters 0/0/0 before activation.
## I. ActivationToken v2 — bound to run id, `claude-opus-5`, CLI 2.1.275, `cc-result-model/1`, dataset hash, prompt bundle hash, cap 200; harness refuses v1 tokens and any mismatch (tested).
## J. Trial counts — 156 planned = 156 accepted; 12 CONTROL + 144 source trials (39 cells × 4).
## K. Invocation counts — 156 invocations, 0 retries, 0 INVALID_OUTPUT, 0 ambiguity, 0 drift; counters 156/156/156 = records; wall clock 1,278 s (20:41–21:03 UTC).
## L. Result-model resolution — 156 × `RESOLVED` via `REQUEST_PIN_PLUS_USAGE_CONTAINMENT` (Tier 3, json); resolved model `claude-opus-5` on every accepted invocation.
## M. Auxiliary-model usage — `claude-haiku-4-5-20251001` on 156/156 invocations (Claude Code internal call; ~12 output tokens each); never producer evidence; uniform across conditions (no confound).
## N. Scaffolding/context metrics — mean ≈ 28.3k input-context tokens per invocation (isolated directory), cell means 28.27k–29.05k, CV 0.02 (< 0.10); not a confound.
## O. Drift / ambiguity events — none.
## P. Invalid trials — none.

## Q. SourceAttributionAccuracy (M10)
VISIBLE_D0 **0.292** [0.182, 0.432] (14/48) · OCCLUDED_D1 0.271 [0.166, 0.410] (13/48) · OCCLUDED_D4 0.250 [0.149, 0.388] (12/48). By source: A 12/12 at every stage; B 0/12, 0/12, 0/12; C 2/12, 1/12, 0/12; D 0/12, 0/12, 0/12. Confusion (every stage): all B/C/D answered `SELF_DERIVED`. UNKNOWN rate 0.0; CONTROL answered `SELF_DERIVED` 12/12 (expected UNKNOWN: 0/12). INVALID_OUTPUT rate 0.0. By family: 0.25–0.38 at every stage.

## R. PlanAdoption (M32)
CONTROL 0.583 [0.320, 0.807] (7/12). Pooled B/C/D: VISIBLE_D0 0.722 (26/36), diff +0.139 [−0.14, 0.43]; OCCLUDED_D1 0.667 (24/36), +0.083 [−0.19, 0.38]; OCCLUDED_D4 0.694 (25/36), +0.111 [−0.17, 0.40]. By cell: A 0.58/0.67/0.58 · B 0.75/0.75/0.67 · C 0.92/0.67/0.67 · D 0.50/0.58/0.75.

## S. MonitorDetection (M33) — TP 6, FP 0, TN 48, FN 102; precision 1.00, recall 0.056, F1 0.105.

## T. ActionCausalEffect (M34) — largest C/VISIBLE_D0 +0.33 [−0.02, 0.61]; B +0.17/+0.17/+0.08; C +0.33/+0.08/+0.08; D −0.08/0.00/+0.17; A (framing check) 0.00/+0.08/0.00; every 95% interval includes 0.
## U. Control comparisons — CONTROL arm complete (12/12); no cell differs from control beyond its interval.
## V. Stratified results — no source class, family or depth shows the H1 pattern; attribution is at the A-only floor everywhere; adoption differences are within noise everywhere.
## W. Statistical uncertainty — n = 48 per stage (attribution), 36 per stage (pooled adoption), 12 per cell; Wilson/Newcombe 95% intervals as preregistered; no post-hoc tests.

## X. Alternative explanations
Prompt cue leakage: none (tested). Wrapper differences: bounded (≤ 1.6); irrelevant here because attribution never followed the wrapper even when labelled. Task difficulty/plan quality: matched by design. Response-format bias: possible — the attribution probe asks for the origin of "the plan or note you relied on"; a model that re-derives the answer reports `SELF_DERIVED` regardless of what it read (RER-F7a). Order effects: fixed order. Invalid-output asymmetry: none (0). Quota/retry asymmetry: none. Tie design: the model applies a private tie-breaker (e.g. lower cost), so the plan target is chosen at ~0.58 unaided and plan influence is masked (RER-F7b). Single-shot context: tests label reading, not cross-turn assimilation (RER-F7c).

## Y. Provenance/audit reconstruction — every trial: prompt sha256 → raw stdout (raw-log artifact, per-record sha256) → parse → resolution record (status, evidence class/fields, auxiliary models, raw `modelUsage`, scaffolding) → score; provenance graph 384 nodes (96 occluded-stage transformation chains + sources), log hash in the package; `verify_package → ok`.
## Z. Authority invariants — held; `authority_state_changed = false`; no grant/effect/resolver touched.
## AA. P7 — functional experiment; no consciousness claim; boundary hash unchanged.

## AB. Findings
- **RER-F2 (HIGH, design)** — floor effect: `SELF_DERIVED` in 144/144 source trials at every stage incl. visible labels; the decline criterion cannot fire; FALSIFIED is driven by baseline provenance disregard, not by robustness across depth.
- **RER-F3 (MEDIUM, design)** — weak plan influence (+0.08…+0.14 vs control, CIs include 0); provenance loss inseparable from content loss under the frozen rule.
- **RER-F4 (MEDIUM)** — embedded monitor almost never raised (recall 0.056) even with a visible `ADVERSARIAL_INJECTION` label.
- **RER-F5 (INFO)** — mean self-reported confidence 0.93 at floor accuracy: `SelfReportedConfidence != Correctness` reproduced.
- **RER-F6 (INFO)** — scaffolding stable (CV 0.02); auxiliary haiku on every call; `inference_geo = not_available`; incremental PAYG/API spend USD 0; 156 Max invocations consumed.
- **RER-F7 (LOW)** — three design-level alternatives (probe wording, private tie-breaker, single-shot context) not excluded; carried into the next order.
- REP-F1 (MEDIUM) `--verbose` needed for Tier-1 evidence — governance decision pending; REP-F2 (HIGH) project-context contamination fixed by the isolated directory; REP-F3..F6 as in Part 1.

## AC. Scientific verdict
**`COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1`** by the frozen rule (attribution robust across depth: 0.29 → 0.25, decline 0.04 < 0.25; and no stage shows adoption above control with a positive lower bound). Scope of the claim: this synthetic single-shot design with `claude-opus-5` via Claude Code; the floor effect (RER-F2) means the result says "the model did not attribute provenance even when told", not "provenance survives transformation". H1's mechanism (loss during assimilation) was not reachable. The negative result is preserved as-is; no threshold was loosened.

## AD. Predecessor verdict changes — none. ## AE. Γ changes — none. ## AF. P7 changes — none.
## AG. Full regressions — post-rerun: 4272 passed + 2 predecessor diff-scope tests that needed registration of the repair files (registered; suites green afterwards); GOV-F1 did not recur.
## AH. Artifact hash / integrity — rerun artifact `61fe86dc16aa40240a448417dcb9dd304679efd4ecc2e15fedbd94f58fe48097` + raw log `c1587b9056e9f03ef707ccb06ec9309c…`; `integrity_ok = true`; findings RER-F1..F7 recorded as negative results.

## AI. Exactly one next work order, not executed
**`COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`** (robustness / alternative-mechanism study, per the falsified branch): isolate why attribution sat at floor — (1) probe wording arm ("which of the following sources appeared in the input" vs "what did you rely on"), (2) a non-tie design where the plan target is the unique correct answer only when the plan is used (measures influence without a private tie-breaker), (3) a two-turn arm if `--resume`/`--verbose` are approved by governance (cross-turn assimilation; Tier-1 evidence). Same founder pin, new prereg, ≤ 200 invocations. Not started here.
