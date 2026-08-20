"""Complete-state capture/intervention helpers for Mamba-style InferenceParams.

This module intentionally snapshots only the continuation-relevant fields exposed by
state-spaces/mamba. It has no authority/governance fields and cannot mint grants.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
from types import SimpleNamespace
from typing import Any, Callable, Mapping

import torch

_ALLOWED_FIELDS = (
    "max_seqlen",
    "max_batch_size",
    "seqlen_offset",
    "batch_size_offset",
    "key_value_memory_dict",
    "lengths_per_sample",
)


def _clone_tree(value: Any) -> Any:
    if torch.is_tensor(value):
        return value.detach().clone()
    if isinstance(value, tuple):
        return tuple(_clone_tree(v) for v in value)
    if isinstance(value, list):
        return [_clone_tree(v) for v in value]
    if isinstance(value, dict):
        return {copy.deepcopy(k): _clone_tree(v) for k, v in value.items()}
    return copy.deepcopy(value)


def _walk_tensors(value: Any, path: tuple[str, ...] = ()):
    if torch.is_tensor(value):
        yield path, value
    elif isinstance(value, Mapping):
        for key in sorted(value.keys(), key=lambda x: repr(x)):
            yield from _walk_tensors(value[key], path + (f"dict:{repr(key)}",))
    elif isinstance(value, (tuple, list)):
        for idx, item in enumerate(value):
            yield from _walk_tensors(item, path + (f"seq:{idx}",))


@dataclass(frozen=True)
class MambaStateSnapshot:
    max_seqlen: int
    max_batch_size: int
    seqlen_offset: int
    batch_size_offset: int
    key_value_memory_dict: dict
    lengths_per_sample: torch.Tensor | None

    def clone(self) -> "MambaStateSnapshot":
        return MambaStateSnapshot(
            max_seqlen=int(self.max_seqlen),
            max_batch_size=int(self.max_batch_size),
            seqlen_offset=int(self.seqlen_offset),
            batch_size_offset=int(self.batch_size_offset),
            key_value_memory_dict=_clone_tree(self.key_value_memory_dict),
            lengths_per_sample=_clone_tree(self.lengths_per_sample),
        )


def capture_state(inference_params: Any) -> MambaStateSnapshot:
    """Deep-copy the complete allowlisted continuation state."""
    missing = [name for name in _ALLOWED_FIELDS if not hasattr(inference_params, name)]
    if missing:
        raise TypeError(f"InferenceParams missing required fields: {missing}")
    return MambaStateSnapshot(
        max_seqlen=int(inference_params.max_seqlen),
        max_batch_size=int(inference_params.max_batch_size),
        seqlen_offset=int(inference_params.seqlen_offset),
        batch_size_offset=int(inference_params.batch_size_offset),
        key_value_memory_dict=_clone_tree(inference_params.key_value_memory_dict),
        lengths_per_sample=_clone_tree(inference_params.lengths_per_sample),
    )


def restore_state(
    snapshot: MambaStateSnapshot,
    *,
    target: Any | None = None,
    inference_params_factory: Callable[..., Any] | None = None,
) -> Any:
    """Restore a snapshot into a target or construct a new InferenceParams-like object."""
    snap = snapshot.clone()
    if target is None:
        kwargs = dict(
            max_seqlen=snap.max_seqlen,
            max_batch_size=snap.max_batch_size,
            seqlen_offset=snap.seqlen_offset,
            batch_size_offset=snap.batch_size_offset,
            key_value_memory_dict=snap.key_value_memory_dict,
            lengths_per_sample=snap.lengths_per_sample,
        )
        return inference_params_factory(**kwargs) if inference_params_factory else SimpleNamespace(**kwargs)
    for field in _ALLOWED_FIELDS:
        setattr(target, field, _clone_tree(getattr(snap, field)))
    return target


def fresh_state(
    model: Any,
    *,
    batch_size: int,
    max_seqlen: int,
    inference_params_factory: Callable[..., Any],
    dtype: torch.dtype | None = None,
) -> Any:
    """Allocate a genuinely new Mamba cache and wrap it in fresh InferenceParams.

    This deliberately does not call ``InferenceParams.reset()`` because upstream reset
    does not clear ``key_value_memory_dict`` tensors.
    """
    cache = model.allocate_inference_cache(batch_size, max_seqlen, dtype=dtype)
    return inference_params_factory(
        max_seqlen=max_seqlen,
        max_batch_size=batch_size,
        seqlen_offset=0,
        batch_size_offset=0,
        key_value_memory_dict=_clone_tree(cache),
        lengths_per_sample=None,
    )


def swap_state(a: MambaStateSnapshot, b: MambaStateSnapshot) -> tuple[MambaStateSnapshot, MambaStateSnapshot]:
    """Return complete cloned state objects in swapped order."""
    return b.clone(), a.clone()


def permute_state(snapshot: MambaStateSnapshot, seed: int) -> MambaStateSnapshot:
    """Deterministically permute tensor elements while preserving shape/dtype/value multiset."""
    out = snapshot.clone()
    generator = torch.Generator(device="cpu")
    generator.manual_seed(int(seed))

    def permute(value: Any) -> Any:
        if torch.is_tensor(value):
            original_device = value.device
            flat_cpu = value.detach().cpu().contiguous().view(-1)
            if flat_cpu.numel() <= 1:
                return value.detach().clone()
            idx = torch.randperm(flat_cpu.numel(), generator=generator)
            return flat_cpu[idx].view(value.shape).to(device=original_device, dtype=value.dtype)
        if isinstance(value, tuple):
            return tuple(permute(v) for v in value)
        if isinstance(value, list):
            return [permute(v) for v in value]
        if isinstance(value, dict):
            return {k: permute(v) for k, v in value.items()}
        return copy.deepcopy(value)

    return MambaStateSnapshot(
        max_seqlen=out.max_seqlen,
        max_batch_size=out.max_batch_size,
        seqlen_offset=out.seqlen_offset,
        batch_size_offset=out.batch_size_offset,
        key_value_memory_dict=permute(out.key_value_memory_dict),
        lengths_per_sample=permute(out.lengths_per_sample),
    )


def state_digest(snapshot: MambaStateSnapshot) -> str:
    """Content digest independent of device placement but sensitive to state bytes."""
    h = hashlib.sha256()
    meta = {
        "max_seqlen": snapshot.max_seqlen,
        "max_batch_size": snapshot.max_batch_size,
        "seqlen_offset": snapshot.seqlen_offset,
        "batch_size_offset": snapshot.batch_size_offset,
    }
    h.update(json.dumps(meta, sort_keys=True, separators=(",", ":")).encode())
    for root_name, value in (
        ("key_value_memory_dict", snapshot.key_value_memory_dict),
        ("lengths_per_sample", snapshot.lengths_per_sample),
    ):
        if value is None:
            h.update(root_name.encode() + b":null")
            continue
        for path, tensor in _walk_tensors(value, (root_name,)):
            cpu = tensor.detach().cpu().contiguous()
            h.update("/".join(path).encode())
            h.update(str(cpu.dtype).encode())
            h.update(json.dumps(list(cpu.shape)).encode())
            h.update(cpu.numpy().tobytes())
    return h.hexdigest()
