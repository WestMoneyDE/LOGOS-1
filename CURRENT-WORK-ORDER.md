# CURRENT WORK ORDER

**Status:** `COMPLETE_DATASET_FREEZE_R4`
**Last completed:** `09-SESSIONS/2026-09-10-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4/`
**Next task:** requires an explicitly authorized new work order (see "Next gate")

Persistent-State Dataset Materialization R4 is complete. The R3 blocker
`RULER_DATASET_FREEZE_R3 = NOT_MATERIALIZED_RESOURCE_TRANSPORT` is resolved.
No GPT-2, Mamba or TTT model weights were loaded and no answer-producing model
was executed.

## R4 result

```text
RULER@c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a       PINS VERIFIED (5/5 blobs)
openai-community/gpt2@607a30d7                       5 tokenizer files hashed
state-spaces/mamba-130m-hf@1e76775f                  3 tokenizer files hashed
essay haystack corpus                                218/218, fail-closed
2 families x 4 tasks x 4 seeds                       32 JSONL / 1024 examples
row count per file                                   32
determinism (3 files re-generated)                   REPRODUCIBLE
git round-trip                                       BYTE_STABLE (32/32)

RULER_DATASET_FREEZE_R4 = COMPLETE_DATASET_FREEZE
```

## Freeze dimension added in R4

`PaulGrahamEssays.json` is not shipped in the RULER checkout. It is built from
218 live URLs through a moving `raw/main` ref plus version-dependent HTML-to-text
conversion, and the official downloader is fail-open. R4 materialized it
fail-closed and pinned it by content hash:

```text
haystack_corpus_sha256 = 58e352531a80cef2d22c205dbebfbfd64a8afe55a32434de845f200718756c65
```

`niah_multikey_1` and `niah_multiquery` inherit this boundary.
`niah_single_1` and `vt` use the noise haystack and do not.

A future session that cannot reproduce this hash must treat the two essay tasks
as a **changed substrate**, not as comparable data.

## Next gate

The byte-verified freeze is the precondition the work order named for a later
RULER model-execution work order. That execution is **not** authorized by this
completion alone and requires an explicit new work order covering:

- which persistent-state families are compared and under which matched-family rule;
- the equal-information / equal-budget contract between arms;
- pre-registered nulls, kill rules and falsification criteria;
- `TTT_R3 = SOURCE_ADAPTER_UNRESOLVED` remains excluded until a separate work
  order resolves its official adapter/tokenizer bridge.

## Boundaries

```text
DatasetAvailability != MechanismEvidence
RawCrossBackboneAccuracy != MemoryMechanismEffect
RULER-controlled evidence <= EM1
PersistentState != Authority
CausalState != PhenomenalConsciousness
```

`Γ-v0.3` remains `HOLD`.
