from logos_pstate.retrieval import Chunk, BM25Index, build_retrieval_record

def chunks():
    return [
        Chunk("a", "alpha beta beta"),
        Chunk("b", "alpha gamma"),
        Chunk("c", "delta epsilon zeta"),
        Chunk("d", "theta iota"),
    ]

def test_bm25_is_deterministic_and_ties_break_by_id():
    idx = BM25Index(chunks())
    r1 = idx.rank("alpha")
    r2 = idx.rank("alpha")
    assert r1 == r2
    assert r1[0].chunk_id in {"a","b"}

def test_matched_distractor_count_and_exclusion():
    idx = BM25Index(chunks())
    selected = idx.matched_distractors(excluded_ids=["a"], target_token_count=3, k=1)
    assert len(selected) == 1 and selected[0].chunk_id != "a"

def test_record_persists_required_provenance():
    idx = BM25Index(chunks())
    selected = [chunks()[0]]
    record = build_retrieval_record(query="alpha", index=idx, selected=selected, final_prompt="ctx\nquery")
    assert record.candidate_chunk_ids == ("a","b","c","d")
    assert record.selected_chunk_ids == ("a",)
    assert len(record.selected_text_sha256[0]) == 64
    assert len(record.final_prompt_sha256) == 64
