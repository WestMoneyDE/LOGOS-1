from dataclasses import dataclass, field
import torch

from logos_pstate.mamba_state import capture_state, restore_state, fresh_state, swap_state, permute_state, state_digest

@dataclass
class FakeInferenceParams:
    max_seqlen: int
    max_batch_size: int
    seqlen_offset: int = 0
    batch_size_offset: int = 0
    key_value_memory_dict: dict = field(default_factory=dict)
    lengths_per_sample: torch.Tensor | None = None

class FakeModel:
    def __init__(self):
        self.calls = 0
    def allocate_inference_cache(self, batch_size, max_seqlen, dtype=None):
        self.calls += 1
        dt = dtype or torch.float32
        return {
            0: (torch.zeros(batch_size, 6, 4, dtype=dt), torch.zeros(batch_size, 6, 3, dtype=dt)),
            1: (torch.zeros(batch_size, 6, 4, dtype=dt), torch.zeros(batch_size, 6, 3, dtype=dt)),
        }

def make_state(offset=7):
    return FakeInferenceParams(
        max_seqlen=128,
        max_batch_size=1,
        seqlen_offset=offset,
        key_value_memory_dict={0: (torch.arange(24.0).reshape(1,6,4), torch.arange(18.0).reshape(1,6,3))},
        lengths_per_sample=torch.tensor([offset], dtype=torch.int32),
    )

def test_capture_restore_is_deep_and_digest_identical():
    live = make_state()
    snap = capture_state(live)
    restored = restore_state(snap, inference_params_factory=FakeInferenceParams)
    assert state_digest(capture_state(restored)) == state_digest(snap)
    live.key_value_memory_dict[0][0].add_(999)
    assert state_digest(capture_state(live)) != state_digest(snap)

def test_identical_history_captures_have_identical_digest():
    assert state_digest(capture_state(make_state())) == state_digest(capture_state(make_state()))

def test_fresh_state_allocates_new_cache_not_mutated_reuse():
    model = FakeModel()
    a = fresh_state(model, batch_size=1, max_seqlen=128, inference_params_factory=FakeInferenceParams)
    a.key_value_memory_dict[0][0].fill_(9)
    b = fresh_state(model, batch_size=1, max_seqlen=128, inference_params_factory=FakeInferenceParams)
    assert model.calls == 2
    assert torch.count_nonzero(b.key_value_memory_dict[0][0]).item() == 0
    assert a.key_value_memory_dict[0][0].data_ptr() != b.key_value_memory_dict[0][0].data_ptr()

def test_swap_exchanges_complete_snapshots_without_aliasing():
    a = capture_state(make_state(offset=3))
    b = capture_state(make_state(offset=9))
    b2, a2 = swap_state(a, b)
    assert b2.seqlen_offset == 9 and a2.seqlen_offset == 3
    b2.key_value_memory_dict[0][0].add_(1)
    assert state_digest(b2) != state_digest(b)

def test_permutation_preserves_shape_dtype_and_value_multiset():
    snap = capture_state(make_state())
    p = permute_state(snap, seed=73000)
    src = snap.key_value_memory_dict[0][0]
    dst = p.key_value_memory_dict[0][0]
    assert src.shape == dst.shape and src.dtype == dst.dtype
    assert torch.equal(src.flatten().sort().values, dst.flatten().sort().values)
    assert not torch.equal(src, dst)
    assert state_digest(p) == state_digest(permute_state(snap, seed=73000))

def test_snapshot_allowlist_excludes_authority_fields():
    live = make_state()
    live.authority = "NEVER_CAPTURE"
    snap = capture_state(live)
    assert not hasattr(snap, "authority")
