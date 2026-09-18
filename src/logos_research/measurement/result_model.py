"""ResultModelResolution — which model produced Claude Code's `result`? (COGNITIVE-PROVENANCE-ABLATION-R1-INSTRUMENT-REPAIR-R1)

Contract `cc-result-model/1` (docs/research/CLAUDE-CODE-OUTPUT-CONTRACT-R1.md). Evidence hierarchy:

    Tier 1  EXPLICIT_ASSISTANT_MODEL          stream-json: `message.model` of the main-conversation assistant message(s)
    Tier 2  EXPLICIT_RESULT_MODEL             a DOCUMENTED top-level producer field (none exists in 2.1.275 -> never fires)
    Tier 3  REQUEST_PIN_PLUS_USAGE_CONTAINMENT requested == pin AND modelUsage contains the pin AND nothing names another producer

Never valid: first/last key, token counts, insertion or lexical order of `modelUsage`.

    AuxiliaryModelUsage != PrimaryResponseModel
    ModelUsagePresence  != ResultProducerIdentity
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

CONTRACT_VERSION = "cc-result-model/1"
STATUSES: tuple[str, ...] = ("RESOLVED", "AMBIGUOUS", "PIN_MISSING", "OUTPUT_INVALID", "CONTRACT_UNSUPPORTED")
EVIDENCE_CLASSES: tuple[str, ...] = ("EXPLICIT_ASSISTANT_MODEL", "EXPLICIT_RESULT_MODEL", "REQUEST_PIN_PLUS_USAGE_CONTAINMENT", "AMBIGUOUS_USAGE_ONLY", "PIN_ABSENT", "UNSUPPORTED_CONTRACT", "INVALID_OUTPUT")
OUTPUT_FORMATS: tuple[str, ...] = ("json", "stream-json")
ALIASES: frozenset[str] = frozenset({"opus", "sonnet", "haiku", "fable", "default"})
#: documented top-level result producer fields per contract version — none in cc-result-model/1
EXPLICIT_RESULT_FIELDS: dict[str, tuple[str, ...]] = {CONTRACT_VERSION: ()}
_DATED = re.compile(r"^(?P<base>.+?)-(?P<date>\d{8})$")


@dataclass(frozen=True)
class ResultModelResolution:
    status: str
    requested_model: str
    resolved_model: str | None
    evidence_class: str
    evidence_fields: tuple[str, ...]
    auxiliary_models: tuple[str, ...]
    reason_code: str
    contract_version: str = CONTRACT_VERSION
    auxiliary_usage: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in STATUSES or self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError(f"closed vocabulary: {self.status} / {self.evidence_class}")

    @property
    def drift(self) -> bool:
        """True model drift (Section 9): explicit producer != pin, or pin absent from the required evidence."""
        return self.status == "PIN_MISSING" or (self.status == "RESOLVED" and not same_model(self.resolved_model or "", self.requested_model))

    def to_dict(self) -> dict:
        return asdict(self)


def is_pin(model: str) -> bool:
    """A founder pin is a full model name, never an alias."""
    return bool(model) and model not in ALIASES and "-" in model


def same_model(candidate: str, pin: str) -> bool:
    """Exact pin, or the pin with a dated snapshot suffix (`claude-opus-5-20260301`). Nothing else."""
    if not candidate or not pin:
        return False
    if candidate == pin:
        return True
    m = _DATED.match(candidate)
    return bool(m and m.group("base") == pin)


def _usage_entries(model_usage) -> list[tuple[str, str | None, dict]]:
    """(key, canonicalModel, entry) for a well-formed modelUsage map; raises ValueError on malformed input."""
    if not isinstance(model_usage, dict):
        raise ValueError("modelUsage is not a map")
    out = []
    for k, v in model_usage.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            raise ValueError("modelUsage entry malformed")
        canon = v.get("canonicalModel")
        if canon is not None and not isinstance(canon, str):
            raise ValueError("canonicalModel malformed")
        out.append((k, canon, v))
    return out


def _pin_entries(entries, pin: str) -> list[str]:
    return sorted(k for k, canon, _ in entries if same_model(k, pin) or (canon is not None and same_model(canon, pin)))


def _aux(entries, pin_keys: list[str]) -> tuple[tuple[str, ...], dict]:
    aux = sorted(k for k, _, _ in entries if k not in pin_keys)
    usage = {k: {f: v.get(f) for f in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "canonicalModel", "provider")} for k, _, v in entries if k in aux}
    return tuple(aux), usage


def explicit_assistant_models(events: list) -> list[str]:
    """Tier-1 evidence: `message.model` of main-conversation assistant messages (parent_tool_use_id == null), in stream order."""
    out: list[str] = []
    for e in events:
        if isinstance(e, dict) and e.get("type") == "assistant" and e.get("parent_tool_use_id") is None:
            msg = e.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("model"), str) and msg["model"]:
                out.append(msg["model"])
    return out


def resolve_result_model(requested_model: str, parsed_output, output_format: str, contract_version: str = CONTRACT_VERSION) -> ResultModelResolution:
    """`parsed_output`: the result dict (json) or the list of stream events (stream-json). Deterministic; never consults key order."""
    R = ResultModelResolution
    if contract_version not in EXPLICIT_RESULT_FIELDS or output_format not in OUTPUT_FORMATS:
        return R("CONTRACT_UNSUPPORTED", requested_model, None, "UNSUPPORTED_CONTRACT", (), (), "contract or output format not supported", contract_version)
    if not is_pin(requested_model):
        return R("PIN_MISSING", requested_model, None, "PIN_ABSENT", (), (), "requested model is not a full pin", contract_version)
    if output_format == "stream-json":
        if not isinstance(parsed_output, list) or not parsed_output:
            return R("OUTPUT_INVALID", requested_model, None, "INVALID_OUTPUT", (), (), "stream has no events", contract_version)
        result = next((e for e in reversed(parsed_output) if isinstance(e, dict) and e.get("type") == "result"), None)
        explicit = explicit_assistant_models(parsed_output)
    else:
        if not isinstance(parsed_output, dict):
            return R("OUTPUT_INVALID", requested_model, None, "INVALID_OUTPUT", (), (), "result is not an object", contract_version)
        result, explicit = parsed_output, []
    if result is None:
        return R("OUTPUT_INVALID", requested_model, None, "INVALID_OUTPUT", (), (), "no result message", contract_version)
    # usage evidence (may be absent)
    entries = None
    if "modelUsage" in result:
        try:
            entries = _usage_entries(result["modelUsage"])
        except ValueError as e:
            return R("OUTPUT_INVALID", requested_model, None, "INVALID_OUTPUT", ("modelUsage",), (), f"malformed modelUsage: {e}", contract_version)
    pin_keys = _pin_entries(entries, requested_model) if entries else []
    aux, aux_usage = _aux(entries, pin_keys) if entries else ((), {})
    # Tier 1 — explicit producer on the assistant message(s)
    if explicit:
        producer = explicit[-1]
        if any(not same_model(m, producer) for m in explicit):
            return R("AMBIGUOUS", requested_model, None, "AMBIGUOUS_USAGE_ONLY", ("assistant.message.model",), aux, "main-conversation assistant messages name different models", contract_version, aux_usage)
        return R("RESOLVED", requested_model, producer, "EXPLICIT_ASSISTANT_MODEL", ("assistant.message.model",), aux, "explicit producer on assistant message", contract_version, aux_usage)
    # Tier 2 — a documented explicit top-level field (none in this contract)
    for f in EXPLICIT_RESULT_FIELDS[contract_version]:
        if isinstance(result.get(f), str) and result[f]:
            return R("RESOLVED", requested_model, result[f], "EXPLICIT_RESULT_MODEL", (f,), aux, "documented explicit result field", contract_version, aux_usage)
    # Tier 3 — pin containment in modelUsage (weaker; recorded as such)
    if entries is None:
        return R("AMBIGUOUS", requested_model, None, "AMBIGUOUS_USAGE_ONLY", (), (), "no explicit producer and no modelUsage", contract_version)
    if not entries:
        return R("AMBIGUOUS", requested_model, None, "AMBIGUOUS_USAGE_ONLY", ("modelUsage",), (), "empty modelUsage", contract_version)
    if not pin_keys:
        return R("PIN_MISSING", requested_model, None, "PIN_ABSENT", ("modelUsage",), aux, "pinned model absent from modelUsage", contract_version, aux_usage)
    if len(pin_keys) > 1 and len({_DATED.match(k).group("base") if _DATED.match(k) else k for k in pin_keys}) > 1:
        return R("AMBIGUOUS", requested_model, None, "AMBIGUOUS_USAGE_ONLY", ("modelUsage",), aux, "several distinct pin-matching entries", contract_version, aux_usage)
    return R("RESOLVED", requested_model, requested_model, "REQUEST_PIN_PLUS_USAGE_CONTAINMENT", ("requested_model", "modelUsage[" + pin_keys[0] + "]"), aux, "pin present in usage; no evidence of another producer (weaker evidence)", contract_version, aux_usage)
