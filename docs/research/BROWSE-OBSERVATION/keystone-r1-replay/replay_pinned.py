"""Pinned replay: the exact revision (5e7b2b1b) that answered the Keystone run, loaded offline from
the local snapshot, so order and checkpoint effects are measured without revision drift."""
import os, json, math, time, warnings
os.environ["HF_HUB_OFFLINE"] = "1"
warnings.filterwarnings("ignore")
from laya import Agent

SNAP = "/root/.cache/huggingface/hub/models--convaiinnovations--laya/snapshots/5e7b2b1b8ca2ecdd3f2322d94069c9b6ce7e844b"
cases = json.load(open("/tmp/replay_offered.json", encoding="utf-8"))

def wilson(k, n, z=1.96):
    if not n: return (0.0, 1.0)
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d; s = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (round(max(0, c-s), 3), round(min(1, c+s), 3))

def run(agent, c, reverse):
    q = dict(c["question"]); items = list(q["criteria"].items())
    q["criteria"] = dict(items[::-1] if reverse else items)
    a = agent.system_one(c["state"], {c["qid"]: q})["answers"][c["qid"]]
    return a["choice"], a.get("probabilities") or {}

res = {}
for name, sub in (("english", None), ("typed-decisions", "typed-decisions")):
    t0 = time.time()
    agent = Agent(SNAP, device="cpu", subfolder=sub) if sub else Agent(SNAP, device="cpu")
    f = r = a = rep = flips = 0; per = []
    for c in cases:
        cf, pf = run(agent, c, False); cr, pr = run(agent, c, True)
        avg = {k: (pf.get(k, 0) + pr.get(k, 0)) / 2 for k in set(pf) | set(pr)}
        ca = max(avg, key=avg.get); g = set(c["gold"])
        f += cf in g; r += cr in g; a += ca in g; flips += cf != cr
        if name == "english": rep += cf == c["logged_choice"]
        per.append({"id": c["id"], "n": len(c["question"]["criteria"]), "fwd": cf in g, "rev": cr in g, "avg": ca in g})
    n = len(cases)
    two = [p for p in per if p["n"] == 2]
    res[name] = {"n": n, "forward": [f, wilson(f, n)], "reversed": [r, wilson(r, n)], "order_averaged": [a, wilson(a, n)],
                 "flips": flips, "two_option": {"n": len(two), "fwd": sum(p["fwd"] for p in two),
                 "rev": sum(p["rev"] for p in two), "avg": sum(p["avg"] for p in two)},
                 "seconds": round(time.time() - t0, 1), "per": per}
    if name == "english": res[name]["reproduces_logged_choice"] = rep
    print(name, {k: v for k, v in res[name].items() if k != "per"}, flush=True)
    del agent
json.dump(res, open("/tmp/replay_pinned_results.json", "w"), indent=1)
