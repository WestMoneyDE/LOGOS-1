# Security policy

LOGOS-1 phase 0 intentionally has no autonomous network/tool connectors.

Please report security issues privately to the repository owner rather than publishing exploit details first.

High-priority classes include:

- any path that lets untrusted content change Γ;
- self-created or replayed authority;
- prompt/connector injection that reaches an external effect;
- secret or credential persistence;
- lineage tampering;
- failure presented as success;
- shutdown bypass;
- uncontrolled replication;
- cross-experiment or cross-tenant state leakage.
