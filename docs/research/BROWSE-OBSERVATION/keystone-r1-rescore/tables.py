"""Print markdown tables from rescore.json (used to fill RESCORE.md)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
b = json.load(open(os.path.join(HERE, "rescore.json"), encoding="utf-8"))


def w(x):
    return "–" if not x else "%.2f–%.2f" % tuple(x)


def d(x):
    return "–" if not x else "%.2f / %.2f / %.2f" % (x["min"], x["median"], x["max"])


print("| Kind | Distinct | Labelled | Unlabelled (1 option) | Unlabelled (other) | Gold present | Gold absent |")
print("|---|---:|---:|---:|---:|---:|---:|")
for x in b["labels"]:
    print("| `%s` | %d | %d | %d | %d | %d | %d |" % (x["kind"], x["total"], x["labelled"], x["unlabelled_degenerate"],
                                                    x["unlabelled_other"], x["gold_present"], x["gold_absent"]))
print()
print("| Kind | Present: correct / n | Wilson 95% | Present: gate fired | Present: wrong and gate passed |")
print("|---|---:|---:|---:|---:|")
for x in b["accuracy_logged"]:
    if x["present_n"]:
        print("| `%s` | %d / %d | %s | %d | %d |" % (x["kind"], x["present_correct"], x["present_n"], w(x["present_wilson"]),
                                               x["present_gate_fired"], x["present_wrong_and_gate_passed"]))
print()
print("| Kind | Absent n | `none` offered | chose `none` | Wilson 95% |")
print("|---|---:|---:|---:|---:|")
for x in b["accuracy_logged"]:
    if x["absent_none_offered"]:
        print("| `%s` | %d | %d | %d | %s |" % (x["kind"], x["absent_n"], x["absent_none_offered"], x["absent_chose_none"], w(x["absent_chose_none_wilson"])))
print()
print("| Kind | Absent, no `none` offered | Gate fired (stop) | Wilson 95% | top ≥ 0.40 | top min/median/max | gap min/median/max |")
print("|---|---:|---:|---:|---:|---:|---:|")
for x in b["accuracy_logged"]:
    if x["absent_no_none_n"]:
        print("| `%s` | %d | %d | %s | %d | %s | %s |" % (x["kind"], x["absent_no_none_n"], x["absent_no_none_gate_fired"],
                                                     w(x["absent_no_none_gate_wilson"]), x["absent_no_none_top_ge_0_4"],
                                                     d(x["absent_no_none_top"]), d(x["absent_no_none_gap"])))
print()
print("| Kind | Present top min/median/max | Present gap min/median/max |")
print("|---|---:|---:|")
for x in b["accuracy_logged"]:
    if x["present_n"]:
        print("| `%s` | %s | %s |" % (x["kind"], d(x["present_top"]), d(x["present_gap"])))
print()
print(b["accuracy_logged_per_call_present"])
print(b["reconciliation_keystone_45"])
print()
print("| Stop trigger kind | Label | Stops |")
print("|---|---|---:|")
for x in b["stops_aggregate"]:
    print("| `%s` | %s | %d |" % (x["kind"], x["label"], x["n"]))
print()
print("| Task | Tick | Kind | Options | Label | Laya choice correct | top | gap |")
print("|---|---:|---|---:|---|---|---:|---:|")
for s in b["stops"]:
    lab = "unlabelled" if s["status"] != "labelled" else ("present" if s["gold_present"] else "absent")
    print("| %s | %d | `%s` | %d | %s | %s | %.3f | %.3f |" % (s["task"], s["tick"], s["kind"], s["n_options"], lab,
                                                             {True: "yes", False: "no", None: "–"}[s["laya_correct"]], s["top"], s["gap"]))
