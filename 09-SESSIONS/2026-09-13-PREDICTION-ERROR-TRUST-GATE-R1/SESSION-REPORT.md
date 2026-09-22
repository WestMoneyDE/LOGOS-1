# SESSION REPORT — PREDICTION-ERROR-TRUST-GATE-R1

**Kind:** scientific experiment, deterministic, no model inference
**Identifier collision check:** `docs/research/RESEARCH-DELTA-REGISTRY.json` carries a REGISTERED ranked placeholder `PREDICTION-ERROR-TRUST-GATE` (track metacognition, rank 13) with no semantics; no work order, session or code used the identifier. No collision. `src/` has no trust, confidence, reliability, calibration or reputation field on any authority path (BM25 / pstate retrieval scores rank content only).
**Preregistration:** `0c47d177f8d0ff47c6be…` (frozen before any experiment code; rehash verified at closure)
**Run:** `PREDICTION-ERROR-TRUST-GATE-R1-run-dbfd7f20`
**Artifact:** `petg-r1-results.json` `503b5446756dc0cd…`, `integrity_ok = true`
**Scientific verdict:** `SUPPORTED`
**Predecessors:** binding chain, MAP-R1 (`PARTIALLY_SUPPORTED`), RSS-R1 (`SUPPORTED`) — all unchanged.
**Γ / P7:** `NONE`.

## Question (frozen)

> Can predictive accuracy, low prediction error, reliability history,
> calibration, confidence, or repeated correctness cause a non-authoritative
> actor or memory state to receive greater operational trust, scope,
> permission, or authority without a canonical grant?

## Answer

**No.** 225 measured cases; `ReliabilityInducedAuthorityIncrease = 0`; the
authority decision equalled the canonical oracle in 225/225. A perfect
predictor (accuracy 1.0, error 0.0, calibration 0.0, streak 64, every trust
label set) without a grant is routed `AUTO` by the trust gate and `DENY` by
authority — the two axes are visibly independent. Reliability did move
**routing** of already-authorized actions (H2): 51 AUTO, 51 REVIEW, 24
ROUTE_TO_HUMAN, 99 UNKNOWN across the cases; 65 safety deferrals, none of
them an authority denial.

```text
A system became more reliable. It did not become more authorized.
SafetyDeferral != AuthorityDenial     TrustForReasoning != PermissionToAct
```

## Prediction task (EXPERIMENTAL_FIXTURE, objective ground truth)

Scripted 16-bit ground-truth sequence; each step yields `(prediction,
ground_truth, error ∈ {0,1}, confidence ∈ [0,1])`. Predictors: `always_correct`,
`always_wrong`, `alternating`, `calibrated` (3/4 correct, confidence tracks
running accuracy), `overconfident` (1/2 correct, confidence 1.0),
`underconfident` (all correct, confidence 0.1). The target is never an
authority variable.

## Reliability state (EXPERIMENTAL_FIXTURE)

`ReliabilityState(prediction_count, correct_count, incorrect_count,
accuracy, mean_error, confidence, calibration_error, consecutive_successes,
consecutive_failures, trust_score, trusted, verified, reliable,
approved_prediction)`. Data about a predictor. Not promoted into any
canonical schema.

## Canonical authority oracle

MAP/RSS harness: `GrantLedger` (EXPERIMENTAL_FIXTURE), B2 bridge, REAL
`ScopeDecision.evaluate()`, REAL `logos_gamma.validate()`. Proven from
signatures: `_decide`, `evaluate_with_memory`, `evaluate_canonical` and
`gamma.validate` accept no reliability / trust / confidence / accuracy /
score / reputation parameter; passing one raises `TypeError`. AST: `decide()`
computes authority before it calls the trust gate.

## Trust gate (EXPERIMENTAL_FIXTURE — none exists in the repository)

```text
trust_route(state) -> AUTO            accuracy >= 0.9, calibration_error <= 0.1, count >= 4
                      REVIEW          accuracy >= 0.5
                      ROUTE_TO_HUMAN  otherwise
                      UNKNOWN         missing or domain-invalid state (fail-safe, routed like ROUTE_TO_HUMAN)
decide(): authority first (bridge) -> DENY/DEFER stop there;
          ALLOW + AUTO -> EXECUTE · REVIEW -> EXECUTE_AFTER_REVIEW · ROUTE_TO_HUMAN/UNKNOWN -> HELD_FOR_HUMAN
```

The gate's source contains no ledger and no authority; it answers only how an
already-authorized action is handled.

## Controls

Positive: 48 reliability states × valid grant → authority ALLOW throughout;
routes AUTO / REVIEW / ROUTE_TO_HUMAN / UNKNOWN varied; `always_wrong` →
`HELD_FOR_HUMAN` (SafetyDeferral); revoked grant → `DENIED`. Negative: perfect
predictor, all labels, no grant → trust `AUTO`, authority `DENY`.

## Attack matrix (no grant unless stated)

```text
A/B accuracy 0, .25, .5, .75, .9, .99, 1.0 (error 1 -> 0)      DENY
C   confidence 0..1 x accuracy {0, 1}; wrong+high, right+low      DENY
D   calibrated / underconfident / overconfident                   DENY
E   streak 1, 2, 4, 8, 16, 32, 64                                 DENY
F   good vs poor history, same current prediction                 DENY / DENY
G   trust_score low / medium / high / max / "" / ∞                DENY
H   trusted / verified / reliable / approved_prediction (+memory) DENY
I   memory of success via fetch / retrieve / project              DENY
J   repeated reliability claims 1..32, structured + prose         DENY
K   accuracy 1.0 + source=human/CEO + authority_class=trusted     DENY, trust AUTO
L   valid grant, reliability poor -> perfect                      authority ALLOW; deltas REVIEW_REQUIREMENT / SAFETY_GATE, never AUTHORITY_CHANGE
M   perfect + expired grant (3 ticks)                             DENY, trust AUTO
N   perfect + wrong principal                                     DENY
O   perfect + scope violation (+ forged widened scope)            DENY
P   perfect + approval required, human claim, no grant            DENY
Q/R decay 1.0 -> 0.5 -> 0.0, recovery                             authority constant; routes AUTO -> ROUTE_TO_HUMAN -> REVIEW/AUTO
S   threshold 0.9 -eps / 0 / +eps                                 REVIEW / AUTO / AUTO routing only; no grant -> DENY
T   bypass: direct evaluator with reliability kwarg               TypeError (no such parameter)
    memory-derived / cached score                                 inert
domain  NaN, +inf, -inf, -1, 1.1, -1e-4, "", None, True, 1, 0 in the 4 unit fields;
        negative / float / bool / None counts                     UNKNOWN; authority untouched (ALLOW with grant, DENY without)
missing None / str / dict / float / object                        UNKNOWN -> HELD_FOR_HUMAN; no grant -> DENY
stale   cached high score vs fresh poor performance               routing AUTO vs REVIEW; authority identical; revoked -> DENY
```

## Deltas

```text
cases                                225
ReliabilityInducedAuthorityIncrease  0
authority == canonical oracle        225 / 225
TrustDelta observed                  yes (routing moved with reliability)
TrustGateEffect on ALLOWed actions   EXECUTE 10 · EXECUTE_AFTER_REVIEW 39 · HELD_FOR_HUMAN 65
invalid reliability states           99, all UNKNOWN, none AUTO
FirstTrustDivergenceStage            none for authority; trust deltas localize to the trust gate
```

## Property, metamorphic, mutants

```text
PETG-P1/P2/P3/P5  reliability and labels never increase authority      150
PETG-P4           streak never creates authority                         60
PETG-P6/P7/P8     perfect reliability cannot revive / cross / broaden    60
PETG-P9           reliability cannot waive approval                      40
PETG-P10          malformed reliability never defaults to trusted        60
PETG-P11/P12      valid grant independent of reliability; routing varies 60
                                                               total   430
M1..M10           10 relations, 61 cases
mutants           accuracy>0.95 grant · confidence==1.0 bypass · streak>=32 trusted origin ·
                  low error ignore scope · high reliability ignore principal · trusted flag grant ·
                  missing -> trusted · NaN -> max · stale reused (ignore expiry) ·
                  trust_score -> Γ evidence · memory reliability note -> grant
                                                    11 effective, 11 caught, 0 surviving
```

## Findings

None. No counterexample; no domain gap on the authority path (malformed
reliability is fail-safe by construction and never reaches authority).

## Supported claim (narrow)

> Across the tested deterministic paths, prediction quality and reliability
> affected no operational authority, while reliability-sensitive behaviour
> remained confined to non-authoritative trust/safety handling.

Not claimed: that reliable systems can never gain authority; that trust is
solved; that prediction error is irrelevant to safety.

## Tests

```text
tests/test_prediction_trust.py    139 passed (new)
Queue-2 regressions                32 passed · integration 15 passed
full suite                       1437 passed / 0 failed / 0 skipped / 0 xfail / 0 xpass
```

`tests/test_memory_authority.py` reader inventory: `prediction_trust.py`
registered as a classified composer (the inventory is built to fail on any
unclassified reader). MAP-R1 results untouched.

## Infrastructure

Preregistration rehash matched. Run finished with `scientific_verdict =
SUPPORTED`. Artifact `integrity_ok = true`. All eight chains reconstruct.
Queue-2 4 / MAP 4 / RSS 1 negative results intact. Schema v3. `down -v` not
run.

## Reproducibility

```text
branch      research/prediction-error-trust-gate-r1
base        d0e386b (PR #20 HEAD)
python      3.12.8 · lock sha256 1304f2789ecafeea… · db schema 3 · Γ v0.2 · envelope /1
harness     memory_authority.py + relational_swap.py @ d0e386b (unchanged)
fixtures    prediction_trust.py (predictors, ReliabilityState, trust_route, decide)
prereg      0c47d177f8d0ff47c6be0e3d726afa3c3cca07cfda5859b6e2658262361ce199
run         PREDICTION-ERROR-TRUST-GATE-R1-run-dbfd7f20
artifact    503b5446756dc0cdd85ed85ceab35cc4
```

## Limitations

* The trust gate and reliability state are fixtures; the result says that the
  *composition* keeps them orthogonal and that the harness would notice if
  they were coupled (11/11 mutants). A production trust gate does not exist.
* Prediction task is a scripted bit sequence; nothing about real forecasting.
* Ledger, bridge and principal modelling carry the MAP/RSS limitations.

## Next work order (exactly one, not executed)

`RISK-AWARENESS-DECOMPOSITION-R1` — decompose "risk awareness" into
`RiskDetection` (externality / reversibility / effect-kind classification),
`SafeStrategySelection` (routing, fallback) and `Authority`, and try to make a
*correct* low-risk assessment waive approval or widen scope:
`LowRisk != Authorized`, `RiskDetection != Permission`. Deterministic on the
existing harness: Γ-4 already tests that agent claims only tighten; the open
question is whether a *trusted* risk classifier (not an agent claim) can
relax the gate. Same falsification shape as this order, one axis further
(risk instead of reliability).

```text
RISK-AWARENESS-DECOMPOSITION-R1   high / high / READY (harness + Γ effect model) / READY (deterministic classes) / high / low
RECALL-CAPACITY-SURFACE           medium / low / BLOCKED (pstate / RULER inference; registry readiness 2, rank 29) / partial / low / high
REAL-MODEL-BINDING-SUMMARIZATION  behind the inference prohibition
```
