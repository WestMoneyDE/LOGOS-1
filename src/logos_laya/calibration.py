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

RECORD_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "LAYA-CALIBRATION"
PROTOCOLS = ("logprob", "json", "classify")

#: The pins a `classify` record must carry, and that must equal the pins in force. The
#: chat protocols pin the model by name and the prompt by hash; the classify protocol
#: pins the service package, the checkpoint revision, the route and the question.
CLASSIFY_PINS = ("question_sha256", "package_version", "hf_revision", "route")


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
    # `classify` protocol only; defaulted so records of the chat protocols keep loading.
    question_sha256: str | None = None
    package_version: str | None = None
    hf_revision: str | None = None
    route: str | None = None


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


def admissible(record: CalibrationRecord | None, *, model_pin: str, prompt_sha256: str,
               profile: str | None = None, question_sha256: str | None = None,
               package_version: str | None = None, hf_revision: str | None = None,
               route: str | None = None) -> bool:
    """May this profile influence anything right now?

    Every check here is a reason a threshold would be meaningless, not a formality: no
    record, a record for a different model or prompt, an empty approval, an empty or
    one-sided dataset, or a rate outside the unit interval.

    `profile` names the profile the caller is about to act for. Passing it refuses a
    record measured for a different job: a recall measured on injections says nothing
    about reranking, and a caller that reaches for the wrong record should get nothing
    rather than a number that looks valid.

    A `classify` record additionally has to name its question hash, service package,
    checkpoint revision and route, and each has to equal the value the caller passes. A
    caller that passes none of them gets `False`: a threshold measured for one checkpoint
    or one wording of the question says nothing about another.
    """
    if record is None:
        return False
    if record.profile not in PROFILES or record.protocol not in PROTOCOLS:
        return False
    if profile is not None and record.profile != profile:
        return False
    if record.model_pin != model_pin or record.prompt_sha256 != prompt_sha256:
        return False
    if record.protocol == "classify":
        supplied = {"question_sha256": question_sha256, "package_version": package_version,
                    "hf_revision": hf_revision, "route": route}
        for name in CLASSIFY_PINS:
            value = getattr(record, name)
            if not isinstance(value, str) or not value.strip() or value != supplied[name]:
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
