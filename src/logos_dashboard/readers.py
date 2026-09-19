"""Narrative and lab readers: closures (05-WORK-ORDERS), session reports, git/gh, lab runs. Read-only. Fields a reader cannot extract are listed in `unparsed`, never guessed."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .registries import ROOT

ORDERS = ROOT / "05-WORK-ORDERS"; SESSIONS = ROOT / "09-SESSIONS"
VERDICT_CLASS = [("FALSIFIED", "falsified"), ("INVALID", "invalid"), ("PARTIALLY", "partial"), ("SUPPORTED", "supported"), ("VALIDATED", "validated"), ("APPROVED", "approved"), ("AMENDED", "amended"), ("CONSOLIDATED", "validated")]


def _first(pattern: str, text: str, flags=0) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def verdict_class(v: str | None) -> str:
    if not v:
        return "other"
    for k, c in VERDICT_CLASS:
        if k in v:
            return c
    return "other"


def read_closure(path: Path) -> dict:
    s = path.read_text(encoding="utf-8")
    oid = path.name[len("NEXT-SESSION-"):-3]
    verdict = _first(r"\*\*[^*\n]*[Vv]erdict[^*\n]*:\*\*\s*`([^`]+)`", s)
    closure = _first(r"## Closure\s*```text\n(.*?)```", s, re.S)
    successor = _first(r"## Successor[^\n]*\n\n`([A-Z0-9\-]+)`", s)
    findings = re.findall(r"`?([A-Z]{2,5}-F\d+)`?\s+(CRITICAL|HIGH|MEDIUM|LOW|INFO)", s)
    hashes = re.findall(r"`([0-9a-f]{8,64})…?`", s)
    unparsed = [k for k, v in (("verdict", verdict), ("closure", closure), ("successor", successor), ("closed", _first(r"\*\*Closed:\*\*\s*([^\n]+)", s))) if v is None]
    return {"id": oid, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "kind": _first(r"\*\*Kind:\*\*\s*([^\n]+)", s), "verdict": verdict, "verdict_class": verdict_class(verdict),
            "closed": _first(r"\*\*Closed:\*\*\s*([^\n]+)", s), "base": _first(r"\*\*Base:\*\*\s*`([^`]+)`", s), "closure_block": closure, "successor_id": successor, "successor_executed": False,
            "findings": [{"id": a, "severity": b} for a, b in dict.fromkeys(findings)], "hash_refs": list(dict.fromkeys(hashes))[:12], "open_decisions": [p.strip() for p in re.findall(r"## Governance question[^\n]*\n(.*?)(?:\n## |\Z)", s, re.S)],
            "unparsed": unparsed}


def closures() -> list[dict]:
    paths = sorted(ORDERS.glob("NEXT-SESSION-*.md"))
    out = [{**read_closure(p), "_mtime": p.stat().st_mtime} for p in paths]
    out.sort(key=lambda c: ((c["closed"] or "")[:10], c["_mtime"]))          # closure date, then file modification as tie-break
    for c in out:
        c.pop("_mtime")
    return out


def session_report(order_id: str) -> dict | None:
    for d in SESSIONS.iterdir():
        if d.is_dir() and d.name.endswith(order_id):
            p = d / "SESSION-REPORT.md"
            if p.exists():
                s = p.read_text(encoding="utf-8")
                sections = [{"heading": h.strip(), "body": b.strip()} for h, b in re.findall(r"\n## ([^\n]+)\n(.*?)(?=\n## |\Z)", s, re.S)]
                return {"order_id": order_id, "path": str(p.relative_to(ROOT)).replace("\\", "/"), "title": _first(r"^# ([^\n]+)", s), "sections": sections, "markdown": s}
    return None


def git_state() -> dict:
    def run(*a):
        try:
            return subprocess.run(a, capture_output=True, text=True, cwd=ROOT, timeout=20).stdout.strip()
        except Exception as e:  # pragma: no cover
            return f"unavailable: {e}"
    log = [dict(zip(("sha", "date", "subject"), l.split("\t", 2))) for l in run("git", "log", "-40", "--format=%h\t%ad\t%s", "--date=short").splitlines() if "\t" in l]
    return {"branch": run("git", "branch", "--show-current"), "head": run("git", "rev-parse", "--short", "HEAD"), "dirty": bool(run("git", "status", "--porcelain")), "unpushed": run("git", "log", "--oneline", "@{u}..HEAD").count("\n") + (1 if run("git", "log", "--oneline", "@{u}..HEAD") else 0), "log": log}


def pull_requests() -> list[dict]:
    try:
        out = subprocess.run(["gh", "pr", "list", "--state", "all", "--limit", "60", "--json", "number,title,state,baseRefName,headRefName"], capture_output=True, text=True, cwd=ROOT, timeout=30).stdout
        return sorted(json.loads(out or "[]"), key=lambda p: -p["number"])
    except Exception:
        return []


def lab_runs() -> dict:
    """Lab (Postgres) runs/preregistrations/artifacts via the existing research backends. Records-only when unreachable."""
    try:
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from logos_research.infra.backends import backends_from_env
        be = backends_from_env(); repo = be["repository"].connect()
        with repo._conn.cursor() as c:
            c.execute("SELECT run_id, experiment_id, run_status, scientific_verdict, git_sha, preregistration_hash, started_at, completed_at, external_refs FROM runs ORDER BY started_at DESC LIMIT 300")
            runs = [dict(zip(("run_id", "experiment_id", "run_status", "scientific_verdict", "git_sha", "prereg_hash", "started_at", "completed_at", "external_refs"), r)) for r in c.fetchall()]
            c.execute("SELECT preregistration_hash, experiment_id, revision, supersedes, frozen_at FROM preregistrations ORDER BY experiment_id, revision")
            pre = [dict(zip(("hash", "experiment_id", "revision", "supersedes", "frozen_at"), r)) for r in c.fetchall()]
            c.execute("SELECT negative_id, hypothesis, what_falsified_it, scope_of_falsification, run_id, recorded_at FROM negative_results ORDER BY recorded_at DESC LIMIT 300")
            neg = [dict(zip(("negative_id", "hypothesis", "what_falsified_it", "scope", "run_id", "recorded_at"), r)) for r in c.fetchall()]
            arts = []
        repo.close()
        return {"records_only": False, "runs": runs, "preregistrations": pre, "artifacts": arts, "negative_results": neg}
    except Exception as e:
        return {"records_only": True, "error": str(e)[:200], "runs": [], "preregistrations": [], "artifacts": [], "negative_results": []}
