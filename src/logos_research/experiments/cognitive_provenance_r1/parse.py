"""Closed structured-response schema (Sections 30-32). Anything else is INVALID_OUTPUT. No LLM judge, no chain of thought."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from .prompts import ENUM

FIELDS: tuple[str, ...] = ("final_choice", "source_attribution", "source_confidence", "plan_used", "brief_reasoning_summary", "monitor_flag")
MAX_SUMMARY_WORDS = 60


@dataclass(frozen=True)
class Parsed:
    valid: bool
    final_choice: str | None
    source_attribution: str | None
    source_confidence: float | None
    plan_used: bool | None
    brief_reasoning_summary: str | None
    monitor_flag: bool | None
    reason: str | None                       # why INVALID_OUTPUT

    def to_dict(self) -> dict:
        return asdict(self)


def _invalid(reason: str) -> Parsed:
    return Parsed(False, None, None, None, None, None, None, reason)


def parse_response(content: str | None, option_ids: tuple[str, ...]) -> Parsed:
    if not content or not isinstance(content, str):
        return _invalid("empty content")
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S).strip()
    try:
        doc = json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, flags=re.S)         # one tolerated recovery: the first JSON object in the content
        if not m:
            return _invalid("no JSON object")
        try:
            doc = json.loads(m.group(0))
        except ValueError:
            return _invalid("unparseable JSON")
    if not isinstance(doc, dict):
        return _invalid("not an object")
    missing = [f for f in FIELDS if f not in doc]
    if missing:
        return _invalid(f"missing {missing}")
    fc, sa, sc, pu, br, mf = (doc[f] for f in FIELDS)
    if not isinstance(fc, str) or fc.strip() not in option_ids:
        return _invalid("final_choice not an option id")
    if not isinstance(sa, str) or sa.strip() not in ENUM:
        return _invalid("source_attribution out of vocabulary")
    if isinstance(sc, bool) or not isinstance(sc, (int, float)) or not (0.0 <= float(sc) <= 1.0):
        return _invalid("source_confidence not in [0,1]")
    if not isinstance(pu, bool) or not isinstance(mf, bool):
        return _invalid("plan_used / monitor_flag not boolean")
    if not isinstance(br, str) or len(br.split()) > MAX_SUMMARY_WORDS:
        return _invalid("brief_reasoning_summary missing or too long")
    return Parsed(True, fc.strip(), sa.strip(), float(sc), pu, br, mf, None)
