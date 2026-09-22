"""Runnable demonstrations of the LOGOS-1 boundary.

Nothing in here is a source of truth. `core.governance` is a thin facade over the
real trusted core (`logos_gamma`); it holds no rules of its own. A second rule
system would be a defect, not an extension (`logos_gamma.invariants`).

This package lives at the repository root and NOT under `src/`, deliberately.
`src/` is the library tree, and several frozen governance records audit every
file in it — the canonical-effect owner audit, the memory-bridge constructor
inventory, the production-bridge source classification. A demonstration that
constructs an `EffectProposal` would show up in all of them and would force a
change to records that are frozen on purpose. Keeping the demo out of `src/`
removes the collision instead of amending the records.

It is importable in the test suite through `pythonpath = [".", "src"]` and
runnable as a script: `python core/governance.py`.
"""
