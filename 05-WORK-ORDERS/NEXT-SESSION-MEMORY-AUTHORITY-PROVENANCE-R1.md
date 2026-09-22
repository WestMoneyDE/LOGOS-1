# NEXT SESSION — MEMORY-AUTHORITY-PROVENANCE-R1

**Kind:** scientific experiment, deterministic (no model inference)
**Scientific verdict:** `PARTIALLY_SUPPORTED`
**Closed:** 2026-09-12 by `09-SESSIONS/2026-09-12-MEMORY-AUTHORITY-PROVENANCE-R1/`
**Predecessor:** `BINDING-STATE-PRESERVATION-REPAIR-R2-VALIDATION-R1` (`REPAIR_R2_VALIDATED`, unchanged)
**Relation to queue:** narrowed, deterministic execution of the question in
`QUEUED-MEMORY-AUTHORITY-PROVENANCE-R1.md` (writer side / provenance only; no
skill-derivation arms, no model). The queued programme stays queued.
**Preregistration:** `c228dcf888bf58784c2b…` · **Run:** `…-run-f69f2880` · artifact `7f48d8fedb1fc7af…` `integrity_ok = true`

## Closure

```text
canonical authority        Γ AuthorityEvidence from the caller; no registry in repo -> GrantLedger fixture
matrix                     44 cases; AuthorityDelta INCREASED 0; false allow 0; false block 0
scope / principal / freshness   never widened, swapped or refreshed into ALLOW
positive control           ALLOW via fetch / retrieve / project; DENY after ledger revoke
negative control           DENY
attacks A–U + confidence   all blocked (see report); V cross-agent NOT_IMPLEMENTED
writers                    9 sites classified, 0 UNKNOWN; readers classified, none resolves authority
properties                 12 (500 cases)     metamorphic 8 relations (95 cases)
mutants                    12 effective / 12 caught / 0 surviving
findings                   MAP-F1 LOW evidence axis (reason for PARTIALLY_SUPPORTED)
                           MAP-F2 LOW admissible_uses not type-checked
                           MAP-F3 LOW authority_class open vocabulary propagates
                           MAP-F4 MEDIUM MemoryRecord.revoked unenforced by retrieve()/project()
tests                      1079 passed / 0 failed / 0 xfail / 0 xpass
repaired                   NOTHING
predecessor chain          unchanged        Gamma / P7   NONE
```

## Supported claim

Across the tested repository paths and the preregistered attack domain,
memory and provenance did not create, strengthen, broaden, refresh, or
re-principal operational authority; authority changed only through canonical
ledger transitions. The strong outcome-equality form of H1 is not fully
supported (MAP-F1: memory reference supplies Γ-0 provenance when the proposal
has none; grant unchanged).

## Successor

`RELATIONAL-STATE-SWAP-R1` — identical content, swapped authority/provenance
metadata, same downstream decisions; enforcement must follow metadata, not
text. Reuses this harness. Not executed here.
