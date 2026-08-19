#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,zipfile
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("zip",type=Path); args=ap.parse_args()
    with zipfile.ZipFile(args.zip) as z:
        bad=z.testzip(); names=z.namelist(); env=[n for n in names if n.endswith("RETURN-ENVELOPE.json")]
        if bad: raise SystemExit(f"CRC_FAIL:{bad}")
        if len(env)!=1: raise SystemExit("RETURN_ENVELOPE_MISSING_OR_DUPLICATE")
        obj=json.loads(z.read(env[0]))
        print(json.dumps({"crc":"PASS","track":obj.get("track"),"files":len(obj.get("files",[]))},indent=2))
if __name__=="__main__": main()
