"""The only place a `claude` process is started (Sections 26-28).

Reachable only through `make_runner(token)`: the returned callable is what
`ClaudeCodeMaxProvider(runner=...)` invokes. It never sees credentials, never sets
`ANTHROPIC_API_KEY`, never adds flags: the argv comes from `claude_code.build_argv`
and is re-checked here. Never `--dangerously-skip-permissions`.
"""
from __future__ import annotations

import shutil
import subprocess

from logos_research.measurement.claude_code import ActivationToken, ProviderPolicyError, check_argv

FORBIDDEN_ENV: tuple[str, ...] = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")


def make_runner(token: ActivationToken, *, cwd: str | None = None):
    """`cwd`: an isolated empty working directory (repair R1, Section 19) so no project CLAUDE.md / .claude settings enter the context."""
    if not isinstance(token, ActivationToken):
        raise ProviderPolicyError("a governance ActivationToken is required to build the process runner")
    exe = shutil.which("claude")
    if not exe:
        raise ProviderPolicyError("claude executable not on PATH")

    def _run(argv: list[str], timeout: float, env: dict) -> tuple[int | None, str, str]:
        check_argv(argv)
        if argv[0] != "claude":
            raise ProviderPolicyError("argv must start with the documented executable name")
        if any(k in env for k in FORBIDDEN_ENV):
            raise ProviderPolicyError("forbidden environment key present")
        try:
            cp = subprocess.run([exe, *argv[1:]], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env, shell=False, stdin=subprocess.DEVNULL, cwd=cwd)
        except subprocess.TimeoutExpired:
            return None, "", "timeout"
        return cp.returncode, cp.stdout, cp.stderr

    return _run


def cli_version(timeout: float = 30.0) -> str | None:
    """`claude --version` — no prompt, no model, no inference. Returns the version string or None."""
    exe = shutil.which("claude")
    if not exe:
        return None
    try:
        cp = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, shell=False, stdin=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return (cp.stdout or cp.stderr).strip() or None
