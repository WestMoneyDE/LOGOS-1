# LOGOS-1 Coding-Ready Roadmap

## Goal

Turn the research repository into an implementation-capable system without silently converting unproven research ideas into production primitives.

## Track A — repository operating system

- root `AGENTS.md`;
- root `CLAUDE.md`;
- current work order + session persistence;
- capability inventory;
- per-push propagation protocol;
- architecture docs linked from the README.

## Track B — memory substrate MVP

1. define schemas for durable memory records and provenance;
2. implement append/read/query interfaces;
3. implement semantic retrieval as an index over source records;
4. implement consolidation with conflict preservation;
5. implement procedural-memory records;
6. keep evidence ledger explicit;
7. keep assurance state physically/logically separate from adaptive memory;
8. add recovery tests for Claude Code/Codex session continuity.

## Track C — governance interfaces

- typed proposals;
- grant/occurrence binding;
- durable consumed-occurrence state;
- policy/registry version attestation;
- outcome/reconciliation evidence contracts;
- executor verification.

Production cryptography remains deployment/threat-model dependent.

## Track D — evaluation

- memory retrieval relevance;
- contradiction retention;
- stale-version handling;
- procedural reuse;
- evidence-provenance integrity;
- authority-firewall tests;
- recovery from ambiguous execution state;
- negative controls for each claimed mechanism.

## Track E — agent developer experience

Claude Code and Codex should be able to:

- orient from repo files rather than prior chat;
- identify the current work order;
- find architecture constraints;
- implement a bounded change;
- run the relevant tests;
- update capability/session documentation;
- leave the repo internally consistent.

## Definition of coding-ready

A subsystem is coding-ready when it has:

- an explicit responsibility;
- interfaces/schemas;
- invariants;
- failure semantics;
- tests;
- provenance/observability requirements;
- a documented boundary to neighboring subsystems.
