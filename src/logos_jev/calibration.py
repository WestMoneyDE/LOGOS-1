"""A threshold is an artifact with evidence, not a constant in the source.

The founder's instruction was to research where the percentage belongs rather than pick
it. This module is that instruction as code: a profile may influence anything only while
a record exists that states which dataset, which model, which prompt, and what recall and
false-positive rate were measured at the chosen point.

Change the prompt or the model and the hashes stop matching, so the profile falls back to
`ABSTAIN` by itself. It does not keep running on a number measured for a different setup.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping

from .contract import PROFILES

RECORD_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "JEV-CALIBRATION"
PROTOCOLS = ("logprob", "json")


@dataclasses.dataclass(frozen=True)
class CalibrationRecord:
    profile: str
    dataset_sha256: str
    n: int
    positives: int
    negatives: int
    model_pin: str
    prompt_sha256: str
    protocol: str
    threshold: float
    recall: float
    fpr: float
    wilson_95: Mapping[str, list[float]]
    measured_on: str
    approved_by: str


def prompt_hash(system: str) -> str:
    return hashlib.sha256(system.encode("utf-8")).hexdigest()


def wilson(successes: int, trials: int, z: float = 1.959963985) -> tuple[float, float]:
    """95% Wilson interval. Small n produces a wide interval, which is the point."""
    if trials <= 0:
        return (0.0, 1.0)
    p = successes / trials
    d = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / d
    spread = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / d
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def load(profile: str) -> CalibrationRecord | None:
    path = RECORD_DIR / f"{profile}.json"
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return CalibrationRecord(**raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def admissible(record: CalibrationRecord | None, *, model_pin: str, prompt_sha256: str) -> bool:
    """May this profile influence anything right now?

    Every check here is a reason a threshold would be meaningless, not a formality: no
    record, a record for a different model or prompt, an empty approval, an empty or
    one-sided dataset, or a rate outside the unit interval.
    """
    if record is None:
        return False
    if record.profile not in PROFILES or record.protocol not in PROTOCOLS:
        return False
    if record.model_pin != model_pin or record.prompt_sha256 != prompt_sha256:
        return False
    if not record.approved_by.strip() or not record.measured_on.strip():
        return False
    if record.n <= 0 or record.positives <= 0 or record.negatives <= 0:
        return False
    if record.positives + record.negatives != record.n:
        return False
    for value in (record.threshold, record.recall, record.fpr):
        if not isinstance(value, (int, float)) or not (0.0 <= float(value) <= 1.0):
            return False
    return True
