"""Integrity regression for the R4 RULER dataset freeze.

These tests exist because a byte freeze is only worth something if a later
checkout can still reproduce the recorded hashes. The concrete failure mode
guarded here is newline normalization: this repository is developed on a machine
with `core.autocrlf = true`, and without the `.gitattributes` `-text` rules every
recorded SHA-256 would silently become wrong on checkout.

The tests are offline, deterministic and load no model.
"""
import hashlib
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
SESSION = REPO / "09-SESSIONS" / "2026-09-10-PERSISTENT-STATE-DATASET-MATERIALIZATION-R4"

pytestmark = pytest.mark.skipif(
    not SESSION.exists(), reason="R4 session artifact not present in this checkout"
)


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def dataset_manifest() -> dict:
    return json.loads((SESSION / "DATASET-MANIFEST.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((SESSION / "RETURN-ENVELOPE.json").read_text(encoding="utf-8"))


def test_return_envelope_is_a_complete_freeze(envelope):
    assert envelope["classification"] == "COMPLETE_DATASET_FREEZE"
    assert envelope["files_expected"] == envelope["files_produced"] == 32
    assert envelope["total_examples"] == 1024
    assert envelope["determinism"] == "REPRODUCIBLE"
    assert envelope["generator_pins_verified"] is True


def test_no_model_weights_were_loaded(envelope):
    """R4 forbids weight loading and answer-producing model execution."""
    assert envelope["model_weights_loaded"] is False
    assert envelope["answer_producing_model_executed"] is False
    assert envelope["scientific_verdict"] == "NONE"
    assert envelope["gamma_verdict_change"] == "NONE"


def test_every_generated_file_matches_its_recorded_hash(dataset_manifest):
    """The core guard: catches newline normalization and any silent rewrite."""
    mismatches = []
    for rec in dataset_manifest["files"]:
        path = SESSION / "generated" / rec["path"]
        assert path.exists(), f"missing frozen file: {rec['path']}"
        observed = _sha256(path)
        if observed != rec["file_sha256"]:
            mismatches.append((rec["path"], rec["file_sha256"], observed))
    assert not mismatches, f"frozen dataset bytes changed: {mismatches[:3]}"


def test_frozen_envelope_is_unchanged(dataset_manifest):
    env = dataset_manifest["envelope"]
    assert env["tasks"] == ["niah_single_1", "niah_multikey_1", "niah_multiquery", "vt"]
    assert env["seeds"] == [73000, 73001, 73002, 73003]
    assert env["max_seq_length"] == 1024
    assert env["num_samples_per_task_per_seed"] == 32
    assert env["remove_newline_tab"] is False


def test_every_file_has_exactly_32_rows_within_the_token_bound(dataset_manifest):
    for rec in dataset_manifest["files"]:
        assert rec["row_count"] == 32, rec["path"]
        assert len(rec["row_sha256"]) == 32, rec["path"]
        summary = rec["token_length_summary"]
        assert summary["n"] == 32, rec["path"]
        assert summary["max"] <= 1024, f"{rec['path']} exceeds max_seq_length"


def test_per_row_hashes_still_describe_the_rows(dataset_manifest):
    """Recompute canonical row hashes for one file per tokenizer family."""
    seen = set()
    for rec in dataset_manifest["files"]:
        if rec["family"] in seen:
            continue
        seen.add(rec["family"])
        path = SESSION / "generated" / rec["path"]
        rows = [
            json.loads(line)
            for line in path.read_bytes().decode("utf-8").splitlines()
            if line.strip()
        ]
        recomputed = [
            hashlib.sha256(
                json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                    "utf-8"
                )
            ).hexdigest()
            for r in rows
        ]
        assert recomputed == rec["row_sha256"], rec["path"]
    assert seen == {"gpt2", "mamba"}


def test_sha256sums_file_agrees_with_the_tree():
    lines = (SESSION / "SHA256SUMS.txt").read_bytes().decode("utf-8").splitlines()
    assert lines, "SHA256SUMS.txt is empty"
    for line in lines:
        digest, rel = line.split("  ", 1)
        target = SESSION / rel
        assert target.exists(), f"SHA256SUMS references missing file: {rel}"
        assert _sha256(target) == digest, f"hash drift in {rel}"


def test_haystack_corpus_pin_is_recorded_with_its_boundary():
    man = json.loads((SESSION / "HAYSTACK-CORPUS-MANIFEST.json").read_text(encoding="utf-8"))
    assert man["failures"] == 0
    assert man["url_count"] == 218
    assert man["repo_essays"] + man["html_essays"] == 218
    assert man["acquisition"] == "fail_closed_all_or_nothing"
    assert len(man["concatenation_order"]) == 218
    assert len(man["per_essay_sha256"]) == 218
    # The pin type must stay honest: this is not an upstream immutable reference.
    assert "NOT reproducible" in man["reproducibility_boundary"]


def test_tokenizer_manifest_records_both_families_without_weights():
    man = json.loads((SESSION / "TOKENIZER-MANIFEST.json").read_text(encoding="utf-8"))
    assert man["model_weights_loaded"] is False
    assert set(man["families"]) == {"gpt2", "mamba"}
    assert man["families"]["gpt2"]["revision"] == (
        "607a30d783dfa663caf39e06633721c8d4cfcd7e"
    )
    assert man["families"]["mamba"]["revision"] == (
        "1e76775f628fbf1350fbe4dbb3d971ba64af25a1"
    )
    for family in man["families"].values():
        for name in family["files"]:
            assert not name.endswith((".safetensors", ".bin", ".h5", ".msgpack", ".ot")), (
                f"weight artifact leaked into the tokenizer freeze: {name}"
            )


def test_gitattributes_protects_frozen_artifacts():
    """Without these rules core.autocrlf=true invalidates every recorded hash."""
    text = (REPO / ".gitattributes").read_text(encoding="utf-8")
    assert "*.jsonl -text" in text
    assert "SHA256SUMS.txt -text" in text
