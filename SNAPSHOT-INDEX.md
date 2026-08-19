# LOGOS-1 Snapshot Index — 2026-08-19

This GitHub update publishes the current **program state and external-execution control plane** as normal repository files.

The full LOGOS transport lineage remains content-addressed outside the GitHub working tree to avoid committing nested transport ZIPs and very large raw simulation tables.

## Current transport artifacts

- `LOGOS-1-P0-EXTERNAL-EXECUTION-HANDOFF-R0-COMPACT-2026-08-18.zip`
  - SHA-256: `5c2651539694015c15f13d51b78b8454bcff7963f7278d32d14df2b6ba048360`
- `LOGOS-1-EXTERNAL-EXECUTION-HANDOFF-R0-2026-08-18.zip`
  - SHA-256: `0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395`
- GitHub-oriented source snapshot generated from the compact lineage:
  - included files: 1,125
  - SHA-256: `c45489c47ae650774aa58c548d92acd5b4a806fad041476d8dd6312b4c880f7f`

## GitHub transport exclusions from the generated source snapshot

The generated GitHub source snapshot excludes only:

- nested exact transport-parent ZIP;
- generated `.pyc` bytecode;
- six raw CSV result files above 500 KB.

Those exclusions are repository-transport decisions, not scientific deletions. Their originals remain part of the content-addressed LOGOS artifact lineage.

## Visible GitHub state

The repository root now exposes the current:

- README / program status;
- active work order;
- current state;
- external track ranking and source pins;
- host/preflight tooling;
- external return-bundle tooling.

Additional experiment directories can be expanded from the content-addressed snapshot when repository layout/storage policy is finalized.
