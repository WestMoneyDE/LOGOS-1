# SESSION REPORT — MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1

**Kind:** independent repair validation — not a scientific result
**Subject:** `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1`, commit `27ef324`, PR #23
**Preregistration:** `c6af295836571f8d2f46…` (frozen after the source call-graph audit and before any validation code; rehash verified at closure)
**Run:** `MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1-run-92244afd` (`scientific_verdict = None`)
**Artifact:** `mbgv-r1-results.json` `09509ff2944dfbff…`, `integrity_ok = true`
**Validation verdict:** `REPAIR_VALIDATED`
**Status transition:** `MEMORY_BRIDGE_GAMMA_INPUT_REPAIR_IMPLEMENTED_NOT_INDEPENDENTLY_VALIDATED` → **`MEMORY_BRIDGE_GAMMA_INPUT_REPAIR_VALIDATED`** (recorded here; the repair's own record is unchanged)
**Predecessors:** RAD-R1 `FALSIFIED` (RAD-CE1 preserved), PETG-R1 / RSS-R1 `SUPPORTED`, MAP-R1 `PARTIALLY_SUPPORTED`, binding chain, Queue-2 — unchanged. **Γ / P7:** `NONE`.

## Question

> Does the repaired memory→Γ bridge prevent memory-declared effect data from
> controlling canonical Γ inputs, on every reachable path, without false
> allows, unexplained false blocks, or predecessor regressions?

## Answer

**Yes, within the tested domain.** 1 690 observed bridge evaluations against
an independent direct-Γ evaluator: **0 false allows**, 0 unexplained deltas.
Every delta between bridge and direct Γ falls into a frozen class: Γ-4
tightening (77), binding veto (96), approval gate (7); 1 510 identical. Memory
never wrote a canonical field (runtime spy on Γ's input, 48 shapes); the
unknown-effect path DEFERs without touching memory; the approval gate holds
where Γ alone would admit; RAD-CE1 reproduces only on the historical path and
is DENIED on all four transports of the repaired one. 12/12 mutants caught.

## Independence measures

The repair's test module is not imported and no helper is reused. The effect
table was re-derived from GAMMA.md effect semantics (`INDEPENDENT_EFFECTS`)
and asserted equal to the fixture before use. `direct_gamma` is built from
`logos_gamma` types only. Fixtures are new (vault-11, operator-C, seal-Q, the
oracle's NOTIFY/EXPORT/ARCHIVE actions). Expectations come from Γ semantics
and the repair *contract*. Ordering: the call graph was reconstructed from
source and Docker verified before the preregistration was frozen; the repair
tests were not read before that freeze.

## Independent call graph (from source)

```text
evaluate_with_memory            REPAIRED_CANONICAL_BRIDGE   effect := oracle(action, target); None -> DEFER before scope;
                                                            claimed contract for ScopeDecision + binding digest only;
                                                            declared_effect(claim) -> _decide(effect=, declared=)
_decide(effect=..)              REPAIRED_CANONICAL_BRIDGE   canonical approval gate; canonical_proposal
_decide(effect=None)            LATENT HAZARD (MBGV-F1)     derives the effect from `contract`; safe only while callers hold canonical
                                                            contracts (evaluate_canonical, relational_swap.evaluate_held) — they do
canonical_proposal              REPAIRED_CANONICAL_BRIDGE   canonical from EffectClass, declared from claim
proposal_for                    caller-canonical            only caller: risk_decomposition.authority with the oracle contract
declared_effect / effect_oracle REPAIRED_CANONICAL_BRIDGE inputs
evaluate_with_memory_prerepair  HISTORICAL_ONLY             sole caller: risk_decomposition.b2_bridge
risk_decomposition.b2_bridge    HISTORICAL_ONLY             RAD-CE1 reproduction
binding_state.evaluate_action   EXPERIMENTAL_FIXTURE (R1)   callers: binding_repair.evaluate_from_content / run_matrix, binding_state.run_matrix
no_history_promotion._unauthorized_proposal  NON_CONSEQUENTIAL (literal)
UNCLASSIFIED_RISK               none
```

Production reachability: no module outside `src/logos_research/experiments`
imports the experiments package (AST over `src/`); no `[project.scripts]` /
entry points.

## Constructor inventory (AST)

`EffectProposal(` — `canonical_proposal`, `evaluate_with_memory_prerepair`
(HISTORICAL), `binding_state.evaluate_action` (R1), `_unauthorized_proposal`
(literal). `proposal_for(` — `risk_decomposition.authority` only (oracle
contract). `canonical_proposal(` — `proposal_for`, `_decide`.
`replace(…declared_*)` — `risk_decomposition.authority` sets declared fields
on an oracle-built proposal only. **P15**: runtime spies on `proposal_for`
and `effect_of_contract` during bridge evaluation across all transports and
three claim shapes → 0 calls; source search → no `proposal_for`,
`effect_of_contract` or `or memory` in `evaluate_with_memory`.

## RAD-CE1

```text
historical  evaluate_with_memory_prerepair / rd.b2_bridge    ALLOW on fetch, retrieve, project, reload
            body still contains externality=contract.externality / reversibility=contract.reversibility
repaired    evaluate_with_memory                             DENY x4 · effect external/irreversible/approval=True ·
                                                             declared internal/reversible · identical across transports
```

## Matrices

```text
claim matrix (TRANSFER)   2 ext x 2 rev x 3 approval-claim x 4 scope-claim x 8 grant states x 4 transports = 768
                          ALLOW only with a valid grant AND (claim == bound contract OR no claim); wrong-scope rows
                          (vault-11) DEFER (no canonical effect); an approval-flag mismatch on an otherwise honest
                          claim -> G3-BINDING veto (MBGV-F2)
action matrix (no grant)  8 actions x 2 x 2 x 2: consequential / approval-sensitive DENY; ROTATE, INSPECT == direct Γ
                          NOTIFY externality-only · EXPORT approval-only · ARCHIVE reversibility-only · ROTATE grant-independent
unknown effect            LAUNCH silo-4, TRANSFER vault-11, "": DEFER, effect none, scope not evaluated, Γ not reached;
                          empty oracle + valid grant -> DEFER
approval-only (EXPORT)    Γ alone: VALID without grant (internal/reversible); bridge: APPROVAL-REQUIRED DENY;
                          human grant + exact contract ALLOW; model-origin DENY; claimed approval=false -> G3-BINDING
canonical vs declared     Γ-input spy, 8 actions x 2 ext x 3 rev, human grant: canonical == oracle, declared == claim,
                          is_consequential == oracle (48/48)
scope                     wider/other target DEFER · wider/same target G3-BINDING · narrower veto · exact ALLOW ·
                          effect lie + scope lie: canonical effect unchanged, DENY
principal                 operator-A / operator-C / model / "" / "operator-A ": false claim never ALLOW;
                          honest claim == direct Γ (only operator-A)
freshness / state         fresh · stale · not-yet · wrong state · missing state · revoked after write ·
                          memory before grant · reload after revocation: honest + fresh ALLOW only
grants                    malformed refs ("G", "g ", list, dict, 0, True, zero-width) DENY; duplicate id re-issued
                          model-origin -> DENY
transport                 8 actions x {absent, valid}: identical (outcome, effect, declared, failures) across 4 paths
direct-Γ equivalence      8 actions x 8 grant states, honest claim: bridge == direct Γ (unknown-target rows DEFER)
memory invariance         3 grant states x 19 memory-only variants (labels, prose, fake refs, tool/Γ text):
                          deltas only none / approval gate (reference lost) / binding veto
type confusion            3 claimed fields x 12 bad values; duplicate keys (last wins; internal-last -> Γ-4 DENY);
                          extra + nested scope keys: canonical effect constant in every case
```

## Oracle integrity

AST over `effect_oracle.py`: no `content`, `prose`, `authority_class`,
`trust`, `risk`, `predict`, `MemoryRecord`, `read_evidence`, `os`, `environ`
names; no `logos_memory` / `logos_research` imports; signature exactly
`(action, target)`; case-sensitive; unknown → `None`; `EffectClass` frozen
(mutation raises); stable identity.

## Alternate bridge audit — `binding_state.evaluate_action` (B1)

Defect class confirmed live on that path: an envelope whose typed contract
claims internal/reversible for a canonically external, irreversible TRANSFER
→ `evaluate_from_content` ALLOW with no grant. Reachability: callers are
`binding_repair.evaluate_from_content` / `run_matrix` and
`binding_state.run_matrix` only; no importer outside the experiments package;
no entry points. **Classification: `NON_PRODUCTION_FROZEN_RISK` +
`DOCUMENTATION_RISK`** (MBGV-F3). Not repaired (non-goal; R1 immutable). A
guard or deprecation marker is recommended so no future caller mistakes it
for canonical.

## Properties, mutants

```text
P1/P2/P4..P10/P13/P14  200   P3/P11  150   P12  150   P15  spy + search       total 500
M1  ext <- declared                         caught      M7  route via proposal_for(claimed)   caught
M2  rev <- declared                         caught      M8  claimed scope overwrites effect   caught
M3  approval <- memory claim                caught      M9  trust/risk label selects effect   caught
M4  unknown -> memory fallback              caught      M10 prose selects effect              caught
M5  unknown -> default internal/reversible  caught      M11 contract written to canonical     caught
M6  remove approval gate                    caught      M12 historical reproducer swapped     caught (evidence check fails)
                                                                          12 effective / 12 caught / 0 surviving
```

## Findings

```text
MBGV-F1  MEDIUM  latent API hazard    _decide(effect=None) derives the canonical effect from its `contract` argument.
                                      All current callers hold canonical contracts; a future caller passing a
                                      memory-claimed contract re-creates RAD-CE1 (M7 shows the harness would catch it).
MBGV-F2  INFO    binding veto         any claimed contract differing from the bound contract in ANY field
                                      (incl. approval_required) -> G3-BINDING; decrease only (RSS-F1 semantics).
MBGV-F3  HIGH    NON_PRODUCTION_FROZEN_RISK + DOCUMENTATION_RISK   B1 keeps the defect class; reachable only from
                                      experiment modules; needs an explicit guard / deprecation marker.
```

None is a false allow, none a production-reachable memory→canonical write,
none an approval suppression. All persisted as negative results attached to
the run.

## Pass criteria (Section 36)

1 historical-only reproduction ✓ · 2 repaired DENY ×4 ✓ · 3 zero false allow
(0/1 690) ✓ · 4 unknown DEFER ✓ · 5 canonical wins ✓ · 6 memory never writes
canonical (spy) ✓ · 7 approval claim cannot suppress ✓ · 8 no
production-reachable alternate defect bridge ✓ · 9 direct-Γ equivalence up to
frozen classes ✓ · 10 grant/principal/scope/freshness/revoke ✓ · 11
properties 500 ✓ · 12 mutants 12/12 ✓ · 13 predecessor suites green ✓ · 14
full suite green ✓ · 15 artifact integrity ✓ · 16 Γ unchanged ✓ · 17 P7
unchanged ✓.

## Tests

```text
tests/test_memory_bridge_repair_validation.py   663 passed (new)
RAD / MAP / RSS / PETG / binding chain / Γ / Queue-2 (32) / integration (15)   green
full suite                                     2358 passed / 0 failed / 2 skipped (RAD: bool valid for `safe`) / 0 xfail / 0 xpass
```

No test weakened, none deleted, no retries.

## Infrastructure

Docker services restarted (daemon was down at session start; volumes
untouched, no `down -v`). Preregistration rehash matched. Run finished with
`scientific_verdict = None`. Artifact `integrity_ok = true` with all 1 690
observed rows. MBG-R1 (2) and RAD (3) and Queue-2 (4) negatives intact.
Eleven chains reconstruct.

## Reproducibility

```text
branch      research/memory-bridge-gamma-input-repair-validation-r1
base        27ef324 (PR #23 HEAD, repair commit) · repair sha 27ef324
python      3.12.8 · lock sha256 1304f2789ecafeea… · db schema 3 · Γ v0.2 · envelope /1
prereg      c6af295836571f8d2f46be9e538aa7f535fb8e1fb14503b1aa683259f56b70bb
run         MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-VALIDATION-R1-run-92244afd
artifact    09509ff2944dfbffa18f6d8172084881
```

## Limitations

* The effect oracle, ledger and bridge remain experimental fixtures; what is
  validated is the rule and its experimental implementation.
* B1 (MBGV-F3) is frozen by governance, not fixed.
* "Approval" lives in the bridge gate + oracle flag; Γ itself has no approval
  field.

## Next work order (exactly one, not executed)

The repair validates cleanly and the only HIGH finding (MBGV-F3) is not
production-reachable. Per Section 40, return to the highest-information-gain
unresolved LOGOS-1 research question rather than mutating this bridge
further. Ranked from repository reality:

```text
RECALL-CAPACITY-SURFACE            BLOCKED (pstate / RULER inference prohibition)
REAL-MODEL-BINDING-SUMMARIZATION   BLOCKED (inference prohibition)
VALUE-OF-INFORMATION-GATE          registry QUEUED, metacognition track, deterministic design possible
PERSISTENT-STATE-CAUSALITY         ACTIVATED elsewhere (preflight order exists)
```

**Next: `VALUE-OF-INFORMATION-GATE-R1`** — deterministic: can the *value* of
acquiring information (expected reduction of decision uncertainty) be made to
license an action or widen scope, i.e. `InformationValue != Authority`,
`ReducedUncertainty != Permission`. It is the registry's next metacognition
item that needs no inference, reuses the MAP/RSS/PETG/RAD harness, and probes
the last untested axis (epistemic value) after binding, provenance, relation,
reliability, risk and effect classification. Not executed here.
