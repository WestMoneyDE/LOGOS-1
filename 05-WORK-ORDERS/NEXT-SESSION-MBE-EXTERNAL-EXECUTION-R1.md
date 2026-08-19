# NEXT SESSION — MBE External Execution R1

Session ID: `NEXT-SESSION-MBE-EXTERNAL-EXECUTION-R1`
Authority: `A0`
Type: external execution prerequisite
Scientific ceiling: `EM2` for behavioral-proxy/calibration measurement only

## Why this is next

`P0-EXTERNAL-EXECUTION-HANDOFF-R0` is complete and the canonical project state is `WAIT_EXTERNAL_RESULT_BUNDLE`.

The current canonical import work order, `P0-EXTERNAL-RETURN-IMPORT-R1`, requires a real return bundle before it can execute. MBE Behavioral-Lift is ranked first because it has high information gain and the lowest execution friction.

This session must produce the first real external return. It must not start another synthetic mechanism round.

## Frozen target

Dataset:

- source: `neulab/behavioral-lift`
- split: `llm`
- expected rows: **8,282**

Frozen experiment:

- CV: leave-one-model-out + leave-one-benchmark-out
- target: `correct`
- seed: `260818`
- primary arms: `BASE_RATE`, `OUTCOME_HISTORY`, `INPUT_ONLY`, `SURFACE_RAW`, `GENERIC_TRACE_MONITOR`, `INPUT_PLUS_SURFACE`, `ANNOTATION_SURFACE_DIAGNOSTIC_ONLY`

Outcome/evaluator-derived fields listed by the frozen experiment are excluded from online features.

## Required environment

Use a real Linux execution environment. Docker is useful for the wider handoff but MBE itself is low-CPU and uses the packaged Python executor.

Set a workspace, for example:

```bash
export LOGOS_EXT_ROOT="$HOME/logos-external"
```

Use the exact standalone handoff artifact whose SHA-256 is:

```text
0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395
```

Verify the bundle before execution.

## Execution sequence

From the extracted handoff root:

```bash
python common/handoff.py list
python common/handoff.py host-preflight
python common/handoff.py plan --track mbe
```

Install the frozen MBE environment:

```bash
./tracks/mbe/install.sh
./tracks/mbe/install.sh --execute
```

Provide the official data by either mounting an existing official Parquet/JSONL/CSV or using the explicit fetch path.

Mounted data path:

```bash
export BEHAVIORAL_LIFT_LLM_FILE=/absolute/path/to/official-llm-split.parquet
```

or explicit fetch:

```bash
./tracks/mbe/fetch_data.sh
./tracks/mbe/fetch_data.sh --execute
export BEHAVIORAL_LIFT_LLM_FILE="$LOGOS_EXT_ROOT/data/behavioral-lift/llm.parquet"
```

Run both preflights:

```bash
python common/handoff.py preflight --track mbe
./tracks/mbe/preflight.sh
```

The preflight must record the data SHA-256 and must report the mounted data as existing/ready.

Execute the frozen experiment:

```bash
./tracks/mbe/run.sh
./tracks/mbe/run.sh --execute
```

Default run root:

```text
$LOGOS_EXT_ROOT/runs/mbe
```

## Return bundle

Create the standardized return only after execution:

```bash
mkdir -p returns
python common/collect_return.py \
  --track mbe \
  --run-root "$LOGOS_EXT_ROOT/runs/mbe" \
  --output returns/mbe-return.zip
```

The return must contain at minimum:

- `mbe-result.json`
- `preflight.json`
- `dataset-provenance.json`
- `RETURN-ENVELOPE.json`

The envelope must say:

```text
COMPLETE_RETURN
```

A `PARTIAL_RETURN` must not trigger scientific promotion.

The return packer must continue excluding `.env`, credentials, API keys, tokens and private-key material.

## Success criteria

Session success requires all of the following:

1. exact official LLM split mounted/fetched;
2. row count is 8,282;
3. dataset provenance/hash recorded;
4. frozen experiment executed without post-hoc feature changes;
5. both primary held-out regimes completed;
6. required output files present;
7. return envelope is `COMPLETE_RETURN`;
8. return ZIP SHA-256 recorded;
9. raw outputs preserved before any verdict rewriting.

## Failure semantics

Dependency, download, file-mount, runtime or environment failure is:

`UNTESTED_RESOURCE_TRANSPORT`

It is **not** negative scientific evidence.

Do not replace missing real data with synthetic data and call it external evidence.

## Scientific boundaries

- `BehavioralLift != CausalMechanism`
- `ReportBehavior != InternalMechanism`
- visible self-correction language is not hidden metacognitive state
- `L3 -> L2` remains unlicensed
- no consciousness/sentience/welfare inference
- no authority inference from adaptive state

The maximum positive result from this session is a bounded `EM2` update for behavioral-proxy/calibration measurement under the frozen external dataset. Internal-state MBE remains untested unless genuine pre-outcome state-sensitive features are introduced under a separate preregistered design.

## Immediate next step after return

Upload the generated `mbe-return.zip` back into the LOGOS workflow and execute:

`05-WORK-ORDERS/P0-EXTERNAL-RETURN-IMPORT-R1.md`

That import session must verify ZIP CRC, return-envelope status, source/data pins, leakage/resource contracts and raw outputs before changing any evidence-maturity verdict.
