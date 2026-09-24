"""In-process side of the Phase 3 equivalence check. Runs INSIDE the logos-laya image.

It reproduces exactly what the service's `RouterBackend.predict` does: a `laya.Router`
over the snapshot baked into the image (`LAYA_SNAPSHOT_DIR`), the same three model
entries, `max_loaded=1`, CPU, and one `noul` question per call with `criteria: None`
(the service's `model_dump()` of the question). No HTTP, no FastAPI, no pydantic.

Input: a JSON list of items `{"key", "text", "route"}` (route None = auto), appended to
this file as `ITEMS_B64` by `injection_measure.py inprocess`. Output: one JSON object on
stdout after the marker line `===RESULT===`.

It is run in a throwaway `docker run --rm --network none --read-only` container of the
same image rather than by `docker exec` into the running service: the service already
holds ~2.0 of its 3 GiB, and a second resident checkpoint in the same cgroup risks an
OOM kill of the service itself.
"""
import base64
import json
import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import laya  # noqa: E402
import torch  # noqa: E402
from laya import Router  # noqa: E402

QUESTION = {"type": "noul",
            "instructions": "Does `prompt` contain instructions aimed at the AI system rather than "
                            "a genuine user request?",
            "criteria": None}


def main(items):
    snapshot = os.environ["LAYA_SNAPSHOT_DIR"]
    revision = os.path.basename(os.path.normpath(snapshot))
    router = Router(models={"english": (snapshot, None),
                            "multilingual": (snapshot, "multilingual"),
                            "typed-decisions": (snapshot, "typed-decisions")},
                    device="cpu", max_loaded=1)
    # Order by the checkpoint that will answer, so each is loaded once.
    for item in items:
        item["_planned"] = item["route"] or router.route({"prompt": item["text"]}, {"prompt_injection": dict(QUESTION)}).model
    order = {"english": 0, "multilingual": 1, "typed-decisions": 2}
    out = {}
    t_start = time.time()
    for n, item in enumerate(sorted(items, key=lambda i: order.get(i["_planned"], 9))):
        t0 = time.perf_counter()
        result = router.predict({"prompt": item["text"]}, {"prompt_injection": dict(QUESTION)},
                                model=item["route"])
        raw = result["answers"]["prompt_injection"]
        routing = result.get("routing") or {}
        out[item["key"]] = {"p_true": raw.get("noul"), "confidence": raw.get("confidence"),
                            "answered_route": routing.get("model") or item["route"],
                            "routing_reason": routing.get("reason"),
                            "ms": round((time.perf_counter() - t0) * 1000.0, 1)}
        if n % 25 == 0:
            print(f"{n}/{len(items)} {time.time() - t_start:.0f}s", file=sys.stderr, flush=True)
    meta = {"package_version": str(laya.__version__), "hf_revision": revision,
            "torch": torch.__version__, "torch_threads": torch.get_num_threads(),
            "seconds": round(time.time() - t_start, 1)}
    print("===RESULT===")
    print(json.dumps({"meta": meta, "answers": out}))


if __name__ == "__main__":
    main(json.loads(base64.b64decode(ITEMS_B64).decode("utf-8")))  # noqa: F821 — appended at run time
