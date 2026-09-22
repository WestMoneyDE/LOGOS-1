"""One authoritative pin for Γ, instead of a commit id repeated in six guards.

Six predecessor guards asserted `git diff <base> HEAD -- GAMMA.md src/logos_gamma`
is empty. That was right while Γ was frozen outright, and it has two weaknesses now
that the founder has approved extensions:

- each guard hard-codes a different base commit, so "unchanged" silently means six
  different things;
- a guard that compares committed states passes while a change sits in the working
  tree, which is how a violation of the canonical-effect-owner record survived one
  full green run in this repository.

The replacement is stronger, not weaker. Γ is pinned to **one recorded hash** in
`docs/research/DETERMINISTIC-CHAIN-FROZEN-HASHES.json`, that file keeps every
previous value under `superseded` with the order and the reason that replaced it,
and the guards check the bytes on disk rather than a diff between commits. An
unapproved edit to Γ fails immediately, whether it is committed or not.

Changing Γ therefore takes two deliberate acts, not one: the code, and a re-freeze
that records who approved it and why.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_PATH = ROOT / "docs/research/DETERMINISTIC-CHAIN-FROZEN-HASHES.json"
PACKAGE_PATH = ROOT / "docs/research/DETERMINISTIC-CHAIN-CONSOLIDATION.json"

#: Paths a predecessor guard should leave to this module rather than diffing.
GAMMA_PATHS = (":(exclude)GAMMA.md", ":(exclude)src/logos_gamma")


def gamma_bundle_files() -> list[str]:
    return sorted(json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))["gamma_bundle_files"])


def gamma_bundle_hash() -> str:
    """Hash of the Γ bundle as it is on disk, not as it was committed."""
    return hashlib.sha256(b"".join((ROOT / p).read_bytes() for p in gamma_bundle_files())).hexdigest()


def p7_boundary_hash() -> str:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    text = (ROOT / package["p7_boundary_file"]).read_bytes()
    return hashlib.sha256(text[text.index(b"## Consciousness / P7 boundary"):]).hexdigest()


def frozen() -> dict:
    return json.loads(FROZEN_PATH.read_text(encoding="utf-8"))


def assert_gamma_pinned() -> None:
    """Γ is exactly the approved state, and the approval history is intact."""
    record = frozen()
    assert record["gamma_bundle_sha256"] == gamma_bundle_hash(), (
        "Γ differs from the frozen bundle. Either revert the edit, or record a founder-approved "
        "re-freeze in docs/research/DETERMINISTIC-CHAIN-FROZEN-HASHES.json with the previous value "
        "kept under 'superseded'."
    )
    assert record["p7_boundary_sha256"] == p7_boundary_hash(), "the P7 boundary text changed"
    for entry in record.get("superseded", []):
        assert entry["gamma_bundle_sha256"] != record["gamma_bundle_sha256"], "a superseded hash is still active"
        for field in ("superseded_by", "superseded_on", "reason"):
            assert entry.get(field), f"a superseded Γ freeze without {field} is not auditable"
        assert len(entry["reason"]) >= 80, "a one-line reason is not a record of why Γ changed"
