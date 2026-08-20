"""Deterministic token-history interventions for the token-context family."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import hashlib
import json

FULL_CONTEXT_LIMIT = 1024
PRIMARY_TRUNCATION_TOKENS = 512


def _validate(tokens: Sequence[int]) -> tuple[int, ...]:
    out = tuple(int(x) for x in tokens)
    if any(x < 0 for x in out):
        raise ValueError("token ids must be non-negative")
    return out


def full_token_history(tokens: Sequence[int], *, max_tokens: int = FULL_CONTEXT_LIMIT) -> tuple[int, ...]:
    """Preserve all history up to the frozen context limit; reject rather than silently trim."""
    tokens = _validate(tokens)
    if len(tokens) > max_tokens:
        raise ValueError(f"history length {len(tokens)} exceeds frozen max {max_tokens}")
    return tokens


def truncated_history(tokens: Sequence[int], *, keep_last: int = PRIMARY_TRUNCATION_TOKENS) -> tuple[int, ...]:
    """Frozen causal control: retain only the final ``keep_last`` history tokens."""
    tokens = _validate(tokens)
    if keep_last < 0:
        raise ValueError("keep_last must be non-negative")
    return tokens[-keep_last:] if keep_last else tuple()


def history_substitution(
    history_a: Sequence[int],
    history_b: Sequence[int],
    query_tokens: Sequence[int],
    *,
    max_tokens: int = FULL_CONTEXT_LIMIT,
) -> tuple[int, ...]:
    """Construct the A→B intervention using B history and an identical query."""
    _ = _validate(history_a)  # validates the source arm even though it is replaced
    b = _validate(history_b)
    q = _validate(query_tokens)
    if len(b) + len(q) > max_tokens:
        raise ValueError("substituted history + query exceeds frozen context limit")
    return b + q


def token_sequence_digest(tokens: Sequence[int]) -> str:
    payload = json.dumps(list(_validate(tokens)), separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()
