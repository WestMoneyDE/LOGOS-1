"""Merge the in-container replay into rescore.json and print the replay tables."""
import json, os, collections
from labels import wilson

HERE = os.path.dirname(os.path.abspath(__file__))
base = json.load(open(os.path.join(HERE, "rescore_base.json"), encoding="utf-8"))
rep = json.load(open(os.path.join(HERE, "replay_results.json"), encoding="utf-8"))
rows = base["rows"]
routes = {int(k): v for k, v in rep["routes"].items()}
by = collections.defaultdict(dict)
for r in rep["results"]:
    by[r["id"]][r["variant"]] = r
for r in rows:
    r["routed_model"] = routes.get(r["id"])
    r["replay"] = {v: dict(model=x["model"], choice=x["choice"], probabilities=x["probabilities"]) for v, x in by[r["id"]].items()}


def maxdiff(a, b):
    return max(abs(a.get(k, 0) - b.get(k, 0)) for k in set(a) | set(b))


# ---------------------------------------------------------------- reproduction
repro = {}
for v in ("a_routed", "a_english"):
    R = [r for r in rows if v in r["replay"]]
    match = [r for r in R if r["replay"][v]["choice"] == r["choice"]]
    d = [maxdiff(r["replay"][v]["probabilities"], r["probabilities"]) for r in R]
    per_model = collections.Counter()
    for r in R:
        per_model[(r["routed_model"], "n")] += 1
        per_model[(r["routed_model"], "match")] += r["replay"][v]["choice"] == r["choice"]
    repro[v] = dict(n=len(R), choice_match=len(match),
                    max_prob_diff_max=round(max(d), 4) if d else None,
                    n_prob_diff_le_0_01=sum(1 for x in d if x <= 0.01),
                    by_routed_model={m: [per_model[(m, "match")], per_model[(m, "n")]] for m in sorted({k for k, _ in per_model})},
                    mismatches=[dict(id=r["id"], task=r["task"], qid=r["qid"], routed=r["routed_model"],
                                     logged=r["choice"], replay=r["replay"][v]["choice"]) for r in R
                                if r["replay"][v]["choice"] != r["choice"]][:40])
    # the 45 cases of the earlier replay
ids45 = {x["row_id"] for x in base["reconciliation_keystone_45_rows"]}
for v in ("a_routed", "a_english"):
    R = [r for r in rows if r["id"] in ids45 and v in r["replay"]]
    repro[v]["keystone_45_subset"] = [sum(1 for r in R if r["replay"][v]["choice"] == r["choice"]), len(R)]
base["reproduction"] = repro

# ---------------------------------------------------------------- framing on item/next with gold present
F = [r for r in rows if r["kind"] in ("item", "next") and r["status"] == "labelled" and r["gold_present"]]
fr = {}
for v in ("a_routed", "a_english", "a_typed", "b_english", "b_typed", "b_routed", "c_english", "c_typed", "c_routed"):
    R = [r for r in F if v in r["replay"]]
    ok = sum(1 for r in R if r["replay"][v]["choice"] in r["gold"])
    fr[v] = dict(n=len(R), correct=ok, wilson=wilson(ok, len(R)))
fr["logged"] = dict(n=len(F), correct=sum(1 for r in F if r["correct"]), wilson=wilson(sum(1 for r in F if r["correct"]), len(F)))
base["framing"] = fr
base["framing_rows"] = [dict(id=r["id"], task=r["task"], qid=r["qid"], n_options=r["n_options"], gold=r["gold"],
                             logged=r["choice"], **{v: r["replay"][v]["choice"] for v in r["replay"]}) for r in F]

# ---------------------------------------------------------------- holds control
H = [r for r in rows if r["kind"] == "holds"]
hc = {}
for v in ("a_routed", "a_english", "a_typed", "hopens_english", "hopens_typed", "hnames_english", "hnames_typed"):
    R = [r for r in H if v in r["replay"]]
    none = sum(1 for r in R if r["replay"][v]["choice"] == "none")
    hc[v] = dict(n=len(R), chose_none=none, chose_requirement=len(R) - none, wilson_none=wilson(none, len(R)))
base["holds_control"] = hc

json.dump(base, open(os.path.join(HERE, "rescore.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "mismatches"} for k, v in repro.items()}, indent=1))
for k, v in repro.items():
    print(k, v["mismatches"])
print(json.dumps(fr, indent=0))
for x in base["framing_rows"]:
    print(x)
print(json.dumps(hc, indent=0))
