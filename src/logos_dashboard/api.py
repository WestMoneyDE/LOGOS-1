"""FastAPI service — localhost only. GET everything; the single write is the founder's thesis selection (ACTIVE-THESES.json).

    uvicorn logos_dashboard.api:app --host 127.0.0.1 --port 8765
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import readers, registries
from .registries import DASH, FILES

app = FastAPI(title="LOGOS-1 Research Dashboard", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["GET", "POST"], allow_headers=["*"])
_cache: dict[str, tuple[float, object]] = {}


def cached(key: str, ttl: float, fn):
    now = time.time(); hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    val = fn(); _cache[key] = (now, val); return val


def _regs() -> dict:
    return cached("regs", 2.0, registries.load_all)


@app.get("/api/health")
def health():
    regs = _regs(); lab = cached("lab", 10.0, readers.lab_runs)
    return {"time": datetime.now(timezone.utc).isoformat(), "records_only": lab["records_only"], "lab_error": lab.get("error"), "integrity_violations": registries.validate(regs), "counts": registries.counts(regs), "git": readers.git_state()}


@app.get("/api/overview")
def overview():
    regs = _regs(); cl = readers.closures(); latest = cl[-1] if cl else None
    active = regs["active_theses"]["active"]
    return {"tracks": regs["claims"]["tracks"], "counts": registries.counts(regs), "latest_closure": latest, "next_work_order": latest["successor_id"] if latest else None,
            "open_decisions": [{"order_id": c["id"], "text": t} for c in cl for t in c["open_decisions"]], "active_theses": active, "integrity_violations": len(registries.validate(regs)),
            "principles": ["typed authority", "falsification first", "negative results preserved", "construct validity", "provenance", "reproducibility"],
            "does_not_claim": ["does not prove consciousness", "does not prove universal agent safety", "does not establish all LLMs behave identically", "does not treat self-report as ground truth", "does not treat high confidence as correctness", "does not treat memory as authority", "does not treat detection as containment"]}


@app.get("/api/registries/{name}")
def registry(name: str):
    if name not in FILES:
        raise HTTPException(404, "unknown registry")
    return _regs()[name]


@app.get("/api/tracks/{track}")
def track(track: str):
    regs = _regs()
    if track not in regs["claims"]["tracks"]:
        raise HTTPException(404, "unknown track")
    claims = [c for c in regs["claims"]["claims"] if c["track"] == track]
    exps = [e for e in regs["experiments"]["experiments"] if e["research_track"] == track or track in e.get("secondary_tracks", [])]
    invs = [i for i in regs["invariants"]["invariants"] if i["track"] == track]
    ces = [c for c in regs["claims"]["counterexamples"] if any(c["experiment"] == e["experiment_id"] for e in exps)]
    pa = [c for c in regs["prior_art"]["citations"] if c["research_track"] == track]
    qs = [q for q in regs["open_questions"]["questions"] if q["track"] == track]
    paper = next((p for p in regs["publications"]["papers"] if p["paper_id"] == regs["claims"]["tracks"][track]["paper"]), None)
    return {"track": track, **regs["claims"]["tracks"][track], "claims": claims, "experiments": exps, "invariants": invs, "counterexamples": ces, "prior_art": pa, "open_questions": qs, "paper": paper,
            "completeness": {"claims": len(claims), "experiments": len(exps), "invariants": len(invs), "counterexamples": len(ces), "prior_art": len(pa), "open_questions": len(qs), "paper": bool(paper)}}


@app.get("/api/claims/{claim_id}")
def claim(claim_id: str):
    regs = _regs(); c = next((c for c in regs["claims"]["claims"] if c["claim_id"] == claim_id), None)
    if not c:
        raise HTTPException(404, "unknown claim")
    exps = [e for e in regs["experiments"]["experiments"] if any(inv for inv in e["invariants"] if inv in {i["invariant_id"] for i in regs["invariants"]["invariants"] if i["track"] == c["track"]})]
    reps = [r for r in regs["replication"]["replications"] if r["claim_id"] == claim_id]
    papers = [p["paper_id"] for p in regs["publications"]["papers"] if claim_id in p["claims"]]
    return {"claim": c, "experiments": exps, "replication": reps, "papers": papers, "evidence_graph": {"nodes": [{"id": claim_id, "kind": "claim"}] + [{"id": a, "kind": "artifact"} for a in c["supporting_artifacts"]] + [{"id": e["experiment_id"], "kind": "experiment"} for e in exps] + [{"id": x, "kind": "counterevidence"} for x in c["counterevidence"]] + [{"id": l, "kind": "limitation"} for l in c["known_limitations"]],
            "edges": [{"from": claim_id, "to": a, "rel": "supported_by"} for a in c["supporting_artifacts"]] + [{"from": claim_id, "to": e["experiment_id"], "rel": "tested_by"} for e in exps] + [{"from": claim_id, "to": x, "rel": "challenged_by"} for x in c["counterevidence"]] + [{"from": claim_id, "to": l, "rel": "constrained_by"} for l in c["known_limitations"]]}}


@app.get("/api/experiments/{experiment_id}")
def experiment(experiment_id: str):
    regs = _regs(); e = next((e for e in regs["experiments"]["experiments"] if e["experiment_id"] == experiment_id), None)
    if not e:
        raise HTTPException(404, "unknown experiment")
    lab = cached("lab", 10.0, readers.lab_runs)
    return {"experiment": e, "lab_run": next((r for r in lab["runs"] if r["run_id"] == e["run_id"]), None), "closure": next((c for c in readers.closures() if c["id"] == e["order_id"].split(" ")[0]), None)}


@app.get("/api/invariants/graph")
def invariant_graph():
    regs = _regs(); invs = regs["invariants"]["invariants"]
    return {"nodes": [{"id": i["invariant_id"], "label": i["statement"], "track": i["track"], "status": i["status"], "class": i["class"]} for i in invs],
            "edges": [{"from": i["invariant_id"], "to": r["target"], "rel": r["type"]} for i in invs for r in i["relations"]]}


@app.get("/api/falsification")
def falsification():
    regs = _regs()
    return [{"claim_id": c["claim_id"], "title": c["title"], "track": c["track"], "status": c["status"], "falsification_test": c["falsification_test"], "next_falsification_test": c["next_falsification_test"], "counterevidence": c["counterevidence"],
             "what_would_change_our_mind": c["falsification_test"]} for c in regs["claims"]["claims"] if c["claim_type"] in ("hypothesis", "invariant", "architecture")]


@app.get("/api/negative-results")
def negative_results():
    regs = _regs(); lab = cached("lab", 10.0, readers.lab_runs)
    exps = [e for e in regs["experiments"]["experiments"] if e["negative_result"] or "REPAIR_FALSIFIED" in e["verdict"]]
    return {"experiments": exps, "counterexamples": regs["claims"]["counterexamples"], "lab_negative_results": lab["negative_results"][:100], "records_only": lab["records_only"]}


@app.get("/api/timeline")
def timeline():
    cl = readers.closures(); regs = _regs()
    items = [{"date": c["closed"], "order_id": c["id"], "verdict": c["verdict"], "verdict_class": c["verdict_class"], "kind": c["kind"], "successor": c["successor_id"]} for c in cl]
    return {"closures": items, "experiments": [{"experiment_id": e["experiment_id"], "order_id": e["order_id"], "verdict": e["verdict"], "kind": e["kind"], "next": e["next_experiment"]} for e in regs["experiments"]["experiments"]]}


@app.get("/api/reproducibility")
def reproducibility():
    regs = _regs(); lab = cached("lab", 10.0, readers.lab_runs)
    out = []
    for e in regs["experiments"]["experiments"]:
        if not e["run_id"]:
            continue
        run = next((r for r in lab["runs"] if r["run_id"] == e["run_id"]), None)
        out.append({"experiment_id": e["experiment_id"], "run_id": e["run_id"], "prereg_hash": e["prereg_hash"], "artifact_hash": e["artifact_hash"], "commit": e["commit"] or (run or {}).get("git_sha"), "model_provider": e["model_provider"],
                    "record": e["record"], "lab_status": (run or {}).get("run_status"), "requires_live_inference": "claude" in (e["model_provider"] or "").lower(), "instructions": "see the session report's reproducibility section; live inference requires the founder pin, Max auth and a new preregistration"})
    return {"runs": out, "records_only": lab["records_only"]}


@app.get("/api/lab")
def lab():
    return cached("lab", 10.0, readers.lab_runs)


@app.get("/api/closures")
def closures():
    return readers.closures()


@app.get("/api/sessions/{order_id}")
def session(order_id: str):
    s = readers.session_report(order_id)
    if not s:
        raise HTTPException(404, "no session report")
    return s


@app.get("/api/prs")
def prs():
    return cached("prs", 60.0, readers.pull_requests)


@app.get("/api/search")
def search(q: str):
    q = q.lower(); regs = _regs(); hits = []
    for c in regs["claims"]["claims"]:
        if q in json.dumps(c, ensure_ascii=False).lower(): hits.append({"kind": "claim", "id": c["claim_id"], "title": c["title"], "href": f"/claims/{c['claim_id']}"})
    for e in regs["experiments"]["experiments"]:
        if q in json.dumps(e, ensure_ascii=False).lower(): hits.append({"kind": "experiment", "id": e["experiment_id"], "title": e["order_id"], "href": f"/experiments/{e['experiment_id']}"})
    for i in regs["invariants"]["invariants"]:
        if q in json.dumps(i, ensure_ascii=False).lower(): hits.append({"kind": "invariant", "id": i["invariant_id"], "title": i["statement"], "href": "/invariants"})
    for p in regs["prior_art"]["citations"]:
        if q in json.dumps(p, ensure_ascii=False).lower(): hits.append({"kind": "prior_art", "id": p["citation_id"], "title": p["title"], "href": "/prior-art"})
    return hits[:50]


@app.get("/api/export/paper/{paper_id}")
def export_paper(paper_id: str):
    regs = _regs(); p = next((p for p in regs["publications"]["papers"] if p["paper_id"] == paper_id), None)
    if not p:
        raise HTTPException(404, "unknown paper")
    claims = [c for c in regs["claims"]["claims"] if c["claim_id"] in p["claims"]]
    exps = [e for e in regs["experiments"]["experiments"] if e["research_track"] in p["tracks"]]
    pa = [c for c in regs["prior_art"]["citations"] if c["citation_id"] in p["required_related_work"]]
    md = [f"# {p['title']}", "", f"**Status:** {p['manuscript_status']} · missing for preprint: {', '.join(p['missing_for_preprint']) or 'none'}", "", "## Research question", p["research_question"], "", "## Core contribution", p["core_contribution"], "",
          "## Claims and evidence", "| claim | status | strength | scope | falsification test |", "|---|---|---|---|---|"]
    md += [f"| {c['claim_id']} {c['title']} | {c['status']} | {c['evidence_strength']} | {c['scope']} | {c['falsification_test']} |" for c in claims]
    md += ["", "## Experiments", "| id | order | verdict | negative | record |", "|---|---|---|---|---|"] + [f"| {e['experiment_id']} | {e['order_id']} | {e['verdict']} | {'yes' if e['negative_result'] else 'no'} | {e['record']} |" for e in exps]
    md += ["", "## Limitations"] + [f"- {c['claim_id']}: {l}" for c in claims for l in c["known_limitations"]]
    md += ["", "## Related work matrix", "| citation | supports | does not support | novelty |", "|---|---|---|---|"] + [f"| {c['citation_id']} {c['authors']} ({c['year']}) {c['title']} | {c['claim_supported']} | {c['claim_not_supported']} | {c['novelty_status']} |" for c in pa]
    md += ["", "## Open blockers"] + [f"- {b}" for b in p["open_blockers"]] + ["", "## Draft outline"] + [f"{i+1}. {o}" for i, o in enumerate(p["draft_outline"])] + ["", "_Boundary: functional/mechanistic evidence only; P7 — no claim about phenomenal consciousness._"]
    return {"paper_id": paper_id, "markdown": "\n".join(md)}


class ThesesSelection(BaseModel):
    active: list[str]


@app.post("/api/theses/active")
def set_active_theses(sel: ThesesSelection):
    """The founder's selection of theses to work on next (several allowed). Selection only — execution stays a separately governed order."""
    regs = _regs(); ids = {c["claim_id"] for c in regs["claims"]["claims"]}
    unknown = [x for x in sel.active if x not in ids]
    if unknown:
        raise HTTPException(400, f"unknown claim ids {unknown}")
    doc = {"schema": "logos.active-theses/1", "note": "founder selection of theses to work on next; multiple allowed; selection only — execution stays a separate governed order", "active": list(dict.fromkeys(sel.active)), "updated_at": datetime.now(timezone.utc).isoformat()}
    (DASH / FILES["active_theses"]).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    _cache.pop("regs", None)
    return doc


@app.get("/api/theses/active")
def get_active_theses():
    regs = _regs(); active = regs["active_theses"]["active"]
    claims = {c["claim_id"]: c for c in regs["claims"]["claims"]}
    return {"active": [{"claim": claims[a], "next_falsification_test": claims[a]["next_falsification_test"], "execution": "NOT STARTED — requires a governed work order (Part 3 not built)"} for a in active if a in claims]}


# -- deep-research intake (skill logos-prior-art-research wraps deep-research) ----------------

from . import research_intake  # noqa: E402


@app.get("/api/research-queue")
def research_queue():
    return {"tasks": research_intake.queue(_regs()), "briefs": research_intake.briefs(), "skill": ".claude/skills/logos-prior-art-research/SKILL.md", "schema": research_intake.BRIEF_SCHEMA}


class BriefIn(BaseModel):
    brief: dict


@app.post("/api/research-briefs/validate")
def validate_brief(b: BriefIn):
    return {"issues": research_intake.validate_brief(b.brief)}
