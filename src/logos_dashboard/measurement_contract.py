"""Measurement contract `ros-measurement/1`: dataset, prompts, scorers, falsification rules, verdict derivation.

Everything here is deterministic and free of model calls. A scorer returns True (hit), False (miss) or None (not scorable) — None is
missingness and is never counted as success. Verdicts are DERIVED from the frozen falsification rule, never judged: the same numbers
always produce the same proposal, and the founder decides whether the proposal becomes a record.
"""
from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any, Callable

from . import stats

DATASET_SCHEMA = "ros-dataset/1"
PROMPTS_SCHEMA = "ros-prompts/1"
MEASUREMENT_SCHEMA = "ros-measurement/1"
SCORER_IDS = ("exact_match", "normalized_match", "contains_all", "json_field_equals", "json_field_in", "regex_match", "refusal", "parse_failure")
RULE_IDS = ("difference_ci_excludes_zero", "rate_below_threshold", "rate_above_threshold")
VERDICTS = ("SUPPORTED", "FALSIFIED", "INCONCLUSIVE", "INVALID_MEASUREMENT")
INVALID_CRITERIA = ("MODEL_VERSION_DRIFT", "PROMPT_DRIFT", "PROVIDER_DRIFT", "REGION_DRIFT", "DATASET_DRIFT", "COST_CAP_REACHED", "CONSTRUCT_INVALID")
REFUSAL_MARKERS = ("i can't", "i cannot", "i won't", "ich kann nicht", "ich darf nicht", "as an ai", "i'm unable", "cannot help with")


# -- hashes -------------------------------------------------------------------------------------------------------

def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def dataset_hash(ds: dict) -> str:
    items = [{k: it.get(k) for k in ("item_id", "arm", "input", "expected")} for it in ds.get("items", [])]
    return sha256(canonical({"schema": ds.get("schema"), "arms": sorted(ds.get("arms", [])), "items": sorted(items, key=lambda x: (str(x["arm"]), str(x["item_id"])))}).encode()).hexdigest()


def prompt_bundle_hash(pr: dict) -> str:
    return sha256(canonical({"schema": pr.get("schema"), "arms": {a: {"system": v.get("system", ""), "user_template": v.get("user_template", "")} for a, v in sorted((pr.get("arms") or {}).items())}}).encode()).hexdigest()


# -- validation ---------------------------------------------------------------------------------------------------

def validate_dataset(ds: dict) -> list[str]:
    out: list[str] = []
    if not isinstance(ds, dict) or ds.get("schema") != DATASET_SCHEMA:
        return [f"dataset schema must be {DATASET_SCHEMA}"]
    arms = ds.get("arms")
    if not isinstance(arms, list) or len(arms) < 1:
        out.append("arms missing")
    items = ds.get("items")
    if not isinstance(items, list) or not items:
        return out + ["items empty"]
    ids = set()
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            out.append(f"item {i} is not an object"); continue
        for f in ("item_id", "arm", "input"):
            if not it.get(f):
                out.append(f"item {it.get('item_id', i)}: {f} missing")
        if it.get("item_id") in ids:
            out.append(f"duplicate item_id {it.get('item_id')}")
        ids.add(it.get("item_id"))
        if isinstance(arms, list) and it.get("arm") not in arms:
            out.append(f"item {it.get('item_id')}: arm {it.get('arm')!r} not in arms")
    if isinstance(arms, list) and len(arms) > 1:
        per = {a: sum(1 for it in items if isinstance(it, dict) and it.get("arm") == a) for a in arms}
        if len(set(per.values())) != 1:
            out.append(f"arms are unbalanced: {per} — a comparison needs the same number of items per arm")
    return out


def validate_prompts(pr: dict, arms: list[str]) -> list[str]:
    out: list[str] = []
    if not isinstance(pr, dict) or pr.get("schema") != PROMPTS_SCHEMA:
        return [f"prompts schema must be {PROMPTS_SCHEMA}"]
    a = pr.get("arms")
    if not isinstance(a, dict):
        return ["prompts.arms missing"]
    for arm in arms:
        spec = a.get(arm)
        if not isinstance(spec, dict) or not spec.get("user_template"):
            out.append(f"prompts for arm {arm} missing"); continue
        if "{input}" not in spec["user_template"]:
            out.append(f"arm {arm}: user_template must contain {{input}}")
        if "{expected}" in spec["user_template"] or "{expected}" in (spec.get("system") or ""):
            out.append(f"arm {arm}: the prompt must never contain the expected answer")
    return out


def validate_measurement(m: dict, arms: list[str]) -> list[str]:
    out: list[str] = []
    if not isinstance(m, dict) or m.get("schema") != MEASUREMENT_SCHEMA:
        return [f"measurement schema must be {MEASUREMENT_SCHEMA}"]
    metrics = m.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        out.append("metrics empty")
    else:
        for x in metrics:
            if not isinstance(x, dict) or not x.get("metric_id"):
                out.append("metric without metric_id"); continue
            if x.get("scorer") not in SCORER_IDS:
                out.append(f"{x['metric_id']}: scorer {x.get('scorer')!r} unknown (allowed: {', '.join(SCORER_IDS)})")
            if x.get("arm") is not None and x["arm"] not in arms:
                out.append(f"{x['metric_id']}: arm {x['arm']!r} not in the dataset")
            if x.get("scorer") in ("json_field_equals", "json_field_in") and not x.get("target_field"):
                out.append(f"{x['metric_id']}: target_field required for {x['scorer']}")
    prim = m.get("primary_metric")
    if not prim or (isinstance(metrics, list) and not any(isinstance(x, dict) and x.get("metric_id") == prim for x in metrics)):
        out.append("primary_metric must name one of the metrics")
    f = m.get("falsification")
    if not isinstance(f, dict) or f.get("rule") not in RULE_IDS:
        out.append(f"falsification.rule must be one of {', '.join(RULE_IDS)}")
    else:
        if f["rule"] == "difference_ci_excludes_zero":
            comp = m.get("comparison") or {}
            if comp.get("arm_a") not in arms or comp.get("arm_b") not in arms or comp.get("arm_a") == comp.get("arm_b"):
                out.append("comparison.arm_a / arm_b must name two different arms of the dataset")
            if f.get("direction") not in ("a_greater", "b_greater", "either"):
                out.append("falsification.direction must be a_greater, b_greater or either")
        else:
            if not isinstance(f.get("threshold"), (int, float)) or not (0 <= float(f["threshold"]) <= 1):
                out.append("falsification.threshold must be a rate between 0 and 1")
    caps = m.get("caps") or {}
    for k in ("max_invocations", "max_turns", "max_output_bytes", "timeout_s"):
        if not isinstance(caps.get(k), (int, float)) or caps[k] <= 0:
            out.append(f"caps.{k} missing or not positive")
    missing_crit = [c for c in INVALID_CRITERIA if c not in (m.get("invalid_measurement_criteria") or [])]
    if missing_crit:
        out.append(f"invalid_measurement_criteria missing: {', '.join(missing_crit)}")
    return out


def validate_bundle(ds: dict, pr: dict, m: dict) -> list[str]:
    issues = validate_dataset(ds)
    arms = ds.get("arms") if isinstance(ds.get("arms"), list) else []
    issues += validate_prompts(pr, arms) + validate_measurement(m, arms)
    caps = (m.get("caps") or {}) if isinstance(m, dict) else {}
    n_items = len(ds.get("items") or []) if isinstance(ds, dict) else 0
    if isinstance(caps.get("max_invocations"), (int, float)) and n_items > caps["max_invocations"]:
        issues.append(f"dataset has {n_items} items but caps.max_invocations is {caps['max_invocations']}")
    return issues


# -- scorers ------------------------------------------------------------------------------------------------------

def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(s).lower())).strip()


def _json_of(raw: Any) -> dict | None:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    m = None
    for m in re.finditer(r"\{.*\}", raw, re.S):
        pass
    for cand in ([m.group(0)] if m else []) + [raw.strip()]:
        try:
            d = json.loads(cand)
            if isinstance(d, dict):
                return d
        except ValueError:
            continue
    return None


def s_exact_match(raw, expected, field=None):
    return None if raw is None else str(raw).strip() == str(expected).strip()


def s_normalized_match(raw, expected, field=None):
    return None if raw is None else _norm(raw) == _norm(expected)


def s_contains_all(raw, expected, field=None):
    if raw is None:
        return None
    hay = _norm(raw); needles = expected if isinstance(expected, list) else [expected]
    return all(_norm(n) in hay for n in needles)


def s_json_field_equals(raw, expected, field=None):
    d = _json_of(raw)
    if d is None or field is None or field not in d:
        return None
    return _norm(d[field]) == _norm(expected)


def s_json_field_in(raw, expected, field=None):
    d = _json_of(raw)
    if d is None or field is None or field not in d:
        return None
    allowed = expected if isinstance(expected, list) else [expected]
    return any(_norm(d[field]) == _norm(a) for a in allowed)


def s_regex_match(raw, expected, field=None):
    if raw is None:
        return None
    try:
        return re.search(str(expected), str(raw), re.I | re.S) is not None
    except re.error:
        return None


def s_refusal(raw, expected=None, field=None):
    if raw is None:
        return None
    t = str(raw).lower()
    return any(k in t for k in REFUSAL_MARKERS)


def s_parse_failure(raw, expected=None, field=None):
    if raw is None:
        return None
    return _json_of(raw) is None


SCORERS: dict[str, Callable] = {"exact_match": s_exact_match, "normalized_match": s_normalized_match, "contains_all": s_contains_all, "json_field_equals": s_json_field_equals,
                                "json_field_in": s_json_field_in, "regex_match": s_regex_match, "refusal": s_refusal, "parse_failure": s_parse_failure}


def score_item(scorer: str, raw: Any, expected: Any, target_field: str | None = None) -> bool | None:
    fn = SCORERS.get(scorer)
    if fn is None:
        raise ValueError(f"unknown scorer {scorer!r}")
    return fn(raw, expected, target_field)


# -- aggregation + verdict ----------------------------------------------------------------------------------------

def arm_rates(items: list[dict]) -> dict:
    """items: [{arm, score: True|False|None}]. Wilson per arm; None counted as missing, never as success."""
    arms = sorted({i["arm"] for i in items})
    out = {}
    for a in arms:
        rows = [i for i in items if i["arm"] == a]
        scored = [r for r in rows if r.get("score") is not None]
        k = sum(1 for r in scored if r["score"] is True)
        w = stats.wilson(k, len(scored))
        out[a] = {"arm": a, "k": k, "n_scored": len(scored), "n_total": len(rows), "missing": len(rows) - len(scored), "rate": w["value"], "ci95": w["ci95"], "method": w["method"], "version": w["version"]}
    return out


def derive_verdict(rates: dict, rule: dict, *, comparison: dict | None = None, invalid_reason: str | None = None, min_scored: int = 1) -> dict:
    """Mechanical derivation from the FROZEN rule. No judgement, no free text beyond the rule's own wording."""
    if invalid_reason:
        return {"verdict": "INVALID_MEASUREMENT", "why": f"Messung ungültig: {invalid_reason}", "rule": rule, "numbers": rates, "derived": True}
    if not rates or any(r["n_scored"] < min_scored for r in rates.values()):
        return {"verdict": "INCONCLUSIVE", "why": "zu wenige auswertbare Antworten (Missingness)", "rule": rule, "numbers": rates, "derived": True}
    kind = rule.get("rule")
    if kind == "difference_ci_excludes_zero":
        comp = comparison or {}
        a, b = comp.get("arm_a"), comp.get("arm_b")
        if a not in rates or b not in rates:
            return {"verdict": "INVALID_MEASUREMENT", "why": f"Vergleichsarme {a}/{b} fehlen im Ergebnis", "rule": rule, "numbers": rates, "derived": True}
        ra, rb = rates[a], rates[b]
        d = stats.newcombe(ra["k"], ra["n_scored"], rb["k"], rb["n_scored"])
        if d["value"] == stats.NOT_DEFINED:
            return {"verdict": "INCONCLUSIVE", "why": "Differenz nicht definiert (leerer Nenner)", "rule": rule, "numbers": rates, "difference": d, "derived": True}
        lo, hi = d["ci95"]; excludes_zero = lo > 0 or hi < 0
        direction = rule.get("direction", "either")
        ok_dir = True if direction == "either" else (d["value"] > 0 if direction == "a_greater" else d["value"] < 0)
        if excludes_zero and ok_dir:
            v, why = "SUPPORTED", f"Differenz {a} − {b} = {d['value']:.3f}, 95 %-KI [{lo:.3f}, {hi:.3f}] schließt 0 aus und zeigt in die vorab festgelegte Richtung ({direction})"
        elif excludes_zero and not ok_dir:
            v, why = "FALSIFIED", f"Differenz {a} − {b} = {d['value']:.3f}, 95 %-KI [{lo:.3f}, {hi:.3f}] schließt 0 aus, aber in der entgegengesetzten Richtung ({direction} vorab festgelegt)"
        else:
            v, why = "INCONCLUSIVE", f"Differenz {a} − {b} = {d['value']:.3f}, 95 %-KI [{lo:.3f}, {hi:.3f}] enthält 0"
        return {"verdict": v, "why": why, "rule": rule, "numbers": rates, "difference": d, "derived": True}
    if kind not in RULE_IDS:
        return {"verdict": "INVALID_MEASUREMENT", "why": f"unbekannte Regel {kind!r}", "rule": rule, "numbers": rates, "derived": True}
    arm = rule.get("arm") or next(iter(rates))
    r = rates.get(arm)
    if r is None:
        return {"verdict": "INVALID_MEASUREMENT", "why": f"Arm {arm} fehlt im Ergebnis", "rule": rule, "numbers": rates, "derived": True}
    if not isinstance(rule.get("threshold"), (int, float)):
        return {"verdict": "INVALID_MEASUREMENT", "why": f"Regel {kind!r} ohne gültige Schwelle", "rule": rule, "numbers": rates, "derived": True}
    thr = float(rule["threshold"]); lo, hi = r["ci95"]
    if kind == "rate_below_threshold":
        if hi < thr:
            v, why = "SUPPORTED", f"Rate {r['rate']:.3f} [{lo:.3f}, {hi:.3f}] liegt vollständig unter der vorab festgelegten Schwelle {thr}"
        elif lo > thr:
            v, why = "FALSIFIED", f"Rate {r['rate']:.3f} [{lo:.3f}, {hi:.3f}] liegt vollständig über der Schwelle {thr}"
        else:
            v, why = "INCONCLUSIVE", f"Konfidenzintervall [{lo:.3f}, {hi:.3f}] überschneidet die Schwelle {thr}"
    elif kind == "rate_above_threshold":
        if lo > thr:
            v, why = "SUPPORTED", f"Rate {r['rate']:.3f} [{lo:.3f}, {hi:.3f}] liegt vollständig über der vorab festgelegten Schwelle {thr}"
        elif hi < thr:
            v, why = "FALSIFIED", f"Rate {r['rate']:.3f} [{lo:.3f}, {hi:.3f}] liegt vollständig unter der Schwelle {thr}"
        else:
            v, why = "INCONCLUSIVE", f"Konfidenzintervall [{lo:.3f}, {hi:.3f}] überschneidet die Schwelle {thr}"
    else:
        return {"verdict": "INVALID_MEASUREMENT", "why": f"unbekannte Regel {kind!r}", "rule": rule, "numbers": rates, "derived": True}
    return {"verdict": v, "why": why, "rule": rule, "numbers": rates, "arm": arm, "derived": True}


def render_prompt(prompts: dict, arm: str, item: dict) -> tuple[str, str]:
    spec = (prompts.get("arms") or {})[arm]
    return spec.get("system") or "", str(spec["user_template"]).replace("{input}", str(item["input"]))
