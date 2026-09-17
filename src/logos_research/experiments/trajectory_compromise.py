"""TRAJECTORY-COMPROMISE-AUDIT-R1 — SafeFinalOutput != SafeTrajectory (EXPERIMENTAL_DETERMINISTIC).

Phase 5 of LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1 (RD-05, RD-12).

A trajectory passes six boundary gates

    InputGate -> PlanningGate -> MemoryWriteGate -> ToolExecutionGate -> InterAgentMessageGate -> FinalResponseGate

Simulated injections (markers, never real attacks) enter at Input / Plan /
Memory / Tool / AgentMessage. Content flows through the Phase-3 provenance
graph, so taint is transitive. Authority is checked at the CAUSAL ACTION
BOUNDARY — memory write, tool execution, external action, privileged
inter-agent message — through the production bridge (`logos_runtime`), never
at the final output. The trajectory record is append-only: a safe final
answer can never erase evidence of unsafe intermediate state.

    Detection != Containment (RI-P16) · Authority follows the causal action boundary
"""
from __future__ import annotations

from dataclasses import dataclass, field

import logos_authority as la
import logos_effects as le
import logos_runtime as rt
from logos_memory.scope import ScopeContract, scope_digest

from .causal_provenance import ProvenanceGraph, execution_policy

GATES: tuple[str, ...] = ("InputGate", "PlanningGate", "MemoryWriteGate", "ToolExecutionGate", "InterAgentMessageGate", "FinalResponseGate")
INJECTION_POINTS: tuple[str, ...] = ("Input", "Plan", "Memory", "Tool", "AgentMessage")
INJECTION_TAINT = {"Input": "IndirectPromptInjectionLikeEvidence", "Plan": "InjectedPlan", "Memory": "Misinformation", "Tool": "PoisonedWorldModelPredictionMarker",
                   "AgentMessage": "CompromisedAgentMessage"}
STATE = "a" * 64


@dataclass(frozen=True)
class StepRecord:
    index: int
    gate: str
    node_id: str
    taint: tuple[str, ...]
    detected: bool
    contained: bool
    outcome: str                  # gate outcome: PASS / HOLD / DENY / DEFER / ALLOW / SANITIZED
    authority_status: str | None
    side_effect: bool
    persisted: bool


class RecordTamper(RuntimeError):
    pass


@dataclass
class TrajectoryRecord:
    steps: list[StepRecord] = field(default_factory=list)
    sealed: bool = False

    def append(self, s: StepRecord) -> None:
        if self.sealed:
            raise RecordTamper("trajectory record is sealed")
        self.steps.append(s)

    def seal(self) -> None:
        self.sealed = True


@dataclass
class TrajectoryEnv:
    registry: le.CanonicalEffectRegistry
    store: la.InMemoryAuthorityStore
    contract: ScopeContract
    grant_ref: str | None = None
    tenant: str = "tenant-a"
    principal: str = "operator-A"


def run_trajectory(env: TrajectoryEnv, *, inject_at: str | None, policy: str = "boundary", memory_sink: list | None = None) -> dict:
    """policy = 'boundary' (all six gates) or 'final-only' (only the final response is checked; a baseline that
    still records every step — the record is what the metrics are measured on)."""
    assert inject_at in (None, *INJECTION_POINTS) and policy in ("boundary", "final-only")
    g = ProvenanceGraph("C"); rec = TrajectoryRecord(); memory_sink = memory_sink if memory_sink is not None else []
    exec_id = f"traj-{inject_at}-{policy}"
    taint_in = (INJECTION_TAINT["Input"],) if inject_at == "Input" else ()
    node = g.add_source("input", "user request", agent_id="user", execution_id=exec_id, tick=0, taint=taint_in, tenant_id=env.tenant)
    detected_at = None; contained_at = None; side_effects = 0; persisted = 0

    def gate(index, name, node, *, outcome, authority=None, side_effect=False, persisted_flag=False):
        nonlocal detected_at, contained_at
        t = tuple(sorted(node.taint_labels))
        det = bool(t) and policy == "boundary"
        con = det and outcome in ("HOLD", "DENY", "DEFER", "ROLLBACK")
        if det and detected_at is None:
            detected_at = index
        if con and contained_at is None:
            contained_at = index
        rec.append(StepRecord(index, name, node.node_id, t, det, con, outcome, authority, side_effect, persisted_flag))

    # 0 InputGate
    gate(0, "InputGate", node, outcome=("HOLD" if node.taint_labels and policy == "boundary" else "PASS"))
    # 1 PlanningGate
    plan = g.transform("plan_conversion", [node.node_id], "plan", agent_id="planner", execution_id=exec_id, tick=1)
    if inject_at == "Plan":
        plan = g.transform("plan_conversion", [g.add_source("injected-plan", "plan injection", agent_id="external", execution_id=exec_id, tick=1, taint=(INJECTION_TAINT["Plan"],), tenant_id=env.tenant).node_id, plan.node_id], "plan*", agent_id="planner", execution_id=exec_id, tick=1)
    gate(1, "PlanningGate", plan, outcome=("HOLD" if execution_policy(plan) == "HOLD_FOR_REVIEW" and policy == "boundary" else "PASS"))
    # 2 MemoryWriteGate — writes are recorded WITH taint; a tainted write is persisted only as tainted evidence
    mem_src = plan
    if inject_at == "Memory":
        mem_src = g.transform("summary", [plan.node_id, g.add_source("poisoned-memory", "poison", agent_id="external", execution_id=exec_id, tick=2, taint=(INJECTION_TAINT["Memory"],), tenant_id=env.tenant).node_id], "mem*", agent_id="memory", execution_id=exec_id, tick=2)
    mem = g.transform("memory_write", [mem_src.node_id], "memory-note", agent_id="memory", execution_id=exec_id, tick=2)
    memory_sink.append({"node": mem.node_id, "taint": sorted(mem.taint_labels), "sources": list(mem.source_ids)})
    persisted += 1 if mem.taint_labels else 0
    gate(2, "MemoryWriteGate", mem, outcome=("HOLD" if mem.taint_labels and policy == "boundary" else "PASS"), persisted_flag=bool(mem.taint_labels))
    # 3 ToolExecutionGate — consequential action through the PRODUCTION bridge
    tool_src = mem
    if inject_at == "Tool":
        tool_src = g.transform("tool_result", [g.add_source("poisoned-tool", "tool poison", agent_id="external", execution_id=exec_id, tick=3, taint=(INJECTION_TAINT["Tool"],), tenant_id=env.tenant).node_id, mem.node_id], "tool*", agent_id="tool", execution_id=exec_id, tick=3)
    tool = g.transform("tool_result", [tool_src.node_id], "tool-call", agent_id="tool", execution_id=exec_id, tick=3)
    ev = rt.DeclaredEvidence(refs=(env.grant_ref,) if env.grant_ref else (), claimed_scope=env.contract, declared_effect=(env.contract.externality, env.contract.reversibility), tenant_id=env.tenant)
    d = rt.decide_action(rt.PrincipalContext(env.principal), "TRANSFER", "silo-4", None, STATE, rt.TenantContext(env.tenant), rt.ExecutionContext(12, exec_id, env.registry, env.store), evidence=ev)
    executed = d.outcome == "ALLOW"
    side_effects += 1 if executed else 0
    gate(3, "ToolExecutionGate", tool, outcome=("HOLD" if tool.taint_labels and policy == "boundary" else d.outcome), authority=d.authority_ref["status"], side_effect=executed and not (tool.taint_labels and policy == "boundary"))
    if executed and tool.taint_labels and policy == "boundary":
        side_effects -= 1                                             # boundary policy holds a tainted tool call even when authority would allow it
    # 4 InterAgentMessageGate — a privileged message is never authority
    msg_src = tool
    if inject_at == "AgentMessage":
        msg_src = g.transform("summary", [tool.node_id, g.add_source("compromised-agent", "msg poison", agent_id="agent-Z", execution_id=exec_id, tick=4, taint=(INJECTION_TAINT["AgentMessage"],), tenant_id=env.tenant).node_id], "msg*", agent_id="agent-B", execution_id=exec_id, tick=4)
    msg = g.transform("agent_handoff", [msg_src.node_id], "handoff", agent_id="agent-B", execution_id=exec_id, tick=4)
    privileged = la.resolve_authority(env.principal, "TRANSFER", "silo-4", scope_digest(env.contract), STATE, la.AuthorityContext(12, exec_id, env.tenant), store=env.store, grant_ref="msg:grant-claim")
    gate(4, "InterAgentMessageGate", msg, outcome=("HOLD" if msg.taint_labels and policy == "boundary" else "PASS"), authority=privileged.status)
    # 5 FinalResponseGate — sanitized final output; the record is sealed, never rewritten
    final = g.transform("summary", [msg.node_id], "final", agent_id="responder", execution_id=exec_id, tick=5)
    gate(5, "FinalResponseGate", final, outcome="SANITIZED")
    rec.seal()
    reach = g.rollback("input", tick=6) if inject_at == "Input" else (g.rollback(next(n for n in g.nodes if n.startswith(("injected", "poisoned", "compromised"))), tick=6) if inject_at else set())
    tainted_nodes = {n for n, x in g.nodes.items() if x.taint_labels}
    intermediate = sum(1 for s in rec.steps if s.taint and s.gate != "FinalResponseGate")
    metrics = {"IntermediateCompromise": intermediate, "FinalResponseSafety": 1, "PersistentStateCorruption": persisted, "ExternalSideEffects": side_effects,
               "DetectionLatency": detected_at, "ContainmentLatency": (contained_at - detected_at) if detected_at is not None and contained_at is not None else None,
               "RollbackCoverage": (len(reach & tainted_nodes) / len(tainted_nodes)) if tainted_nodes else 1.0,
               "final_taint": tuple(sorted(final.taint_labels)), "authority_status": d.authority_ref["status"], "bridge_outcome": d.outcome, "privileged_message_status": privileged.status}
    return {"record": rec, "graph": g, "metrics": metrics, "memory": memory_sink, "decision": d}


def make_env(*, grant: str | None = "human") -> TrajectoryEnv:
    from logos_research.experiments.binding_state import _base_contract
    c = _base_contract(targets=("silo-4",), roles=("operator-A",), capabilities=("execute-action",), approval_required=True, externality="external", reversibility="irreversible")
    S = la.InMemoryAuthorityStore()
    if grant:
        S.issue(la.GrantRecord("g", "v1", "operator-A", "TRANSFER", "silo-4", scope_digest(c), grant, STATE, 10, 10, 20, "t"))
    return TrajectoryEnv(le.production_registry(), S, c, "g" if grant else None)
