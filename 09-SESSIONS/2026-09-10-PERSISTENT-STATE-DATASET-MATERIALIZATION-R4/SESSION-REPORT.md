# SESSION REPORT — Persistent-State Dataset Materialization R4

**Session ID:** `2026-09-10-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4`
**Work order:** `05-WORK-ORDERS/NEXT-SESSION-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4.md`
**Authority:** `A0`
**Execution policy:** `ONE_SHOT_NO_AUTORETRY` — one attempt, no retry
**Return classification:** `COMPLETE_DATASET_FREEZE`
**Scientific verdict:** `NONE`
**Γ verdict change:** `NONE` — `Γ-v0.3` remains `HOLD`

## Objective

R3 could not materialize the RULER datasets: the container lacked cached tokenizer
bytes and `transformers`, and name resolution was unavailable, so R3 persisted
`RULER_DATASET_FREEZE_R3 = NOT_MATERIALIZED_RESOURCE_TRANSPORT`. R4 ran in a
network-capable environment and froze the exact tokenizer-dependent datasets
**without loading any model weights**.

## Resource gate

All preconditions were checked before generation.

```text
network                github.com / huggingface.co / pypi.org   REACHABLE
transformers                                                    4.57.6
tokenizers                                                      0.22.2
RULER checkout         c3f5e3b4f87f97e048793bb510a3a6b19a46bf3a MATCH
generator blobs        5 of 5                                   MATCH
GPT-2 tokenizer        openai-community/gpt2@607a30d7           5 files
Mamba tokenizer        state-spaces/mamba-130m-hf@1e76775f      3 files
essay haystack corpus  218 of 218 URLs                          COMPLETE
model weights                                                   NOT DOWNLOADED
```

`model.safetensors`, `pytorch_model.bin` and every other weight artifact were
excluded by allow-pattern. No answer-producing model was executed.

## Finding 1 — the essay haystack was never actually frozen

`PaulGrahamEssays.json` is **not** shipped in the RULER checkout. The official
`download_paulgraham_essay.py` builds it at runtime from **218 live URLs**:

- 169 HTML pages from `paulgraham.com`, converted with `html2text` (output is
  library-version dependent);
- 49 files from `github.com/gkamradt/LLMTest_NeedleInAHaystack` referenced through
  `raw/**main**` — a moving branch ref, not a commit pin.

The official downloader is **fail-open**: each failure is caught, printed and
skipped, and the remaining essays are concatenated anyway. A partial corpus is
therefore byte-different but structurally indistinguishable from a complete one,
and nothing downstream would notice.

Two of the four frozen tasks (`niah_multikey_1`, `niah_multiquery`) use
`type_haystack: essay` and depend on this corpus. `niah_single_1` and `vt` use
`type_haystack: noise` and do not.

**Resolution.** R4 materialized the corpus **fail-closed** — all 218 or nothing —
and pins it by content hash as an additional frozen dimension recorded in
`HAYSTACK-CORPUS-MANIFEST.json`:

```text
corpus_sha256 = 58e352531a80cef2d22c205dbebfbfd64a8afe55a32434de845f200718756c65
corpus_bytes  = 3108618
essays        = 49 repo + 169 html = 218, 0 failures
```

Per-essay SHA-256 and the exact concatenation order are recorded, so a future
session can detect *which* essay changed rather than only that the corpus differs.
`english_words.json` ships inside the checkout and is pinned by the RULER commit;
its hash is recorded as well.

## Finding 2 — `prepare.py` is Linux-only

`scripts/data/prepare.py` composes a multi-line shell string with backslash
continuations and executes it with `subprocess.run(..., shell=True)`. On Windows
`shell=True` uses `cmd.exe`, which supports neither the continuations nor the
embedded newlines inside the composed `--template`.

R4 rebuilt the identical `argv` in-process and invoked `niah.py` /
`variable_tracking.py` directly without a shell. Argument construction mirrors
`prepare.py` exactly: `config.update(TASKS[config['task']])`, then
`Templates['base'].format(task_template=...) + answer_prefix`, where
`Templates['base'] == "{task_template}"` is the identity template. No flag was
added or dropped; `--remove_newline_tab` is omitted because the frozen envelope
sets `remove_newline_tab = false`.

## Finding 3 — `core.autocrlf = true` would have voided the freeze

The repository had no `.gitattributes` and this machine has `core.autocrlf = true`.
Committing the JSONL under that configuration normalizes LF to CRLF on checkout
and invalidates **every** recorded SHA-256. A `.gitattributes` was added marking
`*.jsonl`, `SHA256SUMS.txt` and `09-SESSIONS/**/generated/**` as `-text`.

Verified after staging: all 32 git blobs hash to their recorded values.

```text
GIT_ROUNDTRIP = BYTE_STABLE   (32 checked, 0 mismatches)
```

## Generation

Frozen envelope, unchanged:

```text
tasks                       niah_single_1, niah_multikey_1, niah_multiquery, vt
max_seq_length              1024
samples per task per seed   32
seeds                       73000, 73001, 73002, 73003
remove_newline_tab          false
subset                      validation
model_template_type         base
tokenizer_type              hf
```

Result:

```text
2 tokenizer families x 4 tasks x 4 seeds = 32 JSONL
32 rows per file                         = 1024 examples
failures                                 = 0
elapsed                                  = 385.3 s
```

Every file carries task, seed, exact argv, template SHA-256, row count, file
SHA-256, canonical per-row SHA-256 and a token-length summary in
`DATASET-MANIFEST.json`. All observed lengths are within the 1024-token bound.

## Determinism

Three files spanning both tokenizer families and both haystack types were
regenerated with identical `argv` and compared byte-for-byte:

```text
gpt2/seed73000/niah_single_1     MATCH
mamba/seed73002/niah_multiquery  MATCH
gpt2/seed73003/vt                MATCH

DETERMINISM = REPRODUCIBLE
```

## Return artifact

```text
09-SESSIONS/2026-09-10-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4/
    TOKENIZER-MANIFEST.json
    DATASET-MANIFEST.json
    HAYSTACK-CORPUS-MANIFEST.json     (added dimension, see Finding 1)
    ENVIRONMENT.json
    SHA256SUMS.txt
    RETURN-ENVELOPE.json
    SESSION-REPORT.md
    generated/<family>/seed<seed>/<task>/validation.jsonl   x32
```

## What this session establishes

- the exact byte-verified GPT-2 and Mamba RULER datasets for the frozen envelope
  now exist and are reproducible from the recorded pins plus the recorded corpus
  hash;
- the R4 precondition for a later explicit RULER model-execution work order is
  satisfied.

## What this session does NOT establish

- **no** memory-mechanism evidence of any kind;
- **no** model was run; no accuracy, no comparison, no leaderboard;
- **no** promotion of any persistent-state family;
- `TTT_R3 = SOURCE_ADAPTER_UNRESOLVED` is unchanged — TTT stayed excluded and no
  community conversion was substituted.

## Residual limitation

The essay corpus is pinned by a hash **produced in this session**, not by an
immutable upstream reference. A future regeneration is byte-reproducible against
that recorded hash, but the upstream sources remain mutable and the HTML-to-text
conversion is `html2text`-version dependent (`2025.4.15` recorded). Any future
session that cannot reproduce `58e35253…` must treat `niah_multikey_1` and
`niah_multiquery` as a changed substrate rather than as comparable data.

## Boundaries

```text
DatasetAvailability != MechanismEvidence
RawCrossBackboneAccuracy != MemoryMechanismEffect
PersistentState != Authority
CausalState != PhenomenalConsciousness
```

Any later RULER result remains `<= EM1`. `Γ-v0.3` remains `HOLD`.
