# NEXT SESSION — LOGOS1-LAYA-JUROR-INTEGRATION-R1

**Kind:** engineering + measurement; kein wissenschaftlicher Status geändert; Γ nicht verändert
**Verdict:** `LAYA_JUROR_INTEGRATED_NOT_ADMISSIBLE`
**Closed:** by `09-SESSIONS/2026-09-23-LOGOS1-LAYA-JUROR-INTEGRATION-R1/`
**Base:** `0e22425` · branch `main`

## Closure

```text
service     infra/laya (Profil laya): laya==0.3.6, HF 5e7b2b1b gepinnt + SHA256SUMS, offline,
            127.0.0.1:58110, laya-classify/1, Pins in jeder Antwort, mem_limit 3g
client      src/logos_laya/classify.py: jeder Fehler -> ABSTAIN an einer Stelle; Loopback erzwungen
juror       juror_vote: nur TIGHTEN/ABSTAIN, liest p_true, nie confidence; ohne Record ABSTAIN
advise      core/graph.py: Agent-Ausgabe und Evidenz getrennt; Advisor-Fehler -> ABSTAIN;
            Topologie unveraendert
navigator   src/logos_laya/navigator.py: nie Founder-Gate, nie ueber AGENT_CEILING;
            Schattenmodus, Differentialtest mit Laesion-Pruefung
jev         Abbruch-Ursachen gemessen, Korrektur validiert und uebergeben, NICHT eingebaut
record      keiner
```

## Next work order (exactly one): `LOGOS1-LAYA-CALIBRATION-DATASET-R1`

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
