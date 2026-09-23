"""Framing test: Laya classifies a state into the option that best describes it. So make the
target the state and ask which option names it -- instead of page text as state."""
import os, json, math, warnings
os.environ["HF_HUB_OFFLINE"] = "1"; warnings.filterwarnings("ignore")
from laya import Agent
SNAP = "/root/.cache/huggingface/hub/models--convaiinnovations--laya/snapshots/5e7b2b1b8ca2ecdd3f2322d94069c9b6ce7e844b"
cases = json.load(open("/tmp/replay_targets.json", encoding="utf-8"))
def wilson(k, n, z=1.96):
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d; s = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (round(max(0, c-s), 3), round(min(1, c+s), 3))
FRAMES = {
  "names_target": lambda c: ({"target": c["target"]}, "Which option names the same thing as `target`?"),
  "opens_target": lambda c: ({"target": c["target"]}, "Which element opens `target`?"),
}
out = {}
for name, sub in (("english", None), ("typed-decisions", "typed-decisions")):
    agent = Agent(SNAP, device="cpu", subfolder=sub) if sub else Agent(SNAP, device="cpu")
    for fname, f in FRAMES.items():
        ok = two_ok = two_n = 0
        for c in cases:
            state, instr = f(c)
            q = {"type": "choice", "instructions": instr, "criteria": c["question"]["criteria"]}
            a = agent.system_one(state, {"q": q})["answers"]["q"]
            hit = a["choice"] in set(c["gold"]); ok += hit
            if len(q["criteria"]) == 2: two_n += 1; two_ok += hit
        out[f"{name}/{fname}"] = {"correct": ok, "n": len(cases), "wilson": wilson(ok, len(cases)), "two_option": f"{two_ok}/{two_n}"}
        print(name, fname, out[f"{name}/{fname}"], flush=True)
    del agent
json.dump(out, open("/tmp/replay_frame_results.json", "w"), indent=1)
