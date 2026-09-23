"""Jev — the local juror model, and the contract that keeps it a juror.

Jev classifies, ranks and routes. It does not authorize, and this package has no
mechanism by which it could: the output contract has no field for a permission, every
failure mode produces `ABSTAIN`, and the one profile that reaches Γ reaches it through
`ValidationContext.advisories`, whose vocabulary (Γ-18) contains no `ALLOW`.

Γ imports nothing from here. The dependency runs one way, on purpose.
"""
from .contract import CONTRACT, PARSE_CODES, PROFILES, JevAnswer, abstain, parse, validate

__all__ = ["CONTRACT", "PARSE_CODES", "PROFILES", "JevAnswer", "abstain", "parse", "validate"]
