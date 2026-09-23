from __future__ import annotations

import json

from experiments.laya_calibration.dataset import CASES, dataset_hash
from experiments.laya_calibration.run import best_threshold, measure
from logos_laya.client import FakeLaya
from logos_laya.contract import CONTRACT
from logos_laya.profiles import INJECTION


def scripted(p_for_injected: float, p_for_benign: float) -> dict[str, str]:
    out = {}
    for text, injected in CASES:
        out[text] = json.dumps({"contract": CONTRACT, "profile": "injection",
                                "answer": injected, "abstained": False,
                                "p": p_for_injected if injected else p_for_benign})
    return out


def test_the_dataset_is_balanced_and_stable():
    assert len(CASES) >= 24
    assert sum(1 for _, y in CASES if y) == sum(1 for _, y in CASES if not y)
    assert len({t for t, _ in CASES}) == len(CASES)
    assert dataset_hash() == dataset_hash() and len(dataset_hash()) == 64


def test_a_perfect_juror_produces_a_clean_separation():
    laya = FakeLaya(scripted=scripted(0.95, 0.05))
    report = measure(laya, INJECTION)
    best = best_threshold(report["scored"])
    assert best["recall"] == 1.0 and best["fpr"] == 0.0


def test_a_useless_juror_produces_no_admissible_threshold():
    """The real case, and the harness must be able to say so."""
    laya = FakeLaya(scripted=scripted(0.30, 0.70))
    report = measure(laya, INJECTION)
    best = best_threshold(report["scored"])
    assert best["recall"] <= 0.5 or best["fpr"] >= 0.5


def test_an_unreachable_juror_abstains_everywhere_rather_than_scoring_zero():
    laya = FakeLaya(scripted={})
    report = measure(laya, INJECTION)
    assert report["abstained"] == len(CASES)
    assert report["scored"] == []


def test_the_report_carries_what_a_record_needs():
    laya = FakeLaya(scripted=scripted(0.9, 0.1))
    report = measure(laya, INJECTION)
    for key in ("dataset_sha256", "prompt_sha256", "n", "positives", "negatives",
                "abstained", "parse_codes", "scored"):
        assert key in report, key
    assert report["prompt_sha256"] == INJECTION.prompt_sha256


def test_p_is_the_probability_of_the_condition_not_of_the_stated_answer():
    """The defect that made a perfect juror measure a false-positive rate of 1.0.

    A negative answer carrying a low p means "probably not an injection". Reading p as
    confidence-in-the-answer and complementing it turns that into 0.95 and inverts every
    benign case. Every fixture whose answers are all positive still passes either way,
    which is why this pins the negative case explicitly.
    """
    laya = FakeLaya(scripted=scripted(0.95, 0.05))
    report = measure(laya, INJECTION)
    benign = [p for p, truth in report["scored"] if not truth]
    assert benign and all(p == 0.05 for p in benign), benign
