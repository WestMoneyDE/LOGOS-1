# LOGOS-1 External Execution Handoff R0 — GitHub control-plane export

This directory exposes the **control plane** of the source-pinned LOGOS external-validation handoff on GitHub:

- track ordering and scientific ceilings;
- exact source pins and runtime blockers;
- host/track preflight logic;
- result-return packaging and secret exclusion;
- transport provenance.

The complete standalone handoff — including all track-specific install/fetch/run scripts and frozen adapters — remains in the content-addressed transport artifact recorded in [`../SNAPSHOT-INDEX.md`](../SNAPSHOT-INDEX.md):

`LOGOS-1-EXTERNAL-EXECUTION-HANDOFF-R0-2026-08-18.zip`

SHA-256:

`0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395`

## Safety / scientific default

Everything is **plan-only by default**.

No API-key values belong in repository files or return bundles.

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

## GitHub-visible commands

```bash
python external-handoff/common/handoff.py list
python external-handoff/common/handoff.py host-preflight
python external-handoff/common/handoff.py plan --track mbe
python external-handoff/common/handoff.py preflight --track mbe
```

These commands inspect the registry and environment. They do **not** download or execute track workloads.

## Result return

The return packer is included because it is track-agnostic:

```bash
python external-handoff/common/collect_return.py \
  --track <track> \
  --run-root /path/to/run-output \
  --output returns/<track>-return.zip
```

Gamma live-provider execution is not part of this handoff and remains separately gated by a new explicit human authorization.
