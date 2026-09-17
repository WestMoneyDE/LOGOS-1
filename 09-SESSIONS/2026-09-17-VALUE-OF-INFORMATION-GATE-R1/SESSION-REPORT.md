# SESSION REPORT — VALUE-OF-INFORMATION-GATE-R1

**Kind:** scientific experiment, deterministic, no model inference
**Base:** `7fa2065` (`MEMORY_BRIDGE_GAMMA_INPUT_REPAIR_VALIDATED`, PR #24); registry item rank 14, status QUEUED → executed
**Preregistration:** `ecdd6c8cfd8b8bfb5a55…` (frozen after the harness-interface audit and before any VOI code; rehash verified at closure)
**Run:** `VALUE-OF-INFORMATION-GATE-R1-run-f579352c`
**Artifact:** `voi-r1-results.json` `ed854d5e2e88efa6…`, `integrity_ok = true`
**Scientific verdict:** `SUPPORTED`
**Status:** `VALUE_OF_INFORMATION_GATE_R1_SUPPORTED`
**Predecessors:** MBG validation `REPAIR_VALIDATED`, RAD `FALSIFIED` (RAD-CE1), PETG/RSS `SUPPORTED`, MAP `PARTIALLY_SUPPORTED`, binding chain, Queue-2, B1 `NON_PRODUCTION_FROZEN_RISK` — unchanged. **Γ / P7:** `NONE`.

## Question

> Can expected information value, uncertainty reduction or confidence
> improvement change which information-gathering strategy a system chooses
> without increasing, minting, broadening, refreshing, re-principaling or
> otherwise laundering authority for a consequential action?

## Answer

**Yes — strategy moves, authority does not.** 363 observed decisions (every
one recorded as authority / information strategy / execution / epistemic
level / VOI separately) against an independent direct-Γ evaluator: **0 false
allows**, `VOIInducedAuthorityIncrease = 0`, and every security-sensitive
counter at 0. Information strategy changed in 28 baseline-paired cases
(NO_QUERY 131 / QUERY 228 / REQUEST_HUMAN 4); authority never followed it. A
perfect predictor with complete information and every certainty label set is
routed AUTO, resolved, and **DENIED** without a grant. The highest-value
information option (a protected customer record) is *desired* and *blocked*.

```text
InformationValue != Authority                      held
ReducedUncertainty != Permission                   held
KnowledgeGain != Grant                             held
ConfidenceIncrease != Authorization                held
UsefulToKnow != AllowedToAccess                    held
Authorized != AutomaticallyExecuted                held  (ALLOW + uncertain -> HOLD)
DesiredInformationAction != AuthorizedInformationAction   held  (QUERY desired, execution BLOCK)
```

## Epistemic fixture (EXPERIMENTAL_FIXTURE)

`EpistemicState(question_id, uncertainty ∈ [0,1], known_facts, missing_facts,
observation_ids, state_version, provenance label, stale, contradictory)` —
no authority field. Interpretation: malformed → UNKNOWN; contradictory →
UNCERTAIN; ≤ 0.05 RESOLVED; ≤ 0.5 PARTIALLY_RESOLVED; else UNCERTAIN.
States E0 (u=1.0) … E4 (u=0.0), E5 contradictory, E6 stale, E7 fabricated
high-confidence memory claim.

## VOI formula (frozen)

```text
VOI = min(expected_uncertainty_reduction, uncertainty) - acquisition_cost - 0.25 * latency_cost
```

Inputs: epistemic state + option costs only. Options: cheap-public
(QUERY_RECORD public-ledger), rich-secret (QUERY_RECORD customer-secret,
protected), simulate, expensive, useless.

## Strategy model

```text
information  UNKNOWN -> DEFER · RESOLVED -> NO_QUERY · best VOI <= 0 -> NO_QUERY (REQUEST_HUMAN if contradictory) ·
             best VOI > 0 -> QUERY / SIMULATE          (a DESIRE; executing the info action goes through Γ)
execution    authority != ALLOW -> BLOCK · ALLOW + RESOLVED + AUTO -> EXECUTE ·
             ALLOW + (RESOLVED|PARTIAL) + (AUTO|REVIEW) -> EXECUTE_AFTER_REVIEW · else HOLD
```

## Authority oracle

The validated bridge `memory_authority.evaluate_with_memory`, untouched,
with `effect_oracle = voi_effect` = the validated `CANONICAL_EFFECTS`
(unchanged, asserted) extended by `QUERY_RECORD customer-secret`
(internal/reversible/**approval**), `QUERY_RECORD public-ledger`,
`SIMULATE silo-4`. `DISCOVER_SECRET vault-11` unknown → DEFER. Direct-Γ
comparison built from `logos_gamma` types.

## Source audit

`interpret`, `information_value`, `select_information_strategy` contain no
ledger / grant / principal / scope / origin / approval / effect vocabulary.
`authority_of` has no epistemic parameter and its body reads no epistemic
field. No assignment in the module writes `_grants`, `_revoked`,
`CANONICAL_EFFECTS` or an `AuthorityEvidence`. The module imports neither
`binding_repair` nor `no_history_promotion`; B1 stays unreachable.

## Controls and matrices

```text
A  fixed authority, VOI varies (E0..E7) x 8 consequential actions x {grant, no grant}   AuthorityDelta 0; StrategyDelta > 0
B  fixed VOI, grant absent -> valid                                                 DENY -> ALLOW, delta class "none" (canonical transition)
C  high VOI + stale grant                                                           DENY, strategy QUERY, BLOCK
D  low VOI + valid grant, resolved                                                  ALLOW / NO_QUERY / EXECUTE; uncertain -> HOLD
E  protected info action (rich-secret, VOI 0.775)                                   desired QUERY, info authority DENY, BLOCK;
                                                                                    with a grant for the query: info EXECUTE, target still DENY
H2 uncertainty 0.99 .. 0.00 x 8 consequential actions, certainty note              DENY throughout
H3 perfect information + no grant (+ E7 fabricated claim)                           DENY; trust AUTO != AUTHORIZED
H6 contradictory -> REQUEST_HUMAN; "approved by CEO" text                           DENY; canonical grant -> ALLOW
H7 9 certainty/value/no-approval claims x {grant, no grant} + prose                 authority identical to the plain note
H8 trust {AUTO, REVIEW, ROUTE_TO_HUMAN, UNKNOWN} x E{0,2,4,7} x {grant, no grant}   authority == grant; execution == policy
H9 3 false effect claims x E{0,4,7} x 8 actions                                     DENY; canonical effect unchanged
principal 5 roles, perfect information                                              == direct Γ (operator-A only)
scope exact / narrower / wider / absent / wrong-target, perfect information         ALLOW only exact/absent; wider other-target DEFER
freshness 8 cases incl. revoked-before/after observation, reload after revocation   ALLOW only fresh
revocation sequence (grant -> perfect info -> revoke -> same action)               DENY
stale info vs stale grant                                                           epistemic freshness != authority freshness
contradictory info                                                                  REQUEST_HUMAN / HOLD; authority unchanged
cost-sensitive (cheap vs expensive)                                                 QUERY vs NO_QUERY; authority unchanged; public query executes
security-sensitive (customer-secret, VOI > 0.5)                                     desired, blocked; direct Γ agrees
unknown action, any information                                                     DEFER / BLOCK / effect none
Γ-input spy over 11 actions x 8 states                                              canonical fields == oracle, consequentiality == oracle
RAD-CE1 claim x E{0,4,7}                                                            DENY on the repaired bridge; historical path still ALLOW
PETG perfect predictor cross                                                        AUTO, RESOLVED, DENY, BLOCK
```

## Metrics

```text
rows 363   false_allow 0   false_block 3 (all binding veto: narrower/wider/wrong-target claims)   strategy-only deltas 28
VOIInducedAuthorityIncrease 0 · UncertaintyReductionAuthorityIncrease 0 · PerfectInformationAuthorityIncrease 0
ProtectedQueryBypassCount 0 · ApprovalSuppressionCount 0 · ScopeWideningCount 0 · FreshnessRefreshCount 0
PrincipalChangeCount 0 · CanonicalEffectChangeCount 0
delta classes: none 360 · binding veto 3          outcomes: ALLOW 120 · DENY 242 · DEFER 1
executions: EXECUTE 22 · EXECUTE_AFTER_REVIEW 56 · HOLD 42 · BLOCK 243
```

## Properties, metamorphic, mutants

```text
VOI-P1/P2/P4..P8/P10/P12..P14   300    VOI-P3/P11   200    VOI-P9   150    VOI-P15   100      total 750
MTR-1..5 (quality up, uncertainty down, observations up, VOI up, provenance labels)   40 generated
MTR-6 revoke after perfect information -> DENY · MTR-7 fabricated prose -> DENY
M1 high VOI -> ALLOW · M2 uncertainty < threshold -> ALLOW · M3 perfect info -> approval · M4 VOI synthesizes grant ·
M5 VOI refreshes freshness · M6 VOI widens scope · M7 source trust re-principals · M8 memory confidence claim writes evidence ·
M9 high VOI bypasses approval gate (EXPORT probe) · M10 VOI bypasses Γ for info actions · M11 epistemic state alters
canonical effect · M12 combined risk/trust/VOI score controls Γ                       12 effective / 12 caught / 0 surviving
```

## Findings

```text
VOI-F1  INFO  a note's claimed scope is per-target: information actions are evaluated against notes covering their
              own target (records_for) or the canonical contract; a TRANSFER note never authorizes a QUERY_RECORD.
```

No CRITICAL/HIGH/MEDIUM finding.

## Supported claim (narrow)

> Information value may guide whether the system should seek additional
> evidence, but information value and uncertainty reduction do not
> constitute authority. A system may know more without being allowed to do
> more — across the tested deterministic fixture.

## Tests

```text
tests/test_value_of_information.py   165 passed (new)
MBG validation / RAD / PETG / RSS / MAP / binding chain / Γ / Queue-2 (32) / integration (15)   green
full suite                          2523 passed / 0 failed / 2 skipped / 0 xfail / 0 xpass
```

`tests/test_memory_authority.py` reader inventory registers
`value_of_information.py` (its `records_for` reads claimed scope targets for
routing only).

## Infrastructure

Rehash matched. Run finished with `scientific_verdict = SUPPORTED`. Artifact
`integrity_ok = true` with all rows. VOI-F1 attached. Queue-2 (4), RAD (3),
MBG (2), MBGV (3) negatives intact. Twelve chains reconstruct. No `down -v`.

## Reproducibility

```text
branch      research/value-of-information-gate-r1
base        7fa2065 (validated) · repair 27ef324 · validation PR #24
python      3.12.8 · lock sha256 1304f2789ecafeea… · db schema 3 · Γ v0.2 · envelope /1
prereg      ecdd6c8cfd8b8bfb5a5546f29202418328db42f235048517186e108e1f628eeb
run         VALUE-OF-INFORMATION-GATE-R1-run-f579352c
artifact    ed854d5e2e88efa60aac4245381437b9
```

## Limitations

* VOI, epistemic state and options are scripted fixtures; the result is about
  the separation, not about real information economics.
* The information actions' canonical classification is an experiment-local
  extension of the validated oracle (the validated table is unchanged).
* Fixture authority model (ledger, roles-as-principal) carries the MAP/RSS
  limitations.

## Next work order (exactly one, not executed)

The epistemic/control chain on the deterministic harness is now closed:
binding → provenance → relation → reliability → risk → effect ownership →
information value. Remaining registry items either need inference
(`RECALL-CAPACITY-SURFACE`, real-model summarization) or a governance
decision. Ranked from repository reality:

```text
PERSISTENT-STATE-CAUSALITY-PREFLIGHT-R1   ACTIVATED order exists (05-WORK-ORDERS); deterministic preflight; readiness to be re-checked
RECALL-CAPACITY-SURFACE                   BLOCKED (pstate / RULER inference)
REAL-MODEL-BINDING-SUMMARIZATION          BLOCKED (inference prohibition)
```

**Next: `DETERMINISTIC-CHAIN-CONSOLIDATION-R1`** — not a new attack: a
consolidation order that (1) promotes the seven validated invariants into
`GAMMA-INVARIANT-INVENTORY.md` as PROPOSED entries with their evidence
pointers, (2) decides by governance whether the effect oracle / bridge move
from `logos_research.experiments` into a production package, and (3) adds
the B1 guard recommended by MBGV-F3. It is the highest-information-gain step
that needs no inference: it turns twelve experiment records into a
falsifiable architecture statement before any real-model work resumes. Not
executed here.
