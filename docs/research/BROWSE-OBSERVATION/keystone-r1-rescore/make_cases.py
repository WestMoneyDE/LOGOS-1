import json, re
from labels import build, TASKS

rows = build()
cases = []
for i, r in enumerate(rows):
    r["id"] = i
    title = re.search(r"Page title: (.*)", r["state"])
    frame = None
    if r["kind"] in ("item", "next") and r["status"] == "labelled" and r["gold_present"]:
        frame = dict(target=r["targets"][0], page=(title.group(1).strip() if title else ""))
    holds_frame = None
    if r["kind"] == "holds":
        q = re.findall(r'"([^"]+)"', TASKS[r["task"]]["goal"])
        holds_frame = dict(target=q[-1] if q else None)
    cases.append(dict(id=i, task=r["task"], kind=r["kind"], qid=r["qid"], state=r["state"],
                      question=dict(type="choice", instructions=r["instructions"], criteria=r["criteria"]),
                      logged_choice=r["choice"], logged_probs=r["probabilities"],
                      gold=r.get("gold"), status=r["status"], gold_present=r.get("gold_present"),
                      frame=frame, holds_frame=holds_frame))
json.dump(cases, open("cases.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(rows, open("rows_pre.json", "w", encoding="utf-8"), ensure_ascii=False)
print(len(cases), sum(1 for c in cases if c["frame"]), sum(1 for c in cases if c["holds_frame"]))
