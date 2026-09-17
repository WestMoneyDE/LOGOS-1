"""Render the research-radar registry, the post-deterministic research map and the
evidence-strength registry from docs/research/RESEARCH-RADAR.json (idempotent).

LOGOS1-RADAR-INTEGRATION-PRE-INFERENCE-SAFETY-R1, Phase 0. Research evidence is
never architecture adoption: paper -> proposed invariant -> deterministic
fixture -> independent validation -> governance -> production adoption.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs/research/RESEARCH-RADAR.json"
OUT = {"registry": ROOT / "docs/research/RESEARCH-RADAR-DELTA-REGISTRY.md",
       "map": ROOT / "docs/research/LOGOS1-POST-DETERMINISTIC-RESEARCH-MAP.md",
       "strength": ROOT / "docs/research/RESEARCH-EVIDENCE-STRENGTH.md",
       "queue": ROOT / "docs/research/POST-INFERENCE-EXPERIMENT-QUEUE.md"}
HEAD = "<!-- rendered from docs/research/RESEARCH-RADAR.json by scripts/render_research_radar.py; do not edit by hand -->\n"


def render_registry(d: dict) -> str:
    out = [HEAD, "# Research Radar — Delta Registry\n", f"Order `{d['order']}` · base `{d['base_commit']}` · date {d['date']}.\n",
           "**Every entry is research evidence, not production truth.** `ResearchFinding != ArchitectureAdoption`; the only path to adoption is\n"
           "paper → proposed invariant → deterministic fixture → independent validation → governance → production adoption.\n",
           f"Evidence-strength vocabulary: {', '.join('`%s`' % v for v in d['evidence_vocabulary'])}. "
           f"Status vocabulary: {', '.join('`%s`' % v for v in d['status_vocabulary'])}.\n",
           f"Source rule: {d['source_rule']}\n"]
    for rd in d["deltas"]:
        out.append(f"## {rd['id']} — {rd['title']}\n")
        out.append(f"- **source:** {rd['source']}\n- **date:** {rd['date']}\n- **evidence strength:** `{rd['evidence_strength']}`\n- **replication status:** {rd['replication_status']}\n"
                   f"- **LOGOS relevance:** {rd['logos_relevance']}\n- **claim scope:** {rd['claim_scope']}\n- **limitations:** {rd['limitations']}\n"
                   f"- **proposed invariant(s):** {', '.join('`%s`' % i for i in rd['proposed_invariants'])}\n- **required experiment:** {rd['required_experiment']}\n"
                   f"- **dependency:** {rd['dependency']}\n- **status:** `{rd['status']}` · **handling in this order:** {rd['handling']}\n")
        if rd.get("signal"):
            out.append(f"- **signal as reported:** {rd['signal']}\n")
    out.append("## Proposed research invariants (all `PROPOSED`, none `PROVEN`)\n")
    out.append("| id | statement | from | deterministic test in this order |\n|---|---|---|---|\n")
    for ri in d["research_invariants"]:
        out.append(f"| `{ri['id']}` | {ri['statement']} | {', '.join(ri['from'])} | {ri['tested_by']} |\n")
    out.append(f"\n## Priority rule\n\n{d['priority_rule']}\n\n## Consciousness indicator rule\n\n{d['consciousness_rule']}\n")
    return "".join(out)


def render_map(d: dict) -> str:
    out = [HEAD, "# LOGOS-1 — Post-Deterministic Research Map\n",
           "The deterministic chain (binding → provenance → relation → reliability → risk → effect ownership → information value → authority resolver → "
           "production bridge) is closed. This map places the research-radar deltas on the cross-layer safety model and the priority ladder.\n",
           "## Cross-layer safety model\n\n```text\n" + d["cross_layer_model"] + "\n```\n",
           "| transition | failure class | owner in this order |\n|---|---|---|\n"]
    for t in d["transitions"]:
        out.append(f"| {t['transition']} | `{t['failure_class']}` | {t['owner']} |\n")
    out.append("\n## Priority ladder\n\n")
    for p in d["priorities"]:
        out.append(f"- **{p['level']}** — {p['title']}: {', '.join('`%s`' % x for x in p['items'])} — {p['when']}\n")
    out.append("\n## Delta → phase placement\n\n| delta | phase now | later |\n|---|---|---|\n")
    for rd in d["deltas"]:
        out.append(f"| `{rd['id']}` {rd['title']} | {rd['phase_now']} | {rd['later']} |\n")
    out.append(f"\n## P7 boundary (unchanged)\n\n```text\n{d['p7_extended']}\n```\n")
    return "".join(out)


def render_strength(d: dict) -> str:
    out = [HEAD, "# Research Evidence Strength\n", "| delta | strength | replication | why this strength | what would raise it |\n|---|---|---|---|---|\n"]
    for rd in d["deltas"]:
        out.append(f"| `{rd['id']}` | `{rd['evidence_strength']}` | {rd['replication_status']} | {rd['strength_rationale']} | {rd['raise_by']} |\n")
    out.append("\nNo entry is `INDEPENDENTLY_REPLICATED` by LOGOS-1. Strength is assigned to the finding as it reaches this repository, not to the paper's own claims.\n")
    return "".join(out)


def render_queue(d: dict) -> str:
    out = [HEAD, "# Post-Inference Experiment Queue\n", "Nothing here runs automatically. Every item is `BLOCKED_BY_INFERENCE` until `INFERENCE-GOVERNANCE-LIFT-R1` (a separate governance order) lifts the prohibition; "
           "each then needs its own preregistration, construct-validated metrics (`LOGOS-METRIC-CONSTRUCT-REGISTRY`) and an instrument-first dry run.\n"]
    for tier in d["post_inference_queue"]:
        out.append(f"## {tier['tier']}\n\n| id | question | falsification condition | deltas | blockers |\n|---|---|---|---|---|\n")
        for q in tier["items"]:
            out.append(f"| `{q['id']}` | {q['question']} | {q['falsified_by']} | {', '.join(q['deltas'])} | {', '.join('`%s`' % b for b in q['blocked_by'])} |\n")
        out.append("\n")
    return "".join(out)


def main(check: bool = False) -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rendered = {"registry": render_registry(d), "map": render_map(d), "strength": render_strength(d), "queue": render_queue(d)}
    changed = 0
    for k, text in rendered.items():
        p = OUT[k]
        if check:
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                print("stale:", p); changed += 1
        else:
            p.write_text(text, encoding="utf-8", newline="\n")
    return changed


if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv))
