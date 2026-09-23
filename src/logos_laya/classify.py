"""`laya-classify/1` — the client for the local juror service.

This replaces the chat path (`client.HttpLaya`) for new code. The service returns a
closed, typed answer instead of free text the caller has to parse, so the failure
surface is a schema, not a prompt.

Three rules hold here and are tested, not documented:

* **Loopback only.** A `base_url` whose host is not 127.0.0.1, ::1 or localhost is never
  contacted; every call abstains with `BASE_URL_NOT_LOOPBACK`. `UrllibTransport` repeats
  the check, ignores proxy environment variables and refuses redirects.
* **One place maps every failure to an abstention.** `ClassifyClient.ask` has a single
  `except` that turns every failure — timeout, connection error, non-200, a body off the
  schema, a pin mismatch, a malformed request, an unexpected exception — into an
  answer with `ok=False` and a distinct `abstain_reason`. It never raises.
* **`confidence` is carried, never interpreted.** For `choice` and `score` Laya's
  `confidence` is 1 - normalised entropy, which falls with the number of options; it is
  not a probability. The vote reads `p_true` (see `profiles.juror_vote`).

This file and `client.py` are the only files in the package that touch the network.
"""
from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol

SCHEMA_VERSION = "laya-classify/1"
DEFAULT_BASE = "http://127.0.0.1:58110"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
QUESTION_TYPES = ("noul", "choice", "score")
ROUTES = ("english", "multilingual", "typed-decisions")
MAX_STATE_CHARS = 8000
PIN_KEYS = frozenset({"package_version", "hf_revision", "route", "device"})

#: Every way a call can fail to produce a usable answer. All of them abstain.
ABSTAIN_REASONS: tuple[str, ...] = (
    "BASE_URL_NOT_LOOPBACK",   # the configured host is not a loopback address
    "INVALID_REQUEST",         # the caller's request breaks the contract; nothing was sent
    "TIMEOUT",                 # the transport timed out
    "UNAVAILABLE",             # connection refused / reset / unreachable
    "TRANSPORT_ERROR",         # anything else the transport raised (e.g. a non-JSON body)
    "SERVICE_NOT_READY",       # 503 LAYA_NOT_READY
    "SERVICE_BUSY",            # 503 LAYA_BUSY
    "SERVICE_TIMEOUT",         # 504 LAYA_TIMEOUT
    "SERVICE_OUTPUT_INVALID",  # 502 LAYA_OUTPUT_INVALID
    "SERVICE_BAD_REQUEST",     # 422 LAYA_BAD_REQUEST
    "HTTP_STATUS",             # any other non-200, or an error code on the wrong status
    "WRONG_SCHEMA_VERSION",    # schema_version != laya-classify/1
    "SCHEMA_INVALID",          # missing/extra field or wrong type anywhere in the body
    "UNKNOWN_TYPE",            # answer.type is not noul/choice/score
    "TYPE_MISMATCH",           # answer.type differs from the question's type
    "PROBABILITY_OUT_OF_RANGE",  # a probability or confidence outside [0, 1], or NaN
    "CHOICE_NOT_IN_PROBABILITIES",  # the chosen option has no probability
    "ID_MISMATCH",             # request_id / question_id not echoed
    "PIN_MISMATCH",            # pins differ from expected_pins
    "CLIENT_ERROR",            # a bug in this module; still an abstention, never a raise
)

#: The service's error codes, each valid only on its own status.
_ERROR_CODES: Mapping[tuple[int, str], str] = MappingProxyType({
    (503, "LAYA_NOT_READY"): "SERVICE_NOT_READY",
    (503, "LAYA_BUSY"): "SERVICE_BUSY",
    (504, "LAYA_TIMEOUT"): "SERVICE_TIMEOUT",
    (502, "LAYA_OUTPUT_INVALID"): "SERVICE_OUTPUT_INVALID",
    (422, "LAYA_BAD_REQUEST"): "SERVICE_BAD_REQUEST",
})

_QUESTION_ID = re.compile(r"^[a-z0-9_]{1,64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_BODY_KEYS = frozenset({"schema_version", "request_id", "question_id", "answer", "pins", "latency_ms"})
_ANSWER_KEYS: Mapping[str, frozenset[str]] = MappingProxyType({
    "noul": frozenset({"type", "p_true", "confidence"}),
    "choice": frozenset({"type", "choice", "probabilities", "confidence"}),
    "score": frozenset({"type", "level", "probabilities", "confidence"}),
})


@dataclass(frozen=True)
class ClassifyAnswer:
    """One answer under `laya-classify/1`, or an abstention (`ok=False`).

    `p_true` is P(the question's condition holds) for a `noul` question. `confidence` is
    the service's entropy-derived figure, carried for logging only.
    """

    question_id: str
    type: str
    ok: bool
    p_true: float | None
    choice: str | None
    probabilities: Mapping[str, float]
    confidence: float | None
    pins: Mapping[str, str]
    abstain_reason: str | None
    latency_ms: int | None
    level: float | None = None
    detail: str = ""


class Transport(Protocol):
    def post(self, url: str, body: dict, timeout: float) -> tuple[int, dict]:
        ...


def is_loopback(url: str) -> bool:
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname
        parts.port  # noqa: B018 — raises ValueError on a malformed port
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and host in LOOPBACK_HOSTS


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None  # a redirect is surfaced as its status, never followed


class UrllibTransport:
    """The only code in this module that reaches the network, and only to loopback."""

    def __init__(self) -> None:
        # An empty ProxyHandler ignores HTTP(S)_PROXY: a loopback request is never relayed.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def post(self, url: str, body: dict, timeout: float) -> tuple[int, dict]:
        if not is_loopback(url):
            raise PermissionError(f"refusing non-loopback url {url!r}")
        request = urllib.request.Request(url, method="POST", data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        try:
            with self._opener.open(request, timeout=timeout) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                payload = json.load(exc)
            except (ValueError, OSError):
                payload = {}
            return exc.code, payload if isinstance(payload, dict) else {}
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TimeoutError(str(exc.reason)) from exc
            raise ConnectionError(str(exc.reason)) from exc


@dataclass
class FakeTransport:
    """Scripted responses for the deterministic suite. It invents nothing.

    Each entry is a `(status, body)` tuple or an exception to raise. A body's
    `"request_id": "__ECHO__"` is replaced with the request's id. When the script runs
    out, the fake raises `ConnectionError`, so a forgotten case abstains.
    """

    responses: list
    calls: list[tuple[str, dict, float]] = field(default_factory=list)

    def post(self, url: str, body: dict, timeout: float) -> tuple[int, dict]:
        self.calls.append((url, body, timeout))
        if not self.responses:
            raise ConnectionError("no scripted response")
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        status, payload = item
        if isinstance(payload, dict) and payload.get("request_id") == "__ECHO__":
            payload = {**payload, "request_id": body["request_id"]}
        return status, payload


class _Abstain(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        assert reason in ABSTAIN_REASONS, reason
        super().__init__(reason, detail)
        self.reason = reason
        self.detail = detail


class ClassifyClient:
    def __init__(self, base_url: str = DEFAULT_BASE, timeout: float = 5.0,
                 transport: Transport | None = None,
                 expected_pins: Mapping[str, str] | None = None) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.transport: Transport = transport if transport is not None else UrllibTransport()
        self.expected_pins = dict(expected_pins) if expected_pins is not None else None
        # Checked here, enforced on every call: a non-loopback client can be built but
        # can never send anything.
        self.loopback = is_loopback(base_url)

    def ask(self, question_id: str, state: Mapping[str, str], question: Mapping[str, Any],
            route: str | None = None) -> ClassifyAnswer:
        qtype = question.get("type") if isinstance(question, Mapping) else None
        qtype = qtype if isinstance(qtype, str) else ""
        try:
            return self._exchange(question_id, state, question, route)
        except _Abstain as exc:
            return _abstention(question_id, qtype, exc.reason, exc.detail)
        except Exception as exc:  # noqa: BLE001 — the one place every failure becomes ABSTAIN
            return _abstention(question_id, qtype, _reason_for(exc), f"{type(exc).__name__}: {exc}"[:200])

    # -- internals ----------------------------------------------------------

    def _exchange(self, question_id, state, question, route) -> ClassifyAnswer:
        if not self.loopback:
            raise _Abstain("BASE_URL_NOT_LOOPBACK", repr(self.base_url))
        request = _request(question_id, state, question, route)
        status, payload = self.transport.post(f"{self.base_url.rstrip('/')}/v1/classify",
                                              request, self.timeout)
        if status != 200:
            code = payload.get("error_code") if isinstance(payload, dict) else None
            reason = _ERROR_CODES.get((status, code), "HTTP_STATUS")
            raise _Abstain(reason, f"HTTP {status} {code!r}")
        answer = _parse(payload, request)
        if self.expected_pins is not None:
            diff = sorted(k for k, v in self.expected_pins.items() if answer.pins.get(k) != v)
            if diff:
                raise _Abstain("PIN_MISMATCH", f"differs on {diff}")
        return answer


def _reason_for(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return "TIMEOUT"
    if isinstance(exc, (ConnectionError, urllib.error.URLError)):
        return "UNAVAILABLE"
    if isinstance(exc, (OSError, ValueError, PermissionError)):
        return "TRANSPORT_ERROR"
    return "CLIENT_ERROR"


def _abstention(question_id: str, qtype: str, reason: str, detail: str) -> ClassifyAnswer:
    return ClassifyAnswer(question_id=question_id if isinstance(question_id, str) else "",
                          type=qtype, ok=False, p_true=None, choice=None,
                          probabilities=MappingProxyType({}), confidence=None,
                          pins=MappingProxyType({}), abstain_reason=reason, latency_ms=None,
                          detail=detail)


def _request(question_id, state, question, route) -> dict:
    if not isinstance(question_id, str) or not _QUESTION_ID.match(question_id):
        raise _Abstain("INVALID_REQUEST", f"question_id {question_id!r}")
    if not isinstance(state, Mapping) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in state.items()):
        raise _Abstain("INVALID_REQUEST", "state must map str to str")
    if sum(len(v) for v in state.values()) > MAX_STATE_CHARS:
        raise _Abstain("INVALID_REQUEST", f"state exceeds {MAX_STATE_CHARS} chars")
    if not isinstance(question, Mapping) or question.get("type") not in QUESTION_TYPES:
        raise _Abstain("INVALID_REQUEST", "question.type")
    if not isinstance(question.get("instructions"), str) or not question["instructions"].strip():
        raise _Abstain("INVALID_REQUEST", "question.instructions")
    criteria = question.get("criteria")
    if criteria is not None and not isinstance(criteria, (dict, list)):
        raise _Abstain("INVALID_REQUEST", "question.criteria")
    if route is not None and route not in ROUTES:
        raise _Abstain("INVALID_REQUEST", f"route {route!r}")
    return {"request_id": uuid.uuid4().hex, "question_id": question_id, "state": dict(state),
            "question": {"type": question["type"], "instructions": question["instructions"],
                         "criteria": criteria},
            "route": route}


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _unit(value, name: str) -> float:
    if not _is_number(value):
        raise _Abstain("SCHEMA_INVALID", f"{name} is {type(value).__name__}")
    if not (0.0 <= float(value) <= 1.0):  # NaN fails this comparison too
        raise _Abstain("PROBABILITY_OUT_OF_RANGE", f"{name}={value!r}")
    return float(value)


def _probabilities(value) -> Mapping[str, float]:
    if not isinstance(value, dict) or not value:
        raise _Abstain("SCHEMA_INVALID", "probabilities must be a non-empty object")
    out = {}
    for key, p in value.items():
        if not isinstance(key, str):
            raise _Abstain("SCHEMA_INVALID", "probability key")
        out[key] = _unit(p, f"probabilities[{key!r}]")
    return MappingProxyType(out)


def _parse(payload, request: dict) -> ClassifyAnswer:
    if not isinstance(payload, dict):
        raise _Abstain("SCHEMA_INVALID", f"body is {type(payload).__name__}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise _Abstain("WRONG_SCHEMA_VERSION", repr(payload.get("schema_version")))
    if set(payload) != _BODY_KEYS:
        raise _Abstain("SCHEMA_INVALID", f"fields {sorted(set(payload) ^ _BODY_KEYS)}")
    latency = payload["latency_ms"]
    if not isinstance(latency, int) or isinstance(latency, bool) or latency < 0:
        raise _Abstain("SCHEMA_INVALID", "latency_ms")
    pins = payload["pins"]
    if (not isinstance(pins, dict) or set(pins) != PIN_KEYS
            or not all(isinstance(v, str) and v for v in pins.values())
            or not _HEX40.match(pins["hf_revision"])):
        raise _Abstain("SCHEMA_INVALID", "pins")
    if not isinstance(payload["request_id"], str) or not isinstance(payload["question_id"], str):
        raise _Abstain("SCHEMA_INVALID", "ids")
    if payload["request_id"] != request["request_id"] or payload["question_id"] != request["question_id"]:
        raise _Abstain("ID_MISMATCH", "response ids do not echo the request")

    answer = payload["answer"]
    if not isinstance(answer, dict):
        raise _Abstain("SCHEMA_INVALID", "answer must be an object")
    atype = answer.get("type")
    if atype not in _ANSWER_KEYS:
        raise _Abstain("UNKNOWN_TYPE", repr(atype))
    if atype != request["question"]["type"]:
        raise _Abstain("TYPE_MISMATCH", f"{atype!r} for a {request['question']['type']!r} question")
    if set(answer) != _ANSWER_KEYS[atype]:
        raise _Abstain("SCHEMA_INVALID", f"answer fields {sorted(set(answer) ^ _ANSWER_KEYS[atype])}")

    confidence = _unit(answer["confidence"], "confidence")
    p_true = choice = level = None
    probabilities: Mapping[str, float] = MappingProxyType({})
    if atype == "noul":
        p_true = _unit(answer["p_true"], "p_true")
    elif atype == "choice":
        probabilities = _probabilities(answer["probabilities"])
        choice = answer["choice"]
        if not isinstance(choice, str):
            raise _Abstain("SCHEMA_INVALID", "choice")
        if choice not in probabilities:
            raise _Abstain("CHOICE_NOT_IN_PROBABILITIES", repr(choice))
    else:
        probabilities = _probabilities(answer["probabilities"])
        if not _is_number(answer["level"]) or not math.isfinite(answer["level"]):
            raise _Abstain("SCHEMA_INVALID", "level")
        level = float(answer["level"])

    return ClassifyAnswer(question_id=payload["question_id"], type=atype, ok=True, p_true=p_true,
                          choice=choice, probabilities=probabilities, confidence=confidence,
                          pins=MappingProxyType(dict(pins)), abstain_reason=None,
                          latency_ms=latency, level=level)
