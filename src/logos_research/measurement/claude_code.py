"""Claude Code (Max subscription) provider adapter — CONTRACT ONLY in this order.

INFERENCE-GOVERNANCE-PROVIDER-AMENDMENT-R1. The only allowed execution path is

    LOGOS harness -> native, documented Claude Code CLI (`claude -p ... --output-format json|stream-json`)
                  -> Claude Code's own authenticated Max subscription session

The adapter builds documented argv, enforces the model pin, turn/tool limits and
the forbidden-flag rule, maps process/usage/auth failures to closed statuses and
counts every inference invocation. It never handles subscription tokens, never
sets or reads `ANTHROPIC_API_KEY`, never calls the Messages API.

In this amendment order `invoke()` is never executed: it requires an
`ActivationToken` minted only by governance after the two-key rules, the
Claude-Max-auth preflight and the experiment dry run, and the process runner
is injected (tests use a fake). `CALLS["claude_code_inference_invocations"]`
stays 0.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Callable

from .gateway import CALLS

CALLS.setdefault("claude_code_inference_invocations", 0)
STATUSES: tuple[str, ...] = ("OK", "AUTH_NOT_MAX_SUBSCRIPTION", "AUTH_UNAVAILABLE", "USAGE_LIMIT_REACHED", "MODEL_DRIFT", "CLI_VERSION_DRIFT", "PROCESS_ERROR", "INVALID_OUTPUT", "TIMEOUT", "POLICY_BLOCK")
FORBIDDEN_FLAGS: tuple[str, ...] = ("--dangerously-skip-permissions",)
DOCUMENTED_FLAGS: tuple[str, ...] = ("-p", "--output-format", "--model", "--max-turns", "--system-prompt", "--append-system-prompt", "--allowedTools", "--disallowedTools")
OUTPUT_FORMATS: tuple[str, ...] = ("json", "stream-json")
MODEL_PIN_PLACEHOLDER = "TO_BE_PINNED_FROM_MAX_ACCOUNT_BEFORE_RUN"
CONTAMINATION_ENV: tuple[str, ...] = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")


class ProviderPolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ActivationToken:
    """Minted by governance only after: founder approval + clean contamination report + passed preflight + passed dry run + explicit model pin."""
    run_id: str
    model_pin: str
    max_invocations: int
    max_turns: int
    issued_by: str = "logos_research.governance"


@dataclass(frozen=True)
class Limits:
    max_turns: int
    max_output_bytes: int
    timeout_s: float
    disallowed_tools: tuple[str, ...] = ("Bash", "Edit", "Write", "WebFetch", "WebSearch", "NotebookEdit")
    allowed_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderResult:
    status: str
    content: str | None
    session_id: str | None
    requested_model: str
    reported_model: str | None
    claude_code_version: str | None
    usage_metadata: dict | None
    turn_count: int | None
    exit_code: int | None
    stderr_classification: str | None
    latency_s: float
    artifact_refs: tuple[str, ...] = ()
    backend_snapshot: str = "NOT_EXPOSED"

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"status {self.status!r}")


def build_argv(prompt: str, model_pin: str, limits: Limits, *, output_format: str = "json", system_prompt: str | None = None) -> list[str]:
    """Documented non-interactive invocation only."""
    if not model_pin or model_pin == MODEL_PIN_PLACEHOLDER:
        raise ProviderPolicyError("model must be pinned from the Max account (MODEL_PIN_GATE) before any invocation")
    if output_format not in OUTPUT_FORMATS:
        raise ProviderPolicyError("structured output format required")
    argv = ["claude", "-p", prompt, "--output-format", output_format, "--model", model_pin, "--max-turns", str(limits.max_turns)]
    if system_prompt:
        argv += ["--system-prompt", system_prompt]
    if limits.disallowed_tools:
        argv += ["--disallowedTools", ",".join(limits.disallowed_tools)]
    if limits.allowed_tools:
        argv += ["--allowedTools", ",".join(limits.allowed_tools)]
    check_argv(argv)
    return argv


def check_argv(argv: list[str]) -> None:
    for a in argv:
        if a in FORBIDDEN_FLAGS:
            raise ProviderPolicyError(f"forbidden flag {a}")
        if a.startswith("--") and a not in DOCUMENTED_FLAGS:
            raise ProviderPolicyError(f"undocumented flag {a}")
        if a.lower().startswith("sk-ant-") or "api-key" in a.lower():
            raise ProviderPolicyError("API key material in argv")


def contamination(env: dict | None = None) -> dict:
    """Presence-only. Values are never read into the result."""
    env = os.environ if env is None else env
    return {k: bool(env.get(k)) for k in CONTAMINATION_ENV}


def classify_stderr(stderr: str) -> str:
    s = (stderr or "").lower()
    if "usage limit" in s or "rate limit" in s or "quota" in s:
        return "USAGE_LIMIT_REACHED"
    if "not logged in" in s or "login" in s or "unauthorized" in s or "authentication" in s:
        return "AUTH_UNAVAILABLE"
    if "api key" in s or "console" in s or "pay-as-you-go" in s or "billing" in s:
        return "AUTH_NOT_MAX_SUBSCRIPTION"
    if "permission" in s or "policy" in s:
        return "POLICY_BLOCK"
    return "PROCESS_ERROR"


@dataclass
class ClaudeCodeMaxProvider:
    provider_id: str = "anthropic/claude-code/max"
    executable: str = "claude"
    runner: Callable | None = None            # injected process runner: (argv, timeout, env) -> (exit_code, stdout, stderr)
    expected_cli_version: str | None = None
    invocations: int = 0

    # -- zero-inference preflight ------------------------------------------

    def preflight(self, *, auth_class: str | None, env: dict | None = None, cli_version: str | None = None) -> dict:
        """No prompt is submitted. `auth_class` must come from safe status evidence (or None -> STOP for manual evidence)."""
        found = shutil.which(self.executable) is not None
        cont = contamination(env)
        checks = {"claude_executable_exists": found, "claude_code_version_captured": bool(cli_version), "auth_mode_verifiable": auth_class is not None,
                  "max_subscription_selected": auth_class == "MAX_SUBSCRIPTION", "no_anthropic_api_key": not cont["ANTHROPIC_API_KEY"],
                  "no_third_party_cloud_selection": not any(cont[k] for k in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")),
                  "no_payg_path": auth_class not in ("CONSOLE_PAYG",), "model_selector_configurable": "--model" in DOCUMENTED_FLAGS, "tool_restrictions_configurable": "--disallowedTools" in DOCUMENTED_FLAGS,
                  "structured_output_supported": "json" in OUTPUT_FORMATS, "forbidden_flags_blocked": True}
        stop = auth_class is None
        return {"checks": checks, "passed": all(checks.values()) and not stop, "stop_for_manual_auth_evidence": stop, "contamination_presence": cont, "cli_version": cli_version,
                "inference_invocations": CALLS["claude_code_inference_invocations"]}

    # -- invocation (never executed in the amendment order) ------------------

    def invoke(self, prompt: str, model_pin: str, run_context: dict, limits: Limits, *, token: ActivationToken, env: dict | None = None,
               output_format: str = "json") -> ProviderResult:
        if token.model_pin != model_pin or token.run_id != run_context.get("run_id"):
            raise ProviderPolicyError("activation token does not match the run / model pin")
        if self.invocations >= token.max_invocations or limits.max_turns > token.max_turns:
            raise ProviderPolicyError("invocation or turn cap exceeded")
        cont = contamination(env)
        if any(cont.values()):
            raise ProviderPolicyError("contaminated environment: " + ",".join(k for k, v in cont.items() if v))
        if self.runner is None:
            raise ProviderPolicyError("no runner injected")
        argv = build_argv(prompt, model_pin, limits, output_format=output_format, system_prompt=run_context.get("system_prompt"))
        self.invocations += 1; CALLS["claude_code_inference_invocations"] += 1; CALLS["provider_calls"] += 1; CALLS["model_calls"] += 1
        t0 = time.perf_counter()
        exit_code, stdout, stderr = self.runner(argv, limits.timeout_s, {k: v for k, v in (env or {}).items() if k not in CONTAMINATION_ENV})
        latency = time.perf_counter() - t0
        if exit_code is None:
            return ProviderResult("TIMEOUT", None, None, model_pin, None, self.expected_cli_version, None, None, None, "timeout", latency)
        if exit_code != 0:
            return ProviderResult(classify_stderr(stderr), None, None, model_pin, None, self.expected_cli_version, None, None, exit_code, classify_stderr(stderr), latency)
        try:
            doc = json.loads(stdout) if output_format == "json" else [json.loads(l) for l in stdout.splitlines() if l.strip()][-1]
        except (ValueError, IndexError):
            return ProviderResult("INVALID_OUTPUT", None, None, model_pin, None, self.expected_cli_version, None, None, exit_code, None, latency)
        reported = doc.get("model") or (doc.get("modelUsage") and next(iter(doc["modelUsage"]), None))
        if reported and model_pin not in reported and reported not in model_pin:
            return ProviderResult("MODEL_DRIFT", None, doc.get("session_id"), model_pin, reported, self.expected_cli_version, doc.get("usage"), doc.get("num_turns"), exit_code, None, latency)
        content = doc.get("result")
        if content is not None and len(content.encode()) > limits.max_output_bytes:
            return ProviderResult("INVALID_OUTPUT", None, doc.get("session_id"), model_pin, reported, self.expected_cli_version, doc.get("usage"), doc.get("num_turns"), exit_code, "output too large", latency)
        ref = sha256((stdout or "").encode()).hexdigest()
        return ProviderResult("OK", content, doc.get("session_id"), model_pin, reported, self.expected_cli_version, doc.get("usage"), doc.get("num_turns"), exit_code, None, latency, (ref,))
