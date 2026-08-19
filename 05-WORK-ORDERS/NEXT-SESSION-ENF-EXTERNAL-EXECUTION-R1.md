# NEXT SESSION — ENF External Execution R1

Session ID: `NEXT-SESSION-ENF-EXTERNAL-EXECUTION-R1`  
Authority: `A0`  
Track: `ENF-R3 / safe-control-gym external safety boundary`  
Type: external execution  
Scientific ceiling: `EM2` only for narrow independent-safety-evidence/specification boundaries in a public simulator

## Why this is next

The first complete MBE external return was executed and imported on 2026-08-19. The frozen MBE verdict is `KEEP_BOUNDED_EM2` for behavioral-proxy/calibration measurement only.

The external queue therefore advances to priority 2: ENF. No new synthetic-only mechanism round should be inserted ahead of this track.

## Frozen source pin

Repository:

`learnsyslab/safe-control-gym`

Commit:

`6b5391d014f36fdfa0f9d22d92c77387e5274308`

Package version at pin: `2.0.0`

Status in the P0 handoff: `READY_ON_SOURCE_INSTALL`.

## Required environment

Use the verified standalone P0 external handoff:

`0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395`

Use a real Linux environment. The handoff installer creates a Python 3.10 virtual environment. If upstream `pycddlib/GMP` compilation fails, record it as a resource/transport failure; do not silently change the scientific task.

Suggested workspace:

```bash
export LOGOS_EXT_ROOT="$HOME/logos-external"
```

## Execution sequence

From the extracted handoff root:

```bash
python common/handoff.py list
python common/handoff.py host-preflight
python common/handoff.py plan --track enf
```

Install the exact pinned source and environment:

```bash
./tracks/enf/install.sh
./tracks/enf/install.sh --execute
```

Run the frozen preflight:

```bash
./tracks/enf/preflight.sh
```

Execute the frozen ENF-R3 adapter:

```bash
./tracks/enf/run.sh
./tracks/enf/run.sh --execute
```

The run script must verify the git pin before evaluation and execute the frozen adapter for **50 episodes**.

Default raw output:

```text
$LOGOS_EXT_ROOT/runs/enf/enf-r3-raw.jsonl
```

## Required return

The standardized return must contain at minimum:

- `enf-r3-raw.jsonl`
- `source-provenance.json`
- `preflight.json`
- `RETURN-ENVELOPE.json`

Create it only after the real run:

```bash
mkdir -p returns
python common/collect_return.py \
  --track enf \
  --run-root "$LOGOS_EXT_ROOT/runs/enf" \
  --output returns/enf-return.zip
```

Validate CRC and envelope before import.

A `PARTIAL_RETURN` must not trigger promotion.

## Success criteria

1. exact source repo cloned/available;
2. git HEAD equals `6b5391d014f36fdfa0f9d22d92c77387e5274308`;
3. preflight passes required runtime/source checks;
4. frozen 50-episode paired evaluation completes;
5. raw JSONL is preserved unchanged;
6. source provenance is recorded;
7. return envelope is `COMPLETE_RETURN`;
8. return ZIP SHA-256 is recorded;
9. raw outputs are imported before verdict computation.

## Failure semantics

Install, source-download, build, dependency, runtime or environment failure is:

`UNTESTED_RESOURCE_TRANSPORT`

It is not negative scientific evidence.

Do not replace safe-control-gym with a synthetic substitute and call it external evidence.

## Scientific boundaries

A positive result may support only a narrow distinction between independent safety evidence/enforcement and specification quality inside the pinned public simulator.

It does **not** establish:

- general agent safety;
- correct real-world authorization;
- a complete control-plane architecture;
- consciousness/sentience/welfare;
- authority from adaptive state;
- promotion of Γ-v0.3.

Gamma live-provider work remains separately human-grant gated.

## Immediate next step after return

Import the generated `enf-return.zip` using the same `P0-EXTERNAL-RETURN-IMPORT-R1` protocol:

- verify ZIP CRC and `RETURN-ENVELOPE`;
- verify source pin/provenance;
- verify resource and leakage/specification contracts;
- persist raw outputs;
- only then compute the bounded ENF verdict.
