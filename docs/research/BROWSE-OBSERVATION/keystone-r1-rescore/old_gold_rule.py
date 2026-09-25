import os
import json, re, collections, math, sys, itertools
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "keystone-r1-run")  # `dvc pull` restores it
tasks = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(D, "tasks.jsonl"), encoding="utf-8")}
calls = [json.loads(l) for l in open(os.path.join(D, "calls.jsonl"), encoding="utf-8")]
lay = [c for c in calls if c["kind"] == "laya" and c["purpose"] == "decision"]
ro = json.load(open(os.path.join(D, "replay_offered.json"), encoding="utf-8"))

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - s), min(1, c + s))

def target(tid, mode):
    q = re.findall(r'"([^"]+)"', tasks[tid]["goal"])
    if not q: return None
    return q[-1] if mode == "last" else q[0]

def rows(mode="last", ci=False, key="state"):
    out = {}
    for c in lay:
        (qid, q), = c["request"]["questions"].items()
        t = target(c["task"], mode)
        if not t: continue
        if key == "state":
            k = (c["task"], c["request"]["state"], qid, json.dumps(q, sort_keys=True, ensure_ascii=False))
        elif key == "nostate":
            k = (c["task"], qid, json.dumps(q, sort_keys=True, ensure_ascii=False))
        else:
            k = (c["request"]["state"], json.dumps(q, sort_keys=True, ensure_ascii=False))
        if k in out: continue
        f = (lambda s: t.lower() in s.lower()) if ci else (lambda s: t in s)
        gold = [o for o, lab in q["criteria"].items() if f(lab)]
        ch = c["response"]["answers"][qid]["choice"]
        out[k] = dict(task=c["task"], qid=qid, q=q, state=c["request"]["state"], gold=gold, choice=ch, target=t)
    return list(out.values())

if __name__ == "__main__":
    for mode, ci, key in itertools.product(["last", "first"], [False, True], ["state", "nostate", "global"]):
        R = rows(mode, ci, key)
        off = [r for r in R if r["gold"]]
        ok = [r for r in off if r["choice"] in r["gold"]]
        print(mode, ci, key, len(R), len(R) - len(off), len(off), len(ok))
