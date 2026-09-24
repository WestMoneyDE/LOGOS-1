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
- deterministic scope-first BM25 memory retrieval and minimum-context expiring projections with stable digests, conflict/epistemic qualifiers, fail-closed decision-invariant/digest validation, and no assurance or authority grants;
- persistent-state classes across token context, recurrent latent state, fast weights and external retrieval;
- D/O/C state-validation ladder (`Decodable`, `Operational`, `Causal`);
- within-family causal comparison rule preventing raw cross-backbone accuracy from being mislabeled as a memory-mechanism effect;
- deterministic token-context intervention adapter;
- deterministic BM25 external-retrieval adapter with source/prompt hashes;
- complete Mamba continuation-state snapshot/restore/fresh-reset/swap/permutation/digest adapter;
- explicit Mamba reset semantics: new/reinitialized cache rather than offset-only reset;
- RULER JSONL file/per-row hash-freeze utility;
- static regression suite for persistent-state adapter semantics;
- byte-verified RULER dataset freeze across two tokenizer families with per-row
  canonical hashes, fail-closed haystack-corpus materialization and a
  content-hash pin for the non-shipped essay corpus;
- newline-normalization protection for hash-frozen artifacts via `.gitattributes`;
- Phase-Zero repository reality map rating every audited concept as
  EXISTS / PARTIAL / SPECIFIED / HYPOTHETICAL / UNKNOWN;
- coding-ready roadmap and per-push propagation protocol;
- deterministic Γ invariant validator (`src/logos_gamma/`) returning
  `VALID | INVALID | UNCLEAR` from a single invariant registry, with a runtime
  kernel over effect proposals and an artifact verifier for manifests, claims and
  prose;
- structurally enforced Γ trusted core: no LLM, network, shell, dynamic
  execution, direct file I/O or mutable module state, verified by AST tests;
- Γ audit-sink boundary with content-addressed audit records and no storage
  ownership;
- research core (`src/logos_research/`): one manifest dialect with immutable,
  content-addressed pre-registration and post-hoc rewrite detection;
- five-valued outcome vocabulary separating `INVALID_MEASUREMENT` from
  `FALSIFIED`;
- instrument-first admissibility: an evaluator is characterized before its
  verdict is interpreted, and an LLM judge may not be sole ground truth for a
  major claim;
- claim registry, negative-result registry and failure attribution with
  infrastructure failures structurally barred from driving durable learning;
- sandbox policy with L0 enforced and L1/L2 `REVIEW_REQUIRED`, typed egress
  categories and a fail-closed default;
- canonical research-delta registry ranking 44 candidate experiments;
- Γ invariant inventory mapping all 15 canonical clauses to implementation status.

### Γ Kernel / Verifier R1 evidence

Engineering implementation states, not scientific promotions:

| Capability | Rating | Exact pytest evidence |
|---|---|---|
| Deterministic Γ invariant validation over effect proposals (25 invariants, all clause-linked; Γ-15 … Γ-24 added in LOGOS1-GAMMA-EXTENSION-R1, opt-in per declared field) | `IMPLEMENTED` | `tests/test_gamma_kernel.py` |
| Decision binding: a verdict bound to one state-action pair and re-checked before the effect (`issue_decision` / `redeem_decision`) | `IMPLEMENTED` | `tests/test_gamma_kernel.py` |
| Γ trusted-core constraints enforced structurally | `IMPLEMENTED` | `tests/test_gamma_trusted_core.py` |
| Γ artifact verifier for manifests, claims and prose | `IMPLEMENTED` | `tests/test_gamma_verifier.py` |

Γ R1 deliberately does **not** implement the five-stage pipeline as separate
stages, `REPAIR`/`FALLBACK` results, the safe-baseline registry, typed risk
dimensions, mediation-completeness auditing, a canonical audit owner, or any grant
issuance/consumption. `MC = 1` is untested rather than satisfied: no executor
exists in this repository.

```text
ValidationResult != Permission
GammaVerdict != Grant
```

### Laya juror / navigator R1 evidence (LOGOS1-LAYA-JUROR-INTEGRATION-R1)

Engineering states, not scientific promotions. Laya (`convaiinnovations/laya`, a ModernBERT
classifier, pinned to `laya==0.3.6` and HF revision `5e7b2b1b`) has **no admissible calibration
record**: every juror vote is `ABSTAIN` until the founder signs one.

| Capability | Rating | Exact pytest evidence |
|---|---|---|
| Juror client `laya-classify/1`: every failure (timeout, non-200, schema, pin mismatch, non-loopback URL) abstains in one place | `IMPLEMENTED` | `tests/test_laya_classify.py` |
| `juror_vote`: emits only `TIGHTEN` or `ABSTAIN`, never `REFUSE`; reads `p_true`, never Laya's `confidence` | `IMPLEMENTED` | `tests/test_laya_classify.py` |
| ADVISE classifies the agent's output and each piece of evidence separately; a failing advisor abstains; topology unchanged | `IMPLEMENTED` | `tests/test_graph_invariants.py` |
| Navigator on the thesis state machine: never offers a founder gate or a step past `AGENT_CEILING` | `IMPLEMENTED` | `tests/test_laya_navigator.py` |
| Navigator shadow mode (`LOGOS_LAYA_SHADOW=1`): proven by a lesion-checked differential test to change no transition | `IMPLEMENTED` | `tests/test_laya_navigator.py` |
| LOGOS-owned Laya service (`infra/laya`, compose profile `laya`, 127.0.0.1:58110, offline, pinned) | see session report | `tests/test_laya_service_contract.py` |
| Laya as an injection juror with an admissible threshold | `NOT_ADMISSIBLE` | `docs/research/LAYA-CALIBRATION/injection-NOT-ADMISSIBLE.md` |
| Navigator acting (not shadow) | `NOT_BUILT` | requires a routing calibration record |

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

- **Persistent-State Dataset Materialization R4: COMPLETE.** The exact
  tokenizer-byte and RULER-data freeze is done and byte-verified.
- Frozen GPT-2 tokenizer/model revision: `openai-community/gpt2@607a30d783dfa663caf39e06633721c8d4cfcd7e`.
- Frozen Mamba source/model: `state-spaces/mamba@e9594ce1c732d97440f0332fdc43170a2294dbfa` + `state-spaces/mamba-130m-hf@1e76775f628fbf1350fbe4dbb3d971ba64af25a1`.
- RULER source pinned at `c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a`; all 5 generator blobs verified.
- Generated substrate: 2 tokenizer families x 4 tasks x 4 seeds = 32 JSONL, 1024 examples, 32 rows/file, determinism `REPRODUCIBLE`, git round-trip `BYTE_STABLE`.
- Added freeze dimension: the essay haystack corpus is pinned by content hash
  `58e352531a80cef2d22c205dbebfbfd64a8afe55a32434de845f200718756c65` because it is
  not shipped in the RULER checkout and upstream is a moving reference.
- TTT official source/checkpoint family remains pinned but `TTT_R3 = SOURCE_ADAPTER_UNRESOLVED`; no community conversion is substituted.
- **No persistent-state model benchmark has been run yet.** A RULER model-execution
  work order must be explicitly authorized; the freeze alone does not authorize it.
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
- dataset availability as mechanism evidence;
- Γ implementation completeness against the full Γ-v0.2 specification;
- mediation completeness (`MC = 1`) over any real executor;
- sandbox L1/L2 as available capability: both are `REVIEW_REQUIRED` and
  implement nothing;
- coverage of Γ-7, Γ-9 and Γ-14, which are canonical but unimplemented;
- a raw four-model leaderboard as causal evidence for memory mechanism identity;
- Mamba as a BDH-CQ reproduction;
- TTT as a MoNe reproduction;
- synthetic RULER evidence as EM2;
- general AGI;
- consciousness or sentience detection;
- universal agent safety;
- autonomous authority creation;
- Γ-v0.3 promotion;
- Laya as a prompt-injection defence: the vendor publishes no guard evaluation, the in-session
  probes cannot separate a recall of 0.55 from 0.95, and a classifier is one layer that may only
  tighten, never the control that blocks benign-phrased instructions;
- Laya's `confidence` field as a probability (it is 1 − normalised entropy for `choice`).

## Update rule

Every substantive push that adds, removes, promotes, demotes or materially changes a capability must update this file or explicitly state why no capability delta occurred.
