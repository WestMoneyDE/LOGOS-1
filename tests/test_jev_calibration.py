from __future__ import annotations

import dataclasses
import json

import pytest

from logos_jev.calibration import CalibrationRecord, admissible, load, prompt_hash, wilson


def record(**overrides) -> CalibrationRecord:
    base = dict(profile="injection", dataset_sha256="a" * 64, n=240, positives=120, negatives=120,
                model_pin="jev-style-qwen3.5-2b-decision", prompt_sha256="b" * 64,
                protocol="logprob", threshold=0.8, recall=0.91, fpr=0.03,
                wilson_95={"recall": [0.85, 0.95], "fpr": [0.01, 0.07]},
                measured_on="2026-09-23", approved_by="founder")
    base.update(overrides)
    return CalibrationRecord(**base)


def test_a_matching_record_is_admissible():
    r = record()
    assert admissible(r, model_pin=r.model_pin, prompt_sha256=r.prompt_sha256) is True


def test_no_record_is_never_admissible():
    assert admissible(None, model_pin="anything", prompt_sha256="c" * 64) is False


def test_a_changed_model_or_prompt_makes_the_record_inadmissible():
    """A threshold measured for one setup does not carry to another."""
    r = record()
    assert admissible(r, model_pin="some-other-model", prompt_sha256=r.prompt_sha256) is False
    assert admissible(r, model_pin=r.model_pin, prompt_sha256="c" * 64) is False


@pytest.mark.parametrize("bad", [
    {"approved_by": ""}, {"n": 0}, {"threshold": 1.5}, {"threshold": -0.1},
    {"recall": 1.2}, {"fpr": -0.01}, {"protocol": "vibes"}, {"positives": 0},
])
def test_an_incomplete_or_impossible_record_is_inadmissible(bad):
    r = record(**bad)
    assert admissible(r, model_pin=r.model_pin, prompt_sha256=r.prompt_sha256) is False


def test_wilson_widens_when_n_is_small():
    lo_small, hi_small = wilson(9, 10)
    lo_big, hi_big = wilson(900, 1000)
    assert (hi_small - lo_small) > (hi_big - lo_big)
    assert 0.0 <= lo_small <= hi_small <= 1.0


def test_wilson_handles_the_edges():
    assert wilson(0, 10)[0] == 0.0
    assert wilson(10, 10)[1] == 1.0
    assert wilson(0, 0) == (0.0, 1.0)


def test_loading_an_absent_profile_returns_none(tmp_path, monkeypatch):
    import logos_jev.calibration as cal

    monkeypatch.setattr(cal, "RECORD_DIR", tmp_path)
    assert load("injection") is None


def test_a_record_round_trips_through_disk(tmp_path, monkeypatch):
    import logos_jev.calibration as cal

    monkeypatch.setattr(cal, "RECORD_DIR", tmp_path)
    r = record()
    (tmp_path / "injection.json").write_text(json.dumps(dataclasses.asdict(r)), encoding="utf-8")
    assert load("injection") == r
