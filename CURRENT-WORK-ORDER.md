# CURRENT WORK ORDER

**Status:** `READY_GAMMA_KERNEL_AND_INVARIANT_VERIFIER_R1`
**Task:** `05-WORK-ORDERS/NEXT-SESSION-GAMMA-KERNEL-AND-INVARIANT-VERIFIER-R1.md`

## Explicit queue transition

```text
FROM  READY_PERSISTENT_STATE_DATASET_MATERIALIZATION_R4
TO    COMPLETE_DATASET_FREEZE_R4          (closed, evidence recorded)
THEN  READY_GAMMA_KERNEL_AND_INVARIANT_VERIFIER_R1
```

The predecessor was closed, not replaced. Its closure record lives in
`05-WORK-ORDERS/NEXT-SESSION-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4.md`
under **Closure record**, its evidence in
`09-SESSIONS/2026-09-10-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4/`, and its
review in pull request #10.

## Closed predecessor — R4 result

```text
attempts                     1 (ONE_SHOT_NO_AUTORETRY honoured)
return classification        COMPLETE_DATASET_FREEZE
RULER@c3f5e3b4               generator blobs 5/5 verified
openai-community/gpt2        5 tokenizer artifacts hashed
state-spaces/mamba-130m-hf   3 tokenizer artifacts hashed
essay corpus                 218/218 fail-closed, content-hash pinned
datasets                     32 JSONL / 1024 examples / 32 rows each
determinism                  REPRODUCIBLE
git round-trip               BYTE_STABLE 32/32
tests                        122 passed / 0 failed
model weights loaded         NO
model inference performed    NO
mechanism evidence produced  NO
evidence-level promotion     NONE
```

Added freeze dimension, because the essay haystack is not shipped in the RULER
checkout and upstream is a moving reference:

```text
haystack_corpus_sha256 = 58e352531a80cef2d22c205dbebfbfd64a8afe55a32434de845f200718756c65
```

`niah_multikey_1` and `niah_multiquery` inherit that boundary. `niah_single_1` and
`vt` use the noise haystack and do not. A future session that cannot reproduce
this hash must treat the two essay tasks as a **changed substrate**, not as
comparable data.

## Standing inference prohibition

The freeze authorizes no model run.

```text
DatasetMaterializationAuthorization != InferenceAuthorization
```

A RULER model-execution work order is unwritten and must be separately and
explicitly authorized. It must state which persistent-state families are compared
under which matched-family rule, the equal-information / equal-budget contract
between arms, and pre-registered nulls, kill rules and falsification criteria.
`TTT_R3 = SOURCE_ADAPTER_UNRESOLVED` remains excluded.

## Active task — Γ Kernel and Invariant Verifier R1

`GAMMA.md` specifies Γ-v0.2 completely but no executable Γ exists here. R1 builds a
deterministic invariant validator:

```text
validate(context, gamma_invariants) -> VALID | INVALID | UNCLEAR
```

Determined architecture: a **standalone deterministic library** at
`src/logos_gamma/`, importing nothing from `logos_memory`, because no execution
runtime exists in this repository and hosting Γ inside the memory subsystem would
contradict Γ-12 (`AssuranceState != AgentMemory`).

Two deliverables from **one** invariant source (`logos_gamma.invariants`):

- **Γ Verifier** — validates research manifests, claims, work orders and
  architecture artifacts against `GAMMA.md`;
- **Γ Kernel** — deterministic runtime invariant validation with no LLM, no
  network, no arbitrary shell and no hidden mutable state in the trusted core,
  failing closed on consequential ambiguity.

Γ may read state and authority evidence. Γ may write validation/audit evidence only
through the canonical audit owner. Γ must never create authority.

## Successor

Research Infrastructure R1 (PostgreSQL canonical experiment persistence, MLflow
tracking, MinIO artifact storage, machine-readable manifests, pre-registration,
claim/evidence and negative-result registries, instrument-first evaluator
validation, sandbox architecture, failure attribution) begins **only after** Γ R1
is validated, and consumes the invariant boundary rather than redefining it. The
two must not be merged into one implementation.

## Boundaries

```text
Capability != Authority
AssuranceState != AgentMemory
ScopeDecision != DispatchAuthorization
ValidationResult != Permission
DatasetAvailability != MechanismEvidence
RULER-controlled evidence <= EM1
```

`Γ-v0.3` remains `HOLD`.
