"""Does the state drown the question? Same 45 questions, same pinned revision, three states:
full (as jev sent it), goal-only (first line), and goal + finish (first two lines)."""
import os, json, math, time, warnings
os.environ["HF_HUB_OFFLINE"] = "1"
warnings.filterwarnings("ignore")
from laya import Agent
SNAP = "/root/.cache/huggingface/hub/models--convaiinnovations--laya/snapshots/5e7b2b1b8ca2ecdd3f2322d94069c9b6ce7e844b"
cases = json.load(open("/tmp/replay_offered.json", encoding="utf-8"))
def wilson(k, n, z=1.96):
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d; s = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (round(max(0, c-s), 3), round(min(1, c+s), 3))
variants = {
    "full": lambda s: s,
    "goal_only": lambda s: s.split("\n")[0],
    "goal_finish": lambda s: "\n".join(s.split("\n")[:2]),
}
out = {}
for name, sub in (("english", None), ("typed-decisions", "typed-decisions")):
    agent = Agent(SNAP, device="cpu", subfolder=sub) if sub else Agent(SNAP, device="cpu")
    for vname, f in variants.items():
        ok = 0; two_ok = two_n = 0
        for c in cases:
            a = agent.system_one(f(c["state"]), {c["qid"]: c["question"]})["answers"][c["qid"]]
            hit = a["choice"] in set(c["gold"]); ok += hit
            if len(c["question"]["criteria"]) == 2: two_n += 1; two_ok += hit
        out[f"{name}/{vname}"] = {"correct": ok, "n": len(cases), "wilson": wilson(ok, len(cases)), "two_option": f"{two_ok}/{two_n}"}
        print(name, vname, out[f"{name}/{vname}"], flush=True)
    del agent
json.dump(out, open("/tmp/replay_state_results.json", "w"), indent=1)
