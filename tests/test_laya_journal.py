"""Crash/resume for the Laya measurement scripts (experiments/laya_calibration/journal.py and its three users).

Prediction (stated before implementation): a run that crashes after k items leaves exactly k journal lines; a resumed run
asks only the remaining items; its final output equals an uninterrupted run's output except for the `resumed` flags; a
torn last line is moved to `<journal>.torn`, never dropped; resumed latency is kept out of the first-session statistics.

No model and no network: FakeLaya / FakeTransport as in tests/test_laya_calibration_harness.py; a crash is a
BaseException raised by the fake, which the client does not turn into an abstention.
"""
from __future__ import annotations

import json

import pytest

from experiments.laya_calibration import injection_measure as im
from experiments.laya_calibration import run
from experiments.laya_calibration.journal import Journal, JournalError, item_key, open_journal, write_atomic
from logos_laya.classify import ClassifyClient, FakeTransport
from logos_laya.client import FakeLaya
from logos_laya.contract import CONTRACT
from logos_laya.profiles import INJECTION


class Crash(BaseException):
    """The process dies here. BaseException, so no `except Exception` in the client absorbs it."""


def _body(p_true: float, route: str = "english") -> dict:
    return {"schema_version": "laya-classify/1", "request_id": "__ECHO__", "question_id": "prompt_injection",
            "answer": {"type": "noul", "p_true": p_true, "confidence": 0.5},
            "pins": {"package_version": "0.3.6", "hf_revision": "5e7b2b1b8ca2ecdd3f2322d94069c9b6ce7e844b", "route": route, "device": "cpu"},
            "latency_ms": 12}


CASES = [(f"case {i}", i % 2 == 0) for i in range(6)]
P = [0.91, 0.12, 0.83, 0.07, 0.66, 0.21]


def _strip(rows: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if k != "resumed"} for r in rows]


@pytest.fixture(autouse=True)
def _frozen_clock(monkeypatch):
    monkeypatch.setattr(run.time, "sleep", lambda s: None)
    monkeypatch.setattr(run.time, "perf_counter", lambda: 0.0)     # wall_ms is timing, not a result


# -- the journal itself ---------------------------------------------------------------------------------------------

def test_journal_appends_reloads_and_marks_a_resumed_session(tmp_path):
    path = tmp_path / "j.jsonl"
    first = open_journal(path, resume=False)
    assert first.resumed is False
    first.append("a", {"p": 0.1}); first.append("b", {"p": 0.2})
    assert path.read_text(encoding="utf-8").count("\n") == 2
    with pytest.raises(JournalError):
        open_journal(path, resume=False)                        # a non-empty journal is never reused by accident
    second = open_journal(path, resume=True)
    assert second.resumed is True and "a" in second and second.result("b") == {"p": 0.2}
    assert second.append("c", {"p": 0.3})["resumed"] is True
    assert [second.was_resumed(k) for k in "abc"] == [False, False, True]
    with pytest.raises(JournalError):
        second.append("a", {"p": 9})


def test_a_torn_last_line_is_preserved_and_cut(tmp_path):
    path = tmp_path / "j.jsonl"
    j = Journal(path); j.append("a", {"p": 0.1})
    with open(path, "ab") as f:
        f.write(b'{"key": "b", "resu')                          # the write the crash cut
    j2 = Journal(path)
    assert list(j2.entries) == ["a"] and j2.torn_bytes == len(b'{"key": "b", "resu')
    assert (tmp_path / "j.jsonl.torn").read_bytes() == b'{"key": "b", "resu\n'
    assert path.read_bytes().endswith(b"\n") and path.read_bytes().count(b"\n") == 1
    j2.append("b", {"p": 0.2})
    assert list(Journal(path).entries) == ["a", "b"]
    # a second torn line is appended to the same .torn file, never overwriting the first
    with open(path, "ab") as f:
        f.write(b"{")
    Journal(path)
    assert (tmp_path / "j.jsonl.torn").read_bytes() == b'{"key": "b", "resu\n{\n'


def test_a_broken_line_inside_the_journal_fails_closed(tmp_path):
    path = tmp_path / "j.jsonl"
    path.write_bytes(b'{"key": "a", "resumed": false, "result": 1}\nnot json\n{"key": "b", "resumed": false, "result": 2}\n')
    with pytest.raises(JournalError):
        Journal(path)
    path.write_bytes(b'{"key": "a", "resumed": false, "result": 1}\n{"key": "a", "resumed": false, "result": 2}\n')
    with pytest.raises(JournalError):
        Journal(path)


def test_write_atomic_replaces_whole_and_leaves_no_temp(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("old", encoding="utf-8")
    write_atomic(out, '{"new": true}')
    assert json.loads(out.read_text(encoding="utf-8")) == {"new": True} and not (tmp_path / "out.json.tmp").exists()


def test_item_key_changes_with_the_text():
    assert item_key("classify:auto", 3, "x") == item_key("classify:auto", 3, "x") != item_key("classify:auto", 3, "y")


# -- run.py: measure_classify and measure --------------------------------------------------------------------------

def _classify_client(responses) -> tuple[ClassifyClient, FakeTransport]:
    fake = FakeTransport(responses=list(responses))
    return ClassifyClient(transport=fake, timeout=120.0), fake


def test_measure_classify_resumes_only_the_remaining_items(tmp_path):
    whole, _ = _classify_client([(200, _body(p)) for p in P])
    reference = run.measure_classify(whole, CASES, None, journal=open_journal(tmp_path / "ref.jsonl", False))

    k = 3
    crashing, _ = _classify_client([(200, _body(p)) for p in P[:k]] + [Crash()])
    with pytest.raises(Crash):
        run.measure_classify(crashing, CASES, None, journal=open_journal(tmp_path / "j.jsonl", False))
    assert len(Journal(tmp_path / "j.jsonl")) == k

    rest, fake = _classify_client([(200, _body(p)) for p in P[k:]])
    resumed = run.measure_classify(rest, CASES, None, journal=open_journal(tmp_path / "j.jsonl", True))
    assert [call[1]["state"]["prompt"] for call in fake.calls] == [t for t, _ in CASES[k:]]
    assert [r["resumed"] for r in resumed["rows"]] == [False] * k + [True] * (len(CASES) - k)
    assert [r["resumed"] for r in reference["rows"]] == [False] * len(CASES)
    assert _strip(resumed["rows"]) == _strip(reference["rows"])
    assert {k2: v for k2, v in resumed.items() if k2 != "rows"} == {k2: v for k2, v in reference.items() if k2 != "rows"}


def test_measure_without_a_journal_is_unchanged():
    client, _ = _classify_client([(200, _body(p)) for p in P])
    report = run.measure_classify(client, CASES, None)
    assert [r["resumed"] for r in report["rows"]] == [False] * len(CASES) and report["scored"] == [(p, y) for p, (_, y) in zip(P, CASES)]


def _chat_scripted() -> dict[str, str]:
    return {t: json.dumps({"contract": CONTRACT, "profile": "injection", "answer": y, "abstained": False, "p": p})
            for (t, y), p in zip(CASES, P)}


class _CrashingLaya(FakeLaya):
    def __init__(self, scripted, crash_after):
        super().__init__(scripted=scripted); self.crash_after = crash_after

    def ask(self, profile, prompt, *, system, logprobs=False):
        if len(self.calls) == self.crash_after:
            raise Crash()
        return super().ask(profile, prompt, system=system, logprobs=logprobs)


def test_measure_chat_protocol_resumes(tmp_path):
    reference = run.measure(FakeLaya(scripted=_chat_scripted()), INJECTION, CASES, journal=open_journal(tmp_path / "ref.jsonl", False))
    with pytest.raises(Crash):
        run.measure(_CrashingLaya(_chat_scripted(), 2), INJECTION, CASES, journal=open_journal(tmp_path / "j.jsonl", False))
    again = FakeLaya(scripted=_chat_scripted())
    resumed = run.measure(again, INJECTION, CASES, journal=open_journal(tmp_path / "j.jsonl", True))
    assert [prompt for _, prompt in again.calls] == [t for t, _ in CASES[2:]]
    assert reference["resumed_items"] == 0 and resumed["resumed_items"] == len(CASES) - 2
    assert {k: v for k, v in resumed.items() if k != "resumed_items"} == {k: v for k, v in reference.items() if k != "resumed_items"}


def test_run_main_refuses_to_reuse_a_journal_without_resume(tmp_path, monkeypatch):
    out = tmp_path / "report.json"
    Journal(f"{out}.journal.jsonl").append("x", {"p": 1})
    monkeypatch.setattr(run, "ClassifyClient", lambda **kw: _classify_client([])[0])
    with pytest.raises(JournalError):
        run.main(["--protocol", "classify", "--out", str(out)])
    assert not out.exists()


# -- injection_measure.py: http and inprocess ----------------------------------------------------------------------

def _work(tmp_path, name) -> "tuple":
    work = tmp_path / name; work.mkdir()
    calls = {im.call_key(t, None): {"text": t, "route": None} for t, _ in CASES}
    (work / "items.json").write_text(json.dumps({"calls": calls}), encoding="utf-8")
    (work / "inproc.json").write_text(json.dumps({"meta": {}, "answers": {}}), encoding="utf-8")
    return work, calls


def test_http_step_crash_and_resume_matches_an_uninterrupted_run(tmp_path, monkeypatch):
    responses: list = []
    monkeypatch.setattr(im, "ClassifyClient", lambda **kw: ClassifyClient(transport=FakeTransport(responses=responses), timeout=120.0))

    ref_work, calls = _work(tmp_path, "ref")
    responses[:] = [(200, _body(p)) for p in P]
    assert im.main(["http", "--work", str(ref_work)]) == 0
    reference = json.loads((ref_work / "http.json").read_text(encoding="utf-8"))

    work, _ = _work(tmp_path, "crash")
    responses[:] = [(200, _body(p)) for p in P[:4]] + [Crash()]
    with pytest.raises(Crash):
        im.main(["http", "--work", str(work)])
    assert not (work / "http.json").exists() and len(Journal(work / "http.journal.jsonl")) == 4
    with open(work / "http.journal.jsonl", "ab") as f:
        f.write(b'{"key": "tor')                                                 # the crash also cut a write
    responses[:] = [(200, _body(p)) for p in P[4:]]
    assert im.main(["http", "--work", str(work)]) == 2                            # refused without --resume
    assert im.main(["http", "--work", str(work), "--resume"]) == 0
    assert responses == []                                                        # exactly the 2 remaining calls were made
    out = json.loads((work / "http.json").read_text(encoding="utf-8"))
    assert list(out) == list(reference) == list(calls)
    assert [out[k]["resumed"] for k in out] == [False] * 4 + [True] * 2
    assert {k: {**v, "resumed": None} for k, v in out.items()} == {k: {**v, "resumed": None} for k, v in reference.items()}
    assert (work / "http.journal.jsonl.torn").read_bytes() == b'{"key": "tor\n'


def test_resumed_latency_is_reported_apart():
    http = {"a": {"ok": True, "busy_retries": [], "answered_route": "english", "server_latency_ms": 10, "resumed": False},
            "b": {"ok": True, "busy_retries": [], "answered_route": "english", "server_latency_ms": 900, "resumed": True},
            "c": {"ok": True, "busy_retries": [], "answered_route": "english", "server_latency_ms": 12},
            "d": {"ok": True, "busy_retries": ["SERVICE_BUSY"], "answered_route": "english", "server_latency_ms": 5000, "resumed": False}}
    first, resumed = im.latency_groups(http)
    assert first == {"english": [10, 12]} and resumed == {"english": [900]}


def _inproc_line(key: str, p: float) -> str:
    return im.ITEM_MARK + json.dumps({"key": key, "result": {"p_true": p, "confidence": 0.5, "answered_route": "english", "routing_reason": None, "ms": 1.0}}) + "\n"


def test_inprocess_stream_is_journalled_per_item_and_resumes(tmp_path):
    items = {"calls": {im.call_key(t, None): {"text": t, "route": None} for t, _ in CASES}}
    keys = list(items["calls"])
    meta = [im.RESULT_MARK + "\n", json.dumps({"meta": {"seconds": 1.0}, "answers": {}}) + "\n"]     # stdout arrives line by line

    ref = open_journal(tmp_path / "ref.jsonl", False)
    assert im.ingest_inprocess([_inproc_line(k, p) for k, p in zip(keys, P)] + meta, ref) == {"meta": {"seconds": 1.0}, "answers": {}}
    reference = im.inprocess_answers(items, ref)

    j = open_journal(tmp_path / "j.jsonl", False)
    assert im.ingest_inprocess([_inproc_line(k, p) for k, p in zip(keys[:3], P[:3])], j) is None     # container died: no RESULT
    j = open_journal(tmp_path / "j.jsonl", True)
    assert [k for k in items["calls"] if k not in j] == keys[3:]                                     # what the resumed container is sent
    assert im.ingest_inprocess([_inproc_line(k, p) for k, p in zip(keys[3:], P[3:])] + meta, j) is not None
    answers = im.inprocess_answers(items, j)
    assert [answers[k]["resumed"] for k in keys] == [False] * 3 + [True] * 3
    assert _strip(list(answers.values())) == _strip(list(reference.values()))
