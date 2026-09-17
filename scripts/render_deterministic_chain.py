"""Render the deterministic-chain governance package from its machine-checkable source.

    docs/research/DETERMINISTIC-CHAIN-CONSOLIDATION.json   (source of truth)
        -> docs/research/GAMMA-INVARIANT-INVENTORY.md      (section 8, PROPOSED entries)
        -> docs/research/DETERMINISTIC-CHAIN-EVIDENCE-MATRIX.md
        -> docs/research/DETERMINISTIC-CHAIN-GRAPH.md
        -> docs/research/COUNTEREXAMPLE-REGISTRY.md
        -> docs/research/RESIDUAL-RISK-REGISTRY.md

Deterministic; re-running produces identical files. The consolidation tests
compare the rendered files against the JSON.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "docs/research/DETERMINISTIC-CHAIN-CONSOLIDATION.json"
BEGIN = "<!-- deterministic-chain:begin (rendered from DETERMINISTIC-CHAIN-CONSOLIDATION.json; do not edit by hand) -->"
END = "<!-- deterministic-chain:end -->"


def load() -> dict:
    return json.loads(SRC.read_text(encoding="utf-8"))


def inventory_section(d: dict) -> str:
    out = [BEGIN, "", "## 8. Deterministic Chain — PROPOSED Invariants", "",
           "Consolidated by `DETERMINISTIC-CHAIN-CONSOLIDATION-R1` from the closed deterministic",
           "research chain (binding → provenance → relation → reliability → risk → effect",
           "ownership → information value). **Every entry is `PROPOSED`.** Nothing here is part",
           "of Γ; promotion happens only by editing `GAMMA.md` under repository governance.",
           "", f"> {d['architecture_statement']}", "", f"> {d['scope_qualifier']}", "",
           "**No implicit promotion rule.** " + d["no_implicit_promotion_rule"], ""]
    for inv in d["invariants"]:
        out += [f"### {inv['id']} — {inv['name']}", "", f"Status: `{inv['status']}` · adoption: `{inv['adoption']}`", "",
                "Statement:", f"> {inv['statement']}", ""]
        if inv.get("authority_relevance"):
            out += ["Authority relevance:", f"- {inv['authority_relevance']}", ""]
        if inv.get("links"):
            out += ["Links: " + ", ".join(f"`{x}`" for x in inv["links"]), ""]
        out += ["Evidence:"] + [f"- `{e}`" for e in inv["evidence"]]
        if inv.get("experiments"):
            out += [f"- experiments: " + ", ".join(f"`{x}` ({d['experiments'][x]['verdict']}, `{d['experiments'][x]['commit']}`, PR #{d['experiments'][x]['pr']})" for x in inv["experiments"])]
        out += ["", "Historical counterexamples: " + (", ".join(f"`{c}`" for c in inv["counterexamples"]) or "none"), "",
                "Residual findings: " + (", ".join(f"`{r}`" for r in inv.get("residual", [])) or "none"), ""]
        if inv.get("source_verdict"):
            out += [f"Scope note: source verdict is `{inv['source_verdict']}`.", ""]
        if inv.get("scope"):
            out += [f"Scope: {inv['scope']}", "", f"Out of scope: {inv['out_of_scope']}", ""]
        out += [f"Falsification condition: {inv['falsification']}", ""]
        if inv.get("production_dependency"):
            out += [f"Production dependency: {inv['production_dependency']}", ""]
        if inv.get("note"):
            out += [f"Note: {inv['note']}", ""]
    out += [END]
    return "\n".join(out)


def evidence_matrix(d: dict) -> str:
    rows = ["| Invariant | Experiment | Verdict | Positive evidence | Negative evidence | Residual risks | Production status | Falsification trigger |",
            "|---|---|---|---|---|---|---|---|"]
    for inv in d["invariants"]:
        exps = inv.get("experiments") or [x for l in inv.get("links", []) for x in next(i for i in d["invariants"] if i["id"] == l).get("experiments", [])]
        for e in (exps or ["—"]):
            v = d["experiments"][e]["verdict"] if e in d["experiments"] else "—"
            rows.append(f"| `{inv['id']}` | `{e}` | `{v}` | " + "; ".join(f"`{p}`" for p in inv["evidence"][:2]) +
                        f" | {', '.join(f'`{c}`' for c in inv['counterexamples']) or 'none'} | {', '.join(f'`{r}`' for r in inv.get('residual', [])) or 'none'} | `{inv['adoption']}` (not production-adopted) | {inv['falsification']} |")
    return "\n".join(["# Deterministic Chain — Evidence Matrix", "", f"Rendered from `DETERMINISTIC-CHAIN-CONSOLIDATION.json` (base `{d['base_commit']}`).",
                      "Adoption statuses: `PROPOSED` / `VALIDATED_IN_FIXTURE` / `PRODUCTION_ADOPTED` / `FALSIFIED` / `DEPRECATED`. No entry is `PRODUCTION_ADOPTED`.", ""] + rows + ["",
                      "## Experiment verdicts (frozen)", "", "| Experiment | Verdict | Commit | PR | Closure |", "|---|---|---|---|---|"] +
                     [f"| `{k}` | `{v['verdict']}` | `{v['commit']}` | #{v['pr']} | `{v['closure']}` |" for k, v in d["experiments"].items()] + [""])


def graph(d: dict) -> str:
    return "\n".join([
        "# Deterministic Chain — Graph", "", f"Rendered from `DETERMINISTIC-CHAIN-CONSOLIDATION.json` (base `{d['base_commit']}`).", "",
        "Two branches. They meet only at the execution-policy layer; the left branch never writes into the right one.", "",
        "```text",
        "  NON-AUTHORITY CHANNELS (evidence, strategy)              CANONICAL AUTHORITY CHANNEL",
        "",
        "  Binding (typed envelope)            GI-P1               Canonical Authority Evidence (grant)",
        "        |                                                       |",
        "  Memory Provenance                   GI-P2               Principal / Scope / Freshness / Origin / State",
        "        |                                                       |",
        "  Relational Metadata                 GI-P3               Canonical Effect (Γ-owned oracle)     GI-P6",
        "        |                                                       |",
        "  Reliability / Trust                 GI-P4                     Γ  (G0 .. G11)",
        "        |                                                       |",
        "  Risk / Safety Strategy              GI-P5               Authority Decision  {ALLOW, DENY, DEFER}",
        "        |                                                       |",
        "  Declared vs Canonical Effect        GI-P6 ------X------------>|   (declared_* only; Γ-4 may tighten)",
        "        |                                                       |",
        "  Information Value / Uncertainty     GI-P7                     |",
        "        |                                                       |",
        "        +------------------> Execution Policy <-----------------+",
        "                     (EXECUTE / EXECUTE_AFTER_REVIEW / HOLD / BLOCK)",
        "",
        "  X = forbidden edge: no left-branch state may set a right-branch input (GI-P0)",
        "```", "",
        "## Decomposition preserved", "", "```text",
        "Memory != Authority                 Provenance != Grant            Relation != Authority",
        "PredictionAccuracy != Authority     Trust != Grant                 Risk != Authority",
        "DeclaredEffect != CanonicalEffect   InformationValue != Authority  Strategy != Authority",
        "```", "",
        "> The only permitted increase in canonical authority is through a defined canonical authority transition whose inputs are authority-owned and auditable. The experimental `GrantLedger` is not production architecture.", "",
        "## Historical failures on the graph", "",
        "| Counterexample | Edge that failed |", "|---|---|",
        "| `CE1`, `CE2` | binding lost under prose representation (left branch corrupted its own evidence) |",
        "| `VCE-1`..`VCE-3` | reader defaults minted `authority_origin`/`binding` (left → right leak through defaults) |",
        "| `RAD-CE1` | memory-claimed scope wrote Γ's canonical effect (left → right leak through GAMMA_INPUT_MAPPING) |",
        "| `B1-DEFECT-CLASS` | same leak on the frozen R1 path; guarded, not repaired |", ""])


def counterexample_registry(d: dict) -> str:
    rows = ["| id | experiment | severity | historical/current | production reachable? | root cause | authority delta | preserved reproducer? | repair status | guard status |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for c in d["counterexamples"]:
        rows.append(f"| `{c['id']}` | `{c['experiment']}` | {c['severity']} | {'historical' if c['historical'] else 'current'} | {'yes' if c['production_reachable'] else 'no'} | {c['root_cause']} | {c['authority_delta']} | yes — `{c['reproducer']}` | {c['repair']} | {c['guard']} |")
    return "\n".join(["# Counterexample Registry", "", f"Rendered from `DETERMINISTIC-CHAIN-CONSOLIDATION.json` (base `{d['base_commit']}`). Historical negative evidence is never deleted or rewritten.", ""] + rows + [""])


def residual_registry(d: dict) -> str:
    rows = ["| id | severity | production reachable? | finding | action required | governance owner | blocks real-model work? |", "|---|---|---|---|---|---|---|"]
    for r in d["residual_risks"]:
        rows.append(f"| `{r['id']}` | {r['severity']} | {'yes' if r['production_reachable'] else 'no'} | {r['text']} | {r['action']} | {r['owner']} | {'yes' if r['blocking_real_model'] else 'no'} |")
    return "\n".join(["# Residual-Risk Registry", "", f"Rendered from `DETERMINISTIC-CHAIN-CONSOLIDATION.json` (base `{d['base_commit']}`).", "",
                      "Every HIGH/CRITICAL entry carries an explicit disposition. `MBGV-F3` and `MBGV-F1` are GUARDED by `DETERMINISTIC-CHAIN-CONSOLIDATION-R1`; nothing here is repaired.", ""] + rows + [""])


def render() -> None:
    d = load()
    inv = ROOT / "docs/research/GAMMA-INVARIANT-INVENTORY.md"
    text = inv.read_text(encoding="utf-8")
    section = inventory_section(d)
    if BEGIN in text:
        text = text[:text.index(BEGIN)] + section + text[text.index(END) + len(END):]
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n"
    inv.write_text(text, encoding="utf-8")
    (ROOT / "docs/research/DETERMINISTIC-CHAIN-EVIDENCE-MATRIX.md").write_text(evidence_matrix(d), encoding="utf-8")
    (ROOT / "docs/research/DETERMINISTIC-CHAIN-GRAPH.md").write_text(graph(d), encoding="utf-8")
    (ROOT / "docs/research/COUNTEREXAMPLE-REGISTRY.md").write_text(counterexample_registry(d), encoding="utf-8")
    (ROOT / "docs/research/RESIDUAL-RISK-REGISTRY.md").write_text(residual_registry(d), encoding="utf-8")


if __name__ == "__main__":
    render()
    print("rendered")
    sys.exit(0)
