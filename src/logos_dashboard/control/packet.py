"""Thesis packet (spec §5): the prompt for a `thesis_advance` / `prior_art` agent job and the result contract `ros-agent-result/1`.

The packet tells the agent exactly what it may write (files under its thesis directory), what it may propose (one lifecycle event, applied with actor `agent`),
and that it must never edit registries, run inference experiments or claim verdicts. The agent decides itself whether prior art is needed
(heuristic in the packet: < 3 citations for the track or none for the claim) and signals it via `needs_prior_art`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

RESULT_SCHEMA = "ros-agent-result/1"
THESIS_DIR = "docs/research/dashboard/theses"
BRIEFS_DIR = "docs/research/dashboard/research-briefs"
AGENT_EVENTS_BY_STATE = {"IDEA": ["triage"], "TRIAGE": ["start_prior_art", "define_question"], "PRIOR_ART": ["define_question"], "QUESTION_DEFINED": ["define_hypothesis"], "HYPOTHESIS_DEFINED": ["define_metrics"], "METRICS_DEFINED": ["draft_prereg"], "PREREG_DRAFT": []}
STAGE_DELIVERABLE = {"IDEA": "TRIAGE.md (why this thesis, which claims, which track, what would falsify it in one paragraph)", "TRIAGE": "PRIOR-ART.md (closest prior art; or a justified 'not needed' note) — decide needs_prior_art",
                     "PRIOR_ART": "QUESTION.md (one scientific question, scope, out-of-scope)", "QUESTION_DEFINED": "HYPOTHESES.md (H0/H1, directional predictions, alternative mechanisms)",
                     "HYPOTHESIS_DEFINED": "METRICS.md (metric ids, ground-truth mapping, statistics: Wilson/Newcombe/bootstrap, N, effect size, stopping rules)",
                     "METRICS_DEFINED": "PREREG-DRAFT.json + WORK-ORDER-DRAFT.md (all §12 mandatory fields; founder gates listed; caps; deterministic tests to add)"}
ALLOWED_TOOLS_ADVANCE = ("Read", "Write", "Edit", "Glob", "Grep")
ALLOWED_TOOLS_PRIOR_ART = ("Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "Skill")
DISALLOWED_TOOLS = ("Bash", "NotebookEdit", "Agent", "Task")


@dataclass(frozen=True)
class AgentResult:
    proposed_event: str | None
    files: tuple[str, ...]
    needs_prior_art: bool
    summary: str
    uncertainties: tuple[str, ...] = field(default_factory=tuple)
    raw: dict | None = None


def thesis_dir(thesis_id: str) -> str:
    return f"{THESIS_DIR}/{thesis_id}"


def build_thesis_packet(detail: dict, regs: dict, notes: list[dict], prior_art_count: int, *, kind: str = "thesis_advance", brief_task: dict | None = None) -> dict:
    th = detail["thesis"]; state = th["state"]
    claims = [c for c in regs["claims"]["claims"] if c["claim_id"] in th["claim_ids"]]
    track = regs["claims"]["tracks"].get(th["track"], {})
    events = AGENT_EVENTS_BY_STATE.get(state, [])
    allowed_dir = thesis_dir(th["thesis_id"])
    lines = [f"# LOGOS-1 thesis packet — {th['thesis_id']} ({kind})", "",
             f"Thesis: {th['title']}", f"Track: {th['track']} — {track.get('title', '')}: {track.get('question', '')}", f"Lifecycle state: {state}. Agent ceiling: {detail['agent_ceiling']}.", ""]
    for c in claims:
        lines += [f"## Claim {c['claim_id']} — {c['title']}", f"Statement: {c['statement']}", f"Status: {c['status']} (status ≠ evidence strength) · strength: {c['evidence_strength']} · scope: {c['scope']}",
                  f"Falsification test: {c['falsification_test']}", f"Next falsification test: {c['next_falsification_test'] or 'none named'}", f"Known limitations: {'; '.join(c['known_limitations']) or '—'}", ""]
    lines += [f"Prior-art citations recorded for track '{th['track']}': {prior_art_count} (heuristic: request prior art when < 3 for the track or none for the claim).", ""]
    if notes:
        lines += ["## Founder notes (must be addressed; quote them in your summary)"] + [f"- [#{n['note_id']}{' ⚑ decision' if n['decision_flag'] else ''}] {n['text']}" for n in notes] + [""]
    if kind == "prior_art":
        lines += ["## Task", f"Produce a research brief for the closest prior art using the project skill `.claude/skills/logos-prior-art-research/SKILL.md` (deep-research; web tools allowed).",
                  f"Write exactly one JSON brief to `{BRIEFS_DIR}/{th['thesis_id']}-{(brief_task or {}).get('task_id', 'PRIOR-ART')}.json` following BRIEF_SCHEMA (`logos.research-brief/1`), `reviewed_by_founder: false`, novelty never above CLEAR_DIFFERENTIATION.",
                  f"Also write `{allowed_dir}/PRIOR-ART.md` (summary, ≤ 1 page)."]
        events = ["define_question"] if state in ("PRIOR_ART", "TRIAGE") else []
    else:
        lines += ["## Task", f"Advance this thesis by exactly one lifecycle stage. Deliverable for state {state}: {STAGE_DELIVERABLE.get(state, 'nothing — the agent ceiling is reached; write NOTES.md only')}.",
                  f"Read what already exists under `{allowed_dir}/` and build on it; never contradict a registry record — cite it by path instead."]
    lines += ["", "## Rules (hard)", f"1. Write only under `{allowed_dir}/`" + (f" and `{BRIEFS_DIR}/`" if kind == "prior_art" else "") + ". Any other file change fails the job (INTEGRITY_VIOLATION).",
              "2. Never edit registries (docs/research/dashboard/*.json), preregistrations, closures, GAMMA.md, src/logos_gamma, P7 material. Never run experiments or inference. Never claim a verdict.",
              "3. Status vocabulary stays English; do not upgrade any claim status or evidence strength.",
              f"4. Propose at most one lifecycle event from: {events or ['none']}. Founder gates (freeze_prereg, approve_work_order, ready_to_run) cannot be proposed.",
              "5. Set needs_prior_art=true only if the heuristic above applies and no PRIOR-ART.md exists yet.",
              "", "## Result (mandatory, last thing in your answer)", "Return one fenced JSON block:", "```json",
              json.dumps({"schema": RESULT_SCHEMA, "proposed_event": events[0] if events else None, "files": [f"{allowed_dir}/EXAMPLE.md"], "needs_prior_art": False, "summary": "one paragraph", "uncertainties": ["..."]}, indent=1), "```"]
    return {"prompt": "\n".join(lines), "system": "You are a research agent inside LOGOS-1. You draft; you never approve, freeze, publish or run inference. Cite repository records by path.",
            "allowed_tools": ALLOWED_TOOLS_PRIOR_ART if kind == "prior_art" else ALLOWED_TOOLS_ADVANCE, "disallowed_tools": DISALLOWED_TOOLS,
            "allowed_prefixes": (allowed_dir + "/",) + ((BRIEFS_DIR + "/",) if kind == "prior_art" else ()), "allowed_events": events, "state": state, "thesis_id": th["thesis_id"]}


_FENCE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


def parse_agent_result(text: str | None) -> AgentResult | None:
    if not text:
        return None
    m = None
    for m in _FENCE.finditer(text):
        pass
    cand = m.group(1) if m else text.strip()
    try:
        d = json.loads(cand)
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("schema") != RESULT_SCHEMA:
        return None
    ev = d.get("proposed_event"); files = d.get("files") or []
    if ev is not None and not isinstance(ev, str):
        return None
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        return None
    return AgentResult(ev, tuple(files), bool(d.get("needs_prior_art")), str(d.get("summary", "")), tuple(str(u) for u in (d.get("uncertainties") or [])), d)


RADAR_DIR = "docs/research/dashboard/radar"


def build_radar_packet(item: dict, regs: dict) -> dict:
    """AI_PROPOSAL for a radar item (§40): the agent writes exactly one PROPOSAL.json under the radar directory; the founder still reviews."""
    p = item["payload"]; rid = item["radar_id"]; allowed_dir = f"{RADAR_DIR}/{rid}"
    lines = [f"# LOGOS-1 radar packet — item {rid} ({p['kind']})", "", "## Input", p["text"], f"Source: {p.get('source') or '—'}", "", "## Deterministic analysis (already done)", json.dumps({k: p.get(k) for k in ("parsed", "dedup", "source", "track_map", "claim_impact", "evidence", "action")}, indent=1, default=str)[:6000], "",
             "## Task", f"Write `{allowed_dir}/PROPOSAL.json` with schema `logos.radar-ai-proposal/1`: {{delta_kind (work_order|prior_art|open_question|claim_note|invariant_note|none), BEFORE, PROPOSED, EVIDENCE, WHY, WHAT_WOULD_FALSIFY_IT, impacted_claims, track, confidence (low|medium|high), caveats}}.",
             "Cite registry records by path. Never edit registries. Never claim a verdict or change a status/strength.", "", "## Result (mandatory, last)", "```json", json.dumps({"schema": RESULT_SCHEMA, "proposed_event": None, "files": [f"{allowed_dir}/PROPOSAL.json"], "needs_prior_art": False, "summary": "one paragraph", "uncertainties": []}, indent=1), "```"]
    return {"prompt": "\n".join(lines), "system": "You are a research-radar analyst inside LOGOS-1. You propose deltas; the founder decides.", "allowed_tools": ALLOWED_TOOLS_ADVANCE, "disallowed_tools": DISALLOWED_TOOLS, "allowed_prefixes": (allowed_dir + "/",), "allowed_events": [], "state": item["state"], "thesis_id": None, "radar_id": rid}
