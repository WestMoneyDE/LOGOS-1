"""Production bridge v1 — `decide_action` (CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1, C2).

Relocation of the validated experimental path (MEMORY-BRIDGE-GAMMA-INPUT-REPAIR
→ VALIDATION → canonical owner adapter) into production code. Order of
evaluation, each step terminal on failure:

    1. canonical effect      owner UNKNOWN / UNAVAILABLE / INVALID  -> DEFER
    2. memory evidence       reader non-RESOLVED                   -> DEFER (typed status -> failure code)
    3. claimed scope         none                                  -> DEFER
    4. canonical authority   resolver by explicit grant reference(s):
                             RESOLVED -> evidence; NO_GRANT where a grant is required -> DENY;
                             REVOKED/STALE/NOT_YET_VALID/WRONG_* -> DENY; INVALID/UNAVAILABLE/UNKNOWN -> DEFER
    5. binding (scope engine) claimed scope vs request             -> DENY
    6. approval              approval-sensitive effect needs a human-rooted RESOLVED grant -> DENY
    7. Γ                     canonical fields from the owner, memory only as declared_* / provenance
    8. audit                 emitter failure                       -> DEFER (never silent)

No fallback to any experimental fixture, historical bridge, memory prose,
trust, risk, VOI or default. Memory carries references; it is never authority
(the bridge does not discover grants by principal — a reference must be
presented, exactly as the validated bridge required).
"""
from __future__ import annotations

from hashlib import sha256

import logos_gamma as gamma
from logos_authority import DEFER_STATUSES, DENY_STATUSES, AuthorityContext, AuthorityResolution, resolve_authority
from logos_effects import CanonicalEffectContext, CanonicalEffectResolution
from logos_memory.scope import ScopeContract, ScopeDecision, ScopeRequest, scope_digest

from .types import (
    BRIDGE_API_VERSION,
    AuditUnavailable,
    BridgeDecision,
    DeclaredEvidence,
    ExecutionContext,
    PrincipalContext,
    TenantContext,
)


def proposal_digest(action: str, target: str) -> str:
    return sha256(f"{action}:{target}".encode()).hexdigest()


def proposer_claim(action: str, target: str) -> gamma.ProvenanceClaim:
    """The proposal's own provenance: the proposing agent, origin "model" (never authority)."""
    d = proposal_digest(action, target)
    return gamma.ProvenanceClaim("proposal://" + d[:16], "model", d)


def canonical_proposal(action: str, target: str, effect, provenance, declared) -> gamma.EffectProposal:
    """Canonical fields from the owner's effect; the memory claim only as declared_*."""
    return gamma.EffectProposal(action=action, target=target,
                                effect_kind="deployment" if effect.externality == "external" else "write-internal",
                                externality=effect.externality, reversibility=effect.reversibility,
                                proposal_digest=proposal_digest(action, target), provenance=tuple(provenance),
                                declared_externality=declared[0], declared_reversibility=declared[1])  # type: ignore[arg-type]


def _effect_ref(r: CanonicalEffectResolution | None) -> dict:
    if r is None:
        return {"status": "NOT_EVALUATED"}
    return {"status": r.status, "definition_id": r.definition_id, "version": r.version, "definition_hash": r.definition_hash,
            "owner_type": r.audit_metadata.get("owner_type"), "registry_hash": r.audit_metadata.get("registry_hash"), "error": r.error}


def _authority_ref(r: AuthorityResolution | None) -> dict:
    if r is None:
        return {"status": "NOT_EVALUATED"}
    return {"status": r.status, "grant_id": r.grant_id, "grant_version": r.grant_version, "grant_origin": r.grant_origin,
            "definition_hash": r.definition_hash, "revocation_state": r.revocation_state, "store_hash": r.audit_metadata.get("store_hash"), "error": r.error}


def decide_action(principal: PrincipalContext, action: str, target: str, memory_ref: str | None, state: str,
                  tenant_context: TenantContext, execution_context: ExecutionContext, *,
                  evidence: DeclaredEvidence | None = None) -> BridgeDecision:
    """`evidence` may be supplied directly by a caller that already holds typed
    evidence (C2 validation); otherwise `memory_ref` is read through the
    execution context's memory reader."""
    x = execution_context
    trace_id = sha256(f"{x.run_id}|{tenant_context.tenant_id}|{principal.principal}|{action}|{target}|{x.tick}|{state}|{memory_ref}".encode()).hexdigest()
    trace: dict = {"api_version": BRIDGE_API_VERSION, "run_id": x.run_id, "tenant": tenant_context.tenant_id, "principal": principal.principal,
                   "action": action, "target": target, "tick": x.tick, "state_hash": state, "memory_ref": memory_ref, "decision_trace_id": trace_id}
    eff = auth = None
    declared: tuple[str | None, str | None] = (None, None)
    binding = "not-evaluated"; approval = "NOT_EVALUATED"

    def finish(outcome: str, *codes: str) -> BridgeDecision:
        d = BridgeDecision(outcome, tuple(codes), _effect_ref(eff), _authority_ref(auth), declared, binding, approval, trace_id, BRIDGE_API_VERSION, trace)
        return _audited(d, x, tenant_context, principal, action, target, state)

    # 1. canonical effect
    eff = x.effect_registry.resolve(action, target, CanonicalEffectContext(x.run_id, x.effect_domain, tenant_context.tenant_id))
    if eff.status != "RESOLVED":
        trace["effect"] = "none"; trace["scope"] = "not-evaluated"
        return finish("DEFER", f"EFFECT_{eff.status}")
    effect = eff.effect
    trace["effect"] = f"{effect.externality}/{effect.reversibility}/approval={effect.approval_required}"

    # 2. memory evidence
    if evidence is None:
        if memory_ref is None:
            evidence = DeclaredEvidence()
        elif x.memory_reader is None:
            trace["scope"] = "not-evaluated"
            return finish("DEFER", "MEMORY_UNAVAILABLE")
        else:
            read = x.memory_reader.read(memory_ref, tenant_context, principal)
            trace["memory_status"] = read.status
            if read.status != "RESOLVED" or read.evidence is None:
                trace["scope"] = "not-evaluated"
                return finish("DEFER", f"MEMORY_{read.status}")
            evidence = read.evidence
    if evidence.tenant_id is not None and evidence.tenant_id != tenant_context.tenant_id:
        trace["scope"] = "not-evaluated"
        return finish("DEFER", "MEMORY_WRONG_TENANT")
    declared = evidence.declared_effect
    trace["declared"] = f"{declared[0]}/{declared[1]}"; trace["memory_refs"] = ",".join(evidence.refs) or "none"

    # 3. claimed scope (scope evaluation + binding digest only)
    contract: ScopeContract | None = evidence.claimed_scope
    if contract is None:
        trace["scope"] = "none"
        return finish("DEFER", "NO_SCOPE_CONTRACT")
    digest = scope_digest(contract)

    # 4. canonical authority — explicit references only
    actx = AuthorityContext(x.tick, x.run_id, tenant_context.tenant_id)
    if evidence.refs:
        results = [resolve_authority(principal.principal, action, target, digest, state, actx, store=x.authority_store, grant_ref=ref) for ref in evidence.refs]
        auth = next((r for r in results if r.resolved), results[0])
    else:
        # no reference presented: the store is still consulted for availability / integrity (UNAVAILABLE / INVALID
        # dominate); an empty reference is an unsupported form (UNKNOWN) which here means: NO_GRANT
        probe = resolve_authority(principal.principal, action, target, digest, state, actx, store=x.authority_store, grant_ref="")
        auth = probe if probe.status != "UNKNOWN" else AuthorityResolution(
            "NO_GRANT", None, None, None, None, principal.principal, digest, None, None, None, state, None, None,
            "no grant reference presented", {**probe.audit_metadata, "status": "NO_GRANT", "error": "no grant reference presented"})
    trace["authority"] = auth.status; trace["grant"] = auth.grant_id or "none"
    authority = None
    if auth.resolved:
        authority = auth.authority_evidence
    elif auth.status == "NO_GRANT":
        if effect.consequential or effect.approval_required:
            binding = "not-evaluated"
            return finish("DENY", "AUTHORITY_NO_GRANT")
    elif auth.status in DENY_STATUSES:
        return finish("DENY", f"AUTHORITY_{auth.status}")
    elif auth.status in DEFER_STATUSES:
        return finish("DEFER", f"AUTHORITY_{auth.status}")

    # 5. binding — scope engine on the CLAIMED contract
    decision = ScopeDecision("ALLOW", contract, digest).evaluate(ScopeRequest(role=principal.principal, tool=principal.tool, memory_kind="semantic",
                                                                              capability=principal.capability, target=target, path=principal.path))
    binding = decision.verdict; trace["scope"] = decision.verdict
    if decision.verdict != "ALLOW":
        return finish("DENY", "BINDING_SCOPE")

    # 6. approval — Γ has no approval field; the bridge enforces it
    if effect.approval_required:
        if authority is None or not authority.is_human_rooted():
            approval = "MISSING"; trace["gamma"] = "not-evaluated"
            return finish("DENY", "APPROVAL_REQUIRED")
        approval = "SATISFIED"
    else:
        approval = "NOT_REQUIRED"

    # 7. Γ — canonical evaluator
    claims = (proposer_claim(action, target),) + tuple(evidence.claims)
    verdict = gamma.validate(gamma.ValidationContext(proposal=canonical_proposal(action, target, effect, claims, declared), tick=x.tick,
                                                     state_hash=state, scope_digest=digest, authority=authority))
    trace["gamma"] = verdict.result; trace["gamma_failures"] = ",".join(f.invariant_id for f in verdict.failures) or "none"
    if verdict.result == "INVALID":
        return finish("DENY", "GAMMA_INVALID")
    if verdict.result == "UNCLEAR":
        return finish("DEFER", "GAMMA_UNCLEAR")
    return finish("ALLOW")


def _audited(d: BridgeDecision, x: ExecutionContext, tenant: TenantContext, principal: PrincipalContext, action: str, target: str, state: str) -> BridgeDecision:
    """8. audit. A decision that cannot be recorded is not returned as computed:
    it becomes DEFER with AUDIT_UNAVAILABLE (preregistered failure semantics)."""
    if x.audit_sink is None:
        return d
    event = {"run_id": x.run_id, "tenant_id": tenant.tenant_id, "principal": principal.principal, "action": action, "target": target,
             "effect_definition_id": d.canonical_effect_ref.get("definition_id"), "effect_version": d.canonical_effect_ref.get("version"),
             "effect_hash": d.canonical_effect_ref.get("definition_hash"), "grant_id": d.authority_ref.get("grant_id"),
             "grant_version": d.authority_ref.get("grant_version"), "grant_origin": d.authority_ref.get("grant_origin"),
             "scope_digest": None, "state_hash": state, "revocation_status": d.authority_ref.get("revocation_state"),
             "binding_result": d.binding_result, "approval_state": d.approval_state, "gamma_outcome": d.trace.get("gamma", "not-evaluated"),
             "bridge_outcome": d.outcome, "failure_codes": list(d.failure_codes), "owner_resolution_status": d.canonical_effect_ref.get("status"),
             "authority_resolution_status": d.authority_ref.get("status"), "api_version": d.api_version, "decision_trace_id": d.decision_trace_id}
    try:
        h = x.audit_sink.emit(event)
    except AuditUnavailable as e:
        t = {**d.trace, "audit": "unavailable", "audit_error": str(e), "computed_outcome": d.outcome}
        return BridgeDecision("DEFER", tuple(c for c in d.failure_codes) + ("AUDIT_UNAVAILABLE",), d.canonical_effect_ref, d.authority_ref, d.declared_effect,
                              d.binding_result, d.approval_state, d.decision_trace_id, d.api_version, t)
    d.trace["audit"] = "recorded"; d.trace["audit_event_hash"] = h
    return d
