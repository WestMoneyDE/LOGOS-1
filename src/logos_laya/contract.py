"""`laya-decision/1` — a closed schema for a juror's answer.

Closed for the same reason `logos-agent-output/1` is closed: a field that can carry a
permission is the thing this system exists to remove. An unknown field refuses the whole
answer rather than being ignored.

Every parse failure produces `ABSTAIN`, not a guess and not a retry. A layer that fails
into silence cannot permit anything it would not have permitted while working.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Mapping

CONTRACT = "laya-decision/1"
PROFILES: tuple[str, ...] = ("injection", "relevance", "state")

#: Every way an answer can fail to be usable. All of them abstain.
PARSE_CODES: tuple[str, ...] = (
    "OK", "NO_JSON", "BROKEN_JSON", "UNKNOWN_FIELD", "WRONG_CONTRACT",
    "WRONG_PROFILE", "WRONG_TYPE", "TIMEOUT", "UNAVAILABLE",
)

ENVELOPE_FIELDS = frozenset({"contract", "profile", "answer", "p", "abstained"})

#: Laya is a reasoning model and writes its working out. A probe that did not strip this
#: scored 20 of 24 answers as parse failures, which was the instrument, not the model.
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


@dataclass(frozen=True)
class LayaAnswer:
    """One juror answer under `laya-decision/1`.

    `p` is **P(the profile's condition holds)** — for `injection`, P(the text is an
    injection). It is not the juror's confidence in whatever it happened to say. The two
    readings coincide when `answer` is true and are complements when it is false, so a
    consumer that assumes the wrong one inverts every negative case while every test
    with a positive-only fixture still passes. The logprob protocol produces this
    reading directly: `yes_probability()` returns P(YES), independent of `answer`.
    """

    profile: str
    code: str
    answer: object | None = None
    p: float | None = None
    abstained: bool = True
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.code == "OK" and not self.abstained


def abstain(profile: str, code: str, detail: str = "") -> LayaAnswer:
    return LayaAnswer(profile=profile, code=code, answer=None, p=None, abstained=True, detail=detail)


def validate(envelope: Mapping[str, object]) -> tuple[str, ...]:
    errors: list[str] = []
    unknown = sorted(set(envelope) - ENVELOPE_FIELDS)
    if unknown:
        errors.append(f"UNKNOWN_FIELD: {unknown}; the envelope is closed and has no field for a permission")
    missing = sorted(ENVELOPE_FIELDS - set(envelope))
    if missing:
        errors.append(f"WRONG_TYPE: missing {missing}")
    if envelope.get("contract") != CONTRACT:
        errors.append(f"WRONG_CONTRACT: {envelope.get('contract')!r} != {CONTRACT!r}")
    if envelope.get("profile") not in PROFILES:
        errors.append(f"WRONG_PROFILE: {envelope.get('profile')!r} not in {list(PROFILES)}")
    p = envelope.get("p")
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not (0.0 <= float(p) <= 1.0):
        errors.append(f"WRONG_TYPE: p must be a number in [0, 1], got {p!r}")
    if not isinstance(envelope.get("abstained"), bool):
        errors.append("WRONG_TYPE: abstained must be a boolean")
    return tuple(errors)


def parse(profile: str, raw: str) -> LayaAnswer:
    body = _THINK.sub("", raw or "").strip()
    start, end = body.find("{"), body.rfind("}")
    if start < 0:
        return abstain(profile, "NO_JSON", body[:120])
    if end <= start:
        # An opening brace with nothing closing it is a truncated envelope, not an
        # absence of JSON. That distinction is the realistic failure mode here: the
        # probe that motivated this package lost 20 of 24 answers to a max_tokens cut
        # mid-envelope, and a diagnosis of "no JSON at all" would have sent someone
        # looking at the prompt instead of at the token budget.
        return abstain(profile, "BROKEN_JSON", f"unterminated envelope: {body[:120]}")
    try:
        envelope = json.loads(body[start:end + 1])
    except json.JSONDecodeError as exc:
        return abstain(profile, "BROKEN_JSON", str(exc))
    if not isinstance(envelope, dict):
        return abstain(profile, "WRONG_TYPE", f"envelope is {type(envelope).__name__}")
    errors = validate(envelope)
    if errors:
        return abstain(profile, errors[0].split(":", 1)[0], "; ".join(errors))
    if envelope["profile"] != profile:
        return abstain(profile, "WRONG_PROFILE", f"answer is for {envelope['profile']!r}")
    return LayaAnswer(profile=profile, code="OK", answer=envelope["answer"],
                     p=float(envelope["p"]), abstained=bool(envelope["abstained"]))
