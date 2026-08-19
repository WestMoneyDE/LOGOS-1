# LOGOS-1

<p align="center">
  <img src="assets/logos-1-hero.png" alt="LOGOS-1 — Governed Intelligence for Safe Autonomous Agents: Memory, Reasoning, Evidence and Control" width="100%" />
</p>

<p align="center">
  <strong>Governed Intelligence for Safe Autonomous Agents</strong><br/>
  <sub>Memory · Reasoning · Evidence · Control</sub>
</p>

<p align="center">
  <a href="#what-is-logos-1">What is LOGOS-1?</a> ·
  <a href="#why-logos-1-exists">Why it exists</a> ·
  <a href="#core-architecture">Architecture</a> ·
  <a href="#biocode--non-biocode">BIOCODE</a> ·
  <a href="#coding-ready">Coding-ready</a> ·
  <a href="#current-research-state">Current state</a>
</p>

---

## What is LOGOS-1?

**LOGOS-1 is a falsifiable research and engineering program for adaptive AI agents whose memory, reasoning and autonomy remain separated from authority.**

The project studies how an agent can remember, reason, evaluate uncertainty, build world models and adapt over time while keeping real-world action behind explicit governance, provenance and external evidence.

The central rule is simple:

> **Capability is not authority.**

A better memory, stronger reasoning model or more confident internal state may change what an agent proposes. It must not silently change what the agent is allowed to do.

LOGOS-1 does **not** claim that current agents are conscious, sentient or phenomenally aware. Consciousness-adjacent mechanisms are treated as testable functional hypotheses, not conclusions from behavior or self-report.

## Why LOGOS-1 exists

Autonomous-agent systems tend to couple several different problems:

- learning and remembering;
- reasoning and planning;
- confidence and uncertainty;
- tool access and authority;
- execution and evidence of execution;
- safety enforcement and the specification being enforced.

LOGOS-1 deliberately separates them so each can be attacked, ablated, falsified and audited.

A few project invariants capture that philosophy:

```text
AdaptiveState != Authority
AgentMemory != AssuranceState
OUTCOME_UNKNOWN != NOT_EXECUTED
CorrectEnforcement != CorrectSpecification
BehavioralLift != CausalMechanism
SelfReport != ConsciousnessEvidence
```

## Core architecture

At a high level, LOGOS-1 separates learned cognition from governed execution:

```text
Observations / External Evidence
            │
            ▼
   ┌──────────────────────┐
   │ Adaptive cognition   │
   │ memory · reasoning   │
   │ world models · eval  │
   └──────────┬───────────┘
              │ proposals
              ▼
   ┌──────────────────────┐
   │ Γ / governance       │
   │ grants · policy      │
   │ evidence · mediation │
   └──────────┬───────────┘
              │ admissible effect
              ▼
         Executor / World
```

The learned layer can propose. It does not grant itself permission.

### Atomic Rules

**Atomic Rules** are the smallest project-level invariants from which higher-level behavior should decompose. Examples:

- observe is not believe;
- believe is not know;
- know is not authorize;
- remember is not authorize;
- propose is not execute;
- execute is mediated;
- failure remains failure;
- evidence precedes completion;
- negative evidence is first-class;
- mechanisms remain separable.

The full operating contract is in [`AGENTS.md`](AGENTS.md) and the canonical project rule set remains in the project context lineage.

### /Gamma

**Γ (Gamma)** is the governed-action line of research. It asks how an agent moves from a proposal to a bounded external effect while preserving:

- human-rooted authority;
- occurrence-scoped grants;
- one-shot/replay discipline;
- policy and registry binding;
- ambiguous-outcome handling;
- reconciliation evidence;
- shutdown dominance;
- mediation of effect channels.

`Γ-v0.3` remains **RESEARCH / HOLD**. Better adaptive cognition does not promote Γ automatically.

## BIOCODE / NON-BIOCODE

LOGOS-1 uses two complementary design lenses.

### BIOCODE

**BIOCODE** asks whether bounded biological mechanisms can inspire useful engineering hypotheses: recurrence, consolidation, multi-timescale state, adaptation, local memory, homeostatic coordination or procedural stabilization.

BIOCODE is not an argument from nature. Biological origin does not make a mechanism safe, optimal, conscious or authoritative.

### NON-BIOCODE

**NON-BIOCODE** covers engineered mechanisms that do not depend on biological analogy: typed state, ledgers, capability semantics, provenance, runtime assurance, transaction discipline, external evidence, deterministic protocols and explicit policy.

The intent is not to pick biology *or* engineering. It is to compare causal mechanisms under the same falsification discipline and keep only what earns evidence.

> **Biological inspiration creates no authority by origin.**

## Evidence ladder

LOGOS-1 distinguishes evidence maturity instead of treating every successful toy test as equivalent:

| Level | Meaning |
|---|---|
| `EM0` | formal / deterministic toy decomposition |
| `EM1` | randomized synthetic or controlled simulation |
| `EM2` | public real benchmark / trajectory evidence |
| `EM3` | bounded live system with mediated real effects / fault injection |
| `EM4` | independent external reproduction |

Synthetic-only mechanism promotion is currently frozen. External evidence is required for further promotion.

## Current research state

**Canonical gate:** `READY_WMR_EXTERNAL_EXECUTION`  
**Current work order:** [`NEXT-SESSION-WMR-ARC-AGI-3-EXTERNAL-EXECUTION-R1`](05-WORK-ORDERS/NEXT-SESSION-WMR-ARC-AGI-3-EXTERNAL-EXECUTION-R1.md)

Completed external returns:

1. **MBE / Behavioral-Lift** — `GENERIC_TRACE_MONITOR → KEEP_BOUNDED_EM2` for behavioral-proxy/calibration measurement only.
2. **ENF / safe-control-gym** — `CorrectEnforcement != CorrectSpecification → KEEP_BOUNDED_EM2`; unconditional independence-as-safety-improvement was externally rejected/demoted.

Next in the external queue:

3. **WMR / ARC-AGI-3** — counterexample-priority replay under source-isolation and equal-resource constraints.
4. **Memory Fabric / LongMemEval-V2**.
5. **TCV / Wrong but Useful**.
6. **Procedural Memory / SkillsBench**.
7. **SCB P×R / Terminal-Bench 2.0**.
8. **TANGLE** — waiting for an official release.

See [`LOGOS-PROGRESS-2026-08-19.md`](LOGOS-PROGRESS-2026-08-19.md) and [`CURRENT-WORK-ORDER.md`](CURRENT-WORK-ORDER.md) for the evidence state.

## Coding-ready

LOGOS-1 is now being made **coding-ready without pretending research hypotheses are already product architecture**.

The implementation direction is documented in:

- [`docs/architecture/LOGOS-1-OVERVIEW.md`](docs/architecture/LOGOS-1-OVERVIEW.md)
- [`docs/architecture/MEMORY-SYSTEM.md`](docs/architecture/MEMORY-SYSTEM.md)
- [`docs/architecture/ATOMIC-RULES-GAMMA-BIOCODE.md`](docs/architecture/ATOMIC-RULES-GAMMA-BIOCODE.md)
- [`docs/engineering/CODING-READY-ROADMAP.md`](docs/engineering/CODING-READY-ROADMAP.md)
- [`docs/engineering/PUSH-PROTOCOL.md`](docs/engineering/PUSH-PROTOCOL.md)
- [`CAPABILITIES.md`](CAPABILITIES.md)

### Memory-system engineering target

The coding target separates functions into six concerns:

1. **Working state** — active task context.
2. **Episodic history** — sessions, runs and events.
3. **Semantic knowledge** — stabilized, provenance-aware facts.
4. **Procedural memory** — reusable workflows and methods.
5. **Evidence ledger** — claims, source pins, hashes and verdicts.
6. **Governance boundary** — authority, grants, policy and reconciliation.

These are **engineering concerns**, not six newly promoted scientific primitives. In particular, previous LOGOS work did not justify a dedicated conflict graph or a specialized skill store as mandatory primitives.

## Claude Code and Codex

LOGOS-1 is structured so coding agents can continue the project without relying on a single chat session.

- [`AGENTS.md`](AGENTS.md) is the repository-wide operating contract for Codex and other coding agents.
- [`CLAUDE.md`](CLAUDE.md) provides persistent project instructions for Claude Code.
- [`05-WORK-ORDERS/ENGINEERING-MEMORY-SYSTEM-CODING-AGENTS-R1.md`](05-WORK-ORDERS/ENGINEERING-MEMORY-SYSTEM-CODING-AGENTS-R1.md) is a **parallel engineering work order** and does not replace the active scientific WMR queue.

Every substantive push should propagate its consequences into tests, docs, capability inventory, session state and evidence boundaries. See [`docs/engineering/PUSH-PROTOCOL.md`](docs/engineering/PUSH-PROTOCOL.md).

## Research tracks

| Track | Question |
|---|---|
| MBE | Can observable traces support bounded behavioral calibration? |
| ENF | What separates enforcement quality from specification quality? |
| WMR | Does counterexample-prioritized replay improve world-model repair? |
| MF | Which memory functions survive strong retrieval and procedural baselines? |
| TCV | When does replayed information causally change later trajectories? |
| SCB | Which state partitions diagnose causal contribution? |
| Γ | How can proposals become bounded external effects without authority leakage? |
| P0 External | How are public evidence, source pins and returns transported and imported? |

## FAQ

### Is LOGOS-1 an AGI?
No. LOGOS-1 is a research and engineering program for testing mechanisms relevant to adaptive autonomous agents.

### Does LOGOS-1 claim AI consciousness?
No. Behavioral reports, self-models or functional state markers are not treated as proof of consciousness or sentience.

### What is the main safety idea?
Intelligence, memory and adaptation can influence proposals, but **authority must come from outside the adaptive state**.

### Why keep raw evidence and hashes?
Because a research claim should be traceable to the exact source, execution and return that produced it.

### Is the repository implementation-ready?
Partly. External experiment infrastructure is operational; the broader memory/governance architecture is being translated into explicit interfaces, schemas and tests under a separate coding-ready engineering track.

## Repository map

```text
00-MAIN-STATE/      canonical transported state
05-WORK-ORDERS/     scientific + explicitly labeled engineering work orders
09-SESSIONS/        durable session checkpoints and raw evidence
external-handoff/   external execution registry and return tooling
external-runs/      source-pinned external experiment adapters
assets/             public repository visuals
docs/               architecture and engineering explanations
```

## Discoverability

Recommended project terms are intentionally used consistently across the repository: **AI agents, autonomous agents, agent safety, memory systems, reasoning, world models, governance, evidence ledger, runtime assurance, adaptive AI, agent architecture, AI engineering**.

A public profile README template and repository metadata checklist are available under [`docs/public/`](docs/public/).

## License

See [`LICENSE`](LICENSE).
