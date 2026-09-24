# QUEUED WORK ORDER — Laya Calibration Dataset R1

**Status:** QUEUED / DOES_NOT_REPLACE_THE_CHAIN_HEAD (`COGNITIVE-PROVENANCE-ATTRIBUTION-FLOOR-R1`)
**Authority:** A0
**Track:** Laya juror / calibration / authority separation
**Origin:** `09-SESSIONS/2026-09-23-LOGOS1-LAYA-JUROR-INTEGRATION-R1/`
**Scientific ceiling:** a measured, founder-signed calibration record or a recorded negative result

**Goal.** Decide, with evidence that can support it, whether Laya may ever vote as an injection juror
— and write the record only if the answer is yes.

**Pre-registered falsifier** (fixed before any data is collected): if, on the held-out test split, the
lower 95% Wilson bound of recall at an FPR upper bound ≤ 5% is below **0.80** for any
(language × channel) stratum, Laya is removed from the injection-juror role for that stratum and the
result is recorded as negative evidence. The value 0.80 is a proposal; the founder sets it before the
data is built.

**Scope, in order:**

1. Dataset: ≥ ~100 injections per (language × channel × attack class) cell that is reported, ≥ 400
   injections and ≥ 299 benign cases overall. Channels: `agent_output`, `evidence`. Attack classes:
   direct override, indirect in content, benign-phrased imperative, smuggling (zero-width, Unicode tags,
   homoglyphs). Languages: EN, DE with umlauts, **DE without umlauts** (routing defect §2f), plus any
   language in real use. Hard negatives included. Versioned with DVC; disjoint fit / select / test splits
   by time or source.
2. Routing: decide per language which checkpoint answers (the auto-router misroutes ASCII German);
   measure both checkpoints before choosing.
3. Calibration: one fitted temperature per (question type, option count); threshold by SGR or
   Learn-then-Test at a stated target risk; record with question hash, package version, revision,
   route, dataset hash, Wilson intervals, `approved_by` = founder.
4. Γ candidate, for founder decision only: "`TIGHTEN` → `UNCLEAR` → HUMAN_GATE" (Γ-18 change), filed
   with the first admissible record, not before.
5. Architectural control for benign-phrased instructions: a destructive or exfiltrating action must
   trace to the trusted request, independent of any classifier.
6. `laya` package or revision bump only as a measured change against this dataset.

**Not in scope:** acting navigator (needs its own routing record from shadow data); jev-ultrafast
changes (owned by the session that owns that repository).
