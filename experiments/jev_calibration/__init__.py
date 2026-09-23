"""The harness that produces a calibration record, and nothing else.

Deterministic in everything except the model call: the cases, the prompts, the ordering
and the scoring are fixed, so two runs differ only where the model differs.
"""
