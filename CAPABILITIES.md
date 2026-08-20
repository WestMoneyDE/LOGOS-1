# LOGOS-1 Capability Map

This file is a **living implementation/research capability inventory**. A listed capability is not automatically a scientific claim.

## Operational today

- source-pinned external experiment handoff and preflight;
- standardized external return packing and validation;
- durable session/evidence persistence in GitHub;
- MBE Behavioral-Lift external execution/import;
- ENF safe-control-gym external execution/import;
- WMR ARC-AGI-3 external execution/import;
- explicit canonical work-order queue;
- one-shot/no-auto-retry external execution discipline;
- bounded Γ live GitHub pilot from prior work, with Γ-v0.3 still `HOLD`.

## Engineering-ready / specified

- coding-agent operating contract via `AGENTS.md`;
- Claude Code project instructions via `CLAUDE.md`;
- working / episodic / semantic / procedural / evidence / governance memory decomposition;
- source provenance distinct from authority provenance;
- derived procedural/skill lineage with revocation requirements under test;
- persistent-state classes across token context, recurrent latent state, fast weights and external retrieval;
- D/O/C state-validation ladder (`Decodable`, `Operational`, `Causal`);
- state-swap, reset and corruption/recovery intervention requirements;
- **within-family causal comparison rule** preventing raw cross-backbone accuracy from being mislabeled as a memory-mechanism effect;
- coding-ready roadmap and per-push propagation protocol.

## Current canonical research

- **Persistent-State Matched-Family R2:** freeze exact model/checkpoint/state adapters for within-family causal interventions.
- Recurrent-state source representative: `state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa`.
- Fast-weight source representative: `test-time-training/ttt-lm-pytorch@cd831db10c8c9a0f6340f02da5613316a8a92b67`.
- Controlled substrate candidate: `NVIDIA/RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a`, **EM1 ceiling only** because it generates synthetic examples.
- BDH-CQ and MoNe remain high-priority architecture anchors; exact executable state adapters are unresolved and are not silently replaced by Mamba/TTT.

## Parked external evidence dependencies

- **MF-R1 / LongMemEval-V2:** `UNTESTED_RESOURCE_TRANSPORT`.
- **TCV-R2 / Wrong but Useful:** `UNTESTED_RESOURCE_TRANSPORT`.
- **MF-R3 / SkillsBench:** `UNTESTED_RESOURCE_TRANSPORT`.
- **SCB-R2 / Terminal-Bench P×R:** `UNTESTED_RESOURCE_TRANSPORT`.
- **TANGLE:** `WAIT_OFFICIAL_RELEASE`.

## Queued research

- realistic/non-synthetic confirmation of persistent-state causal interventions after controlled adapter validation;
- memory-authority provenance and derived-skill revocation;
- TANGLE conflict benchmark once an official release is pinned;
- later Γ provider work only under explicit human grant.

## Explicitly not claimed

- a raw four-model leaderboard as causal evidence for memory mechanism identity;
- Mamba as a BDH-CQ reproduction;
- TTT as a MoNe reproduction;
- synthetic RULER evidence as EM2;
- general AGI;
- consciousness or sentience detection;
- universal agent safety;
- autonomous authority creation;
- Γ-v0.3 promotion.

## Update rule

Every substantive push that adds, removes, promotes, demotes or materially changes a capability must update this file or explicitly state why no capability delta occurred.
