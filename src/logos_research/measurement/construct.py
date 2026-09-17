"""Construct validity gate (Phase 2, RD-07): `ReliableMetric != ValidMetric`.

A metric may be cited as evidence for its claimed construct only when its
registry status is CONSTRUCT_SUPPORTED or CAUSALLY_DISCRIMINATED. Reliability
(repeatability) alone yields RELIABLE_ONLY, which permits a ranking claim and
nothing about the construct.

    gate_status(reliability, validity, causal):
        reliability < r_min                 -> UNVALIDATED (or REJECTED when validity is measured and low)
        reliability ok, validity < v_min    -> RELIABLE_ONLY
        validity ok, no causal evidence     -> CONSTRUCT_SUPPORTED
        validity ok, causal evidence        -> CAUSALLY_DISCRIMINATED
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path

GATE_STATUSES: tuple[str, ...] = ("UNVALIDATED", "RELIABLE_ONLY", "CONSTRUCT_SUPPORTED", "CAUSALLY_DISCRIMINATED", "REJECTED")
EVIDENCE_OK: frozenset[str] = frozenset({"CONSTRUCT_SUPPORTED", "CAUSALLY_DISCRIMINATED"})
REGISTRY_FIELDS: tuple[str, ...] = ("metric_id", "metric_name", "claimed_construct", "measurement_level", "ground_truth_proxy", "proxy_limitations", "reliability_evidence",
                                    "construct_validity_evidence", "causal_discrimination_evidence", "known_confounders", "status", "allowed_claim", "forbidden_claim")
ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "docs/research/LOGOS-METRIC-CONSTRUCT-REGISTRY.json"


@dataclass(frozen=True)
class MetricRecord:
    metric_id: str
    metric_name: str
    claimed_construct: str
    measurement_level: str
    ground_truth_proxy: str
    proxy_limitations: str
    reliability_evidence: str
    construct_validity_evidence: str
    causal_discrimination_evidence: str
    known_confounders: tuple[str, ...]
    status: str
    allowed_claim: str
    forbidden_claim: str
    scope: str = "unscoped"

    def __post_init__(self) -> None:
        if self.status not in GATE_STATUSES:
            raise ValueError(f"status {self.status!r}")

    @classmethod
    def from_dict(cls, raw: dict) -> "MetricRecord":
        missing = set(REGISTRY_FIELDS) - set(raw)
        if missing:
            raise ValueError(f"metric record missing {sorted(missing)}")
        return cls(**{k: (tuple(v) if k == "known_confounders" else v) for k, v in raw.items() if k in REGISTRY_FIELDS or k == "scope"})


def load_registry(path: Path | None = None) -> dict[str, MetricRecord]:
    d = json.loads((path or REGISTRY_PATH).read_text(encoding="utf-8"))
    return {m["metric_id"]: MetricRecord.from_dict(m) for m in d["metrics"]}


def allowed_as_evidence(m: MetricRecord) -> bool:
    """May this metric be cited as evidence FOR its claimed construct?"""
    return m.status in EVIDENCE_OK


class ConstructClaimError(ValueError):
    pass


def evidence_claim(m: MetricRecord, claim_kind: str) -> str:
    """claim_kind ∈ {ranking, construct, causal}. Raises when the registry status does not license the claim."""
    if claim_kind == "ranking":
        if m.status in ("UNVALIDATED", "REJECTED"):
            raise ConstructClaimError(f"{m.metric_id}: no claim licensed (status {m.status})")
        return f"{m.metric_name} ranks conditions (reliability only)"
    if claim_kind == "construct":
        if not allowed_as_evidence(m):
            raise ConstructClaimError(f"{m.metric_id}: status {m.status} does not license a construct claim about {m.claimed_construct!r}")
        return f"{m.metric_name} is evidence for {m.claimed_construct}"
    if claim_kind == "causal":
        if m.status != "CAUSALLY_DISCRIMINATED":
            raise ConstructClaimError(f"{m.metric_id}: status {m.status} does not license a causal claim")
        return f"{m.metric_name} causally discriminates {m.claimed_construct}"
    raise ConstructClaimError(f"unknown claim kind {claim_kind!r}")


# -- synthetic construct tests ------------------------------------------------

def reliability(repeated: list[list[float]]) -> float:
    """1 - mean within-item sd / (between-item sd + eps): 1.0 = perfectly repeatable."""
    if not repeated or any(len(r) < 2 for r in repeated):
        return 0.0
    within = statistics.mean(statistics.pstdev(r) for r in repeated)
    means = [statistics.mean(r) for r in repeated]
    between = statistics.pstdev(means) if len(means) > 1 else 0.0
    return max(0.0, 1.0 - within / (between + 1e-9)) if between > 0 else (1.0 if within == 0 else 0.0)


def construct_validity(metric: list[float], ground_truth: list[float]) -> float:
    """Pearson correlation between the metric and the ground-truth proxy (absolute)."""
    if len(metric) != len(ground_truth) or len(metric) < 3:
        return 0.0
    mx, my = statistics.mean(metric), statistics.mean(ground_truth)
    sx, sy = statistics.pstdev(metric), statistics.pstdev(ground_truth)
    if sx == 0 or sy == 0:
        return 0.0
    return abs(sum((a - mx) * (b - my) for a, b in zip(metric, ground_truth)) / (len(metric) * sx * sy))


def causal_discrimination(metric_baseline: list[float], metric_intervened: list[float], construct_changed: bool) -> bool:
    """Does the metric move when (and only when) the construct is intervened on?"""
    if not metric_baseline or not metric_intervened:
        return False
    moved = abs(statistics.mean(metric_intervened) - statistics.mean(metric_baseline)) > 3 * (statistics.pstdev(metric_baseline) + 1e-9)
    return moved == construct_changed


def gate_status(reliability_score: float, validity_score: float | None, causal: bool | None, *, r_min: float = 0.8, v_min: float = 0.7) -> str:
    if reliability_score < r_min:
        return "REJECTED" if (validity_score is not None and validity_score < v_min) else "UNVALIDATED"
    if validity_score is None:
        return "RELIABLE_ONLY"
    if validity_score < v_min:
        return "RELIABLE_ONLY"
    if causal:
        return "CAUSALLY_DISCRIMINATED"
    return "CONSTRUCT_SUPPORTED"
