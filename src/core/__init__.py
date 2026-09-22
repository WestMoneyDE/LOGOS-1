"""Runnable demonstrations of the LOGOS-1 boundary.

Nothing in here is a source of truth. `core.governance` is a thin facade over the
real trusted core (`logos_gamma`); it holds no rules of its own. A second rule
system would be a defect, not an extension (`logos_gamma.invariants`).

This package is deliberately excluded from the distribution
(`pyproject.toml`, `[tool.setuptools.packages.find] exclude`): `core` is too
generic a name to install into a shared environment. It is importable in the
test suite through `pythonpath = ["src"]` and runnable as a script.
"""
