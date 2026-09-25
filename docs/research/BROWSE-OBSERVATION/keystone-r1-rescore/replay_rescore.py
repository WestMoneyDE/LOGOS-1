"""Pinned, offline replay for the Keystone R1 rescore. Runs in its own process inside the
jev-ultrafast-laya container; does not touch the serving process.

1. Reproduction: every distinct logged question, as logged, on (i) the checkpoint the service's
   laya.Router would route it to and (ii) the English checkpoint alone.
2. Framing: element-choice questions (item/next) with the gold option present, three variants,
   on english / typed-decisions / routed.
3. Holds control: holds questions as logged (does Laya still answer "none"?) and with the
   target framing wrongly applied (what the earlier replay measured).
"""
import os, sys, json, time, warnings
os.environ["HF_HUB_OFFLINE"] = "1"
warnings.filterwarnings("ignore")
from laya import Agent, Router

SNAP = "/root/.cache/huggingface/hub/models--convaiinnovations--laya/snapshots/5e7b2b1b8ca2ecdd3f2322d94069c9b6ce7e844b"
SUB = {"english": None, "multilingual": "multilingual", "typed-decisions": "typed-decisions"}
cases = json.load(open("/tmp/rescore/cases.json", encoding="utf-8"))
router = Router(models={k: (SNAP, v) for k, v in SUB.items()})   # routing only; nothing is loaded by route()

OPENS = "Which element opens `target`?"
NAMES = "Which option names the same thing as `target`?"


def jobs_for(model):
    """(case id, variant, state, question) tuples to run on `model`."""
    out = []
    for c in cases:
        q = c["question"]
        routed = router.route(c["state"], {c["qid"]: q})["model"]
        c["routed_model"] = routed
        if model == routed:
            out.append((c["id"], "a_routed", c["state"], q))
        if model == "english":
            out.append((c["id"], "a_english", c["state"], q))
        if model == "typed-decisions" and (c["frame"] or c["holds_frame"]):
            out.append((c["id"], "a_typed", c["state"], q))
        if c["frame"]:
            fb = {"target": c["frame"]["target"]}
            fc = {"target": c["frame"]["target"], "page": c["frame"]["page"]}
            for tag, st in (("b", fb), ("c", fc)):
                qq = dict(q, instructions=OPENS)
                r = router.route(st, {c["qid"]: qq})["model"]
                if model in ("english", "typed-decisions"):
                    out.append((c["id"], "%s_%s" % (tag, "typed" if model == "typed-decisions" else "english"), st, qq))
                if model == r:
                    out.append((c["id"], "%s_routed" % tag, st, qq))
        if c["holds_frame"] and c["holds_frame"]["target"] and model in ("english", "typed-decisions"):
            st = {"target": c["holds_frame"]["target"]}
            for tag, ins in (("hopens", OPENS), ("hnames", NAMES)):
                out.append((c["id"], "%s_%s" % (tag, "typed" if model == "typed-decisions" else "english"),
                            st, dict(q, instructions=ins)))
    return out


PART = "/tmp/rescore/replay_partial.jsonl"
results = [json.loads(l) for l in open(PART, encoding="utf-8")] if os.path.exists(PART) else []
done_keys = {(r["id"], r["variant"]) for r in results}
sink = open(PART, "a", encoding="utf-8")
for model in ("english", "multilingual", "typed-decisions"):
    jobs = [j for j in jobs_for(model) if (j[0], j[1]) not in done_keys]
    if not jobs:
        continue
    t0 = time.time()
    agent = Agent(SNAP, device="cpu", subfolder=SUB[model]) if SUB[model] else Agent(SNAP, device="cpu")
    qid_of = {c["id"]: c["qid"] for c in cases}
    for cid, variant, st, q in jobs:
        k = qid_of[cid]   # keep the logged question id; it may be part of the encoded input
        a = agent.system_one(st, {k: q})["answers"][k]
        rec = dict(id=cid, model=model, variant=variant, choice=a["choice"],
                   probabilities=a.get("probabilities") or {})
        results.append(rec)
        sink.write(json.dumps(rec, ensure_ascii=False) + chr(10)); sink.flush()
    print(model, len(jobs), "jobs", round(time.time() - t0, 1), "s", flush=True)
    del agent

json.dump({"routes": {c["id"]: c.get("routed_model") for c in cases}, "results": results},
          open("/tmp/rescore/replay_results.json", "w", encoding="utf-8"), ensure_ascii=False)
print("done", len(results))
