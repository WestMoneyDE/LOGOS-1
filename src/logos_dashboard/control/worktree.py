"""Isolated git worktrees for agent jobs. Branch `ros/<thesis_id>/<run_id>` from HEAD; outputs are confined to an allowlist; the main working tree is never touched."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _git(repo: Path, *args: str, check: bool = True) -> str:
    cp = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
    if check and cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {cp.stderr.strip()}")
    return cp.stdout


def branch_name(thesis_id: str, run_id: str) -> str:
    return f"ros/{thesis_id}/{run_id}"


def create(repo: Path, worktrees_root: Path, thesis_id: str, run_id: str) -> Path:
    worktrees_root.mkdir(parents=True, exist_ok=True)
    path = worktrees_root / run_id
    _git(repo, "worktree", "add", "-b", branch_name(thesis_id, run_id), str(path), "HEAD")
    return path


def changed_files(path: Path) -> list[str]:
    out = _git(path, "status", "--porcelain", "--untracked-files=all")
    return sorted(line[3:].strip().replace("\\", "/") for line in out.splitlines() if line.strip())


def check_allowlist(files: list[str], allowed_prefixes: tuple[str, ...]) -> list[str]:
    return [f for f in files if not f.startswith(allowed_prefixes)]


def commit(path: Path, message: str) -> str | None:
    if not changed_files(path):
        return None
    _git(path, "add", "-A")
    _git(path, "-c", "user.name=logos-ros-agent", "-c", "user.email=ros-agent@logos.local", "commit", "-q", "-m", message)
    return _git(path, "rev-parse", "HEAD").strip()


def remove(repo: Path, path: Path, *, delete_branch: str | None = None) -> None:
    _git(repo, "worktree", "remove", "--force", str(path), check=False)
    _git(repo, "worktree", "prune", check=False)
    if delete_branch:
        _git(repo, "branch", "-D", delete_branch, check=False)


def head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").strip()
