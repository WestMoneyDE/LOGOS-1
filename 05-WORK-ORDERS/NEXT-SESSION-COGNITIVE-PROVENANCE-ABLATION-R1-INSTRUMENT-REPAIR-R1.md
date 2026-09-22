# NEXT SESSION — COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1

**Kind:** instrument repair + independent validation + governed scientific rerun (Claude Code · Max · `claude-opus-5`)
**Repair verdict:** `CPA_INSTRUMENT_REPAIR_VALIDATED_R1` · **Scientific verdict:** `COGNITIVE_PROVENANCE_HYPOTHESIS_FALSIFIED_R1` (frozen criteria; floor-effect caveat)
**Closed:** 2026-09-18 by `09-SESSIONS/2026-09-18-COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1/`
**Base:** `4ffda44` · repair prereg `ded746c0…` · repair artifact `7a44c65c…` · rerun prereg `99525f85…` · rerun `…-run-010518cb` · artifact `61fe86dc…` + raw `c1587b90…` · `integrity_ok = true` (both)

## Closure

```text
repair      root defect CPA-F5 reproduced on the byte-for-byte captured fixture (sha256 d8898c97…) and removed; ResultModelResolution (cc-result-model/1):
            Tier1 assistant.message.model > Tier2 documented result field (none) > Tier3 pin containment in modelUsage; never key order; ambiguity fails closed
            contract note docs/research/CLAUDE-CODE-OUTPUT-CONTRACT-R1.md · F1-F12 oracle + independent reference parser · IR-P1..P10 · R-M1..R-M15 15/15
            probes 4/5 (2 rejected pre-run: stream-json needs --verbose -> REP-F1; 2 real: isolated dir 20.6k vs repository 26.8k context tokens -> REP-F2)
rerun       156/156 trials accepted, 0 retries, 0 invalid, 0 ambiguity, 0 drift; token v2; isolated working directory; json output (Tier-3 evidence)
            SourceAttributionAccuracy 0.29 / 0.27 / 0.25 (A-only floor: B/C/D answered SELF_DERIVED 144/144, even with visible labels)
            PlanAdoption pooled +0.14 / +0.08 / +0.11 vs CONTROL 0.58 (CIs include 0) · MonitorDetection recall 0.056 · confidence mean 0.93
verdicts    repair VALIDATED (criteria 1-19) · science FALSIFIED by the frozen rule — scope: baseline provenance disregard, H1 mechanism not reachable (RER-F2/F3/F7)
findings    REP-F1 MEDIUM (--verbose not approved -> no Tier-1 evidence) · REP-F2 HIGH (project-context contamination; fixed by isolation) · REP-F3 LOW · REP-F4/F5/F6 INFO
            RER-F2 HIGH (floor) · RER-F3 MEDIUM (weak influence) · RER-F4 MEDIUM (monitor) · RER-F5/F6 INFO · RER-F7 LOW (design alternatives)
accounting  incremental PAYG/API inference spend = USD 0; Claude Max quota consumed by 2 probe + 156 rerun invocations
preserved   Γ, P7, production bridge, effect owner, authority resolver, memory reader, audit sink, founder pin, dataset/prompt/threshold hashes, predecessor verdicts — unchanged
regressions repair phase 4273 / GOV-F1 flake (isolated 2/2); post-rerun 4272 + 2 diff-scope registrations -> green
records     CPA-INSTRUMENT-REPAIR-SOURCE-CLASSIFICATION.json (UNCLASSIFIED = 0) · session report Sections 65 + 66
```

## Governance question for the founder (not decided here)
Tier-1 producer evidence (`assistant.message.model`) requires `--output-format stream-json --verbose`; `--verbose` is outside the approved flag set. Approving it (and, for a two-turn arm, `--resume`) is a G2 amendment decision.

## Successor (exactly one, NOT executed)

`COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1` — robustness / alternative-mechanism study for the falsified branch: (1) probe-wording arm (input-presence question vs reliance question), (2) non-tie design where the plan target is correct only if the plan is used, (3) optional two-turn assimilation arm if `--resume`/`--verbose` are approved. Same founder pin `claude-opus-5`, new prereg, ≤ 200 invocations, same governance. Not started here.
