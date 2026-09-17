"""VALUE-OF-INFORMATION-GATE-R1 — a system may know more without being allowed to do more.

    InformationValue != Authority          ReducedUncertainty != Permission
    KnowledgeGain != Grant                 ConfidenceIncrease != Authorization
    UsefulToKnow != AllowedToAccess        Authorized != AutomaticallyExecuted
    DesiredInformationAction != AuthorizedInformationAction

Two branches that meet only at the execution-policy layer:

    Epistemic State -> Information Value -> Information Strategy        (this module, EXPERIMENTAL_FIXTURE)
    Authority Evidence -> Γ -> Authority Decision                        (the validated memory->Γ bridge, untouched)

Nothing in the epistemic branch reads or writes a grant, a principal, a
scope, a freshness tick, an authority origin, an approval flag or a canonical
effect. The authority branch never reads an epistemic field. The tests spy on
both boundaries.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

from logos_memory.records import MemoryRecord
from logos_research.experiments import effect_oracle as eo
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import prediction_trust as pt
from logos_research.experiments.binding_state import ProposedAction

Level = Literal["UNCERTAIN", "PARTIALLY_RESOLVED", "RESOLVED", "UNKNOWN"]
Strategy = Literal["NO_QUERY", "QUERY", "SIMULATE", "REQUEST_HUMAN", "DEFER"]
Execution = Literal["EXECUTE", "EXECUTE_AFTER_REVIEW", "HOLD", "BLOCK"]

RESOLVED_AT = 0.05
PARTIAL_AT = 0.5


# --------------------------------------------------------------------------
# Epistemic state — EXPERIMENTAL_FIXTURE; no authority fields by construction
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class EpistemicState:
    question_id: str
    uncertainty: object                      # float in [0, 1]; 0 = certain
    known_facts: tuple[str, ...] = ()
    missing_facts: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    state_version: int = 1
    provenance: str = "observation"         # a label; never authority
    stale: bool = False
    contradictory: bool = False


def _unit(v: object) -> bool:
    return type(v) is float and math.isfinite(v) and 0.0 <= v <= 1.0


def interpret(state: object) -> Level:
    """Malformed -> UNKNOWN. Never a privileged default."""
    if not isinstance(state, EpistemicState) or not _unit(state.uncertainty) \
            or type(state.stale) is not bool or type(state.contradictory) is not bool:
        return "UNKNOWN"
    if state.contradictory:
        return "UNCERTAIN"
    if state.uncertainty <= RESOLVED_AT:
        return "RESOLVED"
    if state.uncertainty <= PARTIAL_AT:
        return "PARTIALLY_RESOLVED"
    return "UNCERTAIN"


# --------------------------------------------------------------------------
# Information options and value
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class InformationOption:
    option_id: str
    action: str
    target: str
    expected_uncertainty_reduction: float
    acquisition_cost: float
    latency_cost: float = 0.0
    risk_classification_reference: str = ""          # reference only; VOI never resolves it
    required_authority_reference: str | None = None  # reference only; VOI never resolves it


@dataclass(frozen=True)
class InformationValue:
    option_id: str
    expected_value: float
    expected_uncertainty_reduction: float
    cost: float
    reason: str


def information_value(state: EpistemicState, option: InformationOption) -> InformationValue:
    """Frozen VOI = min(expected_reduction, uncertainty) - acquisition_cost - 0.25 * latency_cost.

    Inputs: the epistemic state and the option's costs. Nothing else."""
    u = state.uncertainty if _unit(state.uncertainty) else 1.0
    gain = min(option.expected_uncertainty_reduction, u)
    cost = option.acquisition_cost + 0.25 * option.latency_cost
    return InformationValue(option.option_id, gain - cost, gain, cost,
                            f"gain={gain:.3f} cost={cost:.3f}")


# --------------------------------------------------------------------------
# Information strategy — a DESIRE. It authorizes nothing.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class InformationDecision:
    strategy: Strategy
    option_id: str | None
    value: float | None
    level: Level


def select_information_strategy(state: object, options: Sequence[InformationOption]) -> InformationDecision:
    level = interpret(state)
    if level == "UNKNOWN":
        return InformationDecision("DEFER", None, None, level)
    if level == "RESOLVED":
        return InformationDecision("NO_QUERY", None, None, level)
    values = [information_value(state, o) for o in options]
    if not values:
        return InformationDecision("REQUEST_HUMAN" if state.contradictory else "NO_QUERY", None, None, level)
    best = max(values, key=lambda v: (v.expected_value, v.option_id))
    if best.expected_value <= 0.0:
        return InformationDecision("REQUEST_HUMAN" if state.contradictory else "NO_QUERY", best.option_id, best.expected_value, level)
    option = next(o for o in options if o.option_id == best.option_id)
    return InformationDecision("SIMULATE" if option.action == "SIMULATE" else "QUERY", best.option_id, best.expected_value, level)


# --------------------------------------------------------------------------
# Canonical effect for this experiment: the validated oracle, extended for the
# information actions. The validated CANONICAL_EFFECTS table is not modified.
# --------------------------------------------------------------------------

INFO_EFFECTS: dict[tuple[str, str], eo.EffectClass] = {
    ("QUERY_RECORD", "customer-secret"): eo.EffectClass("internal", "reversible", True),    # protected: approval-sensitive
    ("QUERY_RECORD", "public-ledger"): eo.EffectClass("internal", "reversible", False),
    ("SIMULATE", "silo-4"): eo.EffectClass("internal", "reversible", False),
}


def voi_effect(action: str, target: str) -> eo.EffectClass | None:
    e = eo.canonical_effect(action, target)
    return e if e is not None else INFO_EFFECTS.get((action, target))


# --------------------------------------------------------------------------
# Authority — the validated bridge, untouched; then the execution policy
# --------------------------------------------------------------------------

def canonical_contract(action: ProposedAction):
    """The Γ-owned scope for an action known to the effect oracle (None otherwise)."""
    e = voi_effect(action.action, action.target)
    if e is None:
        return None
    return ma._base_contract(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",),
                             approval_required=e.approval_required, externality=e.externality, reversibility=e.reversibility)


def records_for(records: Sequence[MemoryRecord], action: ProposedAction) -> list[MemoryRecord]:
    """Notes whose claimed scope covers this action's target (or carry no scope).
    A note written for TRANSFER silo-4 says nothing about QUERY_RECORD public-ledger."""
    out = []
    for r in records:
        c = ma.read_evidence([r]).contract
        if c is None or action.target in c.targets:
            out.append(r)
    return out


def authority_of(records: Sequence[MemoryRecord], action: ProposedAction, ledger: ma.GrantLedger,
                 *, tick: int, state_hash: str, fallback=None) -> tuple[ma.Outcome, dict[str, str]]:
    """Canonical authority. No epistemic argument exists on this signature."""
    return ma.evaluate_with_memory(list(records), action, ledger, tick=tick, state_hash=state_hash,
                                   fallback_contract=fallback, effect_oracle=voi_effect)


@dataclass(frozen=True)
class Outcome:
    authority: ma.Outcome
    level: Level
    information: InformationDecision
    execution: Execution
    information_execution: Execution | None      # for the desired information action, if any
    trace: dict[str, str]

    @property
    def authority_level(self) -> int:
        return ma.level(self.authority)


def execution_policy(authority: ma.Outcome, level: Level, trust: pt.TrustRoute) -> Execution:
    """The only place the two branches meet. Authority is a precondition; epistemic
    state and trust decide HOW an authorized action is carried out."""
    if authority != "ALLOW":
        return "BLOCK"
    if level == "RESOLVED" and trust == "AUTO":
        return "EXECUTE"
    if level in ("RESOLVED", "PARTIALLY_RESOLVED") and trust in ("AUTO", "REVIEW"):
        return "EXECUTE_AFTER_REVIEW"
    return "HOLD"


def decide(records: Sequence[MemoryRecord], target: ProposedAction, ledger: ma.GrantLedger, state: object,
           options: Sequence[InformationOption] = (), *, tick: int, state_hash: str, trust: pt.TrustRoute = "AUTO",
           fallback=None, principal: str = "operator-A") -> Outcome:
    info = select_information_strategy(state, options)
    auth, trace = authority_of(records, target, ledger, tick=tick, state_hash=state_hash, fallback=fallback)
    trace = dict(trace); trace.update({"level": info.level, "strategy": info.strategy, "voi": "" if info.value is None else f"{info.value:.3f}", "trust": trust})
    info_exec: Execution | None = None
    if info.strategy in ("QUERY", "SIMULATE") and info.option_id is not None:
        opt = next(o for o in options if o.option_id == info.option_id)
        info_action = ProposedAction(opt.action, opt.target, role=principal)
        ia, itr = authority_of(records_for(records, info_action), info_action, ledger, tick=tick, state_hash=state_hash,
                               fallback=canonical_contract(info_action))
        trace["info_authority"] = ia; trace["info_effect"] = itr.get("effect", "none")
        info_exec = "EXECUTE" if ia == "ALLOW" else "BLOCK"          # DesiredInformationAction != AuthorizedInformationAction
    return Outcome(auth, info.level, info, execution_policy(auth, info.level, trust), info_exec, trace)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def epistemic_fixture() -> dict[str, EpistemicState]:
    return {
        "E0": EpistemicState("q", 1.0, missing_facts=("balance", "owner")),
        "E1": EpistemicState("q", 0.8, known_facts=("owner",), missing_facts=("balance",), observation_ids=("o1",)),
        "E2": EpistemicState("q", 0.5, known_facts=("owner",), missing_facts=("balance",), observation_ids=("o1", "o2")),
        "E3": EpistemicState("q", 0.2, known_facts=("owner", "balance"), observation_ids=("o1", "o2", "o3")),
        "E4": EpistemicState("q", 0.0, known_facts=("owner", "balance", "limit"), observation_ids=("o1", "o2", "o3", "o4")),
        "E5": EpistemicState("q", 0.6, known_facts=("owner",), observation_ids=("o1", "o5"), contradictory=True),
        "E6": EpistemicState("q", 0.1, known_facts=("owner", "balance"), observation_ids=("o0",), stale=True),
        "E7": EpistemicState("q", 0.0, known_facts=("owner", "balance", "limit", "approval"), provenance="memory-prose",
                             observation_ids=("m1",)),
    }


def option_fixture() -> dict[str, InformationOption]:
    return {
        "cheap-public": InformationOption("cheap-public", "QUERY_RECORD", "public-ledger", 0.3, 0.05, 0.0, "low", None),
        "rich-secret": InformationOption("rich-secret", "QUERY_RECORD", "customer-secret", 0.9, 0.1, 0.1, "protected", "approval"),
        "simulate": InformationOption("simulate", "SIMULATE", "silo-4", 0.5, 0.2, 0.3, "low", None),
        "expensive": InformationOption("expensive", "QUERY_RECORD", "public-ledger", 0.95, 0.9, 0.9, "low", None),
        "useless": InformationOption("useless", "QUERY_RECORD", "public-ledger", 0.0, 0.1, 0.0, "low", None),
    }


def certainty_note(ref, contract, **claims) -> str:
    """What a memory writer may say about certainty and value. Evidence, nothing more."""
    return ma.authority_note(ref, contract, confidence=0.99, all_facts_known=True, decisive=True,
                             risk="low", no_approval_needed=True, **claims)
