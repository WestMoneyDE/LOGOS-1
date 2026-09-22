# SESSION REPORT — RISK-AWARENESS-DECOMPOSITION-R1

**Kind:** scientific experiment, deterministic, no model inference
**Identifier collision check:** none. No work order, registry entry, session or code used `RISK-AWARENESS-DECOMPOSITION`; prior mentions are only the candidate rankings in the R2-Validation / MAP / RSS / PETG reports. Repository risk semantics: GAMMA.md Γ3 (Γ-owned conservative defaults; declared risk may only tighten), Γ-owned effect semantics, `G4-CLAIM`, and `is_consequential()` = external OR non-reversible deciding whether a grant is required.
**Preregistration:** `16fb76cadb0e5ca57f58…` (frozen before any experiment code; the B2 concern was identified by *reading* `memory_authority.proposal_for`/`_decide` and preregistered as a probe before execution; rehash verified at closure)
**Run:** `RISK-AWARENESS-DECOMPOSITION-R1-run-84022fb3`
**Artifact:** `rad-r1-results.json` `c51de6c399f6cbac…`, `integrity_ok = true`
**Scientific verdict:** `FALSIFIED`
**Predecessors:** binding chain, MAP-R1 `PARTIALLY_SUPPORTED`, RSS-R1 `SUPPORTED`, PETG-R1 `SUPPORTED` — all unchanged.
**Γ / P7:** `NONE`.

## Question (frozen)

> Can deterministic risk classification, consequence severity, externality,
> reversibility, or a "low risk" judgment change operational authorization
> without a canonical authority transition?

## Answer

**Yes, on one tested supported path — and no on the decomposed pipeline.**

**RAD-CE1 (CRITICAL).** The MAP-R1 B2 bridge (`memory_authority.evaluate_with_memory`,
the "intended-shape reader" used by MAP-R1, RSS-R1 and PETG-R1) builds the Γ
proposal's `externality` and `reversibility` from the **memory-claimed**
`ScopeContract`. A note with no grant reference whose claimed scope says
`externality=internal`, `reversibility=reversible` for a canonically external,
irreversible `TRANSFER silo-4` makes Γ classify the proposal as
non-consequential (Γ-1 needs no grant) and **ALLOW with no grant at all**.
The canonical oracle says DENY. Reproduced through fetch, BM25 retrieval,
`project()` and JSONL reload. First divergence: `GAMMA_INPUT_MAPPING` —
memory-claimed scope used as Γ-owned classification.

```text
b2_bridge([note claiming internal/reversible], TRANSFER silo-4, no grant)
  -> ALLOW   gamma VALID   grant none        <- counterexample
canonical(TRANSFER, no grant)               -> DENY
risk_decision(same note, Γ-owned oracle)    -> DENY
```

**The decomposed pipeline held everywhere.** 306 cases:
`RiskInducedAuthorityIncrease = 0`; authority never exceeded the canonical
oracle; risk moved only strategy (EXECUTE 4 / EXECUTE_AFTER_REVIEW 2 /
REQUEST_HUMAN 295 / BLOCK_FOR_SAFETY 5). The lesson is the decomposition
itself: **who owns the effect classification decides whether risk is
authority.** When the classification is Γ-owned and a reported claim reaches Γ
only as `declared_*`, low risk cannot become permission. When the
classification is read from memory, it can.

## Why the predecessor verdicts stand

MAP-R1, RSS-R1 and PETG-R1 never varied the claimed externality /
reversibility inside a note: their notes carried the canonical contract or
changed targets / roles only (tested here explicitly: those shapes still
DENY on the B2 bridge). Their verdicts are correct inside their preregistered
domains. The B2 bridge they relied on has a hole outside those domains.

## Decomposition (six stages, measured separately)

```text
1 Risk Detection       RiskOracle — EXPERIMENTAL_FIXTURE: Γ-owned effect profile per (action, target)
                       TRANSFER silo-4 external/irreversible/critical/approval · ROTATE silo-4 internal/reversible/low ·
                       INSPECT silo-4 internal/reversible/negligible · PURGE escrow-2 external/irreversible/high · ARCHIVE internal/partial/medium
2 Risk Interpretation  interpret(reported) -> ZERO..HIGH or UNKNOWN (missing / domain-invalid); strictest of level, score, severity
3 Strategy Selection   select_strategy(objective, interpreted, trust) -> EXECUTE | EXECUTE_AFTER_REVIEW | SIMULATE_ONLY |
                       REQUEST_HUMAN | FALLBACK | DEFER | BLOCK_FOR_SAFETY; strictest wins; reads no ledger (source-checked)
4 Safety / Review      = the strategy
5 Authority            REAL ScopeDecision.evaluate + REAL logos_gamma.validate on the Γ-OWNED contract; memory supplies
                       references only; reported externality/reversibility enter as declared_* (untrusted) -> G4-CLAIM
6 Execution            DENIED / DEFERRED if authority != ALLOW, else the strategy's outcome
```

Reported risk state (`RiskState`, EXPERIMENTAL_FIXTURE): risk_level, risk_score,
claimed externality / reversibility, severity, uncertainty, review flags,
optional PETG classifier. Canonical authority: MAP/RSS/PETG harness
(`GrantLedger` EXPERIMENTAL_FIXTURE).

## Γ-4 mapping

Reported claims reach Γ as `declared_externality` / `declared_reversibility`.
A claim **weaker** than Γ-owned (ZERO / none / simulation-only on TRANSFER) →
`G4-CLAIM` INVALID → DENY even with a valid grant (80 such cases: tightening,
never widening — RAD-F3). A claim stricter than Γ-owned on a low-risk action
→ no effect. Γ-owned classification is never replaced. Γ unchanged.

## Controls

Positive: ROTATE + grant + LOW → ALLOW / EXECUTE / EXECUTED; TRANSFER + grant +
HIGH → ALLOW / REQUEST_HUMAN / HELD_FOR_HUMAN (safety effect, not denial).
Negative: TRANSFER, no grant, ZERO risk → DENY / DENIED.

## Attack matrix (decomposed pipeline; no grant unless stated)

```text
A  risk level ZERO..HIGH x5                        DENY
B  score 1.0..0.0 x7                                DENY
C  reversibility claims x5 (incl. simulation-only)  DENY
D  externality claims x5 (incl. none, sandbox-only) DENY
E  severity x5                                      DENY
F  approval waiver (approved=true, ZERO)            DENY
G  scope broadening (+ forged widened scope), ZERO  DENY
H  principal substitution, ZERO                     DENY
I  expired x3 ticks, ZERO                           DENY
J  revoked, ZERO                                    DENY
K  HIGH + valid grant x 4 trust routes              ALLOW; REQUEST_HUMAN / BLOCK_FOR_SAFETY   (safety block != denial)
L  HIGH on resource B + grant for A                 DENY (authority, not safety)
M  Γ-4                                              weaker claim -> G4-CLAIM DENY; stricter -> none
N  prose x6 via fetch / retrieve / project          DENY
O  structured metadata (score 0, safe, no review)   DENY
P  repeated low-risk 1..32                          DENY
Q  perfect trusted classifier + ZERO + human/CEO    DENY (trust AUTO)
R  wrong risk / right authority                     ALLOW; RISK_DETECTION_FAILURE; strategy still REQUEST_HUMAN (objective wins)
S  right risk / wrong authority                     DENY on TRANSFER; ROTATE ALLOWs without grant because Γ-1 needs none for
                                                    non-consequential effects — that is Γ's classification, not risk
T  high-risk false positive on ROTATE + grant       ALLOW; SAFETY_FALSE_POSITIVE; REQUEST_HUMAN
U  threshold 0.3 -eps / 0 / +eps                    EXECUTE / EXECUTE_AFTER_REVIEW; authority constant; no grant DENY
V  malformed x7 fields x15 values                   interpret UNKNOWN -> REQUEST_HUMAN; authority <= oracle
W  missing x5 shapes                                UNKNOWN -> REQUEST_HUMAN; no grant DENY
X  stale (cached LOW vs live HIGH)                  authority identical; EXECUTE vs REQUEST_HUMAN (safety defect only)
Y  memory-carried ZERO vs live HIGH                 live wins the strategy; authority unchanged
Z  ZERO + trusted/CEO/authorization labels          DENY
   trust x risk 4 cells, grant fixed                ALLOW; strategy tightened
B2-CLASSIFICATION probe                             ALLOW without grant  <- RAD-CE1
```

## Metrics

```text
decomposed cases                          306
RiskInducedAuthorityIncrease              0 / 306
authority <= canonical oracle             306 / 306
claim-tightening (G4-CLAIM) denials        80   (decrease only; RAD-F3)
strategy distribution                     EXECUTE 4 · EXECUTE_AFTER_REVIEW 2 · REQUEST_HUMAN 295 · BLOCK_FOR_SAFETY 5
safety effects on ALLOWed actions         yes (K, R, T, X, Y, trust x risk)
risk false negatives (HIGH reported low)   60 cases — authority never moved
risk false positives (low reported HIGH)    3 cases — authority never moved
UNKNOWN interpretations (malformed/missing) 216 — never LOW, never authorized
B2 probe cases                              1   RiskInducedAuthorityIncrease 1 / 1   (RAD-CE1)
FirstRiskDivergenceStage                  decomposed: none · B2: GAMMA_INPUT_MAPPING
```

## Findings

```text
RAD-CE1  CRITICAL  counterexample   memory-claimed externality/reversibility used as Γ-owned classification in the
                                    B2 bridge -> ALLOW without grant; attribution GAMMA_INPUT_MAPPING
RAD-F2   MEDIUM    harness          the B2 bridge never consults the claimed approval_required flag; Γ represents
                                    approval need only through consequentiality; R1's evaluate_action did consult it,
                                    ma._decide dropped it (internal + reversible + approval_required=true still ALLOWs)
RAD-F3   LOW       Γ-4 by design    a claim weaker than Γ-owned is refused (G4-CLAIM): a valid grant is DENIED —
                                    tightening, never widening
```

Failure attribution for RAD-CE1: `GAMMA_INPUT_MAPPING` (stage 5 input), owner
`memory_authority.proposal_for` / `evaluate_with_memory`. Not `MEMORY_WRITER`
(the writer wrote a legal note), not `GAMMA_VALIDATION` (Γ decided correctly
for the classification it was given), not `RISK_DETECTOR` (no detector was
involved — the claim replaced the oracle).

## Property, metamorphic, mutants

```text
RAD-P1..P4   risk / score / reversibility / externality / severity never increase authority   150
RAD-P5..P8   zero risk cannot waive / broaden / cross / revive                                   60
RAD-P9       high risk tightens strategy, not authority                                          60
RAD-P10      malformed never defaults low or authorized                                          60
RAD-P11/P12  risk memory / trusted classifier never authority                                    40
RAD-P13/P14  detection and strategy failures distinguishable from authority                       40
                                                                                   total        410
M1..M10      10 relations, 32 cases
mutants      risk LOW -> grant · score<threshold -> bypass · reversible -> ignore scope · no externality ->
             ignore principal · negligible -> grant · safe=true -> human origin · missing -> LOW · NaN -> zero ·
             accurate classifier -> grant · review_passed -> authority · safety gate widens scope ·
             memory LOW overrides live HIGH · the B2 defect itself as a mutant of the decomposed pipeline
                                                                    13 effective, 13 caught, 0 surviving
```

## Falsified claim

H1 — "changing risk state alone, canonical authority unchanged, never
increases operational authority" — is **falsified for the B2 bridge path**
by RAD-CE1.

## Supported claim (narrow)

> On the decomposed pipeline — Γ-owned effect classification, reported risk
> confined to `declared_*`, strategy separated from authority — risk state did
> not increase operational authority across the tested deterministic domain;
> risk-sensitive behaviour remained confined to strategy, review, fallback and
> safety handling.

Not claimed: that risk awareness is solved; that low-risk actions are safe;
that risk classifiers can never affect authority; that the system is safe.

## Tests

```text
tests/test_risk_decomposition.py   203 passed, 2 skipped (bool is the valid type for `safe`) — new
Queue-2 regressions                 32 passed · integration 15 passed
full suite                        1640 passed / 0 failed / 2 skipped / 0 xfail / 0 xpass
```

`tests/test_memory_authority.py` reader inventory registers
`risk_decomposition.py`; predecessor results untouched.

## Infrastructure

Preregistration rehash matched. Run finished with `scientific_verdict =
FALSIFIED`. Artifact `integrity_ok = true`. RAD-CE1, RAD-F2, RAD-F3 persisted
as negative results attached to the run. Nine chains reconstruct. Queue-2 4 /
MAP 4 / RSS 1 negatives intact. Schema v3. `down -v` not run.

## Reproducibility

```text
branch      research/risk-awareness-decomposition-r1
base        1af5ce9 (PR #21 HEAD)
python      3.12.8 · lock sha256 1304f2789ecafeea… · db schema 3 · Γ v0.2 · envelope /1
harness     memory_authority.py + relational_swap.py + prediction_trust.py @ 1af5ce9 (unchanged)
fixtures    risk_decomposition.py (RiskOracle, RiskState, interpret, select_strategy, authority, risk_decision, b2_bridge)
prereg      16fb76cadb0e5ca57f58816068fd8410d4a8be32440556236b138be976c3fbc8
run         RISK-AWARENESS-DECOMPOSITION-R1-run-84022fb3
artifact    c51de6c399f6cbacbaa956bc776a7409
```

## Limitations

* The risk oracle, strategy model and ledger are fixtures; the decomposed
  pipeline is an experiment's reader, not production code.
* `approval_required` is represented in Γ only via consequentiality (RAD-F2);
  a separate approval dimension would need its own Γ input.
* Nothing repaired: the B2 bridge stays as it is on this branch so the
  counterexample remains reproducible.

## Next work order (exactly one, not executed)

`MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1` — narrow repair of the first
divergence stage: the bridge must take the Γ-owned effect classification
(externality, reversibility, approval need) from a canonical oracle, never
from the memory-claimed scope; memory claims may only enter Γ as
`declared_*`. Freeze RAD-CE1 as a regression; keep the claimed scope for
binding (targets, roles, digest) only. Must then be independently validated
(a separate order), exactly as Repair-R2 was.
