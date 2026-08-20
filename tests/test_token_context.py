import pytest
from logos_pstate.token_context import full_token_history, truncated_history, history_substitution

def test_full_history_rejects_silent_overflow():
    assert full_token_history(range(10), max_tokens=10) == tuple(range(10))
    with pytest.raises(ValueError):
        full_token_history(range(11), max_tokens=10)

def test_primary_truncation_keeps_tail_only():
    assert truncated_history(range(10), keep_last=4) == (6,7,8,9)

def test_substitution_keeps_query_identical():
    a = [1,2,3]
    b = [8,9]
    q = [40,41]
    assert history_substitution(a,b,q,max_tokens=10) == (8,9,40,41)
