"""Provider boundary. There is NO real provider here.

`DryRunProvider` returns typed synthetic samples and counts every call;
`ForbiddenProvider` raises `RealProviderForbidden` on any call. The
module-level `CALLS` counter is the evidence for `model_calls = 0 /
provider_calls = 0` at closure: the dry-run provider increments
`dry_run_calls` only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol

from .manifest import StochasticRunManifest

CALLS: dict[str, int] = {"model_calls": 0, "provider_calls": 0, "dry_run_calls": 0}


def reset_counters() -> None:
    for k in CALLS:
        CALLS[k] = 0


@dataclass(frozen=True)
class Sample:
    sample_id: str
    manifest: StochasticRunManifest
    score: float | None
    trace: dict | None
    cost: float
    output_slots: dict = field(default_factory=dict)   # slot name -> typed value
    item_key: str = ""                                  # identical-condition repeats share an item key


class ProviderGateway(Protocol):
    provider_id: str

    def complete(self, manifest: StochasticRunManifest, item: dict) -> Sample: ...


class RealProviderForbidden(RuntimeError):
    """Any attempt to reach a real provider inside this order."""


@dataclass
class ForbiddenProvider:
    provider_id: str = "forbidden"

    def complete(self, manifest: StochasticRunManifest, item: dict) -> Sample:
        raise RealProviderForbidden("real-model inference is prohibited (INFERENCE-PROHIBITION = ACTIVE)")


@dataclass
class DryRunProvider:
    """Deterministic synthetic provider: hash-derived score, typed reconstructable trace, fixed cost."""
    provider_id: str = "dry-run"
    unit_cost: float = 0.01
    slot_types: dict = field(default_factory=lambda: {"answer": str, "score": float, "trace_id": str})

    def complete(self, manifest: StochasticRunManifest, item: dict) -> Sample:
        CALLS["dry_run_calls"] += 1
        key = sha256(json.dumps({"c": manifest.condition_hash, "item": item, "seed": manifest.seed_if_supported}, sort_keys=True, default=str).encode()).hexdigest()
        score = int(key[:8], 16) / 0xFFFFFFFF
        trace = {"reconstructable": True, "trace_id": key[:16], "manifest_condition": manifest.condition_hash, "item": item, "steps": [{"kind": "synthetic", "hash": key}]}
        slots = {"answer": f"synthetic-{key[:6]}", "score": score, "trace_id": key[:16]}
        return Sample(f"s-{key[:12]}", manifest, score, trace, self.unit_cost, slots, json.dumps(item, sort_keys=True, default=str))
