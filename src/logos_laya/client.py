"""Transport to the local juror. One protocol, one implementation, one fake.

The client reads no credential and talks to one host, which is the loopback address of a
local server. It is the only file in this package that touches the network, and the
network-import scan in `tests/test_inference_governance.py` names it for that reason
rather than exempting the package silently.

Every transport failure produces `ABSTAIN`. A timeout is not a "probably fine".
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Mapping, Protocol

from .contract import LayaAnswer, abstain, parse

DEFAULT_BASE = "http://127.0.0.1:1234/v1"
#: The artifact name the local LM Studio server reports for the model file, not the
#: name of this layer. The layer is Laya-NovaML; the served model id is unchanged and
#: must stay byte-identical, or every request 404s and every profile silently ABSTAINs.
DEFAULT_MODEL = "jev-style-qwen3.5-2b-decision"


class Laya(Protocol):
    def ask(self, profile: str, prompt: str, *, system: str, logprobs: bool = False) -> LayaAnswer:
        ...


@dataclass
class FakeLaya:
    """The client the deterministic suite uses. It invents nothing.

    An unscripted prompt abstains rather than returning a plausible answer, so a test
    that forgot to script a case fails as an abstention instead of passing by accident.
    """

    scripted: Mapping[str, str]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def ask(self, profile: str, prompt: str, *, system: str, logprobs: bool = False) -> LayaAnswer:
        self.calls.append((profile, prompt))
        raw = self.scripted.get(prompt)
        if raw is None:
            return abstain(profile, "UNAVAILABLE", "no scripted answer for this prompt")
        return parse(profile, raw)


def yes_probability(payload: Mapping) -> float | None:
    """P(YES) from the answer's own token distribution.

    A number the model *writes* is a self-report; this one is read out of the
    distribution it sampled from. The repository has a measurement for why that matters:
    a median self-reported confidence of 0.90 alongside a measured recall of 0.29.
    """
    choices = payload.get("choices") or [{}]
    steps = ((choices[0].get("logprobs") or {}).get("content")) or []
    for step in steps:
        tops = {t["token"].strip().upper(): t["logprob"] for t in step.get("top_logprobs", [])}
        yes = max((v for k, v in tops.items() if k.startswith("YES")), default=None)
        no = max((v for k, v in tops.items() if k.startswith("NO")), default=None)
        if yes is None and no is None:
            continue
        py = math.exp(yes) if yes is not None else 0.0
        pn = math.exp(no) if no is not None else 0.0
        if py + pn == 0:
            continue
        return py / (py + pn)
    return None


@dataclass
class HttpLaya:
    """The one implementation that reaches the network, and only to loopback.

    Superseded: this is the chat path to the LM Studio model; new code uses
    `classify.ClassifyClient` (`laya-classify/1`).
    """

    base_url: str = DEFAULT_BASE
    model: str = DEFAULT_MODEL
    timeout: float = 30.0
    max_tokens: int = 900

    def ask(self, profile: str, prompt: str, *, system: str, logprobs: bool = False) -> LayaAnswer:
        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
        }
        if logprobs:
            body["logprobs"] = True
            body["top_logprobs"] = 20
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions", method="POST",
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except TimeoutError:
            return abstain(profile, "TIMEOUT", f"{self.timeout}s")
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            return abstain(profile, "UNAVAILABLE", str(exc)[:120])
        content = (payload.get("choices") or [{}])[0].get("message", {}).get("content", "")
        answer = parse(profile, content)
        if logprobs and answer.ok:
            measured = yes_probability(payload)
            if measured is not None:
                answer = LayaAnswer(profile=answer.profile, code=answer.code, answer=answer.answer,
                                   p=measured, abstained=answer.abstained, detail="p from logprobs")
        return answer
