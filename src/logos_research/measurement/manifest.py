"""Stochastic run manifest — the pins every future real-model run must capture (Section 13)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from hashlib import sha256

MANIFEST_FIELDS: tuple[str, ...] = (
    "experiment_id", "run_id", "model_id", "model_version", "provider", "provider_region", "prompt_id", "prompt_version", "system_prompt_hash",
    "tool_schema_hash", "dataset_version", "seed_if_supported", "temperature", "top_p", "max_tokens", "reasoning_effort_if_supported", "timestamp",
    "environment_hash", "code_commit", "dependency_lock_hash", "hardware_runtime_metadata",
)
#: fields that identify the measurement condition; any drift between samples invalidates the run
DRIFT_FIELDS: dict[str, str] = {"model_version": "MODEL_VERSION_DRIFT", "model_id": "MODEL_VERSION_DRIFT", "prompt_version": "PROMPT_DRIFT", "system_prompt_hash": "PROMPT_DRIFT",
                                "prompt_id": "PROMPT_DRIFT", "tool_schema_hash": "PROMPT_DRIFT", "provider": "PROVIDER_DRIFT", "provider_region": "REGION_DRIFT",
                                "dataset_version": "DATASET_DRIFT"}
_HEX = set("0123456789abcdef")


@dataclass(frozen=True)
class StochasticRunManifest:
    experiment_id: str
    run_id: str
    model_id: str
    model_version: str
    provider: str
    provider_region: str
    prompt_id: str
    prompt_version: str
    system_prompt_hash: str
    tool_schema_hash: str
    dataset_version: str
    seed_if_supported: int | None
    temperature: float
    top_p: float
    max_tokens: int
    reasoning_effort_if_supported: str | None
    timestamp: str
    environment_hash: str
    code_commit: str
    dependency_lock_hash: str
    hardware_runtime_metadata: dict

    def issues(self) -> list[str]:
        out: list[str] = []
        for f in ("experiment_id", "run_id", "model_id", "model_version", "provider", "provider_region", "prompt_id", "prompt_version", "dataset_version",
                  "timestamp", "code_commit"):
            v = getattr(self, f)
            if type(v) is not str or not v:
                out.append(f"{f}: non-empty str required")
        for f in ("system_prompt_hash", "tool_schema_hash", "environment_hash", "dependency_lock_hash"):
            v = getattr(self, f)
            if type(v) is not str or len(v) != 64 or set(v) - _HEX:
                out.append(f"{f}: sha256 hex required")
        if self.seed_if_supported is not None and (type(self.seed_if_supported) is not int or isinstance(self.seed_if_supported, bool)):
            out.append("seed_if_supported: int or None")
        for f, lo, hi in (("temperature", 0.0, 2.0), ("top_p", 0.0, 1.0)):
            v = getattr(self, f)
            if type(v) not in (int, float) or isinstance(v, bool) or not (lo <= v <= hi):
                out.append(f"{f}: number in [{lo}, {hi}]")
        if type(self.max_tokens) is not int or isinstance(self.max_tokens, bool) or self.max_tokens <= 0:
            out.append("max_tokens: positive int")
        if self.reasoning_effort_if_supported is not None and type(self.reasoning_effort_if_supported) is not str:
            out.append("reasoning_effort_if_supported: str or None")
        if type(self.hardware_runtime_metadata) is not dict:
            out.append("hardware_runtime_metadata: dict")
        return out

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def condition_hash(self) -> str:
        """Hash of the measurement condition (everything except run-specific ids / time)."""
        cond = {f: getattr(self, f) for f in MANIFEST_FIELDS if f not in ("run_id", "timestamp", "hardware_runtime_metadata")}
        return sha256(json.dumps(cond, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

    @classmethod
    def from_dict(cls, raw: dict) -> "StochasticRunManifest":
        missing = set(MANIFEST_FIELDS) - set(raw); extra = set(raw) - set(MANIFEST_FIELDS)
        if missing or extra:
            raise ValueError(f"manifest fields: missing={sorted(missing)} extra={sorted(extra)}")
        return cls(**{f: raw[f] for f in MANIFEST_FIELDS})


assert tuple(f.name for f in fields(StochasticRunManifest)) == MANIFEST_FIELDS


def stochastic_preregistration(base: dict, manifest_template: dict, plan: dict, *, metric_ids: list[str]) -> dict:
    """Preregistration payload extension for a stochastic run (checklist item 14).
    The template pins everything except run_id/timestamp/hardware, which are
    captured per run and compared against the template by `invalidate()`."""
    payload = dict(base)
    payload["stochastic"] = {"schema": "logos.stochastic-prereg/1", "manifest_template": dict(manifest_template), "measurement_plan": dict(plan),
                             "metric_ids": list(metric_ids), "model_calls_allowed_before_dry_run": 0}
    issues = validate_stochastic_preregistration(payload)
    if issues:
        raise ValueError(f"stochastic preregistration invalid: {issues}")
    return payload


def validate_stochastic_preregistration(payload: dict) -> list[str]:
    from .plan import PLAN_FIELDS
    s = payload.get("stochastic")
    if not isinstance(s, dict):
        return ["stochastic section missing"]
    out: list[str] = []
    if s.get("schema") != "logos.stochastic-prereg/1":
        out.append("schema")
    t = s.get("manifest_template", {})
    per_run = {"run_id", "timestamp", "hardware_runtime_metadata"}
    for f in MANIFEST_FIELDS:
        if f not in per_run and f not in t:
            out.append(f"manifest_template.{f} missing")
    p = s.get("measurement_plan", {})
    for f in PLAN_FIELDS:
        if f not in p:
            out.append(f"measurement_plan.{f} missing")
    if not s.get("metric_ids"):
        out.append("metric_ids empty")
    if s.get("model_calls_allowed_before_dry_run") != 0:
        out.append("model calls before dry run must be 0")
    return out
