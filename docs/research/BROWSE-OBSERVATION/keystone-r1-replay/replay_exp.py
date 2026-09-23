"""Validation experiment: does option order, and does the checkpoint, change Laya's accuracy
on the 45 logged Keystone choice questions whose correct option was offered?

Read-only against the service: a separate process in the container, its own Router."""
import json, math, time, warnings
warnings.filterwarnings("ignore")
from laya import Router

cases = json.load(open("/tmp/replay_offered.json", encoding="utf-8"))
r = Router(preload=False, max_loaded=2)

def ask(model, state, qid, q, reverse):
    crit = q["criteria"]
    items = list(crit.items())
    if reverse: items = items[::-1]
    q2 = dict(q); q2["criteria"] = dict(items)
    out = r.predict(state, {qid: q2}, model=model)
    a = out["answers"][qid]
    return a["choice"], a.get("probabilities") or {}

def wilson(k, n, z=1.96):
    if not n: return (0.0, 1.0)
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; s = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (round(max(0, c-s), 3), round(min(1, c+s), 3))

results = {}
t0 = time.time()
for model in ("english", "typed-decisions"):
    fwd_ok = rev_ok = avg_ok = repro = 0
    per = []
    for c in cases:
        ch_f, p_f = ask(model, c["state"], c["qid"], c["question"], False)
        ch_r, p_r = ask(model, c["state"], c["qid"], c["question"], True)
        keys = set(p_f) | set(p_r)
        avg = {k: (p_f.get(k, 0) + p_r.get(k, 0)) / 2 for k in keys}
        ch_a = max(avg, key=avg.get)
        g = set(c["gold"])
        fwd_ok += ch_f in g; rev_ok += ch_r in g; avg_ok += ch_a in g
        if model == "english": repro += ch_f == c["logged_choice"]
        per.append({"id": c["id"], "n": len(c["question"]["criteria"]), "fwd": ch_f in g, "rev": ch_r in g,
                    "avg": ch_a in g, "flip": ch_f != ch_r, "top_avg": round(avg[ch_a], 3)})
    n = len(cases)
    results[model] = {"n": n, "forward": [fwd_ok, wilson(fwd_ok, n)], "reversed": [rev_ok, wilson(rev_ok, n)],
                      "order_averaged": [avg_ok, wilson(avg_ok, n)],
                      "choice_flips_with_order": sum(p["flip"] for p in per), "per": per}
    if model == "english":
        results[model]["reproduces_logged_choice"] = repro
    print(model, {k: v for k, v in results[model].items() if k != "per"}, flush=True)
print("elapsed_s", round(time.time() - t0, 1))
json.dump(results, open("/tmp/replay_results.json", "w"), indent=1)
