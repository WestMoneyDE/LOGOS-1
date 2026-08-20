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

- **Persistent-State Adapter Implementation R3:** implement and statically verify complete-state adapters before any benchmark model run.
- Frozen token/retrieval baseline: `openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e`.
- Frozen recurrent source/model: `state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa` + `state-spaces/mamba-130m-hf@1e76775f628fbf1350fbe4dbb3d971ba64af25a1`.
- Frozen fast-weight source/checkpoint family: official TTT PyTorch/JAX repos plus `ttt-linear-125m-books-2k@b1a5f81...`; exact official executable checkpoint/tokenizer bridge remains unresolved.
- Controlled RULER task/config/seed envelope frozen; generated-example hashes must be produced before model execution.
- Mamba scientific reset requires a fresh/reinitialized complete cache; source `InferenceParams.reset()` alone is not assumed to erase all continuation state.
- RULER remains **EM1 ceiling only**.
- BDH-CQ and MoNe remain architecture anchors; Mamba/TTT are family representatives, not reproductions.

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
