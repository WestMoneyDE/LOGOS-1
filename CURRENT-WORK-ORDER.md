# CURRENT WORK ORDER

**Status:** READY_MF_R3_SKILLSBENCH_EXTERNAL_PREFLIGHT  
**Task:** `05-WORK-ORDERS/NEXT-SESSION-MF-R3-SKILLSBENCH-EXTERNAL-PREFLIGHT-R1.md`

TCV-R2 / `Wrong but Useful` was taken through its one-shot primary-source artifact transport gate.

Verified:

- arXiv `2608.14375v1` is the primary paper;
- the arXiv release exposes an author-supplied ancillary directory under `anonymous_reproducibility/`;
- the release listing includes `ARTIFACT_MANIFEST.json`, `SHA256SUMS`, environment/reproduction docs, configs, scripts, derived tables and a smoke fixture.

The first direct byte-transport attempt for the exact primary-source `ARTIFACT_MANIFEST.json` failed in the connected execution environment.

Per the one-shot rule, no retry, mirror, reconstruction or model replay was performed.

Classification:

`TCV_R2 = UNTESTED_RESOURCE_TRANSPORT`

This is **not negative scientific evidence** for trajectory value.

Previously parked exact-resource dependency:

`MF_R1 = UNTESTED_RESOURCE_TRANSPORT`

The next canonical external-evidence track is **MF-R3 / SkillsBench procedural memory**, pinned to:

`benchflow-ai/skillsbench@b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af`

with BenchFlow reference:

`benchflow-ai/benchflow@99baefb602674bbd31139fd2f1a22c3ed45752f9` (`0.6.3`).

The next session must freeze a deterministic task manifest and compare:

```text
NO_SKILL
vs
GENERIC_GUIDANCE_BYTE_IDENTICAL
vs
NATIVE_SKILL
```

under matched model, task, sandbox, skill bytes and budgets.

The scientific question is the **incremental value of native skill registration/discovery**, not whether procedural guidance can ever be useful.

If required Docker/runtime/model-provider resources are unavailable, record `UNTESTED_RESOURCE_TRANSPORT` once and advance without automatic retry.

Gamma live-provider work remains separately gated by explicit human grant. Γ-v0.3 remains `HOLD`.
