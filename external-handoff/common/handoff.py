#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "TRACK-REGISTRY.json").read_text())

def sh(cmd: list[str]) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

def host_preflight():
    out = {"platform": platform.platform(), "python": sys.version, "executables": {}, "disk": {}}
    for name in ["git","bash","docker","uv","conda","nvidia-smi","python3.10","python3.11","python3.12"]:
        p = shutil.which(name)
        out["executables"][name] = {"available": bool(p), "path": p}
    ext = Path(os.environ.get("LOGOS_EXT_ROOT", str(Path.home() / "logos-external")))
    ext.mkdir(parents=True, exist_ok=True)
    du = shutil.disk_usage(ext)
    out["disk"] = {"path": str(ext), "free_bytes": du.free, "total_bytes": du.total}
    if shutil.which("docker"):
        out["docker_info"] = sh(["docker","info","--format","{{json .ServerVersion}}"])
    if shutil.which("nvidia-smi"):
        out["nvidia_smi"] = sh(["nvidia-smi","--query-gpu=name,memory.total,driver_version","--format=csv,noheader"])
    return out

def track_preflight(track: str):
    cfg = REGISTRY["tracks"][track]
    out = {"track": track, "status": cfg["status"], "source_pins": cfg["source_pins"], "ready": True}
    return out

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("host-preflight")
    p = sub.add_parser("plan"); p.add_argument("--track", choices=list(REGISTRY["tracks"]) + ["all"], required=True)
    q = sub.add_parser("preflight"); q.add_argument("--track", choices=list(REGISTRY["tracks"]) + ["all"], required=True)
    args = ap.parse_args()
    if args.cmd == "list":
        for tid in REGISTRY["priority_order"]:
            c = REGISTRY["tracks"][tid]
            print(f"{c['priority']:>2}  {tid:<16} {c['status']:<42} {c['title']}")
        return
    if args.cmd == "host-preflight":
        print(json.dumps(host_preflight(), indent=2)); return
    tracks = list(REGISTRY["tracks"]) if args.track == "all" else [args.track]
    if args.cmd == "plan":
        for t in tracks:
            c = REGISTRY["tracks"][t]
            print(f"\n## {t}: {c['title']}")
            print(f"status: {c['status']}")
            print(f"scientific ceiling: {c['scientific_ceiling']}")
        return
    print(json.dumps({t: track_preflight(t) for t in tracks}, indent=2))

if __name__ == "__main__":
    main()
