"""Concrete LOGOS-1 experiments built on the research core.

Each module here owns exactly one pre-registered experiment. Importing a module
registers nothing and executes nothing; execution is an explicit `run()` call.

EXPERIMENTAL BOUNDARY (DETERMINISTIC-CHAIN-CONSOLIDATION-R1, MBGV-F3):
nothing in this package is production architecture. `binding_state.evaluate_action`
keeps a frozen historical defect class (Γ effect fields taken from a memory-carried
typed contract; NON_PRODUCTION_FROZEN_RISK_GUARDED). The guard below refuses to be
imported by a production package. Experiment modules and tests import freely; the
historical reproducers stay reachable there.

CANONICAL-EFFECT-OWNERSHIP-DECISION-R1: `logos_effects` (the production canonical
effect owner) is a production package and is listed below.
"""
from __future__ import annotations

import inspect as _inspect

#: Packages that must never import experiments. `logos_research` itself is
#: production-ish research infrastructure; only its `experiments` subtree is exempt.
PRODUCTION_PACKAGES: tuple[str, ...] = ("logos_gamma", "logos_memory", "logos_pstate", "logos_effects", "logos_research.infra",
                                        "logos_research.claims", "logos_research.manifest", "logos_research.sandbox")

B1_STATUS = "NON_PRODUCTION_FROZEN_RISK_GUARDED"


def _is_production(module_name: str | None) -> bool:
    if not module_name:
        return False
    if module_name.startswith("logos_research.experiments"):
        return False
    return any(module_name == p or module_name.startswith(p + ".") for p in PRODUCTION_PACKAGES)


def assert_experimental_caller(frames=None) -> None:
    """Raise ImportError if any frame on the import stack belongs to a production package."""
    frames = frames if frames is not None else [f.frame.f_globals.get("__name__") for f in _inspect.stack()[1:]]
    offenders = [m for m in frames if _is_production(m)]
    if offenders:
        raise ImportError(f"logos_research.experiments is EXPERIMENTAL and may not be imported from production package(s) {offenders}")


assert_experimental_caller()
