"""Canonical authority resolver — the production owner of grant resolution.

    resolve_authority(principal, action, target, scope, state, context) -> AuthorityResolution

Evaluation order (preregistered, CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1):

    store unavailable                         -> UNAVAILABLE
    store schema / duplicate / integrity fail -> INVALID
    grant_ref of unsupported form             -> UNKNOWN
    no candidate grant                        -> NO_GRANT
    revoked                                   -> REVOKED
    tick <  valid_from                        -> NOT_YET_VALID
    tick >= expires                           -> STALE
    principal mismatch                        -> WRONG_PRINCIPAL
    scope digest mismatch                     -> WRONG_SCOPE
    state hash mismatch                       -> WRONG_STATE
    otherwise                                 -> RESOLVED (canonical evidence)

A grant is selected by explicit reference (`grant_ref`) when the caller holds
one, otherwise by exact (principal, action, target). Several candidates are
resolved in sorted id order and the FIRST failure class is reported per
candidate; a RESOLVED candidate wins only if no rule failed for it. Nothing
else is consulted: no memory, prose, trust, risk, VOI, declared effect.
"""
from __future__ import annotations

import time

from .store import AuthorityStore
from .types import OWNER_TYPE, AuthorityContext, AuthorityResolution, GrantRecord, proposal_digest


def _classify(r: GrantRecord, principal: str, action: str, target: str, scope: str, state: str, tick: int) -> str:
    if r.revoked:
        return "REVOKED"
    if tick < r.valid_from_tick:
        return "NOT_YET_VALID"
    if tick >= r.expires_tick:
        return "STALE"
    if r.principal != principal:
        return "WRONG_PRINCIPAL"
    if r.scope_digest != scope or r.proposal_digest != proposal_digest(action, target):
        return "WRONG_SCOPE"
    if r.state_hash != state:
        return "WRONG_STATE"
    return "RESOLVED"


def resolve_authority(principal: str, action: str, target: str, scope: str, state: str, context: AuthorityContext, *,
                      store: AuthorityStore, grant_ref: object = None) -> AuthorityResolution:
    t0 = time.perf_counter_ns()
    status, error, rec = _resolve(principal, action, target, scope, state, context, store, grant_ref)
    meta = {"owner_type": OWNER_TYPE, "store_version": getattr(store, "version", None),
            "store_hash": store.integrity_hash() if getattr(store, "available", False) else None,
            "status": status, "error": error, "principal": principal, "action": action, "target": target, "scope_digest": scope,
            "state_hash": state, "tick": context.tick, "tenant": context.tenant, "bridge_run_id": context.bridge_run_id,
            "grant_id": rec.grant_id if rec else None, "grant_version": rec.version if rec else None,
            "definition_hash": rec.definition_hash if rec else None, "latency_ns": time.perf_counter_ns() - t0, "resolved_at_ns": time.time_ns()}
    if status == "RESOLVED":
        assert rec is not None
        return AuthorityResolution("RESOLVED", rec.evidence(), rec.grant_id, rec.version, rec.authority_origin, rec.principal, rec.scope_digest,
                                   rec.issued_at_tick, rec.valid_from_tick, rec.expires_tick, rec.state_hash, "active", rec.definition_hash, None, meta)
    if rec is not None:                                                     # a specific grant failed: report which, without evidence
        return AuthorityResolution(status, None, rec.grant_id, rec.version, rec.authority_origin, rec.principal, rec.scope_digest,
                                   rec.issued_at_tick, rec.valid_from_tick, rec.expires_tick, rec.state_hash,
                                   "revoked" if rec.revoked else "active", rec.definition_hash, error, meta)
    return AuthorityResolution(status, None, None, None, None, principal, scope, None, None, None, state, None, None, error, meta)


def _resolve(principal, action, target, scope, state, context, store, grant_ref):
    if not getattr(store, "available", False):
        return "UNAVAILABLE", f"authority store not loadable: {getattr(store, 'load_error', None)}", None
    issues = store.issues()
    if issues:
        return "INVALID", "; ".join(issues), None
    if type(principal) is not str or type(action) is not str or type(target) is not str or type(scope) is not str or type(state) is not str \
            or type(context.tick) is not int:
        return "INVALID", "principal, action, target, scope, state must be str; tick int", None
    if grant_ref is not None:
        if type(grant_ref) is not str or not grant_ref:
            return "UNKNOWN", f"grant reference of unsupported form: {type(grant_ref).__name__}", None
        r = store.lookup(grant_ref)
        if r is None:
            return "NO_GRANT", f"no grant {grant_ref!r}", None
        candidates = (r,)
    else:
        candidates = store.grants_for(principal, action, target)
        if not candidates:
            return "NO_GRANT", f"no grant for ({principal!r}, {action!r}, {target!r})", None
    first_failure = None
    for r in candidates:
        c = _classify(r, principal, action, target, scope, state, context.tick)
        if c == "RESOLVED":
            return "RESOLVED", None, r
        if first_failure is None:
            first_failure = (c, r)
    c, r = first_failure
    return c, f"grant {r.grant_id!r}: {c}", r
