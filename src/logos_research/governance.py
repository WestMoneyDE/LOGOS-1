"""Inference governance (GOVERNANCE_ONLY) — INFERENCE-GOVERNANCE-LIFT-R1.

Reads docs/research/INFERENCE-GOVERNANCE.json (the founder's decisions,
verbatim) and enforces the two-key activation rules deterministically:

    provider  = governance approval (G2)      + passed zero-inference dry run
    privacy   = approved data class (G3)      + run-specific dataset classification
    cost      = governance ceiling (G4)       + run-specific prereg cost cap (<= ceiling)
    metric    = construct-valid registry entry + experiment-specific ground-truth mapping

`resolve_provider()` never returns anything but `ForbiddenProvider` unless every
key of every rule holds — and even then it returns a *specification*, not a
live client: this module contains no provider adapter and makes no call.
`model_calls = provider_calls = 0` is the invariant of this module.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from logos_research.measurement import allowed_as_evidence, load_registry, validate_stochastic_preregistration
from logos_research.measurement.gateway import CALLS, ForbiddenProvider

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs/research/INFERENCE-GOVERNANCE.json"
INFERENCE_STATES: tuple[str, ...] = ("ACTIVE", "LIFTED_WITH_CONDITIONS", "DEFERRED")
DATA_CLASSES: tuple[str, ...] = ("PUBLIC", "SYNTHETIC", "INTERNAL_NON_SENSITIVE", "CONFIDENTIAL", "PERSONAL_DATA", "SENSITIVE_PERSONAL_DATA", "SECRETS_CREDENTIALS", "PRODUCTION_CUSTOMER_DATA")
DRIFT_RULES: tuple[str, ...] = ("MODEL_VERSION_DRIFT", "PROMPT_DRIFT", "PROVIDER_DRIFT", "REGION_DRIFT", "DATASET_DRIFT", "TOOL_SCHEMA_DRIFT")
TIER_A: tuple[str, ...] = ("BELIEF-STATE-GEOMETRY-R1", "COGNITIVE-PROVENANCE-ABLATION-R1", "WORLD-MODEL-TRUST-BOUNDARY-R1", "TRAJECTORY-UNCERTAINTY-ACCUMULATION-R1")
ORDER_HEADER: tuple[str, ...] = ("INFERENCE_GOVERNANCE", "APPROVED_PROVIDER", "APPROVED_MODEL", "APPROVED_REGION", "APPROVED_DATA_CLASSES", "MAX_BUDGET", "MAX_REQUESTS", "MAX_TOKENS",
                                 "PREREG_SCHEMA", "DRY_RUN_REQUIRED", "PRODUCTION_ACTIONS")
#: amended header (INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1): Claude Code / Max subscription path
ORDER_HEADER_AMENDED: tuple[str, ...] = ("INFERENCE_GOVERNANCE", "APPROVED_PROVIDER", "APPROVED_ACCESS_PATH", "APPROVED_AUTH", "APPROVED_MODEL", "APPROVED_DATA_CLASSES", "API_PAYG_BUDGET",
                                         "MAX_CLAUDE_CODE_INVOCATIONS", "MAX_WALL_CLOCK", "MAX_REPEATS", "MAX_CONCURRENT_SESSIONS", "PREREG_SCHEMA", "DRY_RUN_REQUIRED", "PRODUCTION_ACTIONS",
                                         "FALLBACK_PROVIDER", "API_CREDIT_FALLBACK")
MODEL_PIN_PLACEHOLDER = "TO_BE_PINNED_FROM_MAX_ACCOUNT_BEFORE_RUN"
BILLING_MODES: tuple[str, ...] = ("API_BUDGET", "CLAUDE_MAX_SUBSCRIPTION_ONLY")
#: environment / selection facts that contaminate the research subprocess (values are never read or stored, only presence)
CONTAMINATION_ENV: tuple[str, ...] = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")
FORBIDDEN_CLI_FLAGS: tuple[str, ...] = ("--dangerously-skip-permissions",)
DRY_RUN_CHECKS: tuple[str, ...] = ("metadata_complete", "pins_resolve", "privacy_checks_pass", "cost_accounting_initialized", "construct_metrics_resolve", "artifact_paths_exist",
                                   "provenance_graph_initializes", "trajectory_capture_initializes", "invalid_measurement_rules_load", "forbidden_provider_guard_active")


class GovernanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class GovernanceRecord:
    inference_state: str
    g1: str
    g2: str
    g3: str
    g4: str
    provider: str | None
    model_id: str | None
    region: str | None
    fallback: str | None
    allowed_data_classes: tuple[str, ...]
    max_total_spend: float | None
    max_total_tokens: int | None
    max_requests: int | None
    max_wall_clock_hours: float | None
    max_repeats: int | None
    max_per_run_spend: float | None
    selected_experiment: str | None
    decision_owner: str
    decision_date: str
    raw: dict = field(default_factory=dict, repr=False)
    access_path: str | None = None            # amended: "Claude Code"
    auth_mode: str | None = None              # amended: "Claude Max subscription"
    billing_mode: str = "API_BUDGET"          # amended: CLAUDE_MAX_SUBSCRIPTION_ONLY
    api_credit_fallback: str | None = None    # amended: FORBIDDEN
    max_claude_code_invocations: int | None = None
    max_concurrent_sessions: int | None = None

    @property
    def subscription_only(self) -> bool:
        return self.billing_mode == "CLAUDE_MAX_SUBSCRIPTION_ONLY"

    @property
    def model_pinned(self) -> bool:
        return bool(self.model_id) and self.model_id != MODEL_PIN_PLACEHOLDER

    @property
    def lifted(self) -> bool:
        return self.g1 == "LIFT" and self.inference_state == "LIFTED_WITH_CONDITIONS" and self.g2 == self.g3 == self.g4 == "APPROVED"

    def issues(self) -> list[str]:
        out = []
        if self.inference_state not in INFERENCE_STATES:
            out.append("inference_state")
        if self.g1 not in ("LIFT", "RETAIN", "DEFER"):
            out.append("G1")
        if self.decision_owner != "founder" or not self.decision_date:
            out.append("decision owner/date")
        if self.g1 == "LIFT":
            if self.inference_state != "LIFTED_WITH_CONDITIONS":
                out.append("LIFT requires LIFTED_WITH_CONDITIONS")
            for g in ("g2", "g3", "g4"):
                if getattr(self, g) not in ("APPROVED", "REJECTED", "DEFERRED"):
                    out.append(g)
            if self.g2 == "APPROVED" and not (self.provider and self.model_id and self.region and self.fallback):
                out.append("G2 pins incomplete")
            if self.g2 == "APPROVED" and self.fallback != "NONE":
                out.append("fallback must be NONE unless preregistered")
            if self.billing_mode not in BILLING_MODES:
                out.append("billing_mode")
            if self.subscription_only:
                if self.provider != "Anthropic" or self.access_path != "Claude Code" or self.auth_mode != "Claude Max subscription":
                    out.append("subscription-only billing requires the Anthropic / Claude Code / Max subscription path")
                if self.api_credit_fallback != "FORBIDDEN" or (self.max_total_spend or 0) != 0 or (self.max_per_run_spend or 0) != 0:
                    out.append("subscription-only billing requires api_credit_fallback FORBIDDEN and an API budget of 0")
                if not self.max_claude_code_invocations or not self.max_concurrent_sessions or self.max_concurrent_sessions != 1:
                    out.append("Max caps: invocations and exactly one concurrent session required")
            if self.g3 == "APPROVED" and (not self.allowed_data_classes or set(self.allowed_data_classes) - set(DATA_CLASSES)):
                out.append("G3 classes")
            if self.g4 == "APPROVED" and not self.subscription_only and any(v is None or v <= 0 for v in (self.max_total_spend, self.max_total_tokens, self.max_requests, self.max_wall_clock_hours, self.max_repeats, self.max_per_run_spend)):
                out.append("G4 caps must all be positive and present")
            if self.g4 == "APPROVED" and self.subscription_only and any(v is None or v <= 0 for v in (self.max_wall_clock_hours, self.max_repeats, self.max_claude_code_invocations)):
                out.append("G4 Max operational caps must be positive and present")
            if self.selected_experiment is not None and self.selected_experiment not in TIER_A:
                out.append("selected experiment must be Tier A or NONE")
        elif self.inference_state == "LIFTED_WITH_CONDITIONS":
            out.append("state lifted without a LIFT decision")
        return out


def load_governance(path: Path | None = None) -> GovernanceRecord:
    d = json.loads((path or REGISTRY_PATH).read_text(encoding="utf-8"))
    g2, g3, g4 = d.get("G2", {}), d.get("G3", {}), d.get("G4", {})
    sel = d.get("selected_experiment") or {}
    r = GovernanceRecord(d["inference_state"], d["G1"]["decision"], g2.get("decision", "DEFERRED"), g3.get("decision", "DEFERRED"), g4.get("decision", "DEFERRED"),
                         g2.get("provider"), g2.get("model_id"), g2.get("region"), g2.get("fallback"), tuple(g3.get("allowed_data_classes", ())),
                         g4.get("max_total_spend"), g4.get("max_total_tokens"), g4.get("max_requests"), g4.get("max_wall_clock_hours"), g4.get("max_repeats"), g4.get("max_per_run_spend"),
                         sel.get("id") if sel.get("decision") not in (None, "NONE", "DEFER") else None, d.get("decision_owner", ""), d.get("decision_date", ""), d,
                         g2.get("access_path"), g2.get("auth_mode"), g4.get("billing_mode", "API_BUDGET"), g2.get("api_credit_fallback"),
                         g4.get("max_claude_code_invocations"), g4.get("max_concurrent_sessions"))
    if (d.get("superseded") or {}).get("G2_openai", {}).get("status") not in (None, "SUPERSEDED_BY_FOUNDER_AMENDMENT"):
        raise GovernanceError("superseded record must be marked SUPERSEDED_BY_FOUNDER_AMENDMENT")
    issues = r.issues()
    if issues:
        raise GovernanceError(f"governance record invalid: {issues}")
    return r


# -- two-key activation rules ---------------------------------------------------

def provider_activation(gov: GovernanceRecord, *, dry_run_passed: bool) -> bool:
    return gov.lifted and gov.g2 == "APPROVED" and dry_run_passed is True


def privacy_activation(gov: GovernanceRecord, *, run_dataset_class: str) -> bool:
    if run_dataset_class not in DATA_CLASSES:
        raise GovernanceError(f"unknown data class {run_dataset_class!r}")
    return gov.lifted and gov.g3 == "APPROVED" and run_dataset_class in gov.allowed_data_classes


def cost_activation(gov: GovernanceRecord, *, run_cost_cap: float | None) -> bool:
    if gov.subscription_only:                       # amended: no API budget exists; the run cap must be exactly 0 USD of incremental API spend
        return gov.lifted and gov.g4 == "APPROVED" and run_cost_cap == 0
    if run_cost_cap is None or run_cost_cap <= 0:
        return False
    return gov.lifted and gov.g4 == "APPROVED" and run_cost_cap <= gov.max_per_run_spend and run_cost_cap <= gov.max_total_spend


@dataclass(frozen=True)
class ContaminationReport:
    """Presence-only facts about the research subprocess environment. Never values."""
    env_present: tuple[str, ...]
    auth_class: str                 # MAX_SUBSCRIPTION | CONSOLE_PAYG | THIRD_PARTY_CLOUD | UNKNOWN
    clean: bool


def contamination_check(env: dict, *, auth_class: str) -> ContaminationReport:
    present = tuple(k for k in CONTAMINATION_ENV if env.get(k))
    clean = not present and auth_class == "MAX_SUBSCRIPTION"
    return ContaminationReport(present, auth_class, clean)


def billing_activation(gov: GovernanceRecord, *, report: ContaminationReport) -> bool:
    """Amended two-key billing rule: Max subscription confirmed + PAYG / API-key absence confirmed."""
    return gov.lifted and gov.subscription_only and report.clean and report.auth_class == "MAX_SUBSCRIPTION"


def metric_activation(metric_id: str, *, ground_truth_mapping: str | None, registry=None) -> bool:
    reg = registry or load_registry()
    m = reg.get(metric_id)
    return m is not None and allowed_as_evidence(m) and bool(ground_truth_mapping) and "self-report" not in ground_truth_mapping.lower() and "llm judge" not in ground_truth_mapping.lower() \
        and "final response safety" not in ground_truth_mapping.lower()


@dataclass(frozen=True)
class ProviderSpec:
    """A specification of the approved provider — NOT a client. No adapter exists in this repository."""
    provider: str
    model_id: str
    region: str
    fallback: str


def resolve_provider(gov: GovernanceRecord, *, dry_run_passed: bool, run_dataset_class: str, run_cost_cap: float | None, report: ContaminationReport | None = None,
                     preflight_passed: bool = False, model_pin: str | None = None):
    """Returns ForbiddenProvider unless every two-key rule holds; then a ProviderSpec (still no call possible here).
    Amended path additionally needs: a clean contamination report, a passed Claude-Max-auth preflight and an explicit model pin."""
    if not (provider_activation(gov, dry_run_passed=dry_run_passed) and privacy_activation(gov, run_dataset_class=run_dataset_class) and cost_activation(gov, run_cost_cap=run_cost_cap)):
        return ForbiddenProvider()
    if gov.subscription_only:
        if report is None or not billing_activation(gov, report=report) or not preflight_passed or not model_pin or model_pin == MODEL_PIN_PLACEHOLDER:
            return ForbiddenProvider()
        return ProviderSpec(gov.provider, model_pin, "NOT_ASSUMED", gov.fallback)
    return ProviderSpec(gov.provider, gov.model_id, gov.region, gov.fallback)


# -- experiment-order binding -------------------------------------------------------

def parse_order_header(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    keys = set(ORDER_HEADER) | set(ORDER_HEADER_AMENDED)
    for line in text.splitlines():
        line = line.strip()
        if "=" in line and line.split("=", 1)[0].strip() in keys and line.split("=", 1)[0].strip() not in out:
            k, v = line.split("=", 1); out[k.strip()] = v.strip()
    return out


def validate_experiment_order(text: str, gov: GovernanceRecord) -> list[str]:
    h = parse_order_header(text); out = []
    if gov.subscription_only:
        return _validate_amended_order(text, h, gov)
    for k in ORDER_HEADER:
        if k not in h:
            out.append(f"header {k} missing")
    if out:
        return out
    if h["INFERENCE_GOVERNANCE"] != "APPROVED" or not gov.lifted:
        out.append("governance not approved")
    if h["APPROVED_PROVIDER"] != gov.provider or h["APPROVED_MODEL"] != gov.model_id or h["APPROVED_REGION"] != gov.region:
        out.append("provider/model/region do not match governance")
    if set(x.strip() for x in h["APPROVED_DATA_CLASSES"].split(",")) != set(gov.allowed_data_classes):
        out.append("data classes do not match governance")
    if h["PREREG_SCHEMA"] != "logos.stochastic-prereg/1":
        out.append("prereg schema")
    if h["DRY_RUN_REQUIRED"].lower() != "true" or h["PRODUCTION_ACTIONS"].lower() != "forbidden":
        out.append("dry run / production actions header")
    try:
        if float(h["MAX_BUDGET"].replace("$", "").replace("USD", "").strip()) > gov.max_total_spend:
            out.append("budget exceeds governance ceiling")
        if int(h["MAX_REQUESTS"].replace(",", "")) > gov.max_requests or int(h["MAX_TOKENS"].replace(",", "")) > gov.max_total_tokens:
            out.append("requests/tokens exceed governance caps")
    except ValueError:
        out.append("numeric caps unparsable")
    for rule in DRIFT_RULES:
        if rule not in text:
            out.append(f"drift rule {rule} missing")
    for tok in ("provenance", "trajectory", "SIMULATION ONLY", "ModelOutput != Grant"):
        if tok not in text:
            out.append(f"binding {tok!r} missing")
    if gov.selected_experiment and gov.selected_experiment not in text:
        out.append("selected experiment id missing")
    return out


def _validate_amended_order(text: str, h: dict, gov: GovernanceRecord) -> list[str]:
    out = [f"header {k} missing" for k in ORDER_HEADER_AMENDED if k not in h]
    if out:
        return out
    if h["INFERENCE_GOVERNANCE"] != "APPROVED_WITH_PROVIDER_AMENDMENT" or not gov.lifted:
        out.append("governance not approved with provider amendment")
    if h["APPROVED_PROVIDER"] != gov.provider or h["APPROVED_ACCESS_PATH"] != gov.access_path or h["APPROVED_AUTH"] != gov.auth_mode:
        out.append("provider / access path / auth do not match governance")
    if h["APPROVED_MODEL"] != MODEL_PIN_PLACEHOLDER and h["APPROVED_MODEL"] != gov.model_id:
        out.append("model must stay at the MODEL_PIN_GATE placeholder until pinned from the Max account")
    if "MODEL_PIN_GATE" not in text:
        out.append("MODEL_PIN_GATE missing")
    if set(x.strip() for x in h["APPROVED_DATA_CLASSES"].split(",")) != set(gov.allowed_data_classes):
        out.append("data classes do not match governance")
    if not h["API_PAYG_BUDGET"].startswith("0"):
        out.append("API/PAYG budget must be 0")
    try:
        if int(h["MAX_CLAUDE_CODE_INVOCATIONS"]) > gov.max_claude_code_invocations or int(h["MAX_REPEATS"]) > gov.max_repeats or int(h["MAX_CONCURRENT_SESSIONS"]) != 1:
            out.append("Max caps exceed governance")
    except ValueError:
        out.append("numeric caps unparsable")
    if h["PREREG_SCHEMA"] != "logos.stochastic-prereg/1" or h["DRY_RUN_REQUIRED"].lower() != "true" or h["PRODUCTION_ACTIONS"].lower() != "forbidden":
        out.append("prereg / dry run / production actions header")
    if h["FALLBACK_PROVIDER"] != "NONE" or h["API_CREDIT_FALLBACK"].lower() != "forbidden":
        out.append("fallback / API credit fallback header")
    for rule in DRIFT_RULES:
        if rule not in text:
            out.append(f"drift rule {rule} missing")
    for tok in ("provenance", "trajectory", "SIMULATION ONLY", "ModelOutput != Grant", "--dangerously-skip-permissions", "USAGE_LIMIT_REACHED", "region guarantee = NOT ASSUMED"):
        if tok not in text:
            out.append(f"binding {tok!r} missing")
    for forbidden in ("OpenAI", "gpt-5.6-terra"):
        if forbidden in text.split("## Superseded")[0]:
            out.append(f"stale provider reference {forbidden!r} in the active header/body")
    if gov.selected_experiment and gov.selected_experiment not in text:
        out.append("selected experiment id missing")
    return out


def cli_argv_allowed(argv: list[str]) -> list[str]:
    """Documented Claude Code CLI boundary: forbidden flags never pass; API-key style arguments never appear."""
    out = []
    for a in argv:
        if a in FORBIDDEN_CLI_FLAGS:
            out.append(f"forbidden flag {a}")
        if a.lower().startswith(("--api-key", "sk-ant-")):
            out.append("API key material in argv")
    if not argv or argv[0] != "claude" or "-p" not in argv:
        out.append("must be the documented non-interactive `claude -p` invocation")
    return out


def validate_run_preregistration(payload: dict, gov: GovernanceRecord) -> list[str]:
    """A future stochastic run must carry the extension AND respect the governance caps/pins."""
    out = validate_stochastic_preregistration(payload)
    s = payload.get("stochastic", {}); t = s.get("manifest_template", {}); p = s.get("measurement_plan", {})
    if gov.subscription_only:
        if t.get("provider") != gov.provider or not t.get("model_id") or t.get("model_id") == MODEL_PIN_PLACEHOLDER:
            out.append("manifest must pin the Anthropic provider and an explicit model from the MODEL_PIN_GATE")
        if t.get("provider_region") not in ("NOT_ASSUMED", None) and t.get("provider_region") != "NOT_ASSUMED":
            out.append("region guarantee must be NOT_ASSUMED under the Claude Max path")
        if p.get("cost_cap") != 0:
            out.append("incremental API cost cap must be 0 under subscription-only billing")
        for k in ("max_turns_per_invocation", "max_output_size", "max_total_accepted_trajectories"):
            if not payload.get("stochastic", {}).get("claude_max_limits", {}).get(k):
                out.append(f"claude_max_limits.{k} missing")
    else:
        if t.get("provider") != gov.provider or t.get("model_id") != gov.model_id or t.get("provider_region") != gov.region:
            out.append("manifest pins do not match governance")
        if p.get("cost_cap") is None or p["cost_cap"] > gov.max_per_run_spend:
            out.append("run cost cap missing or above the per-run ceiling")
    if p.get("repeats") is None or p["repeats"] > gov.max_repeats:
        out.append("repeats above the ceiling")
    if p.get("fallback") != "STOP_AND_REPORT":
        out.append("fallback")
    crit = set(p.get("invalid_measurement_criteria", ()))
    for r in ("MODEL_VERSION_DRIFT", "PROMPT_DRIFT", "PROVIDER_DRIFT", "REGION_DRIFT", "DATASET_DRIFT", "COST_CAP_REACHED", "CONSTRUCT_INVALID"):
        if r not in crit:
            out.append(f"invalidation rule {r} not active")
    if payload.get("privacy_class") not in gov.allowed_data_classes:
        out.append("privacy class not approved")
    return out


def dry_run_contract(results: dict) -> list[str]:
    """The zero-inference dry run must report every check True and the counters at zero."""
    out = [c for c in DRY_RUN_CHECKS if results.get(c) is not True]
    if CALLS["model_calls"] != 0 or CALLS["provider_calls"] != 0:
        out.append("counters not zero")
    return out
