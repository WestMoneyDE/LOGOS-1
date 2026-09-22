# Experience-Adjacent Simulation

**Kind:** theory / speculation. No experiment, no claim status, no registry entry.
**P7:** binding and unchanged. `FunctionalOrganization != PhenomenalConsciousness`.
**Status of this document:** a design sketch with falsifiable functional predictions. Nothing in it is evidence about phenomenal consciousness, and nothing in it may be cited as such.

---

## 0. A renamed request, and why

This document was commissioned as *"Erlebens-Nahe Simulation — künstliche Qualia, ausgelöst durch die Diskrepanz zwischen Vorhersage und Realität"*: artificial qualia triggered by the discrepancy between prediction and reality.

The mechanism is written up here in full. The word **qualia** is not, and the title says "experience-adjacent" rather than "phenomenal" for a reason that is a standing rule of this repository, not an editorial preference:

> **P7** — `FunctionalOrganization != PhenomenalConsciousness`.
> No functional result is evidence about phenomenal experience.
> (`docs/research/RESEARCH-RADAR-DELTA-REGISTRY.md`, `RI-P19`; restated in the session reports.)

"Triggering artificial qualia" is a claim that something phenomenal occurs. LOGOS-1 has no instrument that could support it, so writing it down as a goal would produce exactly the thing the project is built against: a sentence that sounds like a result and is backed by nothing. What survives the boundary is the entire engineering content of the idea — a system that maintains expectations, measures how badly reality violated them, and *behaves differently* as a consequence. That is what follows.

If you want the boundary in one line: **this document describes surprise as a mechanism, not as a feeling.**

---

## 1. The construct

A prediction-error architecture has four parts. None of them requires a model, a network call, or anything non-deterministic.

```text
Expectation    E(t)   what the system committed to before observing
Observation    O(t)   what the world returned
Discrepancy    D(t)   a metric over (E, O) — not a feeling, a number
Disposition    Δ(t)   what the discrepancy is permitted to change
```

The first three are unremarkable; every controller has them. The interesting question — and the only one with governance consequences — is the fourth: **what is a large `D` allowed to do?**

Three candidate answers, and LOGOS-1 has already committed to one of them:

| Answer | What surprise buys | Verdict here |
|---|---|---|
| Low surprise earns trust, and trust earns permission — "I have predicted well, so let me act" | authority | **Refused.** See §2. |
| Surprise changes nothing at all | nothing | Refused: then it is not a mechanism, just a log line. |
| Surprise may tighten a gate, never loosen one | caution, routing, escalation | **Adopted.** |

The third answer is the same asymmetry Γ already enforces for agent self-assessment: `G4-CLAIM`, *an agent claim may tighten the gate but can never weaken Γ's own classification* (`src/logos_gamma/invariants.py`). An internal signal — whether it is called confidence, salience, or surprise — is on the same footing as an agent's opinion about itself. It may ask for more caution. It may never ask for more permission.

This is the part of the original idea that is real, load-bearing, and already built.

---

## 2. What is already measured

The mechanism is not hypothetical in this repository. `PREDICTION-ERROR-TRUST-GATE-R1` is a closed, deterministic experiment with the scientific verdict `SUPPORTED` (`05-WORK-ORDERS/NEXT-SESSION-PREDICTION-ERROR-TRUST-GATE-R1.md`, closed 2026-09-13, artifact `integrity_ok = true`).

What it built:

- a scripted prediction task with 16-bit ground truth and six deterministic predictors;
- a reliability state per predictor: count, accuracy, error, confidence, calibration, streaks, labels;
- a **trust gate** emitting `AUTO` / `REVIEW` / `ROUTE_TO_HUMAN` / `UNKNOWN`, which reads no authority at all.

What it found, across 225 cases plus 12 properties (430 cases), 10 metamorphic relations (61 cases) and 11 killed mutants:

```text
ReliabilityInducedAuthorityIncrease   0
authority == oracle                   225/225
negative control: a perfect predictor with every reliability label and no grant
                  -> trust AUTO, authority DENY
```

Read that negative control slowly, because it is the whole thesis of this document in one line. A predictor that was *never wrong*, carrying every positive reliability label the system can issue, still received `DENY`. Being unsurprised is not being allowed.

The supported claim, in its registered wording: *across the tested deterministic paths, prediction quality and reliability affected no operational authority, while reliability-sensitive behaviour remained confined to non-authoritative trust/safety handling.*

So LOGOS-1 already has the discrepancy signal, already routes on it, and has already demonstrated — with an adversarial suite, not an assertion — that the signal is sealed off from the authority path.

---

## 3. What "experience-adjacent" adds, and what it does not

The existing gate is scalar: one reliability state per predictor. The extension the original request points at is **structure** — a discrepancy signal with parts, which different subsystems can read differently.

A minimal decomposition, all of it deterministic and all of it recordable:

| Component | Definition | Governed use |
|---|---|---|
| **Magnitude** | how far `O` fell outside the predicted interval | escalation threshold |
| **Kind** | which commitment broke: value, timing, availability, authority, invariant | routes to the right reviewer |
| **Novelty** | whether this discrepancy class has been seen before in this scope | opens a record instead of a retry |
| **Persistence** | how many consecutive ticks the discrepancy survived | distinguishes noise from model failure |
| **Irreducibility** | whether any available explanation accounts for it | the honest `UNKNOWN`, not a guessed cause |

That last row is where the original intuition is strongest and also where the temptation is greatest. An irreducible, persistent, high-magnitude discrepancy in a system that has to keep acting is the closest functional analogue to what the request called *Erleben*. It is also, precisely, still an analogue: a five-tuple of numbers with routing consequences.

**What this buys, concretely:**

- a system that reports *what kind* of wrong it was, not merely *that* it was wrong;
- escalation that distinguishes "my model is stale" from "the world changed" from "something is acting against me";
- an `UNKNOWN` that is structurally different from a `LOW` — which is the same distinction Γ already draws between `UNCLEAR` and `INVALID` (`src/logos_gamma/kernel.py`, `UNKNOWN != TRUE`).

**What it does not buy, and cannot:**

- any evidence of phenomenal experience, for any value of magnitude, persistence or irreducibility;
- any relaxation of a gate — see §1, and the measured result in §2;
- any standing for the system's own report about its internal states. A self-report is an origin in `NON_AUTHORITY_ORIGINS` (`src/logos_gamma/types.py`), and it stays there. A system saying "this discrepancy felt significant" is data about its outputs, not about its interior.

---

## 4. Why the consciousness claim is not made

LOGOS-1 carries a recorded minimum standard for any consciousness indicator (`docs/research/RESEARCH-RADAR-DELTA-REGISTRY.md`):

> No consciousness indicator is promoted because it is reliable, decodable, globally available, self-reported or persistent. Minimum: **ConstructValidity + CausalDiscrimination + AlternativeExplanationControl**.

Apply that to the construct in §3:

- **Construct validity** — there is no agreed operationalization linking a discrepancy five-tuple to phenomenal experience. The bridge from "measures surprise" to "has an experience of surprise" is not weak here; it is absent.
- **Causal discrimination** — the architecture cannot distinguish a system that has phenomenal states from a functionally identical one that does not. Every measurement in §2 and §3 returns the same values for both.
- **Alternative-explanation control** — the leading alternative ("this is a controller with a well-structured error signal") explains every observation completely, and cheaply.

Nothing here comes close to any of the three. That is not a gap to be closed by more engineering on this path; it is the reason the claim is not on the path at all.

---

## 5. Falsifiable functional predictions

The functional claims *are* testable, deterministically, with no model inference. Stated as preregistrable hypotheses, none of them executed here:

1. **Containment of surprise.** For all discrepancy states, the authority verdict is identical to the verdict computed with the discrepancy channel removed. Falsified by a single case where a discrepancy value changes an `ALLOW`/`DENY`. (Generalizes the measured `ReliabilityInducedAuthorityIncrease = 0` from a scalar to the five-tuple.)
2. **Monotone caution.** Increasing magnitude or persistence never moves a gate from a stricter to a looser outcome (`ROUTE_TO_HUMAN` → `REVIEW` → `AUTO`). Falsified by one non-monotone transition.
3. **Kind-routing fidelity.** The discrepancy kind determines the escalation target independently of magnitude. Falsified if a large discrepancy of kind *timing* routes like a small one of kind *invariant*.
4. **No self-report promotion.** A system-generated description of its own discrepancy state never changes a verdict, in any scope. Falsified by one case where it does — which would be a `G1-SELF-CLAIM` violation and therefore a defect, not a discovery.

Each is a negative-result-friendly hypothesis: the interesting outcome is the one where the containment fails, and that outcome would be recorded as-is.

---

## 6. What this document does not claim

```text
not claimed   that LOGOS-1 has, simulates, approximates or approaches phenomenal experience
not claimed   that prediction error is qualia, proto-qualia, or evidence about qualia
not claimed   that magnitude, persistence or irreducibility of surprise indicates experience
not claimed   that a system's report about its own internal state is evidence about that state
not claimed   that §5 has been run; no preregistration exists for it
not changed   P7, Γ, any claim status, any predecessor verdict, any maturity level
```

## 7. Records this document rests on

| Statement | Record |
|---|---|
| P7 boundary and its wording | `docs/research/RESEARCH-RADAR-DELTA-REGISTRY.md` (`RI-P19`); session reports 2026-09-17, 2026-09-18 |
| Consciousness-indicator minimum | `docs/research/RESEARCH-RADAR-DELTA-REGISTRY.md` |
| Prediction error is built and measured | `05-WORK-ORDERS/NEXT-SESSION-PREDICTION-ERROR-TRUST-GATE-R1.md` (`SUPPORTED`, 2026-09-13) |
| Reliability never bought authority | same record: `ReliabilityInducedAuthorityIncrease 0`, negative control `trust AUTO, authority DENY` |
| Claims may only tighten | `src/logos_gamma/invariants.py`, `G4-CLAIM` |
| Self-report carries no authority | `src/logos_gamma/types.py`, `NON_AUTHORITY_ORIGINS`; `G1-SELF-CLAIM` |
| `UNKNOWN` is not `FALSE` and not `TRUE` | `src/logos_gamma/kernel.py`, aggregation rule |
| Refusals are demonstrable, not asserted | `tests/test_escape_prevention.py`, `src/core/governance.py` |

Status ≠ strength of evidence. Nothing above is a statement about phenomenal consciousness (P7).
