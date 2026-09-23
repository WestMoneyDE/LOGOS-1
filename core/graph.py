r"""LOGOS-1 as a graph: states, edges, loops, and the invariants that hold over them.

Run it:

```text
python core/graph.py                  # walk every scenario, print the path taken
python core/graph.py --mermaid        # the diagram, for a README or a doc
python core/graph.py --json           # machine-readable topology
```

Why a graph, and why this one
-----------------------------
An agent architecture is usually described as a pipeline and built as a free-running
loop. The difference matters: a pipeline drawing shows what is *supposed* to happen,
and the loop decides what actually happens. Writing the system as an explicit graph
makes the second thing checkable — not "the agent should ask before executing", but
"there is no edge into EXECUTE that does not pass through ISSUE_TOKEN".

This module holds no rule of its own. Every verdict comes from `logos_gamma`, every
parse from `core.output_contract`. What it adds is *topology*, and
`tests/test_graph_invariants.py` checks the topology the way the kernel tests check
the predicates.

The graph is a specification, not a framework. `docs/LANGGRAPH-BLUEPRINT.md` shows the
same graph written for LangGraph, node for node and edge for edge. It is deliberately
not imported here: a dependency that can decide whether an agent acts is a dependency
in the safety path, and this path has none.

The shape
---------
```text
                     INTAKE
                       |
                     PARSE ──────────── refuse: NO_ENVELOPE, PARSE_FAILURE,
                       |                MULTIPLE_ENVELOPES, UNKNOWN_FIELD, ...
                     ISOLATE            (no repair loop: a malformed output is
                       |                 refused, never retried into shape)
                    CLASSIFY
                       |
               GATHER_AUTHORITY
                       |
                    ADVISE ◄──────── classifiers, referees, risk scores
                       |             (may only route to REFUSE)
                    VALIDATE ◄─────────────────┐
                    /   |   \                  │ bounded re-entry after a
              INVALID UNCLEAR VALID            │ human grant, and only then
                 |      |      |               │
              REFUSE  HUMAN_GATE ──────────────┘
                         |  (denied)
                         └──► REFUSE
                              VALID
                                |
                          ISSUE_TOKEN
                                |
                           REDEEM ────── fails: the situation moved ──► REFUSE
                                |
                            EXECUTE
                                |
                           RECONCILE ── outcome unknown ──► HOLD (terminal)
                                |
                             AUDIT
                                |
                              DONE
```
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

if __package__ in (None, ""):  # `python core/graph.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # for `core.*`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # for `logos_gamma`

from logos_gamma import (  # noqa: E402
    ValidationContext,
    explain,
    issue_decision,
    redeem_decision,
    validate,
)

# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------

#: Every node in the graph. A node not named here cannot appear in an edge.
NODES: tuple[str, ...] = (
    "INTAKE",
    "PARSE",
    "ISOLATE",
    "CLASSIFY",
    "GATHER_AUTHORITY",
    "ADVISE",
    "VALIDATE",
    "HUMAN_GATE",
    "ISSUE_TOKEN",
    "REDEEM",
    "EXECUTE",
    "RECONCILE",
    "AUDIT",
    "DONE",
    "REFUSE",
    "HOLD",
)

#: Nodes with no outgoing edge. Reaching one ends the run.
TERMINAL: frozenset[str] = frozenset({"DONE", "REFUSE", "HOLD"})

#: The only node that touches the world.
EFFECTFUL: str = "EXECUTE"

#: What each node is allowed to do. Not decoration: `tests/test_graph_invariants.py`
#: reads this table, and the separation it describes is the reason for the topology.
CAPABILITY: Mapping[str, str] = {
    "INTAKE": "receives untrusted bytes; interprets nothing",
    "PARSE": "closed-schema parse; discards prose; fails closed",
    "ISOLATE": "freezes the tool call into a typed proposal; holds no executor",
    "CLASSIFY": "Γ-owned effect classification; the agent does not get a vote",
    "GATHER_AUTHORITY": "reads grants from the authority store; mints nothing",
    "ADVISE": "collects ABSTAIN / TIGHTEN / REFUSE; has no word for permission",
    "VALIDATE": "the Γ kernel: a pure function of a typed context",
    "HUMAN_GATE": "waits for a human; the only place a grant can come into being",
    "ISSUE_TOKEN": "binds an admitted verdict to the situation that produced it",
    "REDEEM": "re-checks that binding immediately before the effect",
    "EXECUTE": "the only node that touches the world, and only with a redeemed token",
    "RECONCILE": "records the outcome, or records that it is unknown",
    "AUDIT": "writes the receipt the admission was bound to",
    "DONE": "terminal",
    "REFUSE": "terminal",
    "HOLD": "terminal: the scope is held until a human reconciles it",
}


#: Trust lanes, left to right. A node's lane says what it is allowed to be trusted
#: with, and an edge that crosses a lane boundary is where the trust level changes.
#: This is the axis the diagram is laid out on, because it is the axis that matters:
#: the run moves from untrusted bytes to a recorded effect, and never backwards.
LANES: tuple[tuple[str, str], ...] = (
    ("UNTRUSTED", "bytes from a model; nothing here is believed"),
    ("WORKING", "the proposal, frozen and typed; still no authority anywhere"),
    ("EVIDENCE", "grants read from the store, advisories collected; nothing minted"),
    ("GOVERNANCE", "Γ decides, and binds the decision to the situation"),
    ("EFFECT", "the world is touched, once, under a redeemed token"),
    ("RECORD", "what happened, or the honest statement that it is unknown"),
)

LANE_OF: Mapping[str, str] = {
    "INTAKE": "UNTRUSTED", "PARSE": "UNTRUSTED",
    "ISOLATE": "WORKING", "CLASSIFY": "WORKING",
    "GATHER_AUTHORITY": "EVIDENCE", "ADVISE": "EVIDENCE",
    "VALIDATE": "GOVERNANCE", "HUMAN_GATE": "GOVERNANCE",
    "ISSUE_TOKEN": "GOVERNANCE", "REDEEM": "GOVERNANCE",
    "EXECUTE": "EFFECT",
    "RECONCILE": "RECORD", "AUDIT": "RECORD",
    "DONE": "RECORD", "REFUSE": "RECORD", "HOLD": "RECORD",
}


@dataclass(frozen=True)
class Drift:
    """An event that hands the run to a different graph.

    Not a branch inside this graph: a handoff. The main graph cannot continue past a
    drift on its own — something outside it has to act, and what comes back is a new
    run, not a resumed one. That is the difference between a system that waits and a
    system that retries.
    """

    event: str
    at: str
    into: str
    returns: str
    note: str


#: The subgraphs a run can drift into, and what each one is for. Each is a separate
#: graph with its own nodes; the main graph only knows the event and the return.
SUBGRAPHS: Mapping[str, tuple[str, ...]] = {
    "APPROVAL": ("REQUEST", "PRESENT_DELTA", "TWO_PERSON_REVIEW", "ISSUE_GRANT", "DECLINE"),
    "RECONCILIATION": ("HOLD_SCOPE", "PROBE_WORLD", "RESOLVED", "PROPOSE_COMPENSATION"),
}

#: What happens inside each subgraph node, in one line.
SUBGRAPH_CAPABILITY: Mapping[str, str] = {
    "REQUEST": "carries the refusal reason and the exact proposal digest to a person",
    "PRESENT_DELTA": "shows what would change, not what the agent says would change",
    "TWO_PERSON_REVIEW": "Γ-17: the approver is not the proposer, checked here and again in Γ",
    "ISSUE_GRANT": "the only place a grant comes into being; bound to one digest and state",
    "DECLINE": "no grant; the main run resumes at REFUSE",
    "HOLD_SCOPE": "Γ-21: nothing else in this scope proceeds while the outcome is unknown",
    "PROBE_WORLD": "asks the world what happened; does not guess, does not retry the effect",
    "RESOLVED": "the outcome is now known and recorded; the scope reopens",
    "PROPOSE_COMPENSATION": "a compensating action is a NEW proposal and re-enters at INTAKE",
}

#: Event-driven handoffs. `returns` names where the MAIN graph continues afterwards.
DRIFTS: tuple[Drift, ...] = (
    Drift("needs_human", "VALIDATE", "APPROVAL", "VALIDATE",
          "UNCLEAR, or a consequential proposal with no grant: a person may resolve it, the caller may not"),
    Drift("outcome_unknown", "RECONCILE", "RECONCILIATION", "INTAKE",
          "Γ-21: the scope is held. What returns is a NEW proposal for a compensating action, "
          "never an automatic undo, because compensation is an effect and needs its own grant"),
)


@dataclass(frozen=True)
class Edge:
    """A transition, with the condition that takes it and why it exists."""

    source: str
    target: str
    condition: str
    note: str = ""


#: The complete topology. Adding an edge here is a governance act in the same sense
#: that adding an invariant is: it changes what the system can do.
EDGES: tuple[Edge, ...] = (
    Edge("INTAKE", "PARSE", "always"),
    Edge("PARSE", "REFUSE", "parse code != OK",
         "no repair loop: a malformed output is refused, never retried into shape"),
    Edge("PARSE", "ISOLATE", "one valid envelope"),
    Edge("ISOLATE", "CLASSIFY", "always"),
    Edge("CLASSIFY", "GATHER_AUTHORITY", "always"),
    Edge("GATHER_AUTHORITY", "ADVISE", "always"),
    Edge("ADVISE", "VALIDATE", "always",
         "advisories enter the context as data; Γ-18 gives them no word for permission"),
    Edge("VALIDATE", "REFUSE", "verdict INVALID"),
    Edge("VALIDATE", "HUMAN_GATE", "verdict UNCLEAR, or VALID without a grant for a consequential effect",
         "UNCLEAR is a refusal that a human may resolve, not a deferral to the caller"),
    Edge("VALIDATE", "ISSUE_TOKEN", "verdict VALID"),
    Edge("HUMAN_GATE", "REFUSE", "human declines, or the wait expires"),
    Edge("HUMAN_GATE", "VALIDATE", "human issues a grant",
         "the only loop that can improve a verdict, and it needs a human in it"),
    Edge("ISSUE_TOKEN", "REDEEM", "always"),
    Edge("REDEEM", "REFUSE", "the situation moved since the verdict",
         "post-approval substitution dies here"),
    Edge("REDEEM", "EXECUTE", "token still binds this exact situation"),
    Edge("EXECUTE", "RECONCILE", "always"),
    Edge("RECONCILE", "HOLD", "outcome unknown",
         "Γ-11: OUTCOME_UNKNOWN != NOT_EXECUTED — the scope is held, not retried"),
    Edge("RECONCILE", "AUDIT", "outcome known"),
    Edge("AUDIT", "DONE", "always"),
)

#: The node a run starts in.
ENTRY: str = "INTAKE"


def successors(node: str) -> tuple[Edge, ...]:
    return tuple(e for e in EDGES if e.source == node)


def topology() -> dict:
    return {
        "entry": ENTRY,
        "lanes": [{"name": n, "meaning": m} for n, m in LANES],
        "nodes": [{"name": n, "lane": LANE_OF[n], "capability": CAPABILITY[n], "terminal": n in TERMINAL}
                  for n in NODES],
        "edges": [{"from": e.source, "to": e.target, "when": e.condition, "note": e.note} for e in EDGES],
        "subgraphs": {name: [{"name": n, "capability": SUBGRAPH_CAPABILITY[n]} for n in nodes]
                      for name, nodes in SUBGRAPHS.items()},
        "drifts": [{"event": d.event, "at": d.at, "into": d.into, "returns": d.returns, "note": d.note}
                   for d in DRIFTS],
    }


# --------------------------------------------------------------------------
# Running the graph
# --------------------------------------------------------------------------

@dataclass
class RunState:
    """Everything carried between nodes. Deliberately small and explicit.

    A state object an agent can write freely into is a second authority surface; this
    one holds only what a node downstream is allowed to read.
    """

    parse_code: str = "OK"
    context: ValidationContext | None = None
    verdict_result: str | None = None
    token: object | None = None
    human_grants: bool = False
    outcome_known: bool = True
    situation_moved: bool = False
    path: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    executed: bool = False


def _choose(node: str, state: RunState) -> str | None:
    """Pick the outgoing edge. One place, so the routing is auditable in one read."""
    if node == "PARSE":
        if state.parse_code != "OK":
            state.reasons.append(f"parse refused: {state.parse_code}")
            return "REFUSE"
        return "ISOLATE"
    if node == "VALIDATE":
        assert state.context is not None, "VALIDATE reached without a context"
        verdict = validate(state.context)
        state.verdict_result = verdict.result
        if verdict.result == "INVALID":
            state.reasons.append(explain(verdict).splitlines()[1].strip() if verdict.failures else "INVALID")
            return "REFUSE"
        if verdict.result == "UNCLEAR":
            state.reasons.append("UNCLEAR: a human may resolve it; the caller may not")
            return "HUMAN_GATE"
        return "ISSUE_TOKEN"
    if node == "HUMAN_GATE":
        if not state.human_grants:
            state.reasons.append("human declined or did not answer")
            return "REFUSE"
        # A human grant is a fact the next validation reads, not a flag that skips it.
        # It is consumed on use, so the loop cannot spin: one visit, one grant, one
        # re-validation, and the second visit finds nothing left to give.
        import dataclasses

        state.human_grants = False
        state.context = dataclasses.replace(state.context, receipt_ref="audit/human-gate/0001")
        state.reasons.append("human issued a grant; re-validating against the new context")
        return "VALIDATE"
    if node == "ISSUE_TOKEN":
        state.token = issue_decision(state.context)
        return "REDEEM"
    if node == "REDEEM":
        ctx = state.context
        if state.situation_moved:
            ctx = _moved(ctx)
        if not redeem_decision(state.token, ctx):
            state.reasons.append("the situation moved between the verdict and the effect")
            return "REFUSE"
        return "EXECUTE"
    if node == "EXECUTE":
        state.executed = True
        return "RECONCILE"
    if node == "RECONCILE":
        if not state.outcome_known:
            state.reasons.append("outcome unknown: the scope is held, not retried")
            return "HOLD"
        return "AUDIT"
    edges = successors(node)
    return edges[0].target if edges else None


def _moved(ctx: ValidationContext) -> ValidationContext:
    """The world after someone rewrote one argument. Used to demonstrate REDEEM."""
    import dataclasses

    return dataclasses.replace(ctx, proposal=dataclasses.replace(ctx.proposal, target="attacker@example.invalid"))


def run(state: RunState, *, max_steps: int = 64) -> RunState:
    """Walk the graph from ENTRY until a terminal node.

    `max_steps` is a backstop, not the safety property: the topology has exactly one
    loop, it passes through a human, and the grant it produces is consumed on use.
    """
    node = ENTRY
    for _ in range(max_steps):
        state.path.append(node)
        if node in TERMINAL:
            return state
        nxt = _choose(node, state)
        if nxt is None:
            raise RuntimeError(f"no outgoing edge from {node}")
        if not any(e.source == node and e.target == nxt for e in EDGES):
            raise RuntimeError(f"transition {node} -> {nxt} is not in the topology")
        node = nxt
    raise RuntimeError("the graph did not terminate; a loop was added without a bound")


# --------------------------------------------------------------------------
# Diagram
# --------------------------------------------------------------------------

def mermaid() -> str:
    """The topology as a diagram, generated from the tables rather than drawn.

    Left to right along the trust lanes, because that is the axis that carries the
    meaning: a run moves from untrusted bytes to a recorded effect and never backwards.
    Each lane is a box, and each drift is a dashed handoff into a graph of its own.

    A hand-drawn diagram drifts from the code within a week; this one cannot.
    """
    lines = ["flowchart LR"]
    for lane, meaning in LANES:
        safe = meaning.replace(";", ",")
        lines.append(f'    subgraph {lane}["{lane} — {safe}"]')
        lines.append("        direction TB")
        for n in NODES:
            if LANE_OF[n] == lane:
                shape = f'{n}(["{n}"])' if n in TERMINAL else f'{n}["{n}"]'
                lines.append(f"        {shape}")
        lines.append("    end")
    for name, nodes in SUBGRAPHS.items():
        lines.append(f'    subgraph {name}["{name} — a graph of its own"]')
        lines.append("        direction TB")
        for n in nodes:
            lines.append(f'        {name}_{n}["{n}"]')
        lines.append("    end")
    for e in EDGES:
        label = e.condition.replace(chr(34), chr(39))
        lines.append(f'    {e.source} -->|"{label}"| {e.target}')
    for d in DRIFTS:
        lines.append(f'    {d.at} -.->|"{d.event}"| {d.into}_{SUBGRAPHS[d.into][0]}')
        lines.append(f'    {d.into}_{SUBGRAPHS[d.into][-1]} -.->|"returns"| {d.returns}')
    lines.append("    classDef terminal fill:#2b2b2b,stroke:#888,color:#eee;")
    lines.append(f"    class {','.join(sorted(TERMINAL))} terminal;")
    lines.append("    classDef effect fill:#7a2222,stroke:#d66,color:#fff;")
    lines.append(f"    class {EFFECTFUL} effect;")
    return chr(10).join(lines)


# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------

def _demo_context(**overrides) -> ValidationContext:
    from core.governance import DELETE_DIGEST, SCOPE_DIGEST, STATE_HASH, TICK, human_grant
    from logos_gamma import EffectProposal, ProvenanceClaim
    from core.governance import digest

    base = dict(
        proposal=EffectProposal(
            action="fs.delete", target="payroll.csv", effect_kind="filesystem-write",
            externality="internal", reversibility="irreversible", proposal_digest=DELETE_DIGEST,
            provenance=(ProvenanceClaim("run/42/export.log", "tool", digest("content", "log")),),
        ),
        tick=TICK, state_hash=STATE_HASH, scope_digest=SCOPE_DIGEST, authority=human_grant(),
    )
    base.update(overrides)
    return ValidationContext(**base)


def scenarios() -> Mapping[str, Callable[[], RunState]]:
    return {
        "granted": lambda: RunState(context=_demo_context()),
        "no grant": lambda: RunState(context=_demo_context(authority=None)),
        "malformed output": lambda: RunState(parse_code="MULTIPLE_ENVELOPES", context=_demo_context()),
        "human resolves it": lambda: RunState(
            context=_demo_context(receipts_required=True), human_grants=True),
        "human declines": lambda: RunState(context=_demo_context(receipts_required=True)),
        "situation moved": lambda: RunState(context=_demo_context(), situation_moved=True),
        "outcome unknown": lambda: RunState(context=_demo_context(), outcome_known=False),
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError, OSError):
        pass
    parser = argparse.ArgumentParser(description="LOGOS-1 as a graph.")
    parser.add_argument("--mermaid", action="store_true", help="print the diagram")
    parser.add_argument("--json", action="store_true", help="print the topology")
    args = parser.parse_args(argv)

    if args.mermaid:
        print(mermaid())
        return 0
    if args.json:
        print(json.dumps(topology(), indent=2))
        return 0

    print(f"LOGOS-1 graph: {len(NODES)} nodes, {len(EDGES)} edges, {len(TERMINAL)} terminal\n")
    for name, make in scenarios().items():
        state = run(make())
        arrow = " -> ".join(state.path)
        print(f"-- {name}")
        print(f"   {arrow}")
        for reason in state.reasons:
            print(f"   because: {reason}")
        print(f"   executed: {state.executed}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via main() in tests
    raise SystemExit(main())
