#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path

def git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git","-C",str(repo),*args], capture_output=True, text=True)
    if p.returncode:
        raise SystemExit(p.stderr.strip() or p.stdout.strip())
    return p.stdout.strip()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",type=Path,required=True); ap.add_argument("--commit",required=True); args=ap.parse_args()
    if not (args.repo/".git").exists(): raise SystemExit("NOT_A_GIT_REPOSITORY")
    head=git(args.repo,"rev-parse","HEAD"); dirty=bool(git(args.repo,"status","--porcelain"))
    out={"repo":str(args.repo),"expected_commit":args.commit,"head":head,"commit_match":head==args.commit,"dirty":dirty}
    print(json.dumps(out,indent=2))
    if head!=args.commit or dirty: raise SystemExit(2)
if __name__=="__main__": main()
