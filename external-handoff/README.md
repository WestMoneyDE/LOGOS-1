# LOGOS-1 External Execution Handoff R0

This handoff moves the source-pinned LOGOS external-validation tracks from sandbox preflight into a real Linux/Docker execution environment.

## Safety / scientific default

Everything is **plan-only by default**.

Track install/fetch/run actions must be explicitly executed. No API-key values are written into manifests or return bundles.

A failed dependency, download, model endpoint, runtime, or external service is:

`UNTESTED_RESOURCE_TRANSPORT`

and never a negative scientific result.

## Recommended order

1. MBE Behavioral-Lift
2. ENF safe-control-gym
3. WMR ARC-AGI-3
4. LongMemEval-V2
5. TCV Wrong but Useful
6. MF SkillsBench
7. SCB P×R Terminal-Bench
8. TANGLE only after an official release is resolved

See `TRACK-RANKING.md` and `TRACK-REGISTRY.json`.

## First commands

```bash
python common/handoff.py list
python common/handoff.py host-preflight
python common/handoff.py plan --track mbe
python common/handoff.py preflight --track mbe
```

## Result return

After a real run:

```bash
python common/collect_return.py \
  --track <track> \
  --run-root /path/to/run-output \
  --output returns/<track>-return.zip
```

Gamma live-provider execution is not part of this handoff and remains separately gated by a new explicit human authorization.
