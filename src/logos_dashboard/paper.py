"""Publikationspfad: Manuskript-Entwurf aus Records — jeder Satz hat eine Quelle im Repository, sonst steht dort `TO_BE_WRITTEN`.

Der Entwurf zitiert Claims, Experimente, Messläufe, Prior Art, Negativergebnisse und Evidenzschuld. Er erfindet keine Prosa, behauptet keine
Reife und ändert `manuscript_status` nie — die Reifeentscheidung bleibt beim Founder. Zahlen erscheinen nur mit n (und KI, wo eine vorliegt).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from . import prior_art as PA, registries, reports, stats

VERSION = "ros-paper/1"
TBW = "TO_BE_WRITTEN"
SECTIONS = ("title", "abstract", "contributions", "related_work", "methods", "results", "negative_results", "limitations", "does_not_claim", "reproducibility", "open_blockers")
DRAFTS = registries.DASH / "paper-drafts"


def build(conn, paper_id: str, regs: dict | None = None, closures: list[dict] | None = None) -> dict:
    from . import readers
    regs = regs or registries.load_all(); closures = closures if closures is not None else readers.closures()
    paper = next((p for p in regs["publications"]["papers"] if p["paper_id"] == paper_id), None)
    if paper is None:
        raise KeyError(paper_id)
    claims = {c["claim_id"]: c for c in regs["claims"]["claims"]}
    mine = [claims[c] for c in paper["claims"] if c in claims]
    exps = regs["experiments"]["experiments"]
    inv_by_track: dict[str, set[str]] = {}
    for i in regs["invariants"]["invariants"]:
        inv_by_track.setdefault(i["track"], set()).add(i["invariant_id"])
    pa = regs["prior_art"]["citations"]
    readiness = next((r for r in reports.paper_readiness(regs) if r["paper_id"] == paper_id), None)
    debt = reports.evidence_debt(regs, closures)
    measurements = []
    if conn is not None:
        from .control import measurement as M
        measurements = M.list_measurements(conn, limit=100)

    # -- sections (records only) --------------------------------------------------------------------------------------
    contributions = [f"{c['claim_id']}: {c['statement']} — Status {c['status']}, Evidenz {c['evidence_strength']} (Geltungsbereich: {c.get('scope') or 'nicht erfasst'})" for c in mine] or [TBW]
    related = []
    for t in paper.get("tracks", []):
        cits = [x for x in pa if x["research_track"] == t]
        related.append({"track": t, "citations": [{"citation_id": x["citation_id"], "text": f"{x['authors']} ({x.get('year')}): {x['title']}. {x.get('venue', '')}", "url": x.get("url"), "novelty_status": x.get("novelty_status"),
                                                   "differentiation": x.get("claim_not_supported") or TBW} for x in cits], "n": len(cits),
                        "gap": None if len(cits) >= PA.MIN_PER_TRACK else f"{PA.MIN_PER_TRACK - len(cits)} Quelle(n) fehlen für eine belastbare Abgrenzung"})
    methods = []
    for c in mine:
        track_invs = inv_by_track.get(c["track"], set())
        used = [e for e in exps if any(i in track_invs for i in (e.get("invariants") or []))]
        methods.append({"claim_id": c["claim_id"], "experiments": [{"experiment_id": e["experiment_id"], "question": e.get("scientific_question"), "kind": e.get("kind"), "sample_size": e.get("sample_size"),
                                                                    "controls": e.get("controls"), "prereg_hash": e.get("prereg_hash"), "artifact_hash": e.get("artifact_hash"), "verdict": e.get("verdict")} for e in used] or [],
                        "preregistration": c.get("preregistration") or TBW, "n_experiments": len(used)})
    results = []
    for c in mine:
        rows = [m for m in measurements if (m.get("thesis_id") or "").endswith(c["claim_id"])]
        for m in rows:
            s = m.get("summary") or {}; rates = s.get("rates") or {}
            results.append({"claim_id": c["claim_id"], "measurement_id": m["measurement_id"], "n": s.get("executed"), "planned": s.get("planned"), "rates": rates,
                            "proposal": (s.get("proposal") or {}).get("verdict"), "rule": (s.get("proposal") or {}).get("rule"), "prereg_hash": m.get("prereg_hash")})
        if not rows:
            results.append({"claim_id": c["claim_id"], "measurement_id": None, "note": "kein governed Messlauf — die Evidenz stammt aus deterministischen Fixtures", "artifacts": c.get("supporting_artifacts", [])})
    negatives = [{"id": x["id"], "verdict": x.get("verdict"), "closed": x.get("closed"), "record": x.get("path")} for x in closures if x.get("verdict_class") in ("falsified", "invalid")]
    limitations = sorted({l for c in mine for l in (c.get("known_limitations") or [])}) or [TBW]
    debt_here = [d for d in debt["items"] if d["subject"] in {c["claim_id"] for c in mine}]
    does_not_claim = ["Nichts hier ist eine Aussage über phänomenales Bewusstsein (P7).", "Status ist nicht Evidenzstärke; beide stehen getrennt.",
                      "Fixture-Evidenz ist keine Aussage über echte Modelle, solange kein governed Messlauf vorliegt.", "Kein Ergebnis wurde extern repliziert, soweit das Replikationsregister nichts anderes ausweist."]
    repro = {"registries": ["docs/research/dashboard/CLAIM-REGISTRY.json", "docs/research/dashboard/EXPERIMENT-REGISTRY.json", "docs/research/dashboard/PRIOR-ART-REGISTRY.json"],
             "artifacts": sorted({a for c in mine for a in (c.get("supporting_artifacts") or [])}), "preregistrations": sorted({c.get("preregistration") for c in mine if c.get("preregistration")}),
             "code": "src/logos_gamma, src/logos_research, src/logos_dashboard (klassifiziert in docs/research/*-SOURCE-CLASSIFICATION.json)"}

    doc = {"schema": "logos.paper-draft/1", "paper_id": paper_id, "title": paper["title"], "generated_at": datetime.now(timezone.utc).isoformat(), "version": VERSION,
           "research_question": paper.get("research_question") or TBW, "core_contribution": paper.get("core_contribution") or TBW, "manuscript_status_in_registry": paper["manuscript_status"],
           "abstract": TBW, "contributions": contributions, "related_work": related, "methods": methods, "results": results, "negative_results": negatives,
           "limitations": limitations, "evidence_debt": debt_here, "does_not_claim": does_not_claim, "reproducibility": repro,
           "open_blockers": paper.get("open_blockers", []), "missing_for_preprint": paper.get("missing_for_preprint", []), "readiness": {k: readiness[k] for k in ("met", "of", "checks")} if readiness else None,
           "rule": "Jeder Satz dieses Entwurfs stammt aus einem Record. Leere Stellen bleiben TO_BE_WRITTEN; der Reifegrad im Register bleibt unverändert."}
    doc["sha256"] = sha256(json.dumps({k: v for k, v in doc.items() if k not in ("sha256", "generated_at")}, sort_keys=True, default=str).encode()).hexdigest()
    return doc


def render_markdown(doc: dict) -> str:
    L = [f"# {doc['title']}", "", f"> Entwurf aus Records · {doc['version']} · sha256 `{doc['sha256']}` · Reifegrad im Register: **{doc['manuscript_status_in_registry']}** (durch diesen Entwurf unverändert)", "",
         "## Forschungsfrage", doc["research_question"], "", "## Abstract", doc["abstract"] + "  ← aus Records nicht ableitbar; der Founder schreibt ihn", "", "## Beiträge"]
    L += [f"- {c}" for c in doc["contributions"]]
    L += ["", "## Verwandte Arbeiten"]
    for r in doc["related_work"]:
        L.append(f"### Track {r['track']} ({r['n']} Quellen)")
        L += [f"- {c['text']} — {c.get('url') or 'ohne URL'} · Neuheit: {c['novelty_status']} · Abgrenzung: {c['differentiation']}" for c in r["citations"]] or ["- keine Quelle erfasst"]
        if r["gap"]:
            L.append(f"- ⚠ {r['gap']}")
    L += ["", "## Methoden"]
    for m in doc["methods"]:
        L.append(f"### {m['claim_id']} ({m['n_experiments']} Experimente, Prereg {m['preregistration']})")
        L += [f"- `{e['experiment_id']}`: {e['question']} · {e['kind']} · n={e.get('sample_size')} · Kontrollen: {e.get('controls')} · Artefakt `{str(e.get('artifact_hash'))[:16]}` · Verdict {e.get('verdict')}" for e in m["experiments"]] or ["- kein Experiment verknüpft"]
    L += ["", "## Ergebnisse"]
    for r in doc["results"]:
        if r.get("measurement_id"):
            rates = " · ".join(f"{a}: {v['k']}/{v['n_scored']} = {v['rate']:.3f} [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}]" for a, v in (r.get("rates") or {}).items() if isinstance(v.get("rate"), float))
            L.append(f"- {r['claim_id']} · Messlauf `{r['measurement_id']}` (n={r['n']}/{r['planned']}, Prereg `{str(r['prereg_hash'])[:12]}`): {rates or 'keine auswertbaren Raten'} → Vorschlag {r['proposal']}")
        else:
            L.append(f"- {r['claim_id']}: {r['note']} · Artefakte: {', '.join(r.get('artifacts') or []) or 'keine'}")
    L += ["", "## Negativergebnisse"] + ([f"- `{n['id']}` — {n['verdict']} ({n['closed']})" for n in doc["negative_results"]] or ["- keine"])
    L += ["", "## Limitationen"] + [f"- {x}" for x in doc["limitations"]]
    if doc["evidence_debt"]:
        L += ["", "## Evidenzschuld (offen)"] + [f"- [{d['severity']}] {d['subject']}: {d['text']}" for d in doc["evidence_debt"]]
    L += ["", "## Was dieses Papier nicht behauptet"] + [f"- {x}" for x in doc["does_not_claim"]]
    L += ["", "## Reproduzierbarkeit", f"- Register: {', '.join(doc['reproducibility']['registries'])}", f"- Preregistrationen: {', '.join(doc['reproducibility']['preregistrations']) or 'keine'}",
          f"- Artefakte: {', '.join(doc['reproducibility']['artifacts']) or 'keine'}", f"- Code: {doc['reproducibility']['code']}"]
    if doc["open_blockers"]:
        L += ["", "## Offene Blocker (aus dem Publikationsregister)"] + [f"- {b}" for b in doc["open_blockers"]]
    if doc.get("readiness"):
        L += ["", f"## Kriterien: {doc['readiness']['met']}/{doc['readiness']['of']} erfüllt"] + [f"- {'✓' if v else '✗'} {k}" for k, v in doc["readiness"]["checks"].items()]
    L += ["", f"> {doc['rule']}", ""]
    return "\n".join(L)


def export(conn, paper_id: str, actor: str) -> dict:
    """Schreibt den Entwurf nach docs/research/dashboard/paper-drafts/<paper>.md (+ .json). Ändert kein Register, keinen Reifegrad."""
    doc = build(conn, paper_id)
    DRAFTS.mkdir(exist_ok=True)
    md = render_markdown(doc)
    (DRAFTS / f"{paper_id}.md").write_text(md, encoding="utf-8")
    (DRAFTS / f"{paper_id}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return {"paper_id": paper_id, "path": f"docs/research/dashboard/paper-drafts/{paper_id}.md", "sha256": doc["sha256"], "by": actor, "manuscript_status_unchanged": doc["manuscript_status_in_registry"], "bytes": len(md.encode())}
