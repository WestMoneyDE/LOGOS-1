import json, sys, collections, statistics, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labels import build, wilson, top_gap, ambiguous, STEPS, LAYA, TASKS, MIN_CONF, GAP

HERE = os.path.dirname(os.path.abspath(__file__))
rows = build()
for i, r in enumerate(rows):
    r["id"] = i
KINDS = ["holds", "item", "next", "submit", "done", "met", "set", "option", "field"]
out = {"thresholds": {"min_confidence": MIN_CONF, "ambiguity_gap": GAP}}

# ------------------------------------------------------------------ 1. label counts
t1 = []
for k in KINDS:
    R = [r for r in rows if r["kind"] == k]
    lab = [r for r in R if r["status"] == "labelled"]
    t1.append(dict(kind=k, total=len(R), labelled=len(lab),
                   unlabelled_degenerate=sum(1 for r in R if r.get("degenerate")),
                   unlabelled_other=sum(1 for r in R if r["status"] != "labelled" and not r.get("degenerate")),
                   gold_present=sum(1 for r in lab if r["gold_present"]),
                   gold_absent=sum(1 for r in lab if not r["gold_present"])))
out["labels"] = t1


# ------------------------------------------------------------------ 2. accuracy on logged answers
def dist(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return dict(min=round(min(vals), 3), median=round(statistics.median(vals), 3), max=round(max(vals), 3))


t2 = []
for k in KINDS:
    lab = [r for r in rows if r["kind"] == k and r["status"] == "labelled"]
    P = [r for r in lab if r["gold_present"]]
    A = [r for r in lab if not r["gold_present"]]
    Ano = [r for r in A if r["none_offered"]]
    Ann = [r for r in A if not r["none_offered"]]
    ok = sum(1 for r in P if r["correct"])
    t2.append(dict(
        kind=k,
        present_n=len(P), present_correct=ok, present_wilson=wilson(ok, len(P)),
        present_gate_fired=sum(1 for r in P if r["gate_fires"]),
        present_correct_and_gate_fired=sum(1 for r in P if r["correct"] and r["gate_fires"]),
        present_wrong_and_gate_passed=sum(1 for r in P if not r["correct"] and not r["gate_fires"]),
        absent_n=len(A),
        absent_none_offered=len(Ano), absent_chose_none=sum(1 for r in Ano if r["chose_none"]),
        absent_chose_none_wilson=wilson(sum(1 for r in Ano if r["chose_none"]), len(Ano)),
        absent_no_none_n=len(Ann), absent_no_none_gate_fired=sum(1 for r in Ann if r["gate_fires"]),
        absent_no_none_gate_wilson=wilson(sum(1 for r in Ann if r["gate_fires"]), len(Ann)),
        absent_no_none_top=dist([r["top"] for r in Ann]), absent_no_none_gap=dist([r["gap"] for r in Ann]),
        absent_no_none_top_ge_0_4=sum(1 for r in Ann if r["top"] >= MIN_CONF),
        present_top=dist([r["top"] for r in P]), present_gap=dist([r["gap"] for r in P]),
    ))
out["accuracy_logged"] = t2

# per-call variant (duplicates counted) for completeness
pc = collections.Counter()
for r in rows:
    if r["status"] == "labelled" and r["gold_present"]:
        g = set(r["gold"])
        for ch in r["choices_all_calls"]:
            pc[(r["kind"], "n")] += 1
            pc[(r["kind"], "ok")] += ch in g
out["accuracy_logged_per_call_present"] = {k: [pc[(k, "ok")], pc[(k, "n")]] for k in KINDS if pc[(k, "n")]}

# ------------------------------------------------------------------ reconciliation with the old gold rule
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import old_gold_rule as oldq  # the superseded target-substring gold rule, kept for reconciliation
old = oldq.rows("last", False, "nostate")
old_off = [r for r in old if r["gold"]]
rec = collections.Counter()
index = {(r["task"], r["qid"], json.dumps(r["criteria"], ensure_ascii=False, sort_keys=True)): r for r in rows}
for o in old_off:
    k = (o["task"], o["qid"], json.dumps(o["q"]["criteria"], ensure_ascii=False, sort_keys=True))
    n = index.get(k)
    kind = o["qid"].split("_")[0]
    rec[(kind, "n")] += 1
    rec[(kind, "old_correct")] += o["choice"] in o["gold"]
    if n and n["status"] == "labelled":
        rec[(kind, "new_labelled")] += 1
        rec[(kind, "new_present")] += bool(n["gold_present"])
        rec[(kind, "new_correct")] += bool(n.get("correct")) or (not n["gold_present"] and n.get("chose_none", False))
out["reconciliation_old_45"] = {k: {m: rec[(k, m)] for m in ("n", "old_correct", "new_labelled", "new_present", "new_correct")}
                                for k in sorted({k for k, _ in rec})}
out["reconciliation_old_45_total"] = len(old_off)

# exact reconciliation with the 45 cases the KEYSTONE-R1 replay used (replay_offered.json)
RO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "keystone-r1-run", "replay_offered.json"), encoding="utf-8"))
rec45 = collections.defaultdict(collections.Counter)
rec45_rows = []
for c in RO:
    crit = json.dumps(c["question"]["criteria"], ensure_ascii=False, sort_keys=True)
    cand = [r for r in rows if r["task"] == c["task"] and r["qid"] == c["qid"]
            and json.dumps(r["criteria"], ensure_ascii=False, sort_keys=True) == crit
            and (r["kind"] not in ("done", "met") or r["state"] == c["state"])]
    n = cand[0] if cand else None
    kind = c["qid"].split("_")[0]
    k = rec45[kind]
    k["n"] += 1
    k["old_gold_hit"] += c["logged_choice"] in c["gold"]
    if n is None:
        k["unmatched"] += 1
        continue
    if n["status"] != "labelled":
        k["new_unlabelled"] += 1
    else:
        k["new_gold_present"] += bool(n["gold_present"])
        k["new_gold_absent"] += not n["gold_present"]
        good = n["correct"] if n["gold_present"] else n.get("chose_none", False)
        k["new_laya_right"] += bool(good)
    rec45_rows.append(dict(task=c["task"], qid=c["qid"], old_gold=c["gold"], logged=c["logged_choice"],
                           row_id=n["id"], new_status=n["status"], new_gold=n.get("gold"), new_present=n.get("gold_present")))
out["reconciliation_keystone_45"] = {k: dict(v) for k, v in rec45.items()}
out["reconciliation_keystone_45_rows"] = rec45_rows

# ------------------------------------------------------------------ 4. low_confidence stops
call_index = collections.defaultdict(list)
for c in LAYA:
    (qid, q), = c["request"]["questions"].items()
    call_index[(c["task"], c["tick"], qid)].append(c)
row_of_call = {}
for r in rows:
    for c in LAYA:
        pass
# map (task, tick, qid) -> row id
for r in rows:
    for t in r["ticks"]:
        row_of_call[(r["task"], t, r["qid"])] = r["id"]

stops = []
for s in STEPS:
    if s["status"] != "low_confidence":
        continue
    cp = s["choice_probabilities"]
    trig = [q for q in s["question_ids"] if (s["raw_answers"].get(q) or {}).get("probabilities") == cp]
    qid = trig[0] if len(trig) == 1 else (trig[-1] if trig else None)
    rid = row_of_call.get((s["task"], s["tick"], qid))
    r = rows[rid] if rid is not None else None
    t, g = top_gap(cp)
    stops.append(dict(task=s["task"], tick=s["tick"], question=qid, kind=qid.split("_")[0] if qid else None,
                      match_count=len(trig), row_id=rid, top=round(t, 4), gap=round(g, 4) if g is not None else None,
                      n_options=len(cp), status=r["status"] if r else None,
                      gold_present=r.get("gold_present") if r else None,
                      gold=r.get("gold") if r else None, laya_choice=r["choice"] if r else None,
                      laya_correct=r.get("correct") if r else None,
                      reason=r["reason"] if r else None))
agg = collections.Counter()
for s in stops:
    lab = "unlabelled" if s["status"] != "labelled" else ("gold present" if s["gold_present"] else "gold absent")
    agg[(s["kind"], lab)] += 1
out["stops"] = stops
out["stops_aggregate"] = [dict(kind=k, label=l, n=n) for (k, l), n in sorted(agg.items(), key=lambda x: (-x[1], x[0]))]
out["stops_total"] = len(stops)
out["stops_tasks_outcome"] = collections.Counter(t["outcome"] for t in TASKS.values())

json.dump(dict(out, rows=rows), open(os.path.join(HERE, "rescore_base.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=list)

if __name__ == "__main__":
    for x in t1: print(x)
    print()
    for x in t2: print({k: v for k, v in x.items()})
    print()
    print(out["reconciliation_old_45_total"], out["reconciliation_old_45"])
    print(out["accuracy_logged_per_call_present"])
    print()
    print(len(stops)); [print(x) for x in out["stops_aggregate"]]
    for s in stops: print(s["task"], s["tick"], s["kind"], s["match_count"], s["status"], s["gold_present"], s["top"], s["gap"], s["n_options"])
