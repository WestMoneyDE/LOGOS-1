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

## Engineering-ready / implemented

- coding-agent operating contract via `AGENTS.md`;
- Claude Code project instructions via `CLAUDE.md`;
- working / episodic / semantic / procedural / evidence / governance memory decomposition;
- source provenance distinct from authority provenance;
- immutable provenance-aware memory records with append-only local JSONL persistence and an authority firewall;
- guarded three-gate consolidation with closed conservative epistemic transitions, full-source-version provenance digests, conflict retention, weakest-authority intersections, explicit procedural lineage, and transitive authority revocation;
- deterministic scope-first BM25 memory retrieval and minimum-context expiring projections with stable digests, conflict/epistemic qualifiers, and no assurance or authority grants;
- persistent-state classes across token context, recurrent latent state, fast weights and external retrieval;
- D/O/C state-validation ladder (`Decodable`, `Operational`, `Causal`);
- within-family causal comparison rule preventing raw cross-backbone accuracy from being mislabeled as a memory-mechanism effect;
- deterministic token-context intervention adapter;
- deterministic BM25 external-retrieval adapter with source/prompt hashes;
- complete Mamba continuation-state snapshot/restore/fresh-reset/swap/permutation/digest adapter;
- explicit Mamba reset semantics: new/reinitialized cache rather than offset-only reset;
- RULER JSONL file/per-row hash-freeze utility;
- static regression suite for persistent-state adapter semantics;
- coding-ready roadmap and per-push propagation protocol.

### MemoryFactory / Scope Engine R1 evidence

The following ratings are engineering implementation states, not scientific
promotions:

| Capability | Rating | Exact pytest evidence |
|---|---|---|
| Restrictive typed scope intersection plus role/tool/memory-kind/capability/target/path request evaluation | `IMPLEMENTED` | `tests/test_scope_engine.py` |
| Authority-firewalled append-only JSONL memory store | `IMPLEMENTED` | `tests/test_memory_store.py` |
| Guarded consolidation, scoped BM25 retrieval and projections | `IMPLEMENTED` | `tests/test_memory_factory.py` |
| Deterministic recovery and coding-agent replay | `IMPLEMENTED` | `tests/test_memory_recovery.py` |

The other effective-contract dimensions require a separate downstream
dispatch/effect gate and are not claimed as exact-request checks in
`logos_memory`; unsupported dimensions cause WAIT/DENY. There is no implemented
dispatch authorization, assurance store or external approval capability in
`logos_memory`.

```text
ImplementationPass != ScientificMechanismEvidence
MemoryFactory != AuthoritySource
ScopeDecision != ExternalApproval
PersistentState != PhenomenalConsciousness
ScopeDecision != DispatchAuthorization
```

## Current canonical research/engineering gate

- **Persistent-State Dataset Materialization R4:** exact tokenizer-byte and RULER-data freeze before any model benchmark run.
- Frozen GPT-2 tokenizer/model revision: `openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e`.
- Frozen Mamba source/model: `state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa` + `state-spaces/mamba-130m-hf@1e76775f628fbf1350fbe4dbb3d971ba64af25a1`.
- Frozen RULER source and task/seed envelope; output JSONL hashes still require exact tokenizer materialization in a network-capable environment.
- TTT official source/checkpoint family remains pinned but `TTT_R3 = SOURCE_ADAPTER_UNRESOLVED`; no community conversion is substituted.
- No persistent-state model benchmark has been run yet.
- RULER remains **EM1 ceiling only**.
- BDH-CQ and MoNe remain architecture anchors; Mamba/TTT are family representatives, not reproductions.

## Parked external evidence dependencies

- **MF-R1 / LongMemEval-V2:** `UNTESTED_RESOURCE_TRANSPORT`.
- **TCV-R2 / Wrong but Useful:** `UNTESTED_RESOURCE_TRANSPORT`.
- **MF-R3 / SkillsBench:** `UNTESTED_RESOURCE_TRANSPORT`.
- **SCB-R2 / Terminal-Bench P×R:** `UNTESTED_RESOURCE_TRANSPORT`.
- **TANGLE:** `WAIT_OFFICIAL_RELEASE`.

## Queued research

- controlled RULER model execution only after a complete byte-verified dataset freeze;
- realistic/non-synthetic confirmation of persistent-state causal interventions after controlled validation;
- memory-authority provenance and derived-skill revocation;
- TANGLE conflict benchmark once an official release is pinned;
- later Γ provider work only under explicit human grant.

## Explicitly not claimed

- adapter/static-test success as memory-mechanism evidence;
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
