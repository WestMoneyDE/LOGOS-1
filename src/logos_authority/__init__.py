"""logos_authority — production owner of canonical authority resolution.

CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1, phase C1. See
docs/adr/ADR-CANONICAL-AUTHORITY-PRODUCTION-BRIDGE.md.

    resolve_authority(principal, action, target, scope, state, context, *, store, grant_ref=None)
        -> AuthorityResolution{status, authority_evidence, grant_id, grant_version, grant_origin, ...}

Only RESOLVED carries canonical authority evidence. Imports: stdlib and
logos_gamma.types (the evidence type Γ reads). Never logos_memory, never
logos_research. PRODUCTION package: `logos_research.experiments` refuses to
be imported from it (B1 guard).
"""
from __future__ import annotations

from .resolver import resolve_authority
from .store import AuthorityStore, InMemoryAuthorityStore
from .types import (
    AUTHORITY_ORIGINS,
    DEFER_STATUSES,
    DENY_STATUSES,
    OWNER_TYPE,
    STATUSES,
    AuthorityContext,
    AuthorityResolution,
    GrantRecord,
    proposal_digest,
)

__all__ = ["AUTHORITY_ORIGINS", "DEFER_STATUSES", "DENY_STATUSES", "OWNER_TYPE", "STATUSES", "AuthorityContext", "AuthorityResolution",
           "AuthorityStore", "GrantRecord", "InMemoryAuthorityStore", "proposal_digest", "resolve_authority"]
