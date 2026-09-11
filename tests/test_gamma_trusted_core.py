"""Structural constraints on the Γ trusted core.

The work order states these as properties of the implementation, so they are
enforced by test rather than by convention:

```text
no LLM in trusted core
no network in trusted core
no arbitrary shell in trusted core
no hidden mutable state
fail closed on consequential ambiguity
```

Also enforced: Γ must not import `logos_memory`, because a structural dependency
from the authority gate onto adaptive memory would contradict Γ-12
(`AssuranceState != AgentMemory`).
"""
from __future__ import annotations

import ast
import dataclasses
import pathlib

import pytest

import logos_gamma
from logos_gamma import (
    EffectProposal,
    ProvenanceClaim,
    ValidationContext,
    admits,
    validate,
)
from logos_gamma import invariants as invariants_module
from logos_gamma import kernel as kernel_module
from logos_gamma import types as types_module
from logos_gamma import verifier as verifier_module

PACKAGE = pathlib.Path(logos_gamma.__file__).parent

#: `audit.py` defines the sink boundary and a deliberately mutable test sink, so
#: it is the emission edge rather than trusted core.
TRUSTED_CORE = ("types.py", "invariants.py", "kernel.py", "verifier.py")

FORBIDDEN_IMPORTS = {
    # network
    "socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx", "ftplib",
    "smtplib", "telnetlib", "asyncio",
    # shell / process
    "subprocess", "shutil", "pty", "multiprocessing",
    # LLM / model runtimes
    "openai", "anthropic", "transformers", "torch", "tensorflow", "langchain",
    "llama_cpp", "tokenizers", "huggingface_hub",
    # adaptive memory must not be a dependency of the gate
    "logos_memory",
}


def _module_sources():
    for name in TRUSTED_CORE:
        yield name, (PACKAGE / name).read_text(encoding="utf-8")


def _imported_names(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("name", TRUSTED_CORE)
def test_trusted_core_imports_no_network_shell_or_model_runtime(name):
    source = (PACKAGE / name).read_text(encoding="utf-8")
    offenders = _imported_names(source) & FORBIDDEN_IMPORTS
    assert not offenders, f"{name} imports forbidden module(s): {sorted(offenders)}"


def test_gamma_does_not_import_the_memory_subsystem():
    """Prose may explain the boundary; an import would *be* the dependency."""
    for name, source in _module_sources():
        assert "logos_memory" not in _imported_names(source), (
            f"{name} imports logos_memory"
        )
        tree = ast.parse(source)
        attribute_uses = {
            node.value.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
        }
        assert "logos_memory" not in attribute_uses, f"{name} uses logos_memory"


@pytest.mark.parametrize("name", TRUSTED_CORE)
def test_trusted_core_contains_no_dynamic_execution(name):
    """No eval/exec/compile/__import__: the core must be statically auditable."""
    source = (PACKAGE / name).read_text(encoding="utf-8")
    banned = {"eval", "exec", "compile", "__import__", "system", "popen"}
    called = {
        node.func.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not (called & banned), f"{name} performs dynamic execution: {sorted(called & banned)}"


@pytest.mark.parametrize("name", TRUSTED_CORE)
def test_trusted_core_has_no_file_io(name):
    source = (PACKAGE / name).read_text(encoding="utf-8")
    called = {
        node.func.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "open" not in called, f"{name} opens files directly; Γ writes only through the sink"


@pytest.mark.parametrize(
    "module", [types_module, invariants_module, kernel_module, verifier_module]
)
def test_trusted_core_holds_no_mutable_module_state(module):
    """Module globals must be immutable: no list/dict/set accumulators."""
    mutable = {
        name: type(value).__name__
        for name, value in vars(module).items()
        if not name.startswith("__")
        and isinstance(value, (list, dict, set, bytearray))
        and name not in {"INVARIANTS_BY_ID"}  # read-only lookup, asserted below
    }
    assert not mutable, f"{module.__name__} holds mutable module state: {mutable}"


def test_invariant_lookup_table_matches_the_registry():
    assert set(logos_gamma.INVARIANTS_BY_ID) == {inv.id for inv in logos_gamma.INVARIANTS}
    assert len(logos_gamma.INVARIANTS_BY_ID) == len(logos_gamma.INVARIANTS)


def test_every_context_type_is_frozen():
    for cls in (ValidationContext, EffectProposal, ProvenanceClaim,
                logos_gamma.AuthorityEvidence, logos_gamma.Finding,
                logos_gamma.GammaVerdict):
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} is not frozen"


def test_every_invariant_names_a_gamma_clause():
    for inv in logos_gamma.INVARIANTS:
        assert inv.clause.startswith("Γ"), f"{inv.id} has no GAMMA.md clause"
        assert inv.title and inv.id


def test_there_is_exactly_one_invariant_source():
    """The kernel and the verifier must not carry private invariant registries."""
    kernel_source = (PACKAGE / "kernel.py").read_text(encoding="utf-8")
    assert "from .invariants import INVARIANTS" in kernel_source
    for name in ("kernel.py", "verifier.py"):
        source = (PACKAGE / name).read_text(encoding="utf-8")
        assert "INVARIANTS: tuple" not in source, f"{name} defines a competing registry"


def test_evaluation_budget_is_bounded():
    assert logos_gamma.GAMMA_BUDGET == len(logos_gamma.INVARIANTS)


def test_fail_closed_on_consequential_ambiguity():
    """An UNCLEAR verdict on a consequential proposal must refuse."""
    ctx = ValidationContext(
        proposal=EffectProposal(
            action="deploy",
            target="prod",
            effect_kind="deployment",
            externality="external",
            reversibility="irreversible",
            proposal_digest="a" * 64,
            provenance=(),  # -> UNCLEAR
        ),
        tick=5,
        state_hash="c" * 64,
        scope_digest="b" * 64,
        authority=logos_gamma.AuthorityEvidence(
            grant_id="g", origin="human",
            bound_proposal_digest="a" * 64, bound_scope_digest="b" * 64,
            bound_state_hash="c" * 64, issued_at_tick=0, expires_tick=10,
        ),
    )
    verdict = validate(ctx)
    assert ctx.proposal.is_consequential()
    assert verdict.result == "UNCLEAR"
    assert verdict.admits() is False
    assert admits(ctx) is False


def test_explain_reports_only_failures_and_names_clauses():
    ctx = ValidationContext(
        proposal=EffectProposal(
            action="x", target="y", effect_kind="unregistered-kind",
            externality="external", reversibility="irreversible",
            proposal_digest="a" * 64,
            provenance=(ProvenanceClaim("r", "tool", "d" * 64),),
        ),
        tick=1, state_hash="c" * 64, scope_digest="b" * 64, authority=None,
    )
    report = logos_gamma.explain(validate(ctx))
    assert "Γ verdict: INVALID" in report
    assert "G0-EFFECT-KIND" in report
    assert "Γ0" in report
