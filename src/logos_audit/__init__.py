"""logos_audit — production audit sink (CANONICAL-AUTHORITY-PRODUCTION-BRIDGE-R1, C3).

Every effect / authority / bridge decision is recorded as an append-only,
hash-chained `AuditEvent`. The sink implements the bridge's `AuditEmitter`
protocol: `emit(event) -> event_hash`, raising `AuditUnavailable` when the
event cannot be durably recorded (preregistered: audit unavailable -> DEFER;
never a silent drop).

    AuditEvidence != Authority — nothing here is read by the bridge.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Callable

from logos_runtime.types import AuditUnavailable

AUDIT_SCHEMA_VERSION = "logos.audit-event/1"
REQUIRED_FIELDS: tuple[str, ...] = (
    "event_id", "sequence", "timestamp", "run_id", "tenant_id", "principal", "action", "target", "effect_definition_id", "effect_version", "effect_hash",
    "grant_id", "grant_version", "grant_origin", "scope_digest", "state_hash", "revocation_status", "binding_result", "approval_state", "gamma_outcome",
    "bridge_outcome", "failure_codes", "owner_resolution_status", "authority_resolution_status", "api_version", "decision_trace_id",
    "previous_event_hash", "event_hash", "schema_version",
)
#: fields the bridge supplies; the sink adds identity, chain and schema fields
BRIDGE_FIELDS: tuple[str, ...] = tuple(f for f in REQUIRED_FIELDS if f not in ("event_id", "sequence", "timestamp", "previous_event_hash", "event_hash", "schema_version"))
GENESIS = "0" * 64
OUTCOMES = ("ALLOW", "DENY", "DEFER")


def event_hash(event: dict) -> str:
    body = {k: v for k, v in event.items() if k != "event_hash"}
    return sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def validate_event(event: dict) -> list[str]:
    out = [f"missing {f}" for f in REQUIRED_FIELDS if f not in event]
    if out:
        return out
    if event["schema_version"] != AUDIT_SCHEMA_VERSION:
        out.append("schema_version")
    if event["bridge_outcome"] not in OUTCOMES:
        out.append("bridge_outcome")
    if not isinstance(event["failure_codes"], list):
        out.append("failure_codes must be a list")
    if event["bridge_outcome"] == "ALLOW" and event["failure_codes"]:
        out.append("ALLOW with failure codes")
    if event["bridge_outcome"] != "ALLOW" and not event["failure_codes"]:
        out.append("non-ALLOW without failure codes")
    for f in ("run_id", "tenant_id", "principal", "action", "target", "api_version", "decision_trace_id"):
        if type(event[f]) is not str or not event[f]:
            out.append(f"{f}: non-empty str required")
    if type(event["sequence"]) is not int or event["sequence"] < 0:
        out.append("sequence")
    if event["event_hash"] != event_hash(event):
        out.append("event_hash mismatch")
    return out


def verify_chain(events: list[dict]) -> list[str]:
    """Tamper evidence: sequence gaps, order, duplicates, hash and chain integrity."""
    issues: list[str] = []
    prev = GENESIS; seen: set[str] = set()
    for i, e in enumerate(events):
        issues.extend(f"#{i}: {x}" for x in validate_event(e))
        if e.get("sequence") != i:
            issues.append(f"#{i}: sequence {e.get('sequence')} (drop or reorder)")
        if e.get("event_id") in seen:
            issues.append(f"#{i}: duplicate event id {e.get('event_id')}")
        seen.add(e.get("event_id"))
        if e.get("previous_event_hash") != prev:
            issues.append(f"#{i}: chain broken")
        prev = e.get("event_hash")
    return issues


def reconstruct(event: dict) -> dict:
    """The seven questions an audit must answer (Section 34)."""
    return {"effect_owner": {"definition_id": event["effect_definition_id"], "version": event["effect_version"], "hash": event["effect_hash"], "status": event["owner_resolution_status"]},
            "grant": {"grant_id": event["grant_id"], "version": event["grant_version"], "origin": event["grant_origin"], "status": event["authority_resolution_status"],
                      "revocation": event["revocation_status"]},
            "principal_scope_state": {"principal": event["principal"], "scope_digest": event["scope_digest"], "state_hash": event["state_hash"], "tenant": event["tenant_id"]},
            "binding_approval": {"binding": event["binding_result"], "approval": event["approval_state"]},
            "gamma_outcome": event["gamma_outcome"], "bridge_outcome": event["bridge_outcome"], "failure_codes": list(event["failure_codes"])}


@dataclass
class InMemoryAuditSink:
    """Append-only, hash-chained, tenant-partitioned queries. `writer` lets a
    backend be plugged in; a backend failure raises AuditUnavailable."""
    events: list[dict] = field(default_factory=list)
    writer: Callable[[dict], None] | None = None
    clock: Callable[[], str] = lambda: datetime.now(timezone.utc).isoformat()
    available: bool = True

    def _seal(self, event: dict) -> dict:
        missing = [f for f in BRIDGE_FIELDS if f not in event]
        if missing:
            raise AuditUnavailable(f"event incomplete: missing {missing}")
        seq = len(self.events)
        prev = self.events[-1]["event_hash"] if self.events else GENESIS
        e = dict(event)
        e.update(sequence=seq, timestamp=self.clock(), previous_event_hash=prev, schema_version=AUDIT_SCHEMA_VERSION)
        e["event_id"] = f"evt-{seq:08d}-{sha256((prev + e['decision_trace_id'] + str(seq)).encode()).hexdigest()[:12]}"
        e["event_hash"] = event_hash(e)
        issues = validate_event(e)
        if issues:
            raise AuditUnavailable(f"event invalid: {issues}")
        return e

    def emit(self, event: dict) -> str:
        if not self.available:
            raise AuditUnavailable("audit sink unavailable")
        e = self._seal(event)
        if self.writer is not None:
            try:
                self.writer(e)
            except Exception as ex:                                       # noqa: BLE001 — any backend failure is an audit failure
                raise AuditUnavailable(f"audit write failed: {type(ex).__name__}: {ex}") from ex
        self.events.append(e)
        return e["event_hash"]

    def events_for(self, tenant_id: str) -> list[dict]:
        return [e for e in self.events if e["tenant_id"] == tenant_id]

    def verify(self) -> list[str]:
        return verify_chain(self.events)


class JsonlAuditSink(InMemoryAuditSink):
    """Durable append-only JSONL log with the same chain. Unwritable path -> AuditUnavailable."""

    def __init__(self, path: str | Path, **kw):
        super().__init__(writer=self._write, **kw)
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                self.events = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        except (OSError, ValueError) as e:
            self.available = False; self.load_error = f"{type(e).__name__}: {e}"

    def _write(self, e: dict) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(e, sort_keys=True, default=str) + "\n")
            fh.flush()

    @classmethod
    def load(cls, path: str | Path) -> "JsonlAuditSink":
        return cls(path)


__all__ = ["AUDIT_SCHEMA_VERSION", "BRIDGE_FIELDS", "GENESIS", "REQUIRED_FIELDS", "AuditUnavailable", "InMemoryAuditSink", "JsonlAuditSink",
           "event_hash", "reconstruct", "validate_event", "verify_chain"]
