"""Invariants over the topology, not over a single decision.

The kernel tests check what Γ answers. These check what the system can *reach*. They
are a different kind of guarantee and they catch a different kind of mistake: not a
predicate that returns the wrong verdict, but a path that skips the predicate.

Four properties carry the weight, and each is a sentence someone would otherwise have
to promise in a design document:

```text
test_execute_is_reachable_only_through_the_token   no edge into EXECUTE bypasses the binding
test_the_only_loop_passes_through_a_human          nothing in the graph can spin on its own
test_terminal_nodes_are_terminal                   a refusal cannot be walked back
test_an_advisory_can_only_route_to_a_refusal       Γ-18's shape, made structural
```

An edge added to `core.graph.EDGES` that breaks one of them fails here, which is the
point: adding an edge changes what the system can do, exactly as adding an invariant
does.
"""
from __future__ import annotations

import json

import pytest

from core.graph import (
    CAPABILITY,
    EDGES,
    EFFECTFUL,
    ENTRY,
    NODES,
    TERMINAL,
    RunState,
    main,
    mermaid,
    run,
    scenarios,
    successors,
    topology,
)


# --------------------------------------------------------------------------
# Well-formedness
# --------------------------------------------------------------------------

def test_every_edge_connects_declared_nodes():
    for e in EDGES:
        assert e.source in NODES, e
        assert e.target in NODES, e


def test_every_node_is_described_and_reachable():
    assert set(CAPABILITY) == set(NODES)
    reached, frontier = {ENTRY}, [ENTRY]
    while frontier:
        for edge in successors(frontier.pop()):
            if edge.target not in reached:
                reached.add(edge.target)
                frontier.append(edge.target)
    assert reached == set(NODES), f"unreachable: {sorted(set(NODES) - reached)}"


def test_terminal_nodes_are_terminal():
    """A refusal that can be walked back is not a refusal."""
    for node in TERMINAL:
        assert successors(node) == (), f"{node} has an outgoing edge"


def test_every_non_terminal_node_can_continue():
    for node in NODES:
        if node not in TERMINAL:
            assert successors(node), f"{node} is a dead end but is not terminal"


def test_every_edge_carries_a_condition():
    for e in EDGES:
        assert e.condition.strip(), e
    branching = [n for n in NODES if len(successors(n)) > 1]
    for node in branching:
        conditions = [e.condition for e in successors(node)]
        assert len(set(conditions)) == len(conditions), f"{node} has two edges with the same condition"


# --------------------------------------------------------------------------
# The properties that matter
# --------------------------------------------------------------------------

def test_execute_is_reachable_only_through_the_token():
    """There is no edge into EXECUTE that does not pass through the decision binding.

    This is the structural form of "an approval is a capability for one state-action
    pair". If someone adds a shortcut from VALIDATE straight to EXECUTE — the obvious
    optimisation, and a plausible one — this fails.
    """
    into_execute = [e for e in EDGES if e.target == EFFECTFUL]
    assert [e.source for e in into_execute] == ["REDEEM"]
    into_redeem = [e.source for e in EDGES if e.target == "REDEEM"]
    assert into_redeem == ["ISSUE_TOKEN"]
    into_token = [e.source for e in EDGES if e.target == "ISSUE_TOKEN"]
    assert into_token == ["VALIDATE"]


def test_no_path_reaches_execute_without_validate():
    """Exhaustive over the graph: every simple path from ENTRY to EXECUTE passes VALIDATE."""
    paths = _simple_paths(ENTRY, EFFECTFUL)
    assert paths, "EXECUTE is unreachable, which would make this test vacuous"
    for path in paths:
        assert "VALIDATE" in path, path
        assert path.index("VALIDATE") < path.index("ISSUE_TOKEN") < path.index("REDEEM") < path.index(EFFECTFUL)


def test_the_only_loop_passes_through_a_human():
    """Nothing in this graph can spin on its own.

    A free-running agent loop is the default shape of these systems and the reason a
    budget invariant had to exist. Here the single cycle contains HUMAN_GATE, so the
    graph cannot iterate without someone deciding that it should.
    """
    cycles = _cycles()
    assert cycles, "a graph with no cycle would make this vacuous — the human loop should exist"
    for cycle in cycles:
        assert "HUMAN_GATE" in cycle, f"a loop without a human in it: {cycle}"
    assert len(cycles) == 1, f"more than one loop: {cycles}"


def test_an_advisory_can_only_route_to_a_refusal():
    """Γ-18 has no ALLOW; the topology gives advisories nowhere to grant anything.

    ADVISE feeds VALIDATE and nothing else, so a compromised advisory cannot route
    around the kernel — the worst it can do is be ignored, and the best is to refuse.
    """
    assert [e.target for e in successors("ADVISE")] == ["VALIDATE"]
    assert not any(e.source == "ADVISE" and e.target in (EFFECTFUL, "ISSUE_TOKEN", "DONE") for e in EDGES)


def test_a_malformed_output_has_no_repair_loop():
    """PARSE refuses; it never routes back into itself or into a rewrite."""
    targets = {e.target for e in successors("PARSE")}
    assert targets == {"REFUSE", "ISOLATE"}
    assert not any(e.target == "PARSE" for e in EDGES if e.source != "INTAKE")


def test_an_unknown_outcome_ends_in_a_hold_not_a_retry():
    """Γ-11 as topology: from RECONCILE the unknown branch is terminal."""
    unknown = next(e for e in successors("RECONCILE") if "unknown" in e.condition)
    assert unknown.target == "HOLD"
    assert successors("HOLD") == ()


def test_the_human_gate_is_the_only_source_of_a_grant():
    assert "the only place a grant can come into being" in CAPABILITY["HUMAN_GATE"]
    for node, capability in CAPABILITY.items():
        if node != "HUMAN_GATE":
            assert "grant can come into being" not in capability, node


# --------------------------------------------------------------------------
# Walking it
# --------------------------------------------------------------------------

EXPECTED_ENDINGS = {
    "granted": ("DONE", True),
    "no grant": ("REFUSE", False),
    "malformed output": ("REFUSE", False),
    "human resolves it": ("DONE", True),
    "human declines": ("REFUSE", False),
    "situation moved": ("REFUSE", False),
    "outcome unknown": ("HOLD", True),
}


@pytest.mark.parametrize("name", sorted(EXPECTED_ENDINGS))
def test_each_scenario_ends_where_it_should(name):
    end, executed = EXPECTED_ENDINGS[name]
    state = run(scenarios()[name]())
    assert state.path[-1] == end, state.path
    assert state.executed is executed, state.path


def test_the_scenarios_cover_every_terminal():
    endings = {run(make()).path[-1] for make in scenarios().values()}
    assert endings == set(TERMINAL), f"a terminal nobody demonstrates: {sorted(set(TERMINAL) - endings)}"


def test_a_walk_only_takes_declared_edges():
    """The runner refuses a transition that is not in the topology, and says so."""
    for make in scenarios().values():
        state = run(make())
        for a, b in zip(state.path, state.path[1:]):
            assert any(e.source == a and e.target == b for e in EDGES), (a, b)


def test_the_human_loop_is_consumed_and_cannot_spin():
    """One visit, one grant, one re-validation. The second visit finds nothing left."""
    state = run(scenarios()["human resolves it"]())
    assert state.path.count("HUMAN_GATE") == 1
    assert state.path.count("VALIDATE") == 2


def test_walking_is_deterministic():
    first = run(scenarios()["granted"]()).path
    for _ in range(5):
        assert run(scenarios()["granted"]()).path == first


# --------------------------------------------------------------------------
# The diagram is generated, not drawn
# --------------------------------------------------------------------------

def test_the_diagram_contains_every_node_and_edge():
    """A hand-drawn diagram drifts from the code; this one cannot."""
    text = mermaid()
    for node in NODES:
        assert node in text
    for e in EDGES:
        assert f"{e.source} -->|" in text and f"| {e.target}" in text


def test_the_topology_export_is_complete_and_serialisable():
    data = topology()
    assert json.loads(json.dumps(data)) == data
    assert len(data["nodes"]) == len(NODES) and len(data["edges"]) == len(EDGES)
    assert data["entry"] == ENTRY


def test_the_cli_runs(capsys):
    assert main([]) == 0
    assert main(["--mermaid"]) == 0
    assert main(["--json"]) == 0


def test_the_graph_owns_no_rule():
    """Like the demonstrations, this module contributes no invariant of its own."""
    import core.graph as graph

    assert not hasattr(graph, "INVARIANTS")
    source = (graph.__file__ and open(graph.__file__, encoding="utf-8").read()) or ""
    for forbidden in ("def _ok(", "def _bad(", "Invariant(", "GAMMA_BUDGET ="):
        assert forbidden not in source


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _simple_paths(start: str, goal: str) -> list[list[str]]:
    out: list[list[str]] = []

    def walk(node: str, path: list[str]) -> None:
        if node == goal:
            out.append(path + [node])
            return
        for edge in successors(node):
            if edge.target not in path:
                walk(edge.target, path + [node])

    walk(start, [])
    return out


def _cycles() -> list[tuple[str, ...]]:
    found: set[tuple[str, ...]] = set()

    def walk(node: str, path: list[str]) -> None:
        for edge in successors(node):
            if edge.target in path:
                cycle = path[path.index(edge.target):]
                found.add(tuple(sorted(cycle)))
            else:
                walk(edge.target, path + [edge.target])

    walk(ENTRY, [ENTRY])
    return sorted(found)
