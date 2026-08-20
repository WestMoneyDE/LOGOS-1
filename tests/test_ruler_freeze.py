import json
from pathlib import Path
from logos_pstate.ruler_freeze import freeze_jsonl

def test_freeze_jsonl_hashes_file_and_canonical_rows(tmp_path: Path):
    p = tmp_path / "x.jsonl"
    rows = [{"b":2,"a":1},{"a":3,"b":4}]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    m = freeze_jsonl(
        p,
        source_repo="NVIDIA/RULER",
        source_commit="c3f5",
        task="niah_single_1",
        seed=73000,
        max_seq_length=1024,
        num_samples=2,
        tokenizer_repo="openai-community/gpt2",
        tokenizer_revision="607a",
        exact_command="python niah.py ...",
    )
    assert m.row_count == 2
    assert len(m.file_sha256) == 64
    assert len(m.row_canonical_sha256) == 2
