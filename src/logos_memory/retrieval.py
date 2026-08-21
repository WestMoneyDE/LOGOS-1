from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import re

from .records import MemoryRecord
from .scope import ScopeDecision


BM25_K1 = 1.5
BM25_B = 0.75
_TOKEN = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class RetrievalItem:
    id: str
    score: float
    content_digest: str
    epistemic_status: str
    conflicts_with: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalRecord:
    query_digest: str
    candidate_ids: tuple[str, ...]
    excluded_ids: tuple[str, ...]
    items: tuple[RetrievalItem, ...]
    scope_digest: str
    context_digest: str
    scope_reasons: tuple[str, ...] = ()
    scope_unresolved_dimensions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectionRecord:
    purpose: str
    audience: str
    valid_until: str
    source_ids: tuple[str, ...]
    source_digests: tuple[str, ...]
    scope_digest: str
    content: str
    digest: str


def canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


def content_digest(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(token.lower() for token in _TOKEN.findall(value))


def retrieve_records(
    records: tuple[MemoryRecord, ...], query: str, scope: ScopeDecision, limit: int
) -> RetrievalRecord:
    query_hash = sha256(query.encode("utf-8")).hexdigest()
    scope = scope.validate()
    if scope.verdict not in {"ALLOW", "NARROW"} or scope.effective is None:
        return RetrievalRecord(
            query_hash, (), (), (), scope.digest, canonical_digest([]),
            scope.reasons, scope.unresolved_dimensions,
        )
    if type(limit) is not int or limit < 0:
        raise ValueError("limit must be a non-negative integer")

    audiences = set(scope.effective.projection_audiences)
    allowed = tuple(sorted(
        (record for record in records if audiences.intersection(record.visibility)),
        key=lambda record: record.id,
    ))
    excluded_ids = tuple(sorted(
        record.id for record in records if not audiences.intersection(record.visibility)
    ))
    candidate_ids = tuple(record.id for record in allowed)
    query_terms = _tokens(query)
    documents = {record.id: Counter(_tokens(record.content)) for record in allowed}
    lengths = {record_id: sum(terms.values()) for record_id, terms in documents.items()}
    average_length = sum(lengths.values()) / len(lengths) if lengths else 0.0
    document_frequencies = {
        term: sum(term in terms for terms in documents.values()) for term in set(query_terms)
    }

    scored: list[tuple[float, MemoryRecord]] = []
    for record in allowed:
        score = 0.0
        terms = documents[record.id]
        for term in query_terms:
            frequency = terms[term]
            if not frequency:
                continue
            document_frequency = document_frequencies[term]
            inverse_frequency = math.log(
                1.0 + (len(allowed) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            normalization = frequency + BM25_K1 * (
                1.0 - BM25_B
                + BM25_B * (lengths[record.id] / average_length if average_length else 0.0)
            )
            score += inverse_frequency * frequency * (BM25_K1 + 1.0) / normalization
        if score > 0.0:
            scored.append((score, record))

    scored.sort(key=lambda pair: (-pair[0], pair[1].id))
    items = tuple(
        RetrievalItem(
            id=record.id,
            score=score,
            content_digest=content_digest(record.content),
            epistemic_status=record.epistemic_status,
            conflicts_with=record.conflicts_with,
        )
        for score, record in scored[:limit]
    )
    return RetrievalRecord(
        query_digest=query_hash,
        candidate_ids=candidate_ids,
        excluded_ids=excluded_ids,
        items=items,
        scope_digest=scope.digest,
        context_digest=canonical_digest([asdict(item) for item in items]),
    )
