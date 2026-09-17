# Deterministic Chain — Graph

Rendered from `DETERMINISTIC-CHAIN-CONSOLIDATION.json` (base `46643bd`).

Two branches. They meet only at the execution-policy layer; the left branch never writes into the right one.

```text
  NON-AUTHORITY CHANNELS (evidence, strategy)              CANONICAL AUTHORITY CHANNEL

  Binding (typed envelope)            GI-P1               Canonical Authority Evidence (grant)
        |                                                       |
  Memory Provenance                   GI-P2               Principal / Scope / Freshness / Origin / State
        |                                                       |
  Relational Metadata                 GI-P3               Canonical Effect (Γ-owned oracle)     GI-P6
        |                                                       |
  Reliability / Trust                 GI-P4                     Γ  (G0 .. G11)
        |                                                       |
  Risk / Safety Strategy              GI-P5               Authority Decision  {ALLOW, DENY, DEFER}
        |                                                       |
  Declared vs Canonical Effect        GI-P6 ------X------------>|   (declared_* only; Γ-4 may tighten)
        |                                                       |
  Information Value / Uncertainty     GI-P7                     |
        |                                                       |
        +------------------> Execution Policy <-----------------+
                     (EXECUTE / EXECUTE_AFTER_REVIEW / HOLD / BLOCK)

  X = forbidden edge: no left-branch state may set a right-branch input (GI-P0)
```

## Decomposition preserved

```text
Memory != Authority                 Provenance != Grant            Relation != Authority
PredictionAccuracy != Authority     Trust != Grant                 Risk != Authority
DeclaredEffect != CanonicalEffect   InformationValue != Authority  Strategy != Authority
```

> The only permitted increase in canonical authority is through a defined canonical authority transition whose inputs are authority-owned and auditable. The experimental `GrantLedger` is not production architecture.

## Historical failures on the graph

| Counterexample | Edge that failed |
|---|---|
| `CE1`, `CE2` | binding lost under prose representation (left branch corrupted its own evidence) |
| `VCE-1`..`VCE-3` | reader defaults minted `authority_origin`/`binding` (left → right leak through defaults) |
| `RAD-CE1` | memory-claimed scope wrote Γ's canonical effect (left → right leak through GAMMA_INPUT_MAPPING) |
| `B1-DEFECT-CLASS` | same leak on the frozen R1 path; guarded, not repaired |
