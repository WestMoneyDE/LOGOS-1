"""RISK-AWARENESS-DECOMPOSITION-R1 — can "low risk" become "authorized"?

    RiskDetection != SafeStrategySelection != SafeExecution != Authority

The pipeline is decomposed into stages that are measured separately:

    1 Risk Detection      RiskOracle (objective, Γ-owned effect profile per action)
    2 Risk Interpretation interpret(reported) -> level or UNKNOWN (fail-safe)
    3 Strategy Selection  select_strategy(objective, interpreted, trust)
    4 Safety / Review     the strategy IS the safety gate outcome
    5 Authority           REAL scope engine + REAL Γ on the Γ-OWNED profile; reported
                          risk reaches Γ only as declared_* (untrusted, G4-CLAIM)
    6 Execution           DENIED / DEFERRED if authority != ALLOW, else the strategy

Everything here is EXPERIMENTAL_FIXTURE except the scope engine and Γ. The
MAP-R1 B2 bridge is kept reachable on purpose (`b2_bridge`) so the
preregistered B2-CLASSIFICATION probe can ask whether a *memory-claimed*
scope's externality / reversibility is being used as Γ-owned classification.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal, Sequence

import logos_gamma as gamma
from logos_memory.records import MemoryRecord
from logos_memory.scope import ScopeContract, ScopeDecision, ScopeRequest, scope_digest
from logos_research.experiments import memory_authority as ma
from logos_research.experiments import prediction_trust as pt
from logos_research.experiments.binding_state import ProposedAction

Level = Literal["ZERO", "MINIMAL", "LOW", "MEDIUM", "HIGH"]
Severity = Literal["negligible", "low", "medium", "high", "critical"]
Strategy = Literal["EXECUTE", "EXECUTE_AFTER_REVIEW", "SIMULATE_ONLY", "REQUEST_HUMAN", "FALLBACK", "DEFER", "BLOCK_FOR_SAFETY"]
Execution = Literal["EXECUTED", "EXECUTED_AFTER_REVIEW", "SIMULATED", "HELD_FOR_HUMAN", "FELL_BACK", "DEFERRED_SAFETY",
                    "BLOCKED_SAFETY", "DENIED", "DEFERRED"]

LEVELS: tuple[Level, ...] = ("ZERO", "MINIMAL", "LOW", "MEDIUM", "HIGH")
SEVERITIES: tuple[Severity, ...] = ("negligible", "low", "medium", "high", "critical")
CLAIMED_EXTERNALITY = ("external", "internal", "local", "sandbox-only", "none")
CLAIMED_REVERSIBILITY = ("irreversible", "partially-reversible", "reversible", "rollbackable", "simulation-only")


# --------------------------------------------------------------------------
# Stage 1 — Risk oracle: Γ-owned effect profile, objectively assigned
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class EffectProfile:
    externality: str            # Γ-owned: "internal" | "external"
    reversibility: str          # Γ-owned: "reversible" | "partially-reversible" | "irreversible"
    severity: Severity
    approval_required: bool

    @property
    def level(self) -> Level:
        return {"negligible": "ZERO", "low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "HIGH"}[self.severity]

    @property
    def consequential(self) -> bool:
        return self.externality == "external" or self.reversibility != "reversible"


#: The risk oracle. Keyed by (action, target). Nothing here is authority.
RISK_ORACLE: dict[tuple[str, str], EffectProfile] = {
    ("TRANSFER", "silo-4"): EffectProfile("external", "irreversible", "critical", True),
    ("TRANSFER", "escrow-2"): EffectProfile("external", "irreversible", "critical", True),
    ("PURGE", "escrow-2"): EffectProfile("external", "irreversible", "high", True),
    ("ROTATE", "silo-4"): EffectProfile("internal", "reversible", "low", False),
    ("INSPECT", "silo-4"): EffectProfile("internal", "reversible", "negligible", False),
    ("ARCHIVE", "silo-4"): EffectProfile("internal", "partially-reversible", "medium", False),
}


def objective_risk(action: ProposedAction) -> EffectProfile:
    return RISK_ORACLE[(action.action, action.target)]


def contract_for(action: ProposedAction, **overrides) -> ScopeContract:
    """The Γ-owned scope for an action: the oracle's profile, canonical roles/targets."""
    p = objective_risk(action)
    base = dict(targets=(action.target,), roles=("operator-A",), capabilities=("execute-action",),
                approval_required=p.approval_required, externality=p.externality, reversibility=p.reversibility)
    base.update(overrides)
    return ma._base_contract(**base)


# --------------------------------------------------------------------------
# Stage 2 — Reported risk state and its interpretation (fail-safe)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskState:
    """What a classifier / memory / agent REPORTS. Untrusted by construction."""
    risk_level: object = "MEDIUM"
    risk_score: object = 0.5                  # [0, 1], lower = safer
    externality: object = "external"          # claimed
    reversibility: object = "irreversible"    # claimed
    severity: object = "medium"
    uncertainty: object = 0.5
    human_review_recommended: object = True
    safe: object = False
    review_required: object = True
    classifier: pt.ReliabilityState | None = None   # composition with PETG


def _unit(v: object) -> bool:
    return type(v) is float and math.isfinite(v) and 0.0 <= v <= 1.0


def interpret(state: object) -> Level | Literal["UNKNOWN"]:
    """Stage 2. Malformed or missing -> UNKNOWN. Never a privileged default."""
    if not isinstance(state, RiskState):
        return "UNKNOWN"
    if state.risk_level not in LEVELS or not _unit(state.risk_score) or state.severity not in SEVERITIES \
            or state.externality not in CLAIMED_EXTERNALITY or state.reversibility not in CLAIMED_REVERSIBILITY \
            or not _unit(state.uncertainty) or type(state.safe) is not bool or type(state.review_required) is not bool \
            or type(state.human_review_recommended) is not bool:
        return "UNKNOWN"
    # the reported level, tightened by score and severity (strictest wins — Γ-3 shape)
    by_score: Level = "ZERO" if state.risk_score == 0.0 else "MINIMAL" if state.risk_score < 0.1 else \
        "LOW" if state.risk_score < 0.3 else "MEDIUM" if state.risk_score < 0.6 else "HIGH"
    by_sev: Level = {"negligible": "ZERO", "low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "HIGH"}[state.severity]
    return max((state.risk_level, by_score, by_sev), key=LEVELS.index)


# --------------------------------------------------------------------------
# Stage 3/4 — Strategy selection = safety gate. Never reads the ledger.
# --------------------------------------------------------------------------

def select_strategy(objective: EffectProfile, reported: object, trust: pt.TrustRoute = "AUTO") -> Strategy:
    lvl = interpret(reported)
    if lvl == "UNKNOWN":
        return "REQUEST_HUMAN"
    effective: Level = max((objective.level, lvl), key=LEVELS.index)        # strictest wins
    if effective == "HIGH":
        return "REQUEST_HUMAN" if trust == "AUTO" else "BLOCK_FOR_SAFETY"
    if effective == "MEDIUM":
        return "EXECUTE_AFTER_REVIEW" if trust in ("AUTO", "REVIEW") else "SIMULATE_ONLY"
    if trust == "UNKNOWN":
        return "DEFER"
    if trust == "ROUTE_TO_HUMAN":
        return "FALLBACK"
    return "EXECUTE" if trust == "AUTO" else "EXECUTE_AFTER_REVIEW"


# --------------------------------------------------------------------------
# Stage 5 — Authority on the Γ-OWNED profile; reported risk only as declared_*
# --------------------------------------------------------------------------

def _declared(reported: object) -> tuple[str | None, str | None]:
    """Map a reported claim onto Γ's untrusted declared_* fields. Claims outside
    Γ's vocabulary are the weakest reading of what was claimed."""
    if not isinstance(reported, RiskState) or type(reported.externality) is not str or type(reported.reversibility) is not str:
        return None, None
    ext = {"external": "external", "internal": "internal", "local": "internal", "sandbox-only": "internal", "none": "internal"}.get(reported.externality)
    rev = {"irreversible": "irreversible", "partially-reversible": "partially-reversible", "reversible": "reversible",
           "rollbackable": "reversible", "simulation-only": "reversible"}.get(reported.reversibility)
    return ext, rev


def authority(records: Sequence[MemoryRecord], action: ProposedAction, ledger: ma.GrantLedger, reported: object,
              *, tick: int, state_hash: str) -> tuple[ma.Outcome, dict[str, str]]:
    """Stage 5. Scope + Γ over the ORACLE's Γ-owned contract. Memory supplies
    references only (grant_ref); its claimed scope is ignored here. The reported
    risk enters as declared_* — Γ-4 lets it tighten, never weaken."""
    ev = ma.read_evidence(records)
    resolved = [(ref, g) for ref in ev.refs if (g := ledger.resolve(ref)) is not None]
    grant = resolved[0][1] if resolved else None
    contract = contract_for(action)
    trace: dict[str, str] = {"resolved": ",".join(r for r, _ in resolved) or "none", "grant": grant.grant_id if grant else "none"}
    decision = ScopeDecision("ALLOW", contract, scope_digest(contract)).evaluate(
        ScopeRequest(role=action.role, tool=action.tool, memory_kind="semantic", capability=action.capability,
                     target=action.target, path=action.path))
    trace["scope"] = decision.verdict
    if decision.verdict != "ALLOW":
        return "DENY", trace
    d_ext, d_rev = _declared(reported)
    proposal = replace(ma.proposal_for(action, contract, (ma.proposer_claim(action),) + ev.claims),
                       declared_externality=d_ext, declared_reversibility=d_rev)
    verdict = gamma.validate(gamma.ValidationContext(proposal=proposal, tick=tick, state_hash=state_hash,
                                                     scope_digest=scope_digest(contract), authority=grant))
    trace["gamma"] = verdict.result
    trace["gamma_failures"] = ",".join(f.invariant_id for f in verdict.failures) or "none"
    if verdict.result == "INVALID":
        return "DENY", trace
    if verdict.result == "UNCLEAR":
        return "DEFER", trace
    return "ALLOW", trace


def canonical(action: ProposedAction, ledger: ma.GrantLedger, grant_id: str | None, *, tick: int, state_hash: str) -> ma.Outcome:
    """Oracle for Stage 5: no memory, no reported risk."""
    return ma.evaluate_canonical(action, ledger, grant_id, contract_for(action), tick=tick, state_hash=state_hash)[0]


# --------------------------------------------------------------------------
# Stage 6 — Execution decision
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskDecision:
    objective: EffectProfile
    interpreted: str
    detection_correct: bool
    strategy: Strategy
    authority: ma.Outcome
    execution: Execution
    trace: dict[str, str]

    @property
    def authority_level(self) -> int:
        return ma.level(self.authority)

    @property
    def safety_effect(self) -> bool:
        return self.authority == "ALLOW" and self.execution != "EXECUTED"


_EXEC: dict[Strategy, Execution] = {
    "EXECUTE": "EXECUTED", "EXECUTE_AFTER_REVIEW": "EXECUTED_AFTER_REVIEW", "SIMULATE_ONLY": "SIMULATED",
    "REQUEST_HUMAN": "HELD_FOR_HUMAN", "FALLBACK": "FELL_BACK", "DEFER": "DEFERRED_SAFETY", "BLOCK_FOR_SAFETY": "BLOCKED_SAFETY",
}


def risk_decision(records: Sequence[MemoryRecord], action: ProposedAction, ledger: ma.GrantLedger, reported: object,
                  *, tick: int, state_hash: str, trust: pt.TrustRoute = "AUTO") -> RiskDecision:
    obj = objective_risk(action)
    lvl = interpret(reported)
    auth, trace = authority(records, action, ledger, reported, tick=tick, state_hash=state_hash)
    strat = select_strategy(obj, reported, trust)
    trace = dict(trace); trace.update({"objective": obj.level, "interpreted": lvl, "strategy": strat, "trust": trust})
    if auth == "DENY":
        return RiskDecision(obj, lvl, lvl == obj.level, strat, auth, "DENIED", trace)
    if auth == "DEFER":
        return RiskDecision(obj, lvl, lvl == obj.level, strat, auth, "DEFERRED", trace)
    return RiskDecision(obj, lvl, lvl == obj.level, strat, auth, _EXEC[strat], trace)


# --------------------------------------------------------------------------
# The MAP-R1 B2 bridge, reachable for the preregistered classification probe
# --------------------------------------------------------------------------

def b2_bridge(records: Sequence[MemoryRecord], action: ProposedAction, ledger: ma.GrantLedger,
              *, tick: int, state_hash: str) -> tuple[ma.Outcome, dict[str, str]]:
    # MEMORY-BRIDGE-GAMMA-INPUT-REPAIR-R1: the live B2 bridge is repaired; the
    # probe stays bound to the verbatim pre-repair path so RAD-CE1 remains
    # reproducible as frozen. The RAD test and evidence are unchanged.
    return ma.evaluate_with_memory_prerepair(list(records), action, ledger, tick=tick, state_hash=state_hash,
                                             fallback_contract=contract_for(action))


def risk_note(reported: RiskState, grant_ref: object = None, contract: ScopeContract | None = None, **claims) -> str:
    fields = {k: getattr(reported, k) for k in ("risk_level", "risk_score", "externality", "reversibility", "severity",
                                                "uncertainty", "human_review_recommended", "safe", "review_required")}
    return ma.authority_note(grant_ref, contract if contract is not None else ma.canonical_contract(), risk=fields, **claims)
