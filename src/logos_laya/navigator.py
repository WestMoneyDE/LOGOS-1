"""The navigator (spec §5, Component 4): Laya proposes the next thesis step; it never takes it.

The navigator runs on the existing state machine (`logos_dashboard.control.state_machines`);
it introduces no state machine of its own. Each step is compiled into ONE Laya `choice`
question whose options are the events an agent may legally fire from the current state, plus
`stay`:

```text
the options   events_from(kind, state) minus founder gates, minus supersede, plus "stay"
the walls     a founder gate next             -> STOP_AT_GATE    (stops in front of it)
              at/beyond AGENT_CEILING          -> STOP_AT_CEILING (nothing is offered)
standing      out-of-set answer, abstention, timeout, anything unexpected -> STAND_STILL
```

Rules that hold here and are tested:

* A founder-gated event, `supersede`, or any step to a state beyond `AGENT_CEILING` is never
  an option, so no answer can make the navigator propose it: an answer naming it lies outside
  the offered set and becomes `STAND_STILL`.
* `answer.confidence` is never read. Laya's confidence is 1 - normalised entropy, not a
  probability; the move records `p_top` and `margin` from `probabilities` only.
* `navigate` never raises.
* The move is a proposal. Nothing in this module calls `transition()` or `advance()`; in
  shadow mode (`service._shadow_navigate`) the move is only written to `ros_audit`.

Question shape: page text passed as a plain string scored 9/45 on element choice in this
session's measurement; the same content in named state fields referenced in backticks scored
40-45/45. So the question references `thesis_state` and `step_output` by name.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping

from logos_dashboard.control.state_machines import (
    AGENT_CEILING, DECISION_FOUNDER_EVENTS, FOUNDER_GATES, TABLES, THESIS_STATES, events_from,
)

from .classify import ClassifyAnswer

ROUTE = "typed-decisions"
STAY = "stay"
STEP_OUTPUT_CHARS = 1500
MOVE_KINDS = ("EVENT", "STAY", "STOP_AT_GATE", "STOP_AT_CEILING", "STAND_STILL")
_NEVER_OFFERED = frozenset({"supersede"})

#: Plain description of each target state: what must be true for a thesis to be there.
TARGET_TEXT: Mapping[str, str] = {
    "TRIAGE": "the idea has been read and is worth sorting: it names a claim that could be tested",
    "PRIOR_ART": "the claim needs a prior-art search before a question can be fixed",
    "QUESTION_DEFINED": "a single research question is stated precisely, and prior art is covered or judged unnecessary with at least three citations",
    "HYPOTHESIS_DEFINED": "a falsifiable hypothesis is stated, with the result that would refute it",
    "METRICS_DEFINED": "the metrics that decide the hypothesis are named, with how each is measured",
    "PREREG_DRAFT": "a preregistration draft exists: hypothesis, metrics, analysis plan and stopping rule written down before any run",
}
#: The exit criterion of each state an agent may leave.
EXIT_TEXT: Mapping[str, str] = {
    "IDEA": "the idea has been read and states a testable claim",
    "TRIAGE": "it is decided whether prior art must be searched",
    "PRIOR_ART": "the prior-art search is done and a question can be stated",
    "QUESTION_DEFINED": "a falsifiable hypothesis answering the question is written",
    "HYPOTHESIS_DEFINED": "the deciding metrics are named and measurable",
    "METRICS_DEFINED": "a complete preregistration draft is written",
}
STAY_TEXT = "the output does not yet meet the exit criterion of the current state"


@dataclass(frozen=True)
class NavigatorMove:
    kind: str
    event: str | None
    reason: str
    p_top: float | None = None
    margin: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in MOVE_KINDS:
            raise ValueError(f"unknown move kind {self.kind!r}")


def _gated(kind: str, event: str) -> bool:
    return event in FOUNDER_GATES or (kind == "decision" and event in DECISION_FOUNDER_EVENTS)


def _beyond_ceiling(state: str) -> bool:
    """At or beyond the wall. An unknown state counts as beyond: it is never navigated."""
    if state not in THESIS_STATES:
        return True
    return THESIS_STATES.index(state) >= THESIS_STATES.index(AGENT_CEILING)


def offered_events(kind: str, state: str) -> tuple[str, ...]:
    """The events the navigator may propose from `state`. Sorted, deterministic.

    For a thesis: nothing at all at or beyond `AGENT_CEILING`, and never an event whose
    target lies beyond it (the same wall `service.advance` enforces for agents).
    """
    if kind not in TABLES:
        return ()
    if kind == "thesis" and _beyond_ceiling(state):
        return ()
    out = []
    for e in events_from(kind, state):
        if e["founder_gate"] or _gated(kind, e["event"]) or e["event"] in _NEVER_OFFERED:
            continue
        if kind == "thesis" and (e["to"] not in THESIS_STATES
                                 or THESIS_STATES.index(e["to"]) > THESIS_STATES.index(AGENT_CEILING)):
            continue
        out.append(e["event"])
    return tuple(sorted(out))


def question_id_for(kind: str, state: str) -> str:
    return f"{kind}_nav_{state}".lower()[:64]


def compile_step(kind: str, state: str, step_output: str) -> tuple[dict, dict] | None:
    """One Laya `choice` question for this step, or None at a wall.

    The question text depends only on `(kind, state)`, so `question_sha256` is stable per
    state; the step output travels in the named state field `step_output`.
    """
    offered = offered_events(kind, state)
    if not offered:
        return None
    to = {e["event"]: e["to"] for e in events_from(kind, state)}
    criteria = {ev: TARGET_TEXT.get(to[ev], f"the thesis is ready to move to {to[ev]}") for ev in offered}
    criteria[STAY] = STAY_TEXT
    exit_text = EXIT_TEXT.get(state, f"the work of {state} is complete")
    instructions = (f"A research thesis is in the state named in `thesis_state`; `step_output` is the result "
                    f"of the last step. The exit criterion of this state is: {exit_text}. "
                    f"Given `thesis_state` and `step_output`, which next step is justified? "
                    f"Choose `{STAY}` unless `step_output` meets the exit criterion.")
    question = {"type": "choice", "instructions": instructions, "criteria": criteria}
    text = step_output if isinstance(step_output, str) else ""
    state_fields = {"thesis_state": state, "step_output": text[:STEP_OUTPUT_CHARS]}
    return state_fields, question


def _top_and_margin(probabilities: Mapping[str, float]) -> tuple[float | None, float | None]:
    ps = sorted((float(p) for p in probabilities.values()), reverse=True)
    if not ps:
        return None, None
    return ps[0], ps[0] - (ps[1] if len(ps) > 1 else 0.0)


def interpret(answer: ClassifyAnswer, offered) -> NavigatorMove:
    """Map one answer to a move. Reads `ok`, `abstain_reason`, `choice`, `probabilities` — never `confidence`."""
    if not getattr(answer, "ok", False):
        return NavigatorMove("STAND_STILL", None, getattr(answer, "abstain_reason", None) or "NOT_OK")
    p_top, margin = _top_and_margin(answer.probabilities or {})
    choice = answer.choice
    if choice == STAY:
        return NavigatorMove("STAY", None, "laya chose stay", p_top, margin)
    if not isinstance(choice, str) or choice not in tuple(offered):
        return NavigatorMove("STAND_STILL", None, f"OUT_OF_SET: {choice!r}"[:200], p_top, margin)
    return NavigatorMove("EVENT", choice, "laya chose an offered event", p_top, margin)


def navigate_with_answer(client, kind: str, state: str, step_output: str) -> tuple[NavigatorMove, ClassifyAnswer | None]:
    """`navigate`, plus the raw answer (for pins and logging). Never raises."""
    try:
        offered = offered_events(kind, state)
        if not offered:
            remaining = [e for e in events_from(kind, state) if e["event"] not in _NEVER_OFFERED] if kind in TABLES else []
            if kind == "thesis" and state in THESIS_STATES and THESIS_STATES.index(state) > THESIS_STATES.index(AGENT_CEILING):
                return NavigatorMove("STOP_AT_CEILING", None, f"{state} is beyond {AGENT_CEILING}"), None
            if remaining and all(e["founder_gate"] or _gated(kind, e["event"]) for e in remaining):
                return NavigatorMove("STOP_AT_GATE", None, "next: " + ",".join(e["event"] for e in remaining)), None
            return NavigatorMove("STOP_AT_CEILING", None, f"nothing an agent may do from {state}"), None
        compiled = compile_step(kind, state, step_output)
        if compiled is None:  # unreachable while offered is non-empty; kept as a wall, not an assumption
            return NavigatorMove("STAND_STILL", None, "NOT_COMPILED"), None
        state_fields, question = compiled
        answer = client.ask(question_id_for(kind, state), state_fields, question, route=ROUTE)
        return interpret(answer, offered), answer
    except Exception as exc:  # noqa: BLE001 — the navigator never raises into its caller
        return NavigatorMove("STAND_STILL", None, f"NAVIGATOR_ERROR: {type(exc).__name__}"), None


def navigate(client, kind: str, state: str, step_output: str) -> NavigatorMove:
    return navigate_with_answer(client, kind, state, step_output)[0]


def shadow_detail(client, kind: str, from_state: str, actual_event: str, step_output: str, actual_actor: str) -> dict[str, Any]:
    """The `ros_audit` detail of one shadow observation. Never raises."""
    t0 = time.monotonic()
    move, answer = navigate_with_answer(client, kind, from_state, step_output)
    latency_ms = int((time.monotonic() - t0) * 1000)
    return {
        "from": from_state, "actual_event": actual_event, "actual_actor": actual_actor,
        "offered": list(offered_events(kind, from_state)),
        "laya_move": move.kind, "laya_event": move.event, "laya_reason": move.reason,
        "agreed": move.kind == "EVENT" and move.event == actual_event,
        "p_top": move.p_top, "margin": move.margin,
        "abstain_reason": answer.abstain_reason if answer is not None else None,
        "pins": dict(answer.pins) if answer is not None else {},
        "latency_ms": latency_ms,
    }
