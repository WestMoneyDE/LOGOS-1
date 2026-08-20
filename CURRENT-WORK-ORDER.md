# CURRENT WORK ORDER

**Status:** READY_TCV_R2_EXTERNAL_ARTIFACT_PREFLIGHT
**Task:** `05-WORK-ORDERS/NEXT-SESSION-TCV-R2-WRONG-BUT-USEFUL-EXTERNAL-PREFLIGHT-R1.md`

MF-R1 / LongMemEval-V2 was taken through its frozen resource gate in the current execution environment. The exact required runtime resources were not available:

- `Qwen/Qwen3.5-9B` reader/controller endpoint;
- `Qwen/Qwen3-Embedding-8B` embedding endpoint;
- `gpt-5.2` judge access under the frozen evaluator contract.

Classification:

`MF_R1 = UNTESTED_RESOURCE_TRANSPORT`

This is **not negative scientific evidence** for associative memory. No substitute model, lexical retriever, alternate judge or synthetic dataset was used. Per the one-shot execution rule, MF-R1 is parked and must not be automatically retried.

The next runnable external-evidence track is TCV-R2 / `Wrong but Useful` (arXiv:2608.14375). The primary paper is verified and states that the verbatim prompt/protocol configuration is included in `anc/reproducibility_artifact.zip`.

Next action:

1. obtain the official ancillary artifact from the primary arXiv release/source;
2. verify SHA-256, CRC and member inventory before interpreting it;
3. map the release schema without guessing;
4. preserve fixed cached-message pools and matched available/hidden replay;
5. execute a real replay only if the exact official artifact and required open-model/evaluator resources are available;
6. otherwise record `UNTESTED_RESOURCE_TRANSPORT` once and advance without retry.

Gamma live-provider work remains separately gated by explicit human grant. Γ-v0.3 remains `HOLD`.
