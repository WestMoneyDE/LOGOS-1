"""JSON-first agent output contract — `logos-agent-output/1`.

The rule is one sentence: **the model emits JSON; the prose is a view rendered
from that JSON, never a second source of truth.**

Why this file exists and an instruction does not
------------------------------------------------
A prompt that tells a model to respect the invariants is a request, not an
enforcement mechanism. Nothing in the model's weights is bound by it. Writing
"always follow Γ" into `AGENTS.md` is ergonomics — it makes the well-behaved path
the easy one — and it must never be counted as evidence that the boundary holds.

Enforcement is here and downstream of the model:

```text
model output (untrusted text)
  -> extract()   one envelope, or a fail-closed code. Prose is discarded.
  -> validate()  closed schema: an unknown field is a refusal, not a warning
  -> to_commands()  typed EffectProposals
  -> logos_gamma.validate()   the actual decision
  -> render()    the human-readable text, derived FROM the JSON
```

The model never authors the prose that a human reads as the record. It authors
data; `render` authors the prose. A model that writes a persuasive paragraph and a
contradicting JSON body cannot win, because the paragraph is thrown away before
anything is decided — `test_output_contract.py::test_prose_cannot_change_anything`
fixes that with a differential test rather than a promise.

Why the closed schema matters
-----------------------------
There is no field in this envelope in which authority can be granted. A model that
invents `{"authority": "approved by operator"}` does not get a weaker check — it
gets `UNKNOWN_FIELD` and the whole envelope is refused. A model that uses the one
field that *does* exist for the purpose, `self_claimed_authority`, is admitted as
data and then refused by Γ (`G1-SELF-CLAIM`). Both paths are tested.

This module holds no invariant of its own. It parses, validates and renders.
Every verdict comes from `logos_gamma`.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in (None, ""):  # `python src/core/output_contract.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance import CANONICAL_EFFECTS, UNREGISTERED, IsolatedCommand, digest  # noqa: E402
from logos_gamma import EffectProposal, ProvenanceClaim  # noqa: E402

CONTRACT = "logos-agent-output/1"

#: Closed schema. Anything outside these names is a refusal.
ENVELOPE_FIELDS = frozenset({"contract", "intent", "reasoning", "proposals", "uncertainties", "requests"})
ENVELOPE_REQUIRED = frozenset({"contract", "intent", "proposals"})

PROPOSAL_FIELDS = frozenset({
    "action", "target", "evidence", "justification",
    "declared_externality", "declared_reversibility",
    "self_claimed_authority", "resists_shutdown", "self_preservation",
})
PROPOSAL_REQUIRED = frozenset({"action", "target"})

EVIDENCE_FIELDS = frozenset({"ref", "origin"})
EVIDENCE_REQUIRED = frozenset({"ref", "origin"})

#: Γ owns these classifications; the model may only report what it *believes*.
DECLARED_EXTERNALITY = frozenset({"internal", "external"})
DECLARED_REVERSIBILITY = frozenset({"reversible", "partially-reversible", "irreversible"})

#: A request the model may raise. It asks; it never answers.
REQUEST_KINDS = frozenset({"authority", "information", "clarification"})

_FENCE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


class ContractError(ValueError):
    """Raised when an envelope is consumed that did not validate."""


@dataclass(frozen=True)
class Extraction:
    """Result of reading one model output. Fail-closed by construction."""

    envelope: Mapping[str, Any] | None
    code: str
    errors: tuple[str, ...] = ()
    discarded_prose: str = ""

    @property
    def ok(self) -> bool:
        return self.code == "OK"

    def require(self) -> Mapping[str, Any]:
        if not self.ok or self.envelope is None:
            raise ContractError(f"{self.code}: {'; '.join(self.errors) or 'no envelope'}")
        return self.envelope


# --------------------------------------------------------------------------
# Extraction — one envelope or nothing
# --------------------------------------------------------------------------

def extract(raw: str) -> Extraction:
    """Pull the single JSON envelope out of a model's output.

    Ambiguity is never resolved by preference. Two envelopes is `MULTIPLE_ENVELOPES`,
    not "take the last one": a model that emits two bodies has not said one thing,
    and picking one for it would be the harness inventing an intention.
    """
    blocks = [m.group(1) for m in _FENCE.finditer(raw)]
    if not blocks:
        stripped = raw.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            return Extraction(None, "NO_ENVELOPE", ("no JSON object and no fenced json block",), raw)
        blocks = [stripped]
    if len(blocks) > 1:
        return Extraction(None, "MULTIPLE_ENVELOPES", (f"{len(blocks)} json blocks",), raw)

    prose = raw.replace(blocks[0], "").strip()
    try:
        parsed = json.loads(blocks[0])
    except json.JSONDecodeError as exc:
        return Extraction(None, "PARSE_FAILURE", (str(exc),), prose)
    if not isinstance(parsed, dict):
        return Extraction(None, "WRONG_TYPE", (f"envelope is {type(parsed).__name__}, not an object",), prose)

    errors = validate(parsed)
    if errors:
        return Extraction(None, errors[0].split(":", 1)[0], tuple(errors), prose)
    return Extraction(parsed, "OK", (), prose)


def validate(envelope: Mapping[str, Any]) -> tuple[str, ...]:
    """Closed-schema check. Returns every problem, so a caller sees all of them."""
    errors: list[str] = []
    unknown = sorted(set(envelope) - ENVELOPE_FIELDS)
    if unknown:
        errors.append(f"UNKNOWN_FIELD: {unknown}; the envelope is closed and has no field for authority")
    missing = sorted(ENVELOPE_REQUIRED - set(envelope))
    if missing:
        errors.append(f"MISSING_FIELD: {missing}")
    if envelope.get("contract") != CONTRACT:
        errors.append(f"WRONG_CONTRACT: {envelope.get('contract')!r} != {CONTRACT!r}")
    if "intent" in envelope and not isinstance(envelope["intent"], str):
        errors.append("WRONG_TYPE: intent must be a string")
    for key in ("reasoning", "uncertainties"):
        if key in envelope and not _is_str_list(envelope[key]):
            errors.append(f"WRONG_TYPE: {key} must be a list of strings")
    if "proposals" in envelope:
        if not isinstance(envelope["proposals"], list):
            errors.append("WRONG_TYPE: proposals must be a list")
        else:
            for index, item in enumerate(envelope["proposals"]):
                errors.extend(f"{e} (proposals[{index}])" for e in _validate_proposal(item))
    if "requests" in envelope:
        if not isinstance(envelope["requests"], list):
            errors.append("WRONG_TYPE: requests must be a list")
        else:
            for index, item in enumerate(envelope["requests"]):
                errors.extend(f"{e} (requests[{index}])" for e in _validate_request(item))
    return tuple(errors)


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _validate_proposal(item: Any) -> list[str]:
    if not isinstance(item, dict):
        return [f"WRONG_TYPE: proposal is {type(item).__name__}, not an object"]
    errors: list[str] = []
    unknown = sorted(set(item) - PROPOSAL_FIELDS)
    if unknown:
        errors.append(f"UNKNOWN_FIELD: {unknown}")
    missing = sorted(PROPOSAL_REQUIRED - set(item))
    if missing:
        errors.append(f"MISSING_FIELD: {missing}")
    for key in ("action", "target", "justification"):
        if key in item and not isinstance(item[key], str):
            errors.append(f"WRONG_TYPE: {key} must be a string")
    for key in ("self_claimed_authority", "resists_shutdown", "self_preservation"):
        if key in item and not isinstance(item[key], bool):
            errors.append(f"WRONG_TYPE: {key} must be a boolean")
    if item.get("declared_externality") is not None and item.get("declared_externality") not in DECLARED_EXTERNALITY:
        errors.append(f"WRONG_TYPE: declared_externality must be one of {sorted(DECLARED_EXTERNALITY)}")
    if item.get("declared_reversibility") is not None and item.get("declared_reversibility") not in DECLARED_REVERSIBILITY:
        errors.append(f"WRONG_TYPE: declared_reversibility must be one of {sorted(DECLARED_REVERSIBILITY)}")
    if "evidence" in item:
        if not isinstance(item["evidence"], list):
            errors.append("WRONG_TYPE: evidence must be a list")
        else:
            for ev in item["evidence"]:
                errors.extend(_validate_evidence(ev))
    return errors


def _validate_evidence(item: Any) -> list[str]:
    if not isinstance(item, dict):
        return [f"WRONG_TYPE: evidence entry is {type(item).__name__}, not an object"]
    errors: list[str] = []
    unknown = sorted(set(item) - EVIDENCE_FIELDS)
    if unknown:
        errors.append(f"UNKNOWN_FIELD: {unknown} in evidence")
    missing = sorted(EVIDENCE_REQUIRED - set(item))
    if missing:
        errors.append(f"MISSING_FIELD: {missing} in evidence")
    if "ref" in item and not isinstance(item["ref"], str):
        errors.append("WRONG_TYPE: evidence.ref must be a string")
    if "origin" in item and not isinstance(item["origin"], str):
        errors.append("WRONG_TYPE: evidence.origin must be a string")
    return errors


def _validate_request(item: Any) -> list[str]:
    if not isinstance(item, dict):
        return [f"WRONG_TYPE: request is {type(item).__name__}, not an object"]
    errors: list[str] = []
    unknown = sorted(set(item) - {"kind", "detail"})
    if unknown:
        errors.append(f"UNKNOWN_FIELD: {unknown} in request")
    if item.get("kind") not in REQUEST_KINDS:
        errors.append(f"WRONG_TYPE: request.kind must be one of {sorted(REQUEST_KINDS)}")
    if "detail" in item and not isinstance(item["detail"], str):
        errors.append("WRONG_TYPE: request.detail must be a string")
    return errors


# --------------------------------------------------------------------------
# JSON -> typed proposals. The only path from model output to a decision.
# --------------------------------------------------------------------------

def to_commands(envelope: Mapping[str, Any]) -> tuple[IsolatedCommand, ...]:
    """Turn a validated envelope into isolated commands Γ can judge.

    The model's `evidence[].origin` is recorded as *claimed* provenance. It never
    becomes `"human"`: an origin the model names for itself is a self-report, and
    `AUTHORITY_BEARING_ORIGINS` is not reachable from here. Grants enter the system
    through the authority store, never through a model's output.
    """
    if validate(envelope):
        raise ContractError("refusing to build commands from an invalid envelope")
    commands = []
    for item in envelope["proposals"]:
        action, target = item["action"], item["target"]
        effect_kind, externality, reversibility = CANONICAL_EFFECTS.get(action, UNREGISTERED)
        commands.append(
            IsolatedCommand(
                raw=json.dumps(item, sort_keys=True),
                proposal=EffectProposal(
                    action=action,
                    target=target,
                    effect_kind=effect_kind,
                    externality=externality,
                    reversibility=reversibility,
                    proposal_digest=digest(action, target),
                    parameters={k: v for k, v in sorted(item.items()) if k not in {"action", "target"}},
                    provenance=tuple(
                        ProvenanceClaim(
                            ref=str(ev["ref"]),
                            origin=_claimed_origin(str(ev["origin"])),
                            content_digest=digest("content", str(ev["ref"])),
                        )
                        for ev in item.get("evidence", ())
                    ),
                    declared_externality=item.get("declared_externality"),
                    declared_reversibility=item.get("declared_reversibility"),
                    self_claimed_authority=bool(item.get("self_claimed_authority", False)),
                    resists_shutdown=bool(item.get("resists_shutdown", False)),
                    self_preservation_motivated=bool(item.get("self_preservation", False)),
                ),
                agent_justification=str(item.get("justification", envelope["intent"])),
            )
        )
    return tuple(commands)


def _claimed_origin(origin: str) -> str:
    """Map a model-claimed origin into Γ's vocabulary, never upward.

    `"human"` is the one origin that carries authority, so a model claiming it is
    recorded as `self-report` — the claim is preserved, its power is not.
    """
    return "self-report" if origin == "human" else origin


# --------------------------------------------------------------------------
# Rendering — the prose a human reads, derived from the JSON
# --------------------------------------------------------------------------

def render(envelope: Mapping[str, Any]) -> str:
    """Deterministic human view of a validated envelope.

    Pure function: same envelope in, identical string out. No clock, no ordering by
    anything but the envelope's own order, nothing from the discarded prose.
    """
    if validate(envelope):
        raise ContractError("refusing to render an invalid envelope")
    lines = [f"Intent: {envelope['intent']}"]

    proposals = envelope["proposals"]
    lines.append("")
    lines.append(f"Proposals ({len(proposals)}):" if proposals else "Proposals: none")
    for index, item in enumerate(proposals, start=1):
        lines.append(f"  {index}. {item['action']} {item['target']}")
        if item.get("justification"):
            lines.append(f"     because: {item['justification']}")
        for ev in item.get("evidence", ()):
            lines.append(f"     evidence: {ev['ref']} (claimed origin: {ev['origin']})")
        declared = [
            f"{key.replace('declared_', '')}={item[key]}"
            for key in ("declared_externality", "declared_reversibility")
            if item.get(key) is not None
        ]
        if declared:
            lines.append(f"     agent's own assessment (untrusted): {', '.join(declared)}")
        flags = [key for key in ("self_claimed_authority", "resists_shutdown", "self_preservation") if item.get(key)]
        if flags:
            lines.append(f"     flags: {', '.join(flags)}")

    for title, key in (("Uncertainties", "uncertainties"), ("Reasoning", "reasoning")):
        values = envelope.get(key) or []
        if values:
            lines.append("")
            lines.append(f"{title}:")
            lines.extend(f"  - {value}" for value in values)

    requests = envelope.get("requests") or []
    if requests:
        lines.append("")
        lines.append("Requests:")
        lines.extend(f"  - {item['kind']}: {item.get('detail', '')}".rstrip() for item in requests)

    lines.append("")
    lines.append("This text is rendered from the agent's JSON. It is a view, not a claim,")
    lines.append("and no statement in it authorizes anything.")
    return "\n".join(lines)


def values_in(envelope: Mapping[str, Any]) -> tuple[str, ...]:
    """Every string the envelope contains, for the derivation check in the tests."""
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            found.append(node)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(envelope)
    return tuple(found)


@dataclass(frozen=True)
class ContractReport:
    """What a governed pipeline records for one model output."""

    code: str
    errors: tuple[str, ...] = ()
    view: str = ""
    commands: tuple[IsolatedCommand, ...] = field(default=())

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "errors": list(self.errors),
            "commands": [c.summary for c in self.commands],
            "view": self.view,
        }


def process(raw: str) -> ContractReport:
    """Full path from untrusted model text to typed commands and a derived view."""
    extraction = extract(raw)
    if not extraction.ok:
        return ContractReport(code=extraction.code, errors=extraction.errors)
    envelope = extraction.require()
    return ContractReport(
        code="OK",
        view=render(envelope),
        commands=to_commands(envelope),
    )


EXAMPLE: Mapping[str, Any] = {
    "contract": CONTRACT,
    "intent": "Remove the stale payroll export produced by run 42.",
    "reasoning": ["The export log lists payroll.csv as superseded."],
    "proposals": [
        {
            "action": "fs.delete",
            "target": "payroll.csv",
            "justification": "Superseded by the run-43 export.",
            "evidence": [{"ref": "run/42/export.log", "origin": "tool"}],
            "declared_reversibility": "irreversible",
        }
    ],
    "uncertainties": ["Whether finance still needs the old export."],
    "requests": [{"kind": "authority", "detail": "Approval to delete payroll.csv in this state."}],
}


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError, OSError):
        pass
    raw = sys.stdin.read() if argv and "-" in argv else "```json\n" + json.dumps(EXAMPLE, indent=2) + "\n```"
    report = process(raw)
    print(f"contract check: {report.code}")
    for error in report.errors:
        print(f"  {error}")
    if report.view:
        print()
        print(report.view)
    return 0 if report.code == "OK" else 1


if __name__ == "__main__":  # pragma: no cover - exercised via main() in tests
    raise SystemExit(main())
