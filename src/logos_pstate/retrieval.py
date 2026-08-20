"""Dependency-free deterministic BM25 retrieval for the external-memory control arm."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re
from typing import Iterable, Sequence

_TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


def lexical_tokens(text: str) -> tuple[str, ...]:
    return tuple(m.group(0).casefold() for m in _TOKEN_RE.finditer(text))


@dataclass(frozen=True, order=True)
class Chunk:
    chunk_id: str
    text: str

    @property
    def token_count(self) -> int:
        return len(lexical_tokens(self.text))

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScoredChunk:
    chunk_id: str
    score: float
    token_count: int
    text_sha256: str


class BM25Index:
    def __init__(self, chunks: Iterable[Chunk], *, k1: float = 1.5, b: float = 0.75):
        self.k1 = float(k1)
        self.b = float(b)
        self.chunks = tuple(sorted(chunks, key=lambda c: c.chunk_id))
        if len({c.chunk_id for c in self.chunks}) != len(self.chunks):
            raise ValueError("chunk_id values must be unique")
        self.docs = {c.chunk_id: lexical_tokens(c.text) for c in self.chunks}
        self.avgdl = sum(len(v) for v in self.docs.values()) / max(len(self.docs), 1)
        df: dict[str, int] = {}
        for toks in self.docs.values():
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        n = len(self.docs)
        self.idf = {t: math.log(1.0 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query: str, chunk: Chunk) -> float:
        q = lexical_tokens(query)
        doc = self.docs[chunk.chunk_id]
        if not doc or not q:
            return 0.0
        counts: dict[str, int] = {}
        for term in doc:
            counts[term] = counts.get(term, 0) + 1
        dl = len(doc)
        total = 0.0
        for term in q:
            tf = counts.get(term, 0)
            if not tf:
                continue
            denom = tf + self.k1 * (1.0 - self.b + self.b * dl / max(self.avgdl, 1e-12))
            total += self.idf.get(term, 0.0) * (tf * (self.k1 + 1.0)) / denom
        return total

    def rank(self, query: str) -> tuple[ScoredChunk, ...]:
        scored = [
            ScoredChunk(c.chunk_id, self.score(query, c), c.token_count, c.sha256)
            for c in self.chunks
        ]
        return tuple(sorted(scored, key=lambda x: (-x.score, x.chunk_id)))

    def select(self, query: str, *, k: int) -> tuple[ScoredChunk, ...]:
        if k < 0:
            raise ValueError("k must be non-negative")
        return self.rank(query)[:k]

    def matched_distractors(
        self,
        *,
        excluded_ids: Sequence[str],
        target_token_count: int,
        k: int,
    ) -> tuple[Chunk, ...]:
        """Deterministic greedy token-budget match with canonical-id tie breaking."""
        excluded = set(excluded_ids)
        pool = [c for c in self.chunks if c.chunk_id not in excluded]
        selected: list[Chunk] = []
        total = 0
        for _ in range(k):
            if not pool:
                raise ValueError("not enough distractor chunks")
            remaining_target = max(target_token_count - total, 0)
            slots = max(k - len(selected), 1)
            ideal = remaining_target / slots
            choice = min(pool, key=lambda c: (abs(c.token_count - ideal), c.chunk_id))
            selected.append(choice)
            total += choice.token_count
            pool.remove(choice)
        return tuple(selected)


@dataclass(frozen=True)
class RetrievalRecord:
    query_sha256: str
    candidate_chunk_ids: tuple[str, ...]
    scored: tuple[ScoredChunk, ...]
    selected_chunk_ids: tuple[str, ...]
    selected_text_sha256: tuple[str, ...]
    retrieved_lexical_token_count: int
    final_prompt_sha256: str


def build_retrieval_record(
    *,
    query: str,
    index: BM25Index,
    selected: Sequence[Chunk],
    final_prompt: str,
) -> RetrievalRecord:
    ranking = index.rank(query)
    return RetrievalRecord(
        query_sha256=hashlib.sha256(query.encode()).hexdigest(),
        candidate_chunk_ids=tuple(c.chunk_id for c in index.chunks),
        scored=ranking,
        selected_chunk_ids=tuple(c.chunk_id for c in selected),
        selected_text_sha256=tuple(c.sha256 for c in selected),
        retrieved_lexical_token_count=sum(c.token_count for c in selected),
        final_prompt_sha256=hashlib.sha256(final_prompt.encode()).hexdigest(),
    )
