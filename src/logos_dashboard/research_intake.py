"""Deep-research intake for the dashboard (related work / novelty / external validation).

Workflow (see .claude/skills/logos-prior-art-research/SKILL.md):
    1. `queue()` derives research tasks from the claim registry (claims whose track lacks related work, citations with novelty UNKNOWN,
       open questions that need external evidence).
    2. The `deep-research` skill (firecrawl/exa MCPs; WebSearch/WebFetch fallback) produces a brief JSON in
       docs/research/dashboard/research-briefs/ following BRIEF_SCHEMA — never touching the registries.
    3. After founder review, `merge_brief()` validates the brief and appends its citations to PRIOR-ART-REGISTRY.json.
       Novelty can never be set to STRONG_NOVELTY_EVIDENCE by a merge; CLEAR_DIFFERENTIATION needs >= 3 sources and an explicit differentiation.
No model call happens in this module.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .registries import DASH, FILES, load_all

BRIEFS = DASH / "research-briefs"
BRIEF_SCHEMA = {"schema": "logos.research-brief/1", "required": ["brief_id", "date", "claim_id", "question", "sub_questions", "sources", "synthesis", "novelty_assessment", "limitations", "reviewed_by_founder"],
                "source_fields": ["citation_id", "title", "authors", "year", "venue", "url", "claim_supported", "claim_not_supported", "notes", "research_track", "novelty_status"],
                "novelty_vocabulary": ["UNKNOWN", "POSSIBLE_INCREMENTAL", "CLEAR_DIFFERENTIATION"]}
URL = re.compile(r"^https?://\S+$")


def queue(d: dict[str, dict] | None = None) -> list[dict]:
    d = d or load_all()
    tasks: list[dict] = []
    tracks = d["claims"]["tracks"]; pa = d["prior_art"]["citations"]
    per_track = {t: [c for c in pa if c["research_track"] == t] for t in tracks}
    for c in d["claims"]["claims"]:
        cits = per_track.get(c["track"], [])
        need = []
        if len(cits) < 3: need.append(f"related-work matrix for track '{c['track']}' has {len(cits)} citations (< 3)")
        if any(x["novelty_status"] == "UNKNOWN" for x in cits): need.append("novelty of the track's citations is UNKNOWN")
        if c["claim_type"] in ("hypothesis", "invariant") and c["status"] in ("SUPPORTED", "PARTIALLY_SUPPORTED", "FALSIFIED", "VALIDATED_IN_FIXTURE"):
            need.append("closest prior art for this specific claim not recorded")
        if need:
            tasks.append({"task_id": f"RQ-{c['claim_id']}", "claim_id": c["claim_id"], "track": c["track"], "title": c["title"], "question": f"What is the closest prior art to: {c['statement']}", "why": need,
                          "deliverable": "research brief JSON (BRIEF_SCHEMA) in docs/research/dashboard/research-briefs/", "priority": "HIGH" if c["publication_target"].startswith(("PAPER-2", "PAPER-3", "PAPER-5")) else "MEDIUM"})
    for q in d["open_questions"]["questions"]:
        if "external" in (q.get("missing", "") + q.get("current_evidence", "")).lower() or q["leverage"] == "HIGH":
            tasks.append({"task_id": f"RQ-{q['question_id']}", "claim_id": None, "track": q["track"], "title": q["question"], "question": q["question"], "why": ["open question with high leverage or missing external evidence"], "deliverable": "research brief JSON", "priority": q["leverage"]})
    return tasks


def briefs() -> list[dict]:
    if not BRIEFS.exists():
        return []
    out = []
    for p in sorted(BRIEFS.glob("*.json")):
        try:
            b = json.loads(p.read_text(encoding="utf-8")); b["_path"] = str(p.relative_to(DASH.parents[2])).replace("\\", "/"); out.append(b)
        except ValueError:
            out.append({"brief_id": p.name, "_path": str(p), "error": "invalid JSON"})
    return out


def validate_brief(b: dict) -> list[str]:
    out = [f"missing field {f}" for f in BRIEF_SCHEMA["required"] if f not in b]
    if b.get("schema") != BRIEF_SCHEMA["schema"]: out.append("schema")
    for i, s in enumerate(b.get("sources", [])):
        for f in BRIEF_SCHEMA["source_fields"]:
            if f not in s: out.append(f"source[{i}] missing {f}")
        if s.get("url") and not URL.match(s["url"]): out.append(f"source[{i}] url not a locator")
        if s.get("novelty_status") not in BRIEF_SCHEMA["novelty_vocabulary"]: out.append(f"source[{i}] novelty outside vocabulary (STRONG_NOVELTY_EVIDENCE is never set by a brief)")
    na = b.get("novelty_assessment", {})
    if isinstance(na, dict) and na.get("status") == "CLEAR_DIFFERENTIATION" and (len(b.get("sources", [])) < 3 or not na.get("differentiation")):
        out.append("CLEAR_DIFFERENTIATION needs >= 3 sources and an explicit differentiation statement")
    if not b.get("reviewed_by_founder"): out.append("brief not reviewed by the founder (reviewed_by_founder must be true before merge)")
    text = json.dumps(b, ensure_ascii=False).upper()
    for w in ("WE ARE THE FIRST", "WORLD-FIRST", "BREAKTHROUGH", "REVOLUTIONARY"):
        if w in text: out.append(f"forbidden phrase {w}")
    return out


def merge_brief(b: dict, *, write: bool = True) -> dict:
    issues = validate_brief(b)
    if issues:
        raise ValueError(issues)
    p = DASH / FILES["prior_art"]; reg = json.loads(p.read_text(encoding="utf-8"))
    have = {c["citation_id"] for c in reg["citations"]}; added = []
    for s in b["sources"]:
        if s["citation_id"] in have:
            continue
        entry = {k: s[k] for k in BRIEF_SCHEMA["source_fields"]}; entry["brief_id"] = b["brief_id"]; reg["citations"].append(entry); added.append(s["citation_id"])
    reg["count"] = len(reg["citations"]); reg["search_status"] = f"systematic search in progress via research briefs (last merge {date.today().isoformat()}, brief {b['brief_id']}); novelty remains at most CLEAR_DIFFERENTIATION"
    if write:
        p.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"added": added, "count": reg["count"]}
