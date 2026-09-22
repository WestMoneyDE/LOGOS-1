"""Agenten-Qualität: deterministische Gold-Profile je Arbeitsstufe — kein LLM-Judge.

Jede Stufe hat ein Profil aus Prüfungen, die eine Datei bestehen muss (Pflichtabschnitte, messbar formuliertes Falsifikationskriterium,
Metriken auf vorhandene Scorer abbildbar, keine Statusaussage, keine Zitate ohne Quelle). Jede Prüfung ist eine reine Funktion über den Text;
das Ergebnis ist Treffer/daneben/nicht bewertbar, die Rate trägt ihr Wilson-Intervall. Damit ist die Frage „ist der Agent gut?" messbar,
ohne dass ein Modell über ein Modell urteilt.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import measurement_contract as mc, stats

VERSION = "ros-evals/1"
SUITE = "AGENT_QUALITY"
STAGES = ("TRIAGE", "PRIOR_ART", "QUESTION", "HYPOTHESIS", "METRICS", "PREREG")
FILE_OF_STAGE = {"TRIAGE": "TRIAGE.md", "PRIOR_ART": "PRIOR-ART.md", "QUESTION": "QUESTION.md", "HYPOTHESIS": "HYPOTHESES.md", "METRICS": "METRICS.md", "PREREG": "PREREG-DRAFT.json"}
STATUS_WORDS = ("SUPPORTED", "FALSIFIED", "VALIDATED", "PARTIALLY_SUPPORTED", "CONSOLIDATED", "EXTERNALLY_REPLICATED")
MEASURABLE = ("konfidenzintervall", "confidence interval", "ci", "wilson", "newcombe", "rate", "quote", "schwelle", "threshold", "differenz", "difference", "p <", "n =", "n=", "anteil")
CITATION = re.compile(r"(https?://\S+|10\.\d{4,9}/\S+|arxiv:\s*\d{4}\.\d{4,5})", re.I)


def _t(text: str) -> str:
    return (text or "").lower()


# -- checks: each returns True (hit), False (miss) or None (not applicable/not scorable) ------------------------------

def c_has_content(text: str, ctx: dict) -> bool | None:
    return None if text is None else len(text.strip()) >= 200


def c_no_status_claim(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    return not any(re.search(rf"\b{w}\b", text) for w in STATUS_WORDS)


def c_cites_records(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    return bool(re.search(r"(docs/research/|05-WORK-ORDERS/|09-SESSIONS/|LOGOS-[A-Z]+-\d{3}|src/)", text))


def c_no_uncited_claims(text: str, ctx: dict) -> bool | None:
    """Zitiert der Text fremde Arbeiten, dann mit Quelle: jede Zeile mit 'et al.' oder Jahreszahl in Klammern braucht eine URL/DOI im Text."""
    if text is None:
        return None
    needs = [ln for ln in text.splitlines() if re.search(r"(et al\.|\(\d{4}\))", ln)]
    return True if not needs else bool(CITATION.search(text))


def c_falsifier_measurable(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    seg = text.lower()
    if not any(k in seg for k in ("falsifik", "falsif", "widerleg", "would falsify")):
        return False
    return any(k in seg for k in MEASURABLE)


def c_has_hypotheses(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    t = _t(text)
    return ("h0" in t and "h1" in t) or ("nullhypothese" in t and "alternativ" in t)


def c_one_question(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    qs = [ln for ln in text.splitlines() if ln.strip().endswith("?")]
    return len(qs) >= 1


def c_scope_and_out_of_scope(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    t = _t(text)
    return ("scope" in t or "geltungsbereich" in t) and ("out of scope" in t or "nicht im" in t or "ausserhalb" in t or "außerhalb" in t)


def c_metrics_map_to_scorers(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    named = [s for s in mc.SCORER_IDS if s in text]
    return bool(named)


def c_prereg_fields(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    try:
        d = json.loads(text)
    except ValueError:
        return False
    need = ("question", "hypothesis", "falsification_criterion", "scope")
    return all(str(d.get(k) or "").strip() for k in need)


def c_prior_art_sources(text: str, ctx: dict) -> bool | None:
    if text is None:
        return None
    return len(CITATION.findall(text)) >= 1


CHECKS = {"has_content": (c_has_content, "genug Substanz (≥ 200 Zeichen)"), "no_status_claim": (c_no_status_claim, "keine Statusaussage (SUPPORTED/FALSIFIED …) — das entscheidet der Founder"),
          "cites_records": (c_cites_records, "zeigt auf Repository-Records"), "no_uncited_claims": (c_no_uncited_claims, "fremde Arbeiten nur mit Quelle"),
          "falsifier_measurable": (c_falsifier_measurable, "Falsifikationskriterium messbar formuliert"), "has_hypotheses": (c_has_hypotheses, "H0 und H1 benannt"),
          "one_question": (c_one_question, "mindestens eine ausformulierte Frage"), "scope_and_out_of_scope": (c_scope_and_out_of_scope, "Geltungsbereich und Abgrenzung"),
          "metrics_map_to_scorers": (c_metrics_map_to_scorers, "Metriken auf vorhandene Scorer abbildbar"), "prereg_fields": (c_prereg_fields, "Prereg-Pflichtfelder gefüllt"),
          "prior_art_sources": (c_prior_art_sources, "mindestens eine belegte Quelle")}

PROFILES = {
    "TRIAGE": ["has_content", "no_status_claim", "cites_records", "falsifier_measurable"],
    "PRIOR_ART": ["has_content", "no_status_claim", "prior_art_sources", "no_uncited_claims"],
    "QUESTION": ["has_content", "no_status_claim", "one_question", "scope_and_out_of_scope"],
    "HYPOTHESIS": ["has_content", "no_status_claim", "has_hypotheses", "falsifier_measurable"],
    "METRICS": ["has_content", "no_status_claim", "metrics_map_to_scorers", "falsifier_measurable"],
    "PREREG": ["prereg_fields", "no_status_claim", "cites_records", "falsifier_measurable"],
}


def profiles() -> dict:
    return {"stages": {s: [{"check": c, "text": CHECKS[c][1]} for c in PROFILES[s]] for s in STAGES}, "files": FILE_OF_STAGE, "version": VERSION, "suite": SUITE,
            "rule": "deterministische Prüfungen über den Text; kein Modell bewertet ein Modell. Nicht bewertbar zählt als fehlend, nie als Treffer."}


def score_file(stage: str, text: str | None) -> dict:
    if stage not in PROFILES:
        raise ValueError(f"unknown stage {stage!r}")
    results = {}
    for name in PROFILES[stage]:
        fn = CHECKS[name][0]
        try:
            results[name] = fn(text, {"stage": stage})
        except Exception:
            results[name] = None
    hits = [v for v in results.values() if v is not None]
    return {"stage": stage, "checks": results, "k": sum(1 for v in hits if v), "n_scored": len(hits), "n_total": len(results), "missing": len(results) - len(hits),
            "passed": bool(hits) and all(v for v in hits) and len(hits) == len(results)}


def evaluate_thesis_dir(base: Path, thesis_id: str) -> dict:
    d = base / "docs" / "research" / "dashboard" / "theses" / thesis_id
    out = []
    for stage in STAGES:
        p = d / FILE_OF_STAGE[stage]
        text = p.read_text(encoding="utf-8") if p.exists() else None
        if text is None:
            continue
        out.append({**score_file(stage, text), "file": FILE_OF_STAGE[stage], "thesis_id": thesis_id})
    return {"thesis_id": thesis_id, "stages": out, "n_stages": len(out)}


def aggregate(evaluations: list[dict]) -> dict:
    """Rate je Stufe und gesamt, mit Wilson-Intervall; nicht bewertbare Prüfungen sind Missingness."""
    per_stage: dict[str, dict] = {}
    for ev in evaluations:
        for s in ev["stages"]:
            acc = per_stage.setdefault(s["stage"], {"k": 0, "n": 0, "missing": 0, "files": 0})
            acc["k"] += s["k"]; acc["n"] += s["n_scored"]; acc["missing"] += s["missing"]; acc["files"] += 1
    rows = []
    tk = tn = tm = 0
    for stage in STAGES:
        a = per_stage.get(stage)
        if not a:
            rows.append({"stage": stage, "status": "NO_DATA", "files": 0, "k": None, "n": None, "rate": None, "ci95": None}); continue
        w = stats.wilson(a["k"], a["n"]); tk += a["k"]; tn += a["n"]; tm += a["missing"]
        rows.append({"stage": stage, "status": "OK", "files": a["files"], "k": a["k"], "n": a["n"], "missing": a["missing"], "rate": w["value"], "ci95": w["ci95"], "method": w["method"]})
    total = stats.wilson(tk, tn)
    return {"stages": rows, "total": {"k": tk, "n": tn, "missing": tm, "rate": total["value"], "ci95": total["ci95"], "method": total["method"]}, "suite": SUITE, "version": VERSION,
            "note": "Rate = bestandene Prüfungen / bewertbare Prüfungen; nicht bewertbare zählen als fehlend, nie als Treffer."}
