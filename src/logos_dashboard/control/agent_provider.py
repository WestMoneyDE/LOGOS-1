"""Agent provider: the Research-OS sibling of `ClaudeCodeMaxProvider` for agent jobs (thesis_advance, prior_art, radar_process).

Differences, all covered by INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1 (founder, 2026-09-19):
  * `--output-format stream-json --verbose` -> the live event stream (what the agent reads, writes, searches) and Tier-1 producer evidence.
  * `subprocess.Popen` with line streaming; every line is condensed into a `ros_run_events` row via `on_event`; `stop_check()` between lines terminates the process.
Everything else is the measurement contract: ActivationToken, invocation counter, contamination presence check, own argv allowlist re-checked by the runner,
no API key, no undocumented flag beyond the amended one, status classification cc-status/2, result-model resolution never by key order.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Callable

from logos_research.measurement.claude_code import (CONTAMINATION_ENV, DOCUMENTED_FLAGS, FORBIDDEN_FLAGS, MODEL_PIN_PLACEHOLDER, ActivationToken, Limits, ProviderPolicyError, ProviderResult,
                                                    classify_result, classify_stderr, contamination)
from logos_research.measurement.gateway import CALLS
from logos_research.measurement.result_model import CONTRACT_VERSION, resolve_result_model

AMENDMENT = "INFERENCE-GOVERNANCE-FLAG-AMENDMENT-R1"
AGENT_FLAGS: tuple[str, ...] = DOCUMENTED_FLAGS + ("--verbose",)
AGENT_KINDS = ("thesis_advance", "prior_art", "radar_process")
MAX_TEXT = 600


def build_agent_argv(prompt: str, model_pin: str, limits: Limits, *, system_prompt: str | None = None) -> list[str]:
    if not model_pin or model_pin == MODEL_PIN_PLACEHOLDER:
        raise ProviderPolicyError("model must be pinned before any invocation")
    argv = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--model", model_pin, "--max-turns", str(limits.max_turns)]
    if system_prompt:
        argv += ["--append-system-prompt", system_prompt]
    if limits.disallowed_tools:
        argv += ["--disallowedTools", ",".join(limits.disallowed_tools)]
    if limits.allowed_tools:
        argv += ["--allowedTools", ",".join(limits.allowed_tools)]
    check_agent_argv(argv)
    return argv


def check_agent_argv(argv: list[str]) -> None:
    for a in argv:
        if a in FORBIDDEN_FLAGS:
            raise ProviderPolicyError(f"forbidden flag {a}")
        if a.startswith("--") and a not in AGENT_FLAGS:
            raise ProviderPolicyError(f"flag {a} is neither documented nor covered by {AMENDMENT}")
        if a.lower().startswith("sk-ant-") or "api-key" in a.lower():
            raise ProviderPolicyError("API key material in argv")


def _short(x, n: int = MAX_TEXT) -> str:
    s = x if isinstance(x, str) else json.dumps(x, default=str, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def condense(ev: dict) -> dict | None:
    """One stream line -> one console event (plain fields; tool inputs reduced to their target). None = nothing worth showing."""
    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init":
        return {"kind": "agent.init", "model": ev.get("model"), "tools": ev.get("tools"), "cwd": ev.get("cwd"), "session_id": ev.get("session_id"), "permission_mode": ev.get("permissionMode")}
    if t == "assistant":
        msg = ev.get("message") or {}; out = []
        for c in msg.get("content") or []:
            if c.get("type") == "text" and c.get("text", "").strip():
                out.append({"kind": "agent.text", "text": _short(c["text"]), "model": msg.get("model")})
            elif c.get("type") == "tool_use":
                inp = c.get("input") or {}; name = c.get("name")
                target = inp.get("file_path") or inp.get("path") or inp.get("pattern") or inp.get("query") or inp.get("url") or inp.get("command") or inp.get("skill") or inp.get("description") or ""
                out.append({"kind": "agent.tool", "tool": name, "target": _short(target, 300), "tool_use_id": c.get("id"), "model": msg.get("model")})
            elif c.get("type") == "thinking":
                out.append({"kind": "agent.thinking", "text": _short(c.get("thinking", ""), 300)})
        return {"kind": "agent.batch", "items": out} if out else None
    if t == "user":
        msg = ev.get("message") or {}; out = []
        for c in (msg.get("content") or []) if isinstance(msg.get("content"), list) else []:
            if c.get("type") == "tool_result":
                content = c.get("content"); text = content if isinstance(content, str) else json.dumps(content, default=str) if content else ""
                out.append({"kind": "agent.tool_result", "tool_use_id": c.get("tool_use_id"), "is_error": bool(c.get("is_error")), "bytes": len(text.encode("utf-8", "replace")), "preview": _short(text, 200)})
        return {"kind": "agent.batch", "items": out} if out else None
    if t == "result":
        return {"kind": "agent.result", "subtype": ev.get("subtype"), "is_error": ev.get("is_error"), "num_turns": ev.get("num_turns"), "duration_ms": ev.get("duration_ms"), "usage": ev.get("usage"), "session_id": ev.get("session_id")}
    return None


@dataclass
class AgentProvider:
    provider_id: str = "anthropic/claude-code/max/agent"
    runner: Callable | None = None            # (argv, timeout, env, on_line, stop_check) -> (exit_code | None, stdout, stderr)
    expected_cli_version: str | None = None
    invocations: int = 0
    events: list = field(default_factory=list)
    raw_lines: list = field(default_factory=list)

    def invoke(self, prompt: str, model_pin: str, run_context: dict, limits: Limits, *, token: ActivationToken, env: dict | None = None,
               on_event: Callable[[dict], None] | None = None, stop_check: Callable[[], bool] | None = None) -> ProviderResult:
        if run_context.get("kind") not in AGENT_KINDS:
            raise ProviderPolicyError(f"agent provider is limited to {AGENT_KINDS} ({AMENDMENT})")
        if token.model_pin != model_pin or token.run_id != run_context.get("run_id"):
            raise ProviderPolicyError("activation token does not match the run / model pin")
        if self.invocations >= token.max_invocations or limits.max_turns > token.max_turns:
            raise ProviderPolicyError("invocation or turn cap exceeded")
        cont = contamination(env)
        if any(cont.values()):
            raise ProviderPolicyError("contaminated environment: " + ",".join(k for k, v in cont.items() if v))
        if self.runner is None:
            raise ProviderPolicyError("no runner injected")
        argv = build_agent_argv(prompt, model_pin, limits, system_prompt=run_context.get("system_prompt"))
        self.invocations += 1; CALLS["claude_code_inference_invocations"] += 1; CALLS["provider_calls"] += 1; CALLS["model_calls"] += 1
        self.events = []; self.raw_lines = []

        def on_line(line: str) -> None:
            line = line.strip()
            if not line:
                return
            self.raw_lines.append(line)
            try:
                ev = json.loads(line)
            except ValueError:
                return
            if isinstance(ev, dict):
                self.events.append(ev)
                c = condense(ev)
                if c and on_event:
                    on_event(c)
        t0 = time.perf_counter()
        exit_code, stdout, stderr = self.runner(argv, limits.timeout_s, {k: v for k, v in (env or {}).items() if k not in CONTAMINATION_ENV}, on_line, stop_check or (lambda: False))
        latency = time.perf_counter() - t0
        if exit_code is None:
            return ProviderResult("TIMEOUT", None, None, model_pin, None, self.expected_cli_version, None, None, None, "timeout", latency)
        if exit_code == -15 or exit_code == "STOPPED":
            return ProviderResult("PROCESS_ERROR", None, None, model_pin, None, self.expected_cli_version, None, None, -15, "stopped", latency)
        if exit_code != 0 and not any(e.get("type") == "result" for e in self.events):
            return ProviderResult(classify_stderr(stderr), None, None, model_pin, None, self.expected_cli_version, None, None, exit_code, classify_stderr(stderr), latency)
        doc = next((e for e in reversed(self.events) if e.get("type") == "result"), None)
        if doc is None:
            return ProviderResult("INVALID_OUTPUT", None, None, model_pin, None, self.expected_cli_version, None, None, exit_code, "no result event", latency)
        res = resolve_result_model(model_pin, self.events, "stream-json", CONTRACT_VERSION)
        usage = doc.get("usage") if isinstance(doc.get("usage"), dict) else None
        common = dict(session_id=doc.get("session_id"), requested_model=model_pin, reported_model=res.resolved_model, claude_code_version=self.expected_cli_version, usage_metadata=usage, turn_count=doc.get("num_turns"), exit_code=exit_code, latency_s=latency, resolution=res,
                      model_usage_raw=doc.get("modelUsage") if isinstance(doc.get("modelUsage"), dict) else None, scaffolding={k: usage.get(k) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")} if usage else None)
        err = classify_result(doc, self.events)
        if err:
            return ProviderResult(err, None, stderr_classification=err, **common)
        if res.drift:
            return ProviderResult("MODEL_DRIFT", None, stderr_classification=res.reason_code, **common)
        if res.status == "OUTPUT_INVALID":
            return ProviderResult("INVALID_OUTPUT", None, stderr_classification=res.reason_code, **common)
        if res.status != "RESOLVED":
            return ProviderResult("RESULT_MODEL_AMBIGUOUS", None, stderr_classification=res.reason_code, **common)
        content = doc.get("result")
        if content is not None and len(str(content).encode()) > limits.max_output_bytes:
            return ProviderResult("INVALID_OUTPUT", None, stderr_classification="output too large", **common)
        return ProviderResult("OK", content, stderr_classification=None, artifact_refs=(sha256("\n".join(self.raw_lines).encode()).hexdigest(),), **common)

    def stream_text(self) -> str:
        return "\n".join(self.raw_lines) + "\n"

    def tool_histogram(self) -> dict:
        h: dict[str, int] = {}
        for e in self.events:
            if e.get("type") == "assistant":
                for c in (e.get("message") or {}).get("content") or []:
                    if c.get("type") == "tool_use":
                        h[c.get("name") or "?"] = h.get(c.get("name") or "?", 0) + 1
        return h
