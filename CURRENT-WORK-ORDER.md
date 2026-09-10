# CURRENT WORK ORDER

**Status:** `READY_RESEARCH_DELTA_EXECUTION`
**Task:** highest-ranked `READY` delta in `docs/research/RESEARCH-DELTA-REGISTRY.json`

## Explicit queue transition

```text
FROM  READY_PERSISTENT_STATE_DATASET_MATERIALIZATION_R4
TO    CLOSED_COMPLETE_DATASET_FREEZE            (evidence recorded, PR #10)
THEN  READY_GAMMA_KERNEL_AND_INVARIANT_VERIFIER_R1
TO    CLOSED_GAMMA_R1_IMPLEMENTED               (evidence recorded)
THEN  READY_RESEARCH_INFRASTRUCTURE_R1
TO    CLOSED_INFRASTRUCTURE_R1_IMPLEMENTED      (evidence recorded)
THEN  READY_RESEARCH_DELTA_EXECUTION
```

Each predecessor was closed with a Closure record in its own work-order file, not
replaced.

## Closed predecessor — Γ R1 result

```text
package                      src/logos_gamma/
invariants                   15, each linked to its GAMMA.md clause
invariant sources            1 (enforced by test)
gamma tests                  107 (46 kernel / 24 trusted core / 37 verifier)
full suite                   229 passed / 0 failed
required adversarial set     10/10 PASS
logos_memory imported        NO (AST-enforced)
LLM / network / shell        NO (AST-enforced)
scientific evidence          NONE
```

Γ is a standalone deterministic library because no execution runtime exists here
and hosting the authority gate inside adaptive memory would contradict Γ-12.
`MC = 1` is **untested, not satisfied**: there is no executor to mediate.
Contract: `docs/architecture/GAMMA-KERNEL.md`.
Evidence: `09-SESSIONS/2026-09-10-GAMMA-KERNEL-AND-INVARIANT-VERIFIER-R1/`.

## Closed predecessor — R4 result

Closure record in
`05-WORK-ORDERS/NEXT-SESSION-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4.md`,
evidence in `09-SESSIONS/2026-09-10-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4/`,
review in pull request #10.

```text
attempts                     1 (ONE_SHOT_NO_AUTORETRY honoured)
return classification        COMPLETE_DATASET_FREEZE
RULER@c3f5e3b4               generator blobs 5/5 verified
openai-community/gpt2        5 tokenizer artifacts hashed
state-spaces/mamba-130m-hf   3 tokenizer artifacts hashed
essay corpus                 218/218 fail-closed, content-hash pinned
datasets                     32 JSONL / 1024 examples / 32 rows each
determinism (same platform)  REPRODUCIBLE
git round-trip               BYTE_STABLE 32/32
tests                        122 passed / 0 failed
model weights loaded         NO
model inference performed    NO
mechanism evidence produced  NO
evidence-level promotion     NONE
```

`file_sha256` identifies the exact frozen byte representation (CRLF, Windows
text-mode generation, preserved by `.gitattributes` `-text`) and is
platform-sensitive under independent regeneration. `row_sha256` is
newline-normalization-independent and is the canonical cross-platform semantic
identity check. A differing regenerated `file_sha256` alone is not changed
substrate when the row hashes and envelope invariants match.

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

## Next task — Research Infrastructure R1

Scope, to be written into its own work order before implementation:

- PostgreSQL canonical experiment persistence;
- MLflow experiment tracking;
- MinIO immutable artifact storage;
- machine-readable experiment manifests;
- hypothesis / null-hypothesis pre-registration;
- claim / evidence registry;
- negative-result registry;
- instrument-first evaluator validation;
- OpenTelemetry / Langfuse where justified;
- sandbox architecture;
- reproducibility metadata;
- failure attribution.

Every new experiment manifest and major research claim is checked by the Γ Verifier
where Γ invariants apply. The infrastructure **consumes** the invariant boundary in
`src/logos_gamma/`; it never redefines it, and the two must not be merged into one
implementation.

Two constraints carried into that work order from this repository's own state:

1. moving canonical experiment truth out of the git-tracked, hash-verified,
   PR-reviewable artifacts and into service-backed storage is a material change to
   how evidence is reviewed, and must be recorded as an ADR;
2. provisioning containers, databases and network services is exactly the class of
   change `AGENTS.md` requires a separate safety review for.

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
