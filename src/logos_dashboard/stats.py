"""Statistics module (spec §8 / order §49). Pure functions; every result carries method, assumptions, n, missingness and version.

Wilson/Newcombe are the same formulas as logos_research.experiments.cognitive_provenance_r1.metrics (kept identical on purpose; tested against them).
Zero denominators yield NOT_DEFINED, never 0 or NaN in the UI.
"""
from __future__ import annotations

import math
import random
from typing import Sequence

VERSION = "ros-stats/1"
Z95 = 1.959963984540054
NOT_DEFINED = "NOT_DEFINED"


def _res(method: str, value, ci, n, *, assumptions: list[str], missingness: dict | None = None, **extra) -> dict:
    return {"method": method, "value": value, "ci95": ci, "n": n, "assumptions": assumptions, "missingness": missingness or {"missing": 0, "of": n}, "version": VERSION, **extra}


def wilson(k: int, n: int, z: float = Z95) -> dict:
    if n <= 0:
        return _res("wilson", NOT_DEFINED, None, n, assumptions=["binomial trials", "independent"], reason="n = 0")
    if k < 0 or k > n:
        raise ValueError("k must satisfy 0 <= k <= n")
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return _res("wilson", p, (max(0.0, c - hw), min(1.0, c + hw)), n, assumptions=["binomial trials", "independent"], k=k)


def newcombe(k1: int, n1: int, k2: int, n2: int) -> dict:
    if n1 <= 0 or n2 <= 0:
        return _res("newcombe", NOT_DEFINED, None, (n1, n2), assumptions=["two independent binomials"], reason="a denominator is 0")
    a, b = wilson(k1, n1), wilson(k2, n2)
    p1, (l1, u1), p2, (l2, u2) = a["value"], a["ci95"], b["value"], b["ci95"]
    d = p1 - p2
    return _res("newcombe", d, (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)), (n1, n2), assumptions=["two independent binomials", "hybrid score interval"], p1=p1, p2=p2)


def bootstrap_mean(xs: Sequence[float], *, reps: int = 2000, seed: int = 0) -> dict:
    xs = [float(x) for x in xs if x is not None]
    if len(xs) < 2:
        return _res("bootstrap_percentile", NOT_DEFINED, None, len(xs), assumptions=["iid sample"], reason="n < 2")
    rng = random.Random(seed); n = len(xs); means = []
    for _ in range(reps):
        means.append(sum(rng.choice(xs) for _ in range(n)) / n)
    means.sort()
    return _res("bootstrap_percentile", sum(xs) / n, (means[int(0.025 * reps)], means[int(0.975 * reps) - 1]), n, assumptions=["iid sample", f"{reps} resamples", f"seed {seed}"], seed=seed, reps=reps)


def cohens_h(p1: float, p2: float) -> dict:
    if not (0 <= p1 <= 1 and 0 <= p2 <= 1):
        raise ValueError("proportions")
    h = 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))
    return _res("cohens_h", h, None, None, assumptions=["two proportions"], magnitude="small" if abs(h) < 0.5 else "medium" if abs(h) < 0.8 else "large")


def pp_delta(p_new: float | None, p_old: float | None) -> dict:
    if p_new is None or p_old is None:
        return _res("pp_delta", NOT_DEFINED, None, None, assumptions=[], reason="missing rate")
    return _res("pp_delta", round((p_new - p_old) * 100, 4), None, None, assumptions=["same metric definition", "comparable runs"], unit="pp")


def relative_change(new: float | None, old: float | None) -> dict:
    if new is None or old is None or old == 0:
        return _res("relative_change", NOT_DEFINED, None, None, assumptions=[], reason="missing value or zero baseline")
    return _res("relative_change", (new - old) / old, None, None, assumptions=["same metric definition", "comparable runs"])


def error_reduction(err_new: float | None, err_old: float | None) -> dict:
    if err_new is None or err_old is None or err_old == 0:
        return _res("error_reduction", NOT_DEFINED, None, None, assumptions=[], reason="missing error rate or zero baseline error")
    return _res("error_reduction", 1 - err_new / err_old, None, None, assumptions=["error rates on the same items"])


def efficiency(successes: int, cost: float | None) -> dict:
    if not cost or cost <= 0:
        return _res("efficiency", NOT_DEFINED, None, successes, assumptions=[], reason="zero or missing cost")
    return _res("efficiency", successes / cost, None, successes, assumptions=["cost unit documented (tokens, invocations or seconds)"])


def confusion(tp: int, fp: int, fn: int, tn: int) -> dict:
    n = tp + fp + fn + tn
    def rate(a, b): return a / b if b else NOT_DEFINED
    return _res("confusion_matrix", {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, None, n, assumptions=["binary labels", "ground truth mapped (order §34 metric gate)"],
                precision=rate(tp, tp + fp), recall=rate(tp, tp + fn), specificity=rate(tn, tn + fp), accuracy=rate(tp + tn, n), false_allow_rate=rate(fp, fp + tn), false_block_rate=rate(fn, fn + tp))


def calibration(pairs: Sequence[tuple[float, int]], bins: int = 10) -> dict:
    """pairs = (confidence in [0,1], outcome 0/1). Expected calibration error with equal-width bins."""
    pairs = [(float(c), int(o)) for c, o in pairs]
    if not pairs:
        return _res("ece", NOT_DEFINED, None, 0, assumptions=[], reason="no pairs")
    n = len(pairs); ece = 0.0; rows = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        inb = [(c, o) for c, o in pairs if (lo <= c < hi) or (b == bins - 1 and c == 1.0)]
        if not inb:
            rows.append({"bin": b, "n": 0, "confidence": None, "accuracy": None}); continue
        conf = sum(c for c, _ in inb) / len(inb); acc = sum(o for _, o in inb) / len(inb)
        ece += len(inb) / n * abs(conf - acc); rows.append({"bin": b, "n": len(inb), "confidence": conf, "accuracy": acc})
    return _res("ece", ece, None, n, assumptions=[f"{bins} equal-width bins"], bins=rows)


def mcnemar_exact(b: int, c: int) -> dict:
    """Paired binary comparison: b = A right/B wrong, c = A wrong/B right. Exact binomial two-sided p."""
    n = b + c
    if n == 0:
        return _res("mcnemar_exact", NOT_DEFINED, None, 0, assumptions=["paired items"], reason="no discordant pairs")
    k = min(b, c)
    def binom(n, k): return math.comb(n, k) / 2 ** n
    p = min(1.0, 2 * sum(binom(n, i) for i in range(0, k + 1)))
    return _res("mcnemar_exact", p, None, n, assumptions=["paired items", "exact binomial on discordant pairs"], b=b, c=c)
