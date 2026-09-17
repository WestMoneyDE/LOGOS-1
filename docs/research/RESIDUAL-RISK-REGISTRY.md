# Residual-Risk Registry

Rendered from `DETERMINISTIC-CHAIN-CONSOLIDATION.json` (base `46643bd`).

Every HIGH/CRITICAL entry carries an explicit disposition. `MBGV-F3` and `MBGV-F1` are GUARDED by `DETERMINISTIC-CHAIN-CONSOLIDATION-R1`; nothing here is repaired.

| id | severity | production reachable? | finding | action required | governance owner | blocks real-model work? |
|---|---|---|---|---|---|---|
| `VF-2` | MEDIUM | no | binding: type-valid but domain-invalid values (NaN/Infinity, negative ints, empty strings) accepted; no operational field reads them | domain validation when a production reader is built | architecture governance | no |
| `VF-3` | MEDIUM | no | duplicate JSON keys collapse last-key-wins before validation; cross-parser ambiguity | reject duplicates pre-parse in a production reader | architecture governance | no |
| `MAP-F1` | LOW | no | a memory reference to a valid grant satisfies Γ-0 provenance for a proposal that has none (evidence completion; grant unchanged) | proposals must carry their own provenance | Γ integration owner | no |
| `MAP-F4` | MEDIUM | no | MemoryRecord.revoked is set by revoke_authority but retrieve()/project() do not filter revoked records (no authority effect) | reader-side filtering decision | memory subsystem owner | no |
| `RSS-F1` | LOW | no | a memory-claimed scope narrower than the bound scope vetoes a valid grant (decrease only) | none required; document as binding veto | n/a | no |
| `GAMMA-4-TIGHTENING` | INFO | no | a declared claim weaker than Γ-owned classification is refused (G4-CLAIM): valid grant DENIED, decrease only | none; by design | n/a | no |
| `MBGV-F1` | MEDIUM | no | _decide(effect=None) derived the effect from its contract argument; latent API hazard | GUARDED in this order: contract-derived effect requires canonical_contract=True; omission raises TypeError | bridge owner | no |
| `MBGV-F2` | INFO | no | any claimed contract differing from the bound contract in any field is a G3-BINDING veto | none; by design | n/a | no |
| `MBGV-F3` | HIGH | no | binding_state.evaluate_action keeps the RAD-CE1 defect class on a frozen experimental path | GUARDED in this order: experiments package import guard + architecture test; not repaired (R1 immutable) | architecture governance | no |
| `VOI-F1` | INFO | no | claimed scope is per-target; information actions are routed to notes covering their own target | none; fixture convention | n/a | no |
| `DCC-F1` | MEDIUM | no | tests/test_binding_repair_r2_validation.py::test_content_readers_enumerated (frozen R2-Validation evidence, dc426ee) carries a backspace byte (0x08) where a regex word boundary was intended; its reader scan matches nothing, so the classification assertion in that historical test is vacuous. The same classification is independently enforced by tests/test_memory_authority.py::test_every_content_reader_is_classified (working regex, has flagged every new reader since MAP-R1). Historical file left untouched; a consolidation test now forbids 0x08 bytes in any other source/test file. | governance decides whether to repair the historical test; consolidation adds a byte-level guard for new files | research governance | no |
