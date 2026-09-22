"""RELATIONAL-STATE-SWAP-R1 — hold content and canonical authority fixed, swap
the relationships around the content, and ask whether enforcement moves.

    ContentIdentity != RelationalIdentity
    ProvenanceLabel != Authority
    WriterIdentity != AuthorityGrant
    ReaderIdentity != AuthorityGrant
    MemoryAssociation != PrincipalBinding

Two invariants under test:

* H1a — a swap of NON-authoritative relational metadata (labels, writer,
  reader, association) leaves the decision unchanged, because the canonical
  oracle is unchanged.
* H1b — a swap of a CANONICAL relation (principal, grant, scope, freshness)
  moves the decision exactly as the oracle moves; memory never masks it.

Everything here reuses the MEMORY-AUTHORITY-PROVENANCE-R1 harness: the
`GrantLedger` (EXPERIMENTAL_FIXTURE), the B2 bridge, the REAL scope engine and
the REAL Γ kernel. New here: a *held-grant* bridge variant for the MAP-F1
follow-up, in which the caller holds the grant and memory can contribute
provenance only — never a reference, never authority.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal, Sequence

from logos_memory.records import MemoryRecord
from logos_research.experiments import memory_authority as ma
from logos_research.experiments.binding_state import ProposedAction

Dimension = Literal["NON_AUTHORITATIVE_METADATA", "CANONICAL_AUTHORITY_RELATION", "AMBIGUOUS", "NOT_SUPPORTED"]
Stage = Literal["none", "write", "store", "retrieve", "project", "provenance mapping", "grant resolution",
                "gamma input mapping", "gamma validation", "action evaluation"]

#: Relational dimensions and their preregistered classification.
DIMENSIONS: dict[str, Dimension] = {
    "authority_class": "NON_AUTHORITATIVE_METADATA",
    "source_label": "NON_AUTHORITATIVE_METADATA",
    "source_type": "NON_AUTHORITATIVE_METADATA",
    "admissible_uses": "NON_AUTHORITATIVE_METADATA",
    "epistemic_status": "NON_AUTHORITATIVE_METADATA",
    "visibility": "NON_AUTHORITATIVE_METADATA",
    "record_id": "NON_AUTHORITATIVE_METADATA",
    "writer_identity": "NON_AUTHORITATIVE_METADATA",
    "reader_path": "NON_AUTHORITATIVE_METADATA",
    "store_context": "NON_AUTHORITATIVE_METADATA",
    "provenance_origin_at_gamma": "NON_AUTHORITATIVE_METADATA",
    "principal": "CANONICAL_AUTHORITY_RELATION",
    "grant_reference": "CANONICAL_AUTHORITY_RELATION",
    "scope": "CANONICAL_AUTHORITY_RELATION",
    "freshness": "CANONICAL_AUTHORITY_RELATION",
    "agent_identity": "NOT_SUPPORTED",
}


# --------------------------------------------------------------------------
# Identity: content vs relation
# --------------------------------------------------------------------------

def content_hash(record: MemoryRecord) -> str:
    return sha256(record.content.encode("utf-8")).hexdigest()


def relational_hash(record: MemoryRecord) -> str:
    """Everything about the record except its content."""
    d = asdict(record)
    d.pop("content")
    return sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# --------------------------------------------------------------------------
# Held-grant bridge (MAP-F1 follow-up): memory contributes provenance only
# --------------------------------------------------------------------------

def evaluate_held(records: Sequence[MemoryRecord], action: ProposedAction, ledger: ma.GrantLedger,
                  held_grant_id: str | None, *, tick: int, state_hash: str, own_provenance: bool,
                  contract=None) -> tuple[ma.Outcome, dict[str, str]]:
    """The caller holds `held_grant_id` (resolved fresh through the ledger).
    Memory references are IGNORED for authority; memory contributes only
    ProvenanceClaims of origin "memory". This isolates the evidence axis."""
    ev = ma.read_evidence(records)
    authority = ledger.resolve(held_grant_id) if held_grant_id else None
    contract = contract or ma.canonical_contract()
    out, trace = ma._decide(action, contract, authority, ev.claims, tick=tick, state_hash=state_hash,
                            own_provenance=own_provenance, canonical_contract=True)   # caller-held contract (MBGV-F1 guard)
    trace["memory_records"] = str(len(records))
    trace["memory_refs_ignored"] = ",".join(ev.refs) or "none"
    return out, trace


# --------------------------------------------------------------------------
# Pair metrics
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class PairResult:
    pair_id: str
    dimension: str
    classification: Dimension
    content_hash: str
    relational_before: str
    relational_after: str
    canonical_before: ma.Outcome
    canonical_after: ma.Outcome
    decision_before: ma.Outcome
    decision_after: ma.Outcome
    gamma_before: str
    gamma_after: str
    first_divergence: Stage
    #: False for canonical probes whose memory CONTENT differs (e.g. a claimed
    #: scope inside the note). Only same-content pairs test H1a.
    same_content: bool = True

    @property
    def relational_delta(self) -> bool:
        return self.relational_before != self.relational_after

    @property
    def authority_delta(self) -> ma.Delta:
        return ma.authority_delta(self.canonical_before, self.canonical_after)

    @property
    def decision_delta(self) -> ma.Delta:
        return ma.authority_delta(self.decision_before, self.decision_after)

    @property
    def unexplained_decision_delta(self) -> bool:
        """Decision moved while canonical authority did not."""
        return self.decision_before != self.decision_after and self.canonical_before == self.canonical_after

    @property
    def memory_veto(self) -> bool:
        """Decision decreased while canonical authority did not: memory blocked
        a valid grant (e.g. a claimed scope narrower than the bound scope)."""
        return self.unexplained_decision_delta and ma.level(self.decision_after) < ma.level(self.decision_before)

    @property
    def unexplained_increase(self) -> bool:
        return self.unexplained_decision_delta and ma.level(self.decision_after) > ma.level(self.decision_before)

    @property
    def missed_canonical_delta(self) -> bool:
        """Canonical authority moved but the decision did not follow it."""
        return self.canonical_before != self.canonical_after and self.decision_after != self.canonical_after


def first_divergence(trace_before: dict[str, str], trace_after: dict[str, str]) -> Stage:
    """Localize where two bridge traces first disagree, in pipeline order."""
    order: tuple[tuple[str, Stage], ...] = (
        ("memory_records", "store"), ("ignored", "provenance mapping"), ("memory_refs", "provenance mapping"),
        ("resolved", "grant resolution"), ("grant", "grant resolution"), ("scope", "action evaluation"),
        ("gamma_failures", "gamma validation"), ("gamma", "gamma validation"),
    )
    for key, stage in order:
        if trace_before.get(key) != trace_after.get(key):
            return stage
    return "none"
