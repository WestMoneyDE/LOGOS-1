"""logos_dashboard — read-mostly research dashboard service (TOOLING; never PRODUCTION).

LOGOS-1-RESEARCH-DASHBOARD-SCIENTIFIC-CORE-R1. Structured state lives in docs/research/dashboard/*.json
(claims, experiments, invariants, prior art, publications, replication, open questions); Markdown records are
narrative; lab artifacts are evidence. The service never infers a scientific status from free text, never calls
a model, and writes exactly one file: ACTIVE-THESES.json (the founder's selection of theses to work on).
"""
from __future__ import annotations

import inspect as _inspect

SOURCE_CLASS = "TOOLING"
#: production packages that must never import this tooling
PRODUCTION_PACKAGES: tuple[str, ...] = ("logos_gamma", "logos_memory", "logos_pstate", "logos_effects", "logos_authority", "logos_runtime", "logos_audit", "logos_research.infra")


def assert_tooling_caller(frames=None) -> None:
    frames = frames if frames is not None else [f.frame.f_globals.get("__name__") for f in _inspect.stack()[1:]]
    offenders = [m for m in frames if m and any(m == p or m.startswith(p + ".") for p in PRODUCTION_PACKAGES)]
    if offenders:
        raise ImportError(f"logos_dashboard is TOOLING and may not be imported from production package(s) {offenders}")


assert_tooling_caller()
