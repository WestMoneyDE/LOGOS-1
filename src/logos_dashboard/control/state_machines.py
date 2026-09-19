"""Pure state machines (spec §4). `transition(kind, state, event, actor)` returns the new state or raises `IllegalTransition`.

Founder gates (`FOUNDER_GATES`) can only be passed by actor `founder`; every other actor (agent, worker, system) is rejected before any lookup.
Vocabulary source: docs/research/dashboard/RESEARCH-OS-TARGET-ARCHITECTURE.md (thesis §6), spec §3 (work order, job, decision).
"""
from __future__ import annotations

THESIS_STATES = ("IDEA", "TRIAGE", "PRIOR_ART", "QUESTION_DEFINED", "HYPOTHESIS_DEFINED", "METRICS_DEFINED", "PREREG_DRAFT", "PREREG_FROZEN", "WORK_ORDER_READY",
                 "DRY_RUN", "READY_TO_RUN", "RUNNING", "ANALYSIS", "VERDICT", "REPLICATION", "PUBLICATION_CANDIDATE", "CLOSED",
                 "BLOCKED_BY_GOVERNANCE", "BLOCKED_BY_DEPENDENCY", "INVALID_MEASUREMENT", "FALSIFIED", "INCONCLUSIVE", "SUPERSEDED")
AGENT_CEILING = "PREREG_DRAFT"   # agents may advance a thesis autonomously up to here (ADR §3)

# (state, event) -> new state
THESIS_TRANSITIONS: dict[tuple[str, str], str] = {
    ("IDEA", "triage"): "TRIAGE",
    ("TRIAGE", "start_prior_art"): "PRIOR_ART",
    ("TRIAGE", "define_question"): "QUESTION_DEFINED",          # agent judged prior art unnecessary (>= 3 citations)
    ("PRIOR_ART", "define_question"): "QUESTION_DEFINED",
    ("QUESTION_DEFINED", "define_hypothesis"): "HYPOTHESIS_DEFINED",
    ("HYPOTHESIS_DEFINED", "define_metrics"): "METRICS_DEFINED",
    ("METRICS_DEFINED", "draft_prereg"): "PREREG_DRAFT",
    ("PREREG_DRAFT", "freeze_prereg"): "PREREG_FROZEN",         # founder gate
    ("PREREG_FROZEN", "approve_work_order"): "WORK_ORDER_READY",  # founder gate
    ("WORK_ORDER_READY", "dry_run"): "DRY_RUN",
    ("DRY_RUN", "ready_to_run"): "READY_TO_RUN",                # founder gate
    ("DRY_RUN", "dry_run_failed"): "BLOCKED_BY_GOVERNANCE",
    ("READY_TO_RUN", "start_run"): "RUNNING",
    ("RUNNING", "finish_run"): "ANALYSIS",
    ("RUNNING", "hard_stop"): "BLOCKED_BY_GOVERNANCE",
    ("ANALYSIS", "record_verdict"): "VERDICT",
    ("ANALYSIS", "invalid_measurement"): "INVALID_MEASUREMENT",
    ("ANALYSIS", "inconclusive"): "INCONCLUSIVE",
    ("VERDICT", "falsified"): "FALSIFIED",
    ("VERDICT", "request_replication"): "REPLICATION",
    ("REPLICATION", "publication_candidate"): "PUBLICATION_CANDIDATE",
    ("PUBLICATION_CANDIDATE", "close"): "CLOSED",
    ("FALSIFIED", "close"): "CLOSED",
    ("INVALID_MEASUREMENT", "repair_instrument"): "METRICS_DEFINED",
    ("INCONCLUSIVE", "redesign"): "HYPOTHESIS_DEFINED",
    ("BLOCKED_BY_GOVERNANCE", "unblock"): "WORK_ORDER_READY",   # founder gate
    ("BLOCKED_BY_DEPENDENCY", "unblock"): "WORK_ORDER_READY",   # founder gate
}
# superseding is allowed from any non-terminal state
for _s in THESIS_STATES:
    if _s not in ("CLOSED", "SUPERSEDED"):
        THESIS_TRANSITIONS[(_s, "supersede")] = "SUPERSEDED"

FOUNDER_GATES = frozenset({"freeze_prereg", "approve_work_order", "ready_to_run", "unblock", "approve", "raise_cap", "change_benchmark", "change_claim_status", "decide"})

WORK_ORDER_STATES = ("DRAFT", "APPROVED", "READY", "RUNNING", "BLOCKED", "FAILED", "VALIDATED", "FALSIFIED", "SUPERSEDED")
WORK_ORDER_TRANSITIONS: dict[tuple[str, str], str] = {
    ("DRAFT", "approve"): "APPROVED",            # founder gate
    ("APPROVED", "dependencies_met"): "READY",
    ("APPROVED", "block"): "BLOCKED",
    ("READY", "start"): "RUNNING",
    ("READY", "block"): "BLOCKED",
    ("BLOCKED", "unblock"): "READY",             # founder gate
    ("RUNNING", "validated"): "VALIDATED",
    ("RUNNING", "falsified"): "FALSIFIED",
    ("RUNNING", "fail"): "FAILED",
    ("FAILED", "retry"): "READY",
}
for _s in WORK_ORDER_STATES:
    if _s not in ("VALIDATED", "FALSIFIED", "SUPERSEDED"):
        WORK_ORDER_TRANSITIONS[(_s, "supersede")] = "SUPERSEDED"

JOB_STATES = ("queued", "waiting_quota", "waiting_dependency", "waiting_governance", "running", "paused", "failed", "done", "stopped")
JOB_TRANSITIONS: dict[tuple[str, str], str] = {
    ("queued", "dequeue"): "running", ("queued", "pause"): "paused", ("queued", "stop"): "stopped",
    ("waiting_quota", "quota_available"): "queued", ("waiting_dependency", "dependency_met"): "queued", ("waiting_governance", "governance_pass"): "queued",
    ("waiting_quota", "stop"): "stopped", ("waiting_dependency", "stop"): "stopped", ("waiting_governance", "stop"): "stopped",
    ("running", "complete"): "done", ("running", "fail"): "failed", ("running", "pause"): "paused", ("running", "stop"): "stopped",
    ("paused", "resume"): "queued", ("paused", "stop"): "stopped",
    ("failed", "retry"): "queued",
}

DECISION_STATES = ("WAITING", "APPROVED", "REJECTED", "DEFERRED", "SUPERSEDED")
DECISION_TRANSITIONS: dict[tuple[str, str], str] = {
    ("WAITING", "approve"): "APPROVED", ("WAITING", "reject"): "REJECTED", ("WAITING", "defer"): "DEFERRED", ("WAITING", "supersede"): "SUPERSEDED",
    ("DEFERRED", "approve"): "APPROVED", ("DEFERRED", "reject"): "REJECTED", ("DEFERRED", "supersede"): "SUPERSEDED",
}

TABLES = {"thesis": THESIS_TRANSITIONS, "work_order": WORK_ORDER_TRANSITIONS, "job": JOB_TRANSITIONS, "decision": DECISION_TRANSITIONS}
DECISION_FOUNDER_EVENTS = frozenset({"approve", "reject", "defer"})


class IllegalTransition(Exception):
    def __init__(self, kind: str, state: str, event: str, actor: str, reason: str):
        super().__init__(f"{kind}: {state} --{event}--> ? by {actor}: {reason}")
        self.kind, self.state, self.event, self.actor, self.reason = kind, state, event, actor, reason


def transition(kind: str, state: str, event: str, actor: str) -> str:
    table = TABLES.get(kind)
    if table is None:
        raise IllegalTransition(kind, state, event, actor, "unknown state machine")
    gated = event in FOUNDER_GATES or (kind == "decision" and event in DECISION_FOUNDER_EVENTS)
    if gated and actor != "founder":
        raise IllegalTransition(kind, state, event, actor, "founder gate")
    nxt = table.get((state, event))
    if nxt is None:
        raise IllegalTransition(kind, state, event, actor, "no such transition")
    return nxt


def events_from(kind: str, state: str) -> list[dict]:
    """Events available from `state` with their target and whether a founder gate applies (UI buttons)."""
    out = []
    for (s, e), t in TABLES[kind].items():
        if s == state:
            out.append({"event": e, "to": t, "founder_gate": e in FOUNDER_GATES or (kind == "decision" and e in DECISION_FOUNDER_EVENTS)})
    return sorted(out, key=lambda x: x["event"])
