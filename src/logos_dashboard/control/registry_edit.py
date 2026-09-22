"""Registerpflege: der geführte Weg vom Entwurf zur tatsächlichen Registeränderung — **eine Founder-Aktion im Werkzeug, nie ein Automatismus**.

Ablauf: Vorschlag (mechanisch aus Verdict-Entwurf / Messlauf / Radar-Draft) → Diff BEFORE/AFTER je Feld → Integritätsprüfung auf dem
*geänderten* Zustand (`registries.validate`, Status ≠ Evidenzstärke, Vokabular, Artefaktpflicht) → 🔒 Founder bestätigt → genau ein Feld wird
geschrieben, mit Dateihash vorher/nachher, Changelog-Zeile und Audit. Schlägt die Prüfung fehl, wird nichts geschrieben. Agenten werden abgelehnt.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from logos_research.governance import GovernanceError

from .. import registries

DASH = registries.DASH
CHANGELOG = DASH / "registry-changelog.jsonl"
STRENGTH = ("PRELIMINARY", "LOW", "LOW_TO_MEDIUM", "MEDIUM", "MEDIUM_TO_HIGH", "HIGH", "INDEPENDENTLY_REPLICATED")
VERSION = "ros-registry-edit/1"
# which fields may be edited through the dashboard at all, and what each one means in plain German
EDITABLE = {
    "claims": {
        "status": "Status der Hypothese (nicht die Evidenzstärke)",
        "evidence_strength": "Stärke der Evidenz (unabhängig vom Status)",
        "evidence_strength_basis": "Begründung der Evidenzstärke",
        "next_falsification_test": "nächster Test, der die Aussage widerlegen würde",
        "supporting_artifacts": "Belege (Pfade/Hashes) — nur anhängen",
        "counterevidence": "Gegenbefunde — nur anhängen",
        "known_limitations": "bekannte Grenzen — nur anhängen",
        "external_replication": "Stand der externen Replikation",
    },
    "replication": {"count": "Stufe der Replikationsleiter (z. B. 1/5)", "missing": "was für die nächste Stufe fehlt", "notes": "Anmerkung"},
}
APPEND_ONLY = {("claims", "supporting_artifacts"), ("claims", "counterevidence"), ("claims", "known_limitations")}
FILE_OF = {"claims": registries.FILES["claims"], "replication": registries.FILES["replication"]}
LIST_KEY = {"claims": ("claims", "claim_id"), "replication": ("replications", "claim_id")}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_hash(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


def _load(registry: str) -> tuple[Path, dict]:
    p = DASH / FILE_OF[registry]
    return p, json.loads(p.read_text(encoding="utf-8"))


def _entry(doc: dict, registry: str, entity_id: str) -> dict | None:
    key, idf = LIST_KEY[registry]
    return next((x for x in doc.get(key, []) if x.get(idf) == entity_id), None)


# -- proposals -------------------------------------------------------------------------------------------------------

def propose_from_verdict(draft: dict) -> list[dict]:
    """A verdict draft (docs/research/dashboard/verdict-drafts/*.json) -> concrete, reviewable field changes. Status changes are proposed only for
    a decided SUPPORTED/FALSIFIED and always require the founder; evidence strength is never raised automatically beyond one step."""
    out: list[dict] = []
    ev = draft.get("EVIDENCE") or {}; verdict = draft.get("verdict"); claims = (draft.get("BEFORE") or {}).get("claims") or []
    mid = draft.get("measurement_id"); why = draft.get("WHY") or ""
    for cid in claims:
        if verdict == "SUPPORTED":
            out.append({"registry": "claims", "entity_id": cid, "field": "status", "value": "SUPPORTED", "reason": f"Messlauf {mid}: {why}"[:400], "source": {"kind": "verdict_draft", "measurement_id": mid}})
        elif verdict == "FALSIFIED":
            out.append({"registry": "claims", "entity_id": cid, "field": "status", "value": "FALSIFIED", "reason": f"Messlauf {mid}: {why}"[:400], "source": {"kind": "verdict_draft", "measurement_id": mid}})
            out.append({"registry": "claims", "entity_id": cid, "field": "counterevidence", "value": [f"{mid}: {why}"[:300]], "reason": "Negativbefund als Gegenevidenz anhängen", "source": {"kind": "verdict_draft", "measurement_id": mid}})
        out.append({"registry": "claims", "entity_id": cid, "field": "supporting_artifacts", "value": [f"measurement://{mid}", f"prereg://{ev.get('prereg_hash', '')}"], "reason": f"Belege des Messlaufs {mid}", "source": {"kind": "verdict_draft", "measurement_id": mid}})
    return out


def proposals(conn=None) -> dict:
    """All open proposals: from verdict drafts on disk (and their state: already applied or not, per changelog)."""
    applied = {f"{c['registry']}:{c['entity_id']}:{c['field']}:{c.get('source', {}).get('measurement_id')}" for c in changelog()}
    items = []
    d = DASH / "verdict-drafts"
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            draft = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for prop in propose_from_verdict(draft):
            key = f"{prop['registry']}:{prop['entity_id']}:{prop['field']}:{prop['source'].get('measurement_id')}"
            items.append({**prop, "draft": str(p.relative_to(DASH.parents[2])).replace("\\", "/"), "already_applied": key in applied})
    return {"proposals": items, "n": len(items), "editable": EDITABLE, "append_only": [f"{a}.{b}" for a, b in APPEND_ONLY], "version": VERSION}


# -- diff + validation -------------------------------------------------------------------------------------------------

def preview(registry: str, entity_id: str, field: str, value, reason: str = "") -> dict:
    """BEFORE/AFTER for exactly one field + the integrity verdict of the CHANGED state. Nothing is written."""
    if registry not in EDITABLE or field not in EDITABLE[registry]:
        raise ValueError(f"field {registry}.{field} is not editable through the dashboard (editable: {sorted(EDITABLE.get(registry, {}))})")
    p, doc = _load(registry)
    entry = _entry(doc, registry, entity_id)
    if entry is None:
        raise KeyError(f"{registry}:{entity_id}")
    before = deepcopy(entry.get(field))
    if (registry, field) in APPEND_ONLY:
        add = [v for v in (value if isinstance(value, list) else [value]) if v and v not in (before or [])]
        after = list(before or []) + add
    else:
        after = value
    changed = deepcopy(doc)
    _entry(changed, registry, entity_id)[field] = after
    issues = _integrity(registry, changed, entity_id, field, before, after, reason)
    return {"registry": registry, "entity_id": entity_id, "field": field, "label": EDITABLE[registry][field], "before": before, "after": after, "unchanged": before == after,
            "issues": issues, "ok": not issues and before != after, "reason": reason, "file": FILE_OF[registry], "file_sha256_before": _file_hash(p), "version": VERSION}


def _integrity(registry: str, changed_doc: dict, entity_id: str, field: str, before, after, reason: str) -> list[str]:
    issues: list[str] = []
    if not reason or len(reason.strip()) < 20:
        issues.append("Begründung fehlt oder ist zu knapp (ein Satz, der auf einen Record zeigt: Messlauf, Closure, Artefakt)")
    if registry == "claims":
        entry = _entry(changed_doc, "claims", entity_id)
        vocab = changed_doc.get("status_vocabulary") or []
        if field == "status":
            if vocab and after not in vocab:
                issues.append(f"Status {after!r} ist nicht im Vokabular des Registers ({', '.join(vocab)})")
            need = {"SUPPORTED": "MEDIUM", "PARTIALLY_SUPPORTED": "LOW_TO_MEDIUM", "EXTERNALLY_REPLICATED": "HIGH"}.get(after)
            have = entry.get("evidence_strength")
            if need and (have not in STRENGTH or STRENGTH.index(have) < STRENGTH.index(need)):
                issues.append(f"Status {after} verlangt mindestens Evidenzstärke {need}, eingetragen ist {have} — Status ist nicht Evidenzstärke: erst die Evidenz, dann der Status")
            if after == "EXTERNALLY_REPLICATED" and (entry.get("external_replication") or "none").lower().startswith("none"):
                issues.append("EXTERNALLY_REPLICATED ohne eingetragene externe Replikation")
            if after in ("SUPPORTED", "FALSIFIED", "INVALID_MEASUREMENT", "PARTIALLY_SUPPORTED") and not entry.get("supporting_artifacts"):
                issues.append("kein Beleg (supporting_artifacts leer) — ein Status ohne Artefakt ist nicht überprüfbar")
        if field == "evidence_strength":
            if after not in STRENGTH:
                issues.append(f"Evidenzstärke {after!r} ist nicht im Vokabular ({', '.join(STRENGTH)})")
            elif before in STRENGTH and STRENGTH.index(after) > STRENGTH.index(before) + 1:
                issues.append(f"Sprung von {before} auf {after} — höchstens eine Stufe je Vorgang, mit Begründung")
            elif after == "INDEPENDENTLY_REPLICATED" and (entry.get("external_replication") or "none").lower().startswith("none"):
                issues.append("INDEPENDENTLY_REPLICATED ohne eingetragene externe Replikation")
    if registry == "replication" and field == "count":
        import re
        if not re.fullmatch(r"\d+/\d+", str(after or "")):
            issues.append("Replikationsstand muss die Form n/m haben (z. B. 1/5)")
    # the whole registry set must still validate with the change applied
    try:
        regs = registries.load_all()
        key = {"claims": "claims", "replication": "replication"}[registry]
        merged = {**regs, key: changed_doc}
        violations = registries.validate(merged)
        issues += [f"{v['rule']}: {v['entity']} — {v['detail']}" for v in violations]
    except Exception as e:
        issues.append(f"Integritätsprüfung nicht durchführbar: {type(e).__name__}: {str(e)[:120]}")
    return issues


# -- apply ---------------------------------------------------------------------------------------------------------------

def apply(conn, registry: str, entity_id: str, field: str, value, actor: str, reason: str, source: dict | None = None) -> dict:
    """🔒 Founder only. Writes exactly one field, after the same preview check, and records the change."""
    if actor != "founder":
        raise GovernanceError("Registeränderungen sind Founder-Sache; ein Agent darf sie nie schreiben")
    pv = preview(registry, entity_id, field, value, reason)
    if pv["unchanged"]:
        raise ValueError("keine Änderung (Wert ist bereits gesetzt)")
    if pv["issues"]:
        raise ValueError(f"Integritätsprüfung fehlgeschlagen: {pv['issues']}")
    p, doc = _load(registry)
    entry = _entry(doc, registry, entity_id)
    entry[field] = pv["after"]
    if registry == "claims":
        entry["last_updated"] = datetime.now(timezone.utc).date().isoformat()
    before_hash = _file_hash(p)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    after_hash = _file_hash(p)
    registries.load_all.cache_clear() if hasattr(registries.load_all, "cache_clear") else None
    rec = {"at": _now(), "actor": actor, "registry": registry, "entity_id": entity_id, "field": field, "before": pv["before"], "after": pv["after"], "reason": reason,
           "source": source or {}, "file": FILE_OF[registry], "file_sha256_before": before_hash, "file_sha256_after": after_hash, "version": VERSION}
    with CHANGELOG.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if conn is not None:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'registry.apply', %s, %s)", (actor, f"{registry}:{entity_id}.{field}", json.dumps(rec, ensure_ascii=False)))
        conn.commit()
    return {"applied": True, **rec}


def changelog(limit: int = 500) -> list[dict]:
    if not CHANGELOG.exists():
        return []
    out = []
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return list(reversed(out))


def revert_proposal(entry_index: int = 0) -> dict:
    """Proposes the inverse of a logged change — as a proposal, never applied automatically."""
    log = changelog()
    if not log or entry_index >= len(log):
        raise KeyError("no such changelog entry")
    e = log[entry_index]
    return {"registry": e["registry"], "entity_id": e["entity_id"], "field": e["field"], "value": e["before"], "reason": f"Rücknahme der Änderung vom {e['at'][:19]} ({e['field']}: {e['before']!r} → {e['after']!r})",
            "source": {"kind": "revert", "of": e["at"]}, "note": "Vorschlag — der Founder muss ihn wie jede andere Änderung bestätigen"}
