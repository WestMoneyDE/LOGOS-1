"""Append-only result journal for the Laya measurement scripts, so a crash loses at most the item in flight.

One JSON line per completed item, `{"key", "resumed", "result"}`, flushed and fsynced before the next item starts.
Opening an existing journal loads its lines; the caller skips every key already present. A torn last line (a write
cut by the crash, recognised by the missing newline) is appended to `<journal>.torn` and cut from the journal, never
dropped silently. Any other unreadable or duplicate line raises: the journal is evidence, and a guess would corrupt it.

`resumed` is true for every item written by a session that opened a non-empty journal. Such an item was produced
by a different process, possibly after a model reload, so its timing is not comparable with the first session.

No network, no model: file I/O only.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class JournalError(ValueError):
    """The journal holds a line that is neither complete JSON nor a torn last line, or a key twice."""


def item_key(scope: str, idx: int, text: str) -> str:
    """Stable key of one item: scope (set/protocol/route), position, and a hash of the text, so a changed case never reuses an answer."""
    return f"{scope}:{idx}:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def write_atomic(path: Path | str, text: str) -> None:
    """Write `text` to `path` via a temporary sibling and `os.replace`: a reader sees the old file or the new one."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class Journal:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.torn_path = self.path.with_name(self.path.name + ".torn")
        self.entries: dict[str, dict] = {}
        self.torn_bytes = 0
        self._load()
        self.resumed = bool(self.entries)

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = self.path.read_bytes()
        complete_end = data.rfind(b"\n") + 1          # bytes up to and including the last newline
        torn = data[complete_end:]
        if torn:
            with open(self.torn_path, "ab") as f:      # preserved, append-only
                f.write(torn + b"\n")
                f.flush()
                os.fsync(f.fileno())
            with open(self.path, "r+b") as f:
                f.truncate(complete_end)
                f.flush()
                os.fsync(f.fileno())
            self.torn_bytes = len(torn)
        for n, raw in enumerate(data[:complete_end].splitlines(), 1):
            if not raw.strip():
                continue
            try:
                line = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise JournalError(f"{self.path}:{n}: unreadable line inside the journal ({type(exc).__name__})") from exc
            if not isinstance(line, dict) or not isinstance(line.get("key"), str) or "result" not in line:
                raise JournalError(f"{self.path}:{n}: not a journal line")
            if line["key"] in self.entries:
                raise JournalError(f"{self.path}:{n}: duplicate key {line['key']!r}")
            self.entries[line["key"]] = line

    def __contains__(self, key: str) -> bool:
        return key in self.entries

    def __len__(self) -> int:
        return len(self.entries)

    def result(self, key: str) -> dict:
        return self.entries[key]["result"]

    def was_resumed(self, key: str) -> bool:
        return bool(self.entries[key]["resumed"])

    def append(self, key: str, result) -> dict:
        if key in self.entries:
            raise JournalError(f"duplicate key {key!r}")
        line = {"key": key, "resumed": self.resumed, "result": result}
        blob = (json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        with open(self.path, "ab") as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        self.entries[key] = line
        return line


def open_journal(path: Path | str, resume: bool) -> Journal:
    """Open `path`; a non-empty journal without `resume` is refused, so a rerun never reuses answers by accident."""
    journal = Journal(path)
    if len(journal) and not resume:
        raise JournalError(f"{journal.path} already holds {len(journal)} results; pass --resume to continue it, or move it away")
    return journal
