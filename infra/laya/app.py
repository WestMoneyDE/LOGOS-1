"""logos-laya — the local juror service, contract `laya-classify/1`.

One question per request, one typed answer per response. The client that consumes this is
`src/logos_laya/classify.py`; the two ends are tied together by
`tests/test_laya_service_contract.py`, which parses this service's bodies with that client.

What this service guarantees, each held by a test:

* **Every question type has exactly one response variant** (`noul`, `choice`, `score`),
  selected by `answer.type`. A raw model answer that does not carry its own type's field
  (e.g. a `noul` answer without `noul`) is a 502 `LAYA_OUTPUT_INVALID`, never a guess.
* **Every 200 names what answered:** `pins` = package_version, hf_revision, route (the
  checkpoint that actually ran), device. `act_probability` is never returned.
* **No probe loads a model.** `/livez` is constant time; `/readyz` reads a flag. Loading
  and one warm-up happen in a background thread started by the lifespan.
* **One inference slot.** A request waits at most `LAYA_QUEUE_WAIT_S` for it, then gets
  503 `LAYA_BUSY`; an inference that exceeds `LAYA_DEADLINE_S` gets 504 `LAYA_TIMEOUT`
  (the slot stays held until that inference really finishes). The slot is acquired and
  released inside the same worker call, so a request whose deadline expires, or that is
  cancelled, before its job starts cannot leave the slot taken; a job that starts after
  its caller has gone runs no inference. The device pin is read inside that call.

The backend (the laya `Router`) is injected through `create_app(backend_factory=...)`, so the
contract tests need neither torch nor the model. Nothing here grants, approves or authorizes
anything: the answer is a classification, and the caller's Γ path decides what it is worth.
"""
from __future__ import annotations

import asyncio
import math
import os
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, Literal, Optional, Protocol, Union

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

SCHEMA_VERSION = "laya-classify/1"
QUESTION_TYPES = ("noul", "choice", "score")
ROUTES = ("english", "multilingual", "typed-decisions")
MAX_STATE_CHARS = 8000

#: The raw laya 0.3.6 field that carries each type's answer. The service's variant field
#: name differs on purpose (`p_true` is P(condition holds); `level` is the expected level).
RAW_ANSWER_FIELD = {"noul": "noul", "choice": "choice", "score": "score"}


# -- configuration --------------------------------------------------------------

@dataclass(frozen=True)
class Config:
    preload: tuple[str, ...] = ("english",)
    max_loaded: int = 1
    device: str = "cpu"
    queue_wait_s: float = 2.0
    deadline_s: float = 20.0
    snapshot_dir: str = ""
    hf_revision: str = ""

    @classmethod
    def from_env(cls) -> "Config":
        preload = tuple(r.strip() for r in os.environ.get("LAYA_PRELOAD", "english").split(",") if r.strip())
        return cls(preload=preload or ("english",),
                   max_loaded=int(os.environ.get("LAYA_MAX_LOADED", "1")),
                   device=os.environ.get("LAYA_DEVICE", "cpu") or "cpu",
                   queue_wait_s=float(os.environ.get("LAYA_QUEUE_WAIT_S", "2.0")),
                   deadline_s=float(os.environ.get("LAYA_DEADLINE_S", "20.0")),
                   snapshot_dir=os.environ.get("LAYA_SNAPSHOT_DIR", ""),
                   hf_revision=os.environ.get("LAYA_HF_REVISION", ""))


# -- the backend ------------------------------------------------------------------

class Backend(Protocol):
    package_version: str
    hf_revision: str

    def preload(self, routes: tuple[str, ...]) -> None: ...
    def loaded(self) -> list[str]: ...
    def device(self) -> str: ...
    def predict(self, state: dict, questions: dict, model: Optional[str]) -> dict: ...


class RouterBackend:
    """laya.Router over the snapshot baked into the image. Imported lazily (torch)."""

    def __init__(self, config: Config) -> None:
        import laya
        from laya import Router

        snapshot = config.snapshot_dir
        if not snapshot or not os.path.isdir(snapshot):
            raise FileNotFoundError(f"LAYA_SNAPSHOT_DIR {snapshot!r} is not a directory")
        # The pin is read from the bytes on disk (the snapshot directory is named by its
        # revision), and must agree with what the image claims.
        revision = os.path.basename(os.path.normpath(snapshot))
        if revision != config.hf_revision:
            raise ValueError(f"snapshot {revision!r} != LAYA_HF_REVISION {config.hf_revision!r}")
        self.package_version = str(laya.__version__)
        self.hf_revision = revision
        self._configured_device = config.device
        self._router = Router(models={"english": (snapshot, None),
                                      "multilingual": (snapshot, "multilingual"),
                                      "typed-decisions": (snapshot, "typed-decisions")},
                              device=config.device, max_loaded=config.max_loaded)

    def preload(self, routes: tuple[str, ...]) -> None:
        self._router.preload(list(routes))

    def loaded(self) -> list[str]:
        return self._router.loaded

    def device(self) -> str:
        # The device the resident agents actually run on (laya can fall back to CPU).
        devices = {str(a.device.type) for a in list(self._router._agents.values())
                   if getattr(a, "device", None) is not None}
        return devices.pop() if len(devices) == 1 else self._configured_device

    def predict(self, state: dict, questions: dict, model: Optional[str]) -> dict:
        return self._router.predict(state, questions, model=model)


# -- request ----------------------------------------------------------------------

class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Question(_Strict):
    type: Literal["noul", "choice", "score"]
    instructions: str = Field(min_length=1, max_length=2000)
    criteria: Union[dict[str, Any], list[Any], None] = None

    @field_validator("instructions")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("instructions is blank")
        return v

    @model_validator(mode="after")
    def _criteria_fit_the_type(self) -> "Question":
        c = self.criteria
        if self.type == "choice":
            if not c or len(c) < 2:
                raise ValueError("choice needs at least two criteria")
            keys = list(c) if isinstance(c, dict) else c
            if not all(isinstance(k, str) and k for k in keys) or len(set(keys)) != len(keys):
                raise ValueError("choice options must be distinct non-empty strings")
        elif self.type == "score":
            # laya enumerates score criteria as levels 0..k-1; a mapping would silently
            # become its keys, so only a list is accepted.
            if not isinstance(c, list) or len(c) < 2:
                raise ValueError("score needs a list of at least two levels")
        elif c is not None:
            if not isinstance(c, dict) or not set(c) <= {"true", "false"}:
                raise ValueError("noul criteria may only describe 'true' and 'false'")
        return self


class ClassifyRequest(_Strict):
    request_id: str = Field(min_length=1, max_length=128)
    question_id: str = Field(pattern=r"^[a-z0-9_]{1,64}$")
    state: dict[str, str]
    question: Question
    route: Optional[Literal["english", "multilingual", "typed-decisions"]] = None

    @field_validator("state")
    @classmethod
    def _bounded(cls, v: dict[str, str]) -> dict[str, str]:
        if sum(len(x) for x in v.values()) > MAX_STATE_CHARS:
            raise ValueError(f"state exceeds {MAX_STATE_CHARS} chars")
        return v


# -- response: one variant per question type --------------------------------------

Unit = Annotated[float, Field(ge=0.0, le=1.0, strict=True, allow_inf_nan=False)]


class NoulAnswer(_Strict):
    type: Literal["noul"]
    p_true: Unit
    confidence: Unit


class ChoiceAnswer(_Strict):
    type: Literal["choice"]
    choice: str = Field(strict=True)
    probabilities: dict[str, Unit] = Field(min_length=1)
    confidence: Unit

    @model_validator(mode="after")
    def _choice_is_an_option(self) -> "ChoiceAnswer":
        if self.choice not in self.probabilities:
            raise ValueError("choice is not one of the probabilities")
        return self


class ScoreAnswer(_Strict):
    type: Literal["score"]
    level: float = Field(strict=True, allow_inf_nan=False)
    probabilities: dict[str, Unit] = Field(min_length=1)
    confidence: Unit


Answer = Annotated[Union[NoulAnswer, ChoiceAnswer, ScoreAnswer], Field(discriminator="type")]
#: The variant for every question type — exactly one each (tested).
VARIANTS: dict[str, type[BaseModel]] = {"noul": NoulAnswer, "choice": ChoiceAnswer, "score": ScoreAnswer}


class Pins(_Strict):
    package_version: str = Field(min_length=1)
    hf_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    route: Literal["english", "multilingual", "typed-decisions"]
    device: str = Field(min_length=1)


class ClassifyResponse(_Strict):
    schema_version: Literal["laya-classify/1"]
    request_id: str
    question_id: str
    answer: Answer
    pins: Pins
    latency_ms: int = Field(ge=0, strict=True)


class OutputInvalid(Exception):
    """The model's raw answer does not fit its own type's variant."""


def to_variant(qtype: str, raw: Any) -> BaseModel:
    """Map one raw laya answer onto its type's variant, or raise OutputInvalid.

    Only the type's own fields are read; `act_probability` and everything else is dropped.
    """
    if not isinstance(raw, dict):
        raise OutputInvalid(f"raw answer is {type(raw).__name__}")
    if raw.get("type") != qtype:
        raise OutputInvalid(f"raw answer type {raw.get('type')!r} for a {qtype!r} question")
    field_ = RAW_ANSWER_FIELD[qtype]
    if field_ not in raw:
        raise OutputInvalid(f"raw {qtype} answer has no {field_!r}")
    if qtype == "noul":
        data = {"type": "noul", "p_true": raw["noul"], "confidence": raw.get("confidence")}
    elif qtype == "choice":
        data = {"type": "choice", "choice": raw["choice"], "probabilities": raw.get("probabilities"),
                "confidence": raw.get("confidence")}
    else:
        data = {"type": "score", "level": raw["score"], "probabilities": raw.get("probabilities"),
                "confidence": raw.get("confidence")}
    try:
        return VARIANTS[qtype].model_validate(data)
    except ValidationError as exc:
        raise OutputInvalid(f"{qtype}: {exc.errors()[0].get('msg', 'invalid')}") from exc


# -- the app ---------------------------------------------------------------------

@dataclass
class _State:
    config: Config
    ready: bool = False
    status: str = "starting"          # starting | loading | ready | failed
    detail: str = ""
    backend: Any = None
    slot: threading.Semaphore = field(default_factory=lambda: threading.Semaphore(1))
    loader: Optional[threading.Thread] = None


def _error(status: int, code: str, detail: str, retry_after: Optional[int] = None) -> JSONResponse:
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(status_code=status, content={"error_code": code, "detail": detail[:300]},
                        headers=headers)


def create_app(backend_factory: Optional[Callable[[Config], Any]] = None,
               config: Optional[Config] = None) -> FastAPI:
    cfg = config if config is not None else Config.from_env()
    factory = backend_factory if backend_factory is not None else RouterBackend
    st = _State(config=cfg)

    def _load() -> None:
        try:
            st.status = "loading"
            backend = factory(cfg)
            backend.preload(cfg.preload)
            warm = backend.predict({"prompt": "warm-up"},
                                   {"warmup": {"type": "noul", "instructions": "Is this a warm-up?"}},
                                   cfg.preload[0])
            to_variant("noul", (warm.get("answers") or {}).get("warmup"))
            st.backend = backend
            st.status, st.ready = "ready", True
        except Exception as exc:  # noqa: BLE001 — a failed load is reported, never served
            st.status, st.detail = "failed", f"{type(exc).__name__}: {exc}"[:300]

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        st.loader = threading.Thread(target=_load, name="laya-loader", daemon=True)
        st.loader.start()
        yield

    app = FastAPI(title="logos-laya", version=SCHEMA_VERSION, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.laya = st

    @app.exception_handler(RequestValidationError)
    async def _bad_request(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", ()))
        return _error(422, "LAYA_BAD_REQUEST", f"{where}: {first.get('msg', 'invalid request')}")

    @app.get("/livez")
    async def livez():
        return {"status": "alive"}

    @app.get("/readyz")
    async def readyz():
        if not st.ready:
            return _error(503, "LAYA_NOT_READY", f"{st.status} {st.detail}".strip(), retry_after=5)
        # Reads a flag only: asking the router what is loaded would take its lock, which an
        # on-demand load holds for seconds.
        return {"status": "ready", "preloaded": list(cfg.preload)}

    @app.post("/v1/classify")
    async def classify(req: ClassifyRequest):
        started = time.monotonic()
        if not st.ready:
            return _error(503, "LAYA_NOT_READY", st.status, retry_after=5)
        question = req.question.model_dump()
        questions = {req.question_id: question}
        loop = asyncio.get_running_loop()
        acquired = asyncio.Event()
        abandoned = threading.Event()   # the caller has gone: a job that starts late runs nothing

        def _signal_acquired() -> None:
            try:
                loop.call_soon_threadsafe(acquired.set)
            except RuntimeError:        # the loop is closed; nobody is waiting
                pass

        def _job() -> tuple:
            # The slot is taken and released in this one worker call. A job cancelled
            # before it starts never took the slot; a job that took it always releases
            # it, when the inference really ends. The device is read here too, while the
            # slot is held: it walks the router's resident agents.
            if not st.slot.acquire(True, cfg.queue_wait_s):
                return ("busy",)
            try:
                _signal_acquired()
                if abandoned.is_set():
                    return ("abandoned",)
                result = st.backend.predict(dict(req.state), questions, req.route)
                return ("ran", result, st.backend.device())
            finally:
                st.slot.release()

        job = asyncio.ensure_future(asyncio.to_thread(_job))
        try:
            waiter = asyncio.ensure_future(acquired.wait())
            try:
                await asyncio.wait({job, waiter}, return_when=asyncio.FIRST_COMPLETED)
            finally:
                waiter.cancel()
            if not acquired.is_set() and job.done() and not job.cancelled() \
                    and job.exception() is None and job.result() == ("busy",):
                return _error(503, "LAYA_BUSY", "the inference slot is taken", retry_after=1)
            try:
                outcome = await asyncio.wait_for(job, timeout=cfg.deadline_s)
            except asyncio.TimeoutError:
                return _error(504, "LAYA_TIMEOUT", f"no answer within {cfg.deadline_s}s")
            except Exception as exc:  # noqa: BLE001 — the model raised; nothing was answered
                return _error(502, "LAYA_OUTPUT_INVALID", f"backend raised {type(exc).__name__}: {exc}")
        finally:
            abandoned.set()
            if not job.done():
                job.cancel()            # unstarted: never runs; running: finishes and releases
        if outcome[0] != "ran":
            return _error(503, "LAYA_BUSY", "the inference slot is taken", retry_after=1)
        _, result, device = outcome

        try:
            if not isinstance(result, dict):
                raise OutputInvalid(f"result is {type(result).__name__}")
            answer = to_variant(req.question.type, (result.get("answers") or {}).get(req.question_id))
            routing = result.get("routing") if isinstance(result.get("routing"), dict) else {}
            route = routing.get("model") or req.route
            if req.route is not None and route != req.route:
                raise OutputInvalid(f"forced route {req.route!r} answered by {route!r}")
            body = ClassifyResponse(
                schema_version=SCHEMA_VERSION, request_id=req.request_id, question_id=req.question_id,
                answer=answer.model_dump(),
                pins={"package_version": st.backend.package_version,
                      "hf_revision": st.backend.hf_revision, "route": route,
                      "device": device},
                latency_ms=max(0, int(round((time.monotonic() - started) * 1000))))
        except (OutputInvalid, ValidationError) as exc:
            return _error(502, "LAYA_OUTPUT_INVALID", str(exc))
        payload = body.model_dump(mode="json")
        if not all(math.isfinite(v) for v in _numbers(payload["answer"])):
            return _error(502, "LAYA_OUTPUT_INVALID", "non-finite number")
        return payload

    return app


def _numbers(obj: Any):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _numbers(v)
    elif isinstance(obj, float):
        yield obj


app = create_app()
