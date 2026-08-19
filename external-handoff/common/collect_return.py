#!/usr/bin/env python3
from __future__ import annotations
import argparse, fnmatch, hashlib, json, shutil, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=json.loads((ROOT/"TRACK-REGISTRY.json").read_text())
FORBIDDEN_PARTS={".env",".envrc","credentials","credential","secret","secrets","token","api_key","apikey","private_key","id_rsa","id_ed25519"}

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""):h.update(b)
    return h.hexdigest()

def forbidden(rel:str):
    low=rel.lower(); parts=set(Path(low).parts)
    if any(x in parts for x in FORBIDDEN_PARTS): return True
    return any(x in Path(low).name for x in ["secret","credential","api_key","apikey","private_key"])

def matches(rel:str, patterns:list[str]):
    return any(fnmatch.fnmatch(rel,p) or Path(rel).match(p) for p in patterns)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--track",choices=list(REG["tracks"]),required=True)
    ap.add_argument("--run-root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--allow-large",action="store_true")
    args=ap.parse_args(); cfg=REG["tracks"][args.track]
    if not args.run_root.exists(): raise SystemExit("RUN_ROOT_NOT_FOUND")
    patterns=cfg.get("return_globs",[]); selected=[]
    for p in sorted(args.run_root.rglob("*")):
        if not p.is_file() or p.is_symlink(): continue
        rel=p.relative_to(args.run_root).as_posix()
        if forbidden(rel): continue
        if patterns and not matches(rel,patterns): continue
        if p.stat().st_size>2_000_000_000 and not args.allow_large: continue
        selected.append((p,rel))
    present_names={Path(rel).name for _,rel in selected}; required=cfg.get("return_required",[]); missing=[]
    for r in required:
        if "/" in r:
            if not any(rel.endswith(r) for _,rel in selected): missing.append(r)
        elif r not in present_names: missing.append(r)
    envelope={"schema":"logos-external-return-v1","track":args.track,"created_at":datetime.now(timezone.utc).isoformat(),"run_root_basename":args.run_root.name,"scientific_ceiling":cfg["scientific_ceiling"],"source_pins":cfg["source_pins"],"required_missing":missing,"status":"COMPLETE_RETURN" if not missing else "PARTIAL_RETURN","files":[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        stage=Path(td)/f"{args.track}-return"; stage.mkdir()
        for p,rel in selected:
            q=stage/"files"/rel; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,q)
            envelope["files"].append({"path":f"files/{rel}","bytes":p.stat().st_size,"sha256":sha256(p)})
        (stage/"RETURN-ENVELOPE.json").write_text(json.dumps(envelope,indent=2)+"\n")
        (stage/"README.md").write_text(f"# LOGOS external return: {args.track}\n\nStatus: `{envelope['status']}`\n\nAPI credentials and .env files are deliberately excluded.\n")
        if args.output.exists(): args.output.unlink()
        with zipfile.ZipFile(args.output,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in sorted(stage.rglob("*")):
                if p.is_file(): z.write(p,arcname=f"{stage.name}/{p.relative_to(stage).as_posix()}")
    d=sha256(args.output); args.output.with_suffix(args.output.suffix+".sha256").write_text(f"{d}  {args.output.name}\n")
    print(json.dumps({"output":str(args.output),"sha256":d,"files":len(selected),"missing_required":missing,"status":envelope["status"]},indent=2))

if __name__=="__main__": main()
