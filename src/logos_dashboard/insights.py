"""„Was wissen wir jetzt?" — mechanisch aus Records erzeugte Sätze, keine generierte Prosa.

Jede Aussage ist eine Schablone über Registerfelder; jede Zahl trägt ihr n; Status und Evidenzstärke bleiben getrennt.
Nichts hier ändert einen Record, und nichts hier behauptet mehr, als in den Records steht: fehlt ein Feld, steht „nicht erfasst".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import registries
from .reports import STRENGTH_ORDER

SUPPORTED_STATES = ("SUPPORTED", "PARTIALLY_SUPPORTED", "VALIDATED_IN_FIXTURE", "EXTERNALLY_REPLICATED", "OBSERVED", "CONSOLIDATED")
NEGATIVE_STATES = ("FALSIFIED", "INVALID_MEASUREMENT", "INCONCLUSIVE")
BLOCKED_STATES = ("BLOCKED_BY_GOVERNANCE", "BLOCKED_BY_INFERENCE")
CONFIDENCE = {"PRELIMINARY": "sehr vorläufig", "LOW": "schwach", "LOW_TO_MEDIUM": "schwach bis mittel", "MEDIUM": "mittel", "MEDIUM_TO_HIGH": "mittel bis stark", "HIGH": "stark", "INDEPENDENTLY_REPLICATED": "unabhängig repliziert"}
VERSION = "ros-insights/1"


def _fmt_date(s: str | None) -> str:
    return (s or "")[:10] or "ohne Datum"


def _sentence(c: dict, n_exp: int, rep: dict | None, measurements: list[dict]) -> str:
    strength = CONFIDENCE.get(c["evidence_strength"], c["evidence_strength"])
    parts = [f"{c['title']}: Status {c['status']}, Evidenz {strength}"]
    parts.append(f"geprüft in {n_exp} Experiment{'en' if n_exp != 1 else ''}" if n_exp else "noch in keinem registrierten Experiment geprüft")
    if measurements:
        m = measurements[0]; prop = ((m.get("summary") or {}).get("proposal") or {}).get("verdict")
        parts.append(f"letzter Messlauf {m['measurement_id']} ({m['executed']}/{m['planned']} Datenpunkte, Vorschlag {prop or 'offen'})")
    if rep:
        parts.append(f"Replikation {rep.get('count', 'nicht erfasst')}")
    parts.append(f"zuletzt geändert {_fmt_date(c.get('last_updated'))}")
    s = " · ".join(parts) + "."
    falsifier = c.get("next_falsification_test") or c.get("falsification_test")
    return s + (f" Widerlegen würde: {falsifier}" if falsifier else " Widerlegen würde: nicht erfasst.")


def build(conn=None, regs: dict | None = None, closures: list[dict] | None = None, days: int = 30) -> dict:
    from . import readers
    regs = regs or registries.load_all(); closures = closures if closures is not None else readers.closures()
    claims = regs["claims"]["claims"]; exps = regs["experiments"]["experiments"]; reps = {r["claim_id"]: r for r in regs["replication"]["replications"]}
    # claims link to experiments through the invariants of their track — the same rule the claim detail endpoint uses (there is no claim field on an experiment)
    inv_by_track: dict[str, set[str]] = {}
    for i in regs["invariants"]["invariants"]:
        inv_by_track.setdefault(i["track"], set()).add(i["invariant_id"])
    by_claim: dict[str, list[str]] = {}
    for c in claims:
        track_invs = inv_by_track.get(c["track"], set())
        by_claim[c["claim_id"]] = [e["experiment_id"] for e in exps if any(inv in track_invs for inv in (e.get("invariants") or []))]
    meas: dict[str, list[dict]] = {}
    if conn is not None:
        from .control import measurement as M
        for m in M.list_measurements(conn, limit=200):
            for cid in (m.get("summary") or {}).get("claims", []) or []:
                meas.setdefault(cid, []).append(m)
            th = m.get("thesis_id") or ""
            if th.startswith("ROS-"):
                meas.setdefault(th[4:], []).append(m)
    groups = {"gestuetzt": [], "widerlegt": [], "offen": [], "blockiert": []}
    for c in claims:
        n_exp = len(by_claim.get(c["claim_id"], []))
        entry = {"claim_id": c["claim_id"], "title": c["title"], "track": c["track"], "status": c["status"], "evidence_strength": c["evidence_strength"], "kind": c["kind"],
                 "sentence": _sentence(c, n_exp, reps.get(c["claim_id"]), meas.get(c["claim_id"], [])), "scope": c.get("scope"), "experiments": by_claim.get(c["claim_id"], []),
                 "artifacts": c.get("supporting_artifacts", []), "counterevidence": c.get("counterevidence", []), "limitations": c.get("known_limitations", []),
                 "certainty": _certainty(c, reps.get(c["claim_id"])), "record": f"docs/research/dashboard/CLAIM-REGISTRY.json#{c['claim_id']}"}
        g = "widerlegt" if c["status"] in NEGATIVE_STATES else "blockiert" if c["status"] in BLOCKED_STATES else "gestuetzt" if c["status"] in SUPPORTED_STATES else "offen"
        groups[g].append(entry)
    for g in groups:
        groups[g].sort(key=lambda e: (-STRENGTH_ORDER.index(e["evidence_strength"]) if e["evidence_strength"] in STRENGTH_ORDER else 0, e["claim_id"]))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    learned = [{"kind": "closure", "id": c["id"], "text": f"{c['id']}: {c.get('verdict') or 'nicht erfasst'} ({c.get('verdict_class')})", "at": c.get("closed"), "record": c.get("path")}
               for c in closures if (c.get("closed") or "") >= since]
    if conn is not None:
        from .control import measurement as M
        for m in M.list_measurements(conn, limit=50):
            if str(m.get("started") or "")[:10] >= since:
                prop = ((m.get("summary") or {}).get("proposal") or {})
                learned.append({"kind": "measurement", "id": m["measurement_id"], "text": f"{m['measurement_id']}: {m['executed']}/{m['planned']} Datenpunkte, Vorschlag {prop.get('verdict', 'offen')}", "at": str(m.get("started"))[:19], "record": f"/measurements/{m['measurement_id']}"})
    learned.sort(key=lambda x: str(x.get("at") or ""), reverse=True)
    counts = {k: len(v) for k, v in groups.items()}
    return {"groups": groups, "counts": counts, "n_claims": len(claims), "learned": learned[:30], "since": since, "version": VERSION,
            "rules": ["Status ist nicht Evidenzstärke — beides steht getrennt da.", "Jede Zahl nennt ihr n; es gibt keine Prozentzahl ohne Nenner.", 'Fehlt ein Feld im Register, steht hier "nicht erfasst" — nichts wird ergänzt.', "Nichts hier ist eine Aussage über phänomenales Bewusstsein (P7)."]}


def _certainty(c: dict, rep: dict | None) -> str:
    s = c["evidence_strength"]; st = c["status"]; scope = (c.get("scope") or "").lower()
    if st in NEGATIVE_STATES:
        return "Negativbefund — er sagt, was nicht gilt; das ist ein Ergebnis, keine Schwäche."
    bits = []
    if s in ("PRELIMINARY", "LOW", "LOW_TO_MEDIUM"):
        bits.append("die Evidenz ist noch schwach")
    if "fixture" in scope or "deterministisch" in scope or "deterministic" in scope:
        bits.append("gilt bisher nur im Fixture, nicht mit echtem Modell")
    if rep and rep.get("count", "0/5").startswith("0"):
        bits.append("keine unabhängige Replikation")
    if c.get("counterevidence"):
        bits.append(f"{len(c['counterevidence'])} Gegenbefund(e) im Register")
    return "Vorsicht: " + ", ".join(bits) + "." if bits else "Soweit die Records reichen, trägt diese Aussage."
