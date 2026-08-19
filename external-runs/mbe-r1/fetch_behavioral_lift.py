#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    from datasets import load_dataset
    ds=load_dataset("neulab/behavioral-lift",split="llm")
    if len(ds)!=8282:raise SystemExit(f"ROW_COUNT_MISMATCH:{len(ds)}")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    ds.to_parquet(str(args.output))
    prov={"dataset":"neulab/behavioral-lift","split":"llm","rows":len(ds),"sha256":sha256(args.output),"bytes":args.output.stat().st_size}
    args.output.with_suffix(args.output.suffix+".provenance.json").write_text(json.dumps(prov,indent=2)+"\n")
    print(json.dumps(prov,indent=2))
if __name__=="__main__":main()
