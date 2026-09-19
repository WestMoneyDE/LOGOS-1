"""Repository work orders: every document in 05-WORK-ORDERS/ mirrored into `ros_work_orders` (ids `REPO:<ID>`), chained by successor, linked to theses.

The documents stay the record; the mirror is re-derived on every import (idempotent) and never edited by hand. Fields the parser cannot find are `NOT_EXTRACTED`,
never guessed. State mapping from the closure verdict class: supported/validated/approved/amended/partial/other-with-closure -> VALIDATED; falsified/invalid -> FALSIFIED;
documents without closure (QUEUED-*, P0-*, generated master orders whose NEXT-SESSION does not exist) -> DRAFT (open).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from psycopg.rows import dict_row

from .. import readers
from ..readers import ORDERS

CLAIM = re.compile(r"\bLOGOS-[A-Z0-9]+-\d{3}\b")
TRACK_WORDS = {"authority": ("authority", "grant", "canonical", "bridge"), "provenance": ("provenance", "binding", "relational", "prediction"), "cognitive-provenance": ("cognitive",), "measurement": ("measurement", "falsification", "governance", "dashboard", "inference", "benchmark", "radar"),
               "memory": ("memory", "persistent", "state", "consolidation", "longmemeval"), "trajectory": ("trajectory", "risk", "value-of-information", "wmr", "arc-agi", "tcv", "scb", "enf", "mbe")}
VERSION = "ros-repo-orders/1"


def _first(pattern: str, text: str, flags=re.M) -> str | None:
    m = re.search(pattern, text, flags); return m.group(1).strip() if m else None


def _question(text: str) -> str:
    for pat in (r"## (?:Primary|Scientific|Research) question[^\n]*\n+([^\n#]+)", r"## 1\.? [^\n]*question[^\n]*\n+([^\n#]+)", r"\*\*Question:\*\*\s*([^\n]+)", r"## Goal[^\n]*\n+([^\n#]+)"):
        q = _first(pat, text, re.M | re.I)
        if q:
            return q[:400]
    return "NOT_EXTRACTED"


def _track(text: str, title: str) -> str | None:
    t = (_first(r"\*\*Track:\*\*\s*([^\n]+)", text) or _first(r"^Track:\s*`?([^`\n]+)`?", text) or "").lower() + " " + title.lower()
    scores = {k: sum(t.count(wd) for wd in ws) for k, ws in TRACK_WORDS.items()}
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0] if best[1] else None


def parse_documents() -> list[dict]:
    cl = {c["id"]: c for c in readers.closures()}
    out = []; closure_ids = {p.stem.replace("NEXT-SESSION-", "") for p in ORDERS.glob("NEXT-SESSION-*.md")}
    for p in sorted(ORDERS.glob("*.md")):
        text = p.read_text(encoding="utf-8"); name = p.stem
        oid = name.replace("NEXT-SESSION-", "") if name.startswith("NEXT-SESSION-") else name
        if not name.startswith("NEXT-SESSION-") and oid in closure_ids:
            continue                                                        # the closure is the record of that order; the generated master order is its input
        title = (_first(r"^# (.+)$", text) or oid).strip()
        c = cl.get(oid) if name.startswith("NEXT-SESSION-") else cl.get(oid)
        if name.startswith("NEXT-SESSION-"):
            vc = (c or {}).get("verdict_class"); closed = (c or {}).get("closed")
            state = "FALSIFIED" if vc in ("falsified", "invalid") else "VALIDATED" if closed else "DRAFT"
        else:
            has_closure = oid in cl
            state = ("FALSIFIED" if cl[oid].get("verdict_class") in ("falsified", "invalid") else "VALIDATED") if has_closure else "DRAFT"
        status_line = _first(r"\*\*Status:\*\*\s*([^\n]+)", text)
        out.append({"work_order_id": f"REPO:{oid}", "order_id": oid, "path": str(p.relative_to(ORDERS.parents[0])).replace("\\", "/"), "title": title, "state": state, "verdict": (c or {}).get("verdict"), "verdict_class": (c or {}).get("verdict_class"),
                    "closed": (c or {}).get("closed"), "successor": (c or {}).get("successor_id"), "status_line": status_line, "question": _question(text), "track": _track(text, title), "claims": sorted(set(CLAIM.findall(text)))[:12],
                    "kind": "closure" if name.startswith("NEXT-SESSION-") else "queued" if name.startswith("QUEUED-") else "master_order"})
    return out


def import_orders(conn, actor: str = "system") -> dict:
    docs = parse_documents(); ids = {d["work_order_id"] for d in docs}; by_oid = {d["order_id"]: d for d in docs}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT thesis_id, claim_ids, track FROM ros_theses"); theses = cur.fetchall()
        n_new = n_upd = 0
        for d in docs:
            spec = {"question": d["question"], "scope": "NOT_EXTRACTED", "hypothesis": "NOT_EXTRACTED", "falsification_criterion": "NOT_EXTRACTED", "metrics": ["NOT_EXTRACTED"], "governance": {"record": d["path"]}, "caps": {"record": d["path"]},
                    "origin": {"repository": True, "path": d["path"], "kind": d["kind"], "verdict": d["verdict"], "verdict_class": d["verdict_class"], "closed": d["closed"], "status_line": d["status_line"], "title": d["title"], "claims": d["claims"], "track": d["track"], "version": VERSION}}
            th = next((t["thesis_id"] for t in theses if set(t["claim_ids"] or []) & set(d["claims"])), None)          # link by shared claim ids only (track alone is too weak)
            cur.execute("SELECT state FROM ros_work_orders WHERE work_order_id = %s", (d["work_order_id"],)); row = cur.fetchone()
            if row is None:
                cur.execute("INSERT INTO ros_work_orders (work_order_id, thesis_id, state, spec, created_by, approved_by, approved_at) VALUES (%s, %s, %s, %s, 'system', %s, CASE WHEN %s <> 'DRAFT' THEN now() END)", (d["work_order_id"], th, d["state"], json.dumps(spec), "founder (repository record)" if d["state"] != "DRAFT" else None, d["state"])); n_new += 1
            else:
                cur.execute("UPDATE ros_work_orders SET state = %s, spec = %s, thesis_id = COALESCE(%s, thesis_id), updated_at = now() WHERE work_order_id = %s", (d["state"], json.dumps(spec), th, d["work_order_id"])); n_upd += 1
        edges = 0
        for d in docs:
            succ = d["successor"]
            if succ and succ in by_oid and by_oid[succ]["work_order_id"] != d["work_order_id"]:
                cur.execute("INSERT INTO ros_work_order_deps (child, parent, mandatory) VALUES (%s, %s, TRUE) ON CONFLICT DO NOTHING", (by_oid[succ]["work_order_id"], d["work_order_id"])); edges += cur.rowcount
        cur.execute("INSERT INTO ros_audit (actor, action, subject, detail) VALUES (%s, 'repo_orders.import', '05-WORK-ORDERS', %s)", (actor, json.dumps({"documents": len(docs), "new": n_new, "updated": n_upd, "edges_added": edges})))
    conn.commit()
    return {"documents": len(docs), "new": n_new, "updated": n_upd, "edges_added": edges, "states": {s: sum(1 for d in docs if d["state"] == s) for s in ("VALIDATED", "FALSIFIED", "DRAFT")}, "version": VERSION}


def chain(conn) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT work_order_id, thesis_id, state, spec->'origin' AS origin FROM ros_work_orders WHERE work_order_id LIKE 'REPO:%' ORDER BY COALESCE(spec->'origin'->>'closed', '9999'), work_order_id"); return cur.fetchall()
