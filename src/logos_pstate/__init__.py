"""Deterministic adapter primitives for LOGOS-1 persistent-state experiments."""

from .mamba_state import (
    MambaStateSnapshot,
    capture_state,
    restore_state,
    fresh_state,
    swap_state,
    permute_state,
    state_digest,
)
from .token_context import (
    FULL_CONTEXT_LIMIT,
    PRIMARY_TRUNCATION_TOKENS,
    full_token_history,
    truncated_history,
    history_substitution,
)
from .retrieval import Chunk, BM25Index, RetrievalRecord, build_retrieval_record
from .ruler_freeze import DatasetFreezeManifest, freeze_jsonl

__all__ = [
    "MambaStateSnapshot",
    "capture_state",
    "restore_state",
    "fresh_state",
    "swap_state",
    "permute_state",
    "state_digest",
    "FULL_CONTEXT_LIMIT",
    "PRIMARY_TRUNCATION_TOKENS",
    "full_token_history",
    "truncated_history",
    "history_substitution",
    "Chunk",
    "BM25Index",
    "RetrievalRecord",
    "build_retrieval_record",
    "DatasetFreezeManifest",
    "freeze_jsonl",
]
