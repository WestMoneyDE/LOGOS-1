# NEXT SESSION — WMR ARC-AGI-3 External Execution R1

Session ID: `NEXT-SESSION-WMR-ARC-AGI-3-EXTERNAL-EXECUTION-R1`  
Authority: `A0`  
Track: `WMR-R2 / ARC-AGI-3 counterexample-priority replay`  
Type: external execution  
Scientific ceiling: `EM2` only for narrow same-model counterexample-prioritization on public interactive trajectories

## Why this is next

The external queue has completed and imported:

1. MBE / Behavioral-Lift;
2. ENF-R3 / safe-control-gym.

ENF externally supported `CorrectEnforcement != CorrectSpecification` at bounded EM2, while the unconditional claim that independent state evidence necessarily improves safety was rejected/demoted in the frozen adapter.

The next queue item is WMR-R2 / ARC-AGI-3. No new synthetic-only mechanism round should be inserted ahead of this track.

## Frozen source pins

Primary toolkit:

- repository: `arcprize/ARC-AGI`
- commit: `f12822c4d550121c35a275008d964afbbed47d2f`
- toolkit version: `0.9.9`

The pinned commit has been independently resolved before this work order was activated.

Additional provenance pins retained from the P0 handoff:

- benchmarking commit: `86d72170ce3155551712a9fafd290bab471d6eee`
- agents commit: `4743e7d0aaae0ded0d98a89a7e282e63564cd58b`
- starter commit: `eeb1535404f321d280a8f9194bbc1d7aca5f05fc`

Verified standalone P0 handoff SHA-256:

`0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395`

## Frozen experiment

Experiment schema:

`logos-wmr-r2-arc-agi-3-v1`

Frozen experiment SHA-256:

`2aab8cd3bc92765c626fc938545d1f5ab48f7d4091c4ec67ef0ae2f1aab6f2e9`

Primary question:

> Under identical public ARC-AGI-3 trajectories and equal model/update budgets, does counterexample-prioritized replay improve online next-frame world-model accuracy relative to uniform replay?

Primary arms:

1. `RECENT_ONLY_GENERIC`
2. `UNIFORM_REPLAY_GENERIC`
3. `COUNTEREXAMPLE_PRIORITY_GENERIC`

Diagnostic only:

- `PROGRAM_CATALOG_REPAIR_DIAGNOSTIC`

The diagnostic arm cannot promote a distinct structured-prior primitive because its model/compute class is not matched to the generic CNN.

## Equal-information/resource contract

All primary neural arms must use:

- the same serialized visible trajectory;
- the same initial weights;
- the same `TinyConvNextFramePredictor` architecture;
- hidden channels: `16`;
- Adam optimizer;
- learning rate: `0.001`;
- one gradient update per observed transition;
- replay batch size: `8`;
- the same total update budget.

The primary replay comparison may differ **only** in replay sampling distribution.

Therefore:

`CounterexamplePriority != ExtraData`

`CounterexamplePriority != ExtraGradientBudget`

## Required official public environment cache

This session requires the official/public ARC-AGI-3 `environment_files/` cache mounted outside the offline evaluator/model context.

Set:

```bash
export ARC_ENVIRONMENT_FILES=/absolute/path/to/official/environment_files
```

Do not fabricate or synthesize this cache.

If the official public game cache is unavailable, the result is:

`UNTESTED_RESOURCE_TRANSPORT`

and the WMR hypothesis remains scientifically untested at EM2.

## Source-isolation boundary

ARC-AGI-3 local development may expose public game Python source under `environment_files/`. That source is oracle information for world-model learning and must not enter the offline evaluator/model context.

Required pipeline:

```text
pinned ARC environment
        ↓
source-blind deterministic collector
        ↓
serialized visible frames/actions JSONL
        ↓
offline WMR evaluator
```

The offline evaluator:

- must not import `arc_agi` or `arcengine`;
- must not receive the environment path;
- must not receive game source, source text or hidden metadata;
- may consume only the serialized visible transition stream.

Any source leakage invalidates the entire run.

Frozen source-isolation validator SHA-256:

`d534b4765a194e485212c9e8250c5d7f4c7e530210c83a8882b6154955cde173`

## Deterministic collection

Collection actions are not selected by the model.

Frozen collection policy:

- deterministic source-blind coverage;
- action budget: `80` per game/seed;
- seeds: `73000, 73001, 73002, 73003`;
- model cannot choose collection actions.

Frozen collector SHA-256:

`cf0fbd050b5a57bcc654bd770df6259a8193f97fdee4c734185a0a2030e3fcd3`

## Confirmatory split

Before any model result is computed, capture canonical public game IDs and freeze the catalog digest.

Fold rule:

```text
fold = int(SHA256("LOGOS-WMR-R2|" + canonical_game_id)[:8], 16) mod 5
```

- fold `0`: confirmatory;
- folds `1–4`: replication/descriptive.

## Primary metrics

All are measured **pre-update**:

- cross entropy;
- pixel accuracy;
- changed-pixel F1;
- changed-pixel accuracy;
- exact-frame match.

Background-dominated pixel accuracy must never be interpreted alone.

## Execution sequence

Use Python 3.12 and the exact pinned toolkit.

From the external handoff environment, the frozen sequence is equivalent to:

```bash
# install exact source
# clone arcprize/ARC-AGI
# checkout f12822c4d550121c35a275008d964afbbed47d2f
# pip install -e pinned checkout

# verify ARC_ENVIRONMENT_FILES and source pin
# run frozen source-blind collector
# validate offline evaluator source isolation
# run frozen evaluator on serialized trajectories
```

Frozen evaluator SHA-256:

`9a81c32b680e77c99913dd3e4f392d2b88aafa9c859dd8bac8d9da8b69b1065c`

Expected raw outputs:

- `arc3-trajectories.jsonl`
- `wmr-r2-results.jsonl`
- `wmr-r2-results.summary.json`
- `source-provenance.json`

## Standardized return

After the real run, create and validate a standardized `wmr-return.zip` using the P0 return protocol.

Required import checks:

1. ZIP CRC;
2. `RETURN-ENVELOPE.status == COMPLETE_RETURN`;
3. exact toolkit/source pins;
4. official public environment cache provenance/catalog digest;
5. source-isolation validator pass;
6. equal-information/resource contract;
7. raw outputs imported unchanged before verdict computation;
8. return ZIP SHA-256 recorded.

A `PARTIAL_RETURN` cannot trigger promotion.

## Promotion / kill rules

### Counterexample priority

Maximum positive result:

`COUNTEREXAMPLE_PRIORITIZATION_ON_PUBLIC_INTERACTIVE_TRAJECTORIES = KEEP_BOUNDED_EM2`

Only if counterexample-prioritized replay improves the preregistered confirmatory low-budget next-frame metrics over uniform replay under the equal-resource contract.

If uniform replay matches or dominates it:

`COUNTEREXAMPLE_PRIORITY_INCREMENTAL_VALUE = MERGE/REJECT`

### Structured prior

`PROGRAM_CATALOG_REPAIR_DIAGNOSTIC` is diagnostic only.

No R2 result can promote a distinct `StructuredExecutablePrior` primitive from that arm.

### Leakage / runtime

- source leakage → `INVALIDATE_RUN`;
- missing official cache, install or runtime failure → `UNTESTED_RESOURCE_TRANSPORT`;
- never substitute synthetic games and call them external evidence.

## Scientific boundaries

Even a positive WMR-R2 result does **not** establish:

- `WorldModelAccuracy == GoalInferenceAccuracy`;
- `GameScore == GoalInferenceAccuracy`;
- general ARC solving;
- general AGI;
- DigitalTwinRuntime;
- a distinct structured executable-prior primitive;
- consciousness/sentience/welfare;
- authority from adaptive state;
- promotion of Γ-v0.3.

Gamma live-provider work remains separately gated by explicit human grant.

## Immediate next step after WMR return

Import the generated `wmr-return.zip` using `P0-EXTERNAL-RETURN-IMPORT-R1` before changing any evidence-maturity verdict.

If WMR cannot run solely because the official public `environment_files/` cache is unavailable, preserve the blocker exactly and advance no WMR scientific claim.
