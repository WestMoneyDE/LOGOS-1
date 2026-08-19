#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("path",type=Path); args=ap.parse_args(); p=args.path
    if p.is_file():
        print(json.dumps({"path":str(p),"bytes":p.stat().st_size,"sha256":sha256(p)},indent=2)); return
    if not p.is_dir(): raise SystemExit("PATH_NOT_FOUND")
    rows=[]
    for f in sorted(x for x in p.rglob("*") if x.is_file() and not x.is_symlink()):
        rows.append({"path":f.relative_to(p).as_posix(),"bytes":f.stat().st_size,"sha256":sha256(f)})
    print(json.dumps({"root":str(p),"files":rows},indent=2))
if __name__=="__main__": main()
