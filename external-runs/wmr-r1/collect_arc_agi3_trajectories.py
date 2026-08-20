#!/usr/bin/env python3
"""Collect source-blind ARC-AGI-3 trajectories."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

COORDS = [(32,32),(8,8),(56,8),(8,56),(56,56),(16,32),(48,32),(32,16),(32,48)]

def _frame(raw: Any) -> list[list[int]]:
    frames = getattr(raw, "frame", None)
    if frames is None or len(frames) == 0:
        raise ValueError("FrameDataRaw.frame missing")
    arr = frames[-1]
    if hasattr(arr, "tolist"):
        return arr.tolist()
    return [list(row) for row in arr]

def _action_payload(action: Any) -> dict:
    try:
        return action.action_data.model_dump()
    except Exception:
        return {}

def canonical_game_id(x: str) -> str:
    return x.split("-", 1)[0]

def game_fold(game_id: str) -> int:
    h = hashlib.sha256(("LOGOS-WMR-R2|" + canonical_game_id(game_id)).encode()).hexdigest()
    return int(h[:8], 16) % 5

def choose_coverage_action(env: Any, step: int):
    from arcengine import GameAction
    actions = [a for a in env.action_space if a is not GameAction.RESET]
    if not actions:
        return GameAction.RESET
    action = actions[step % len(actions)]
    if action.is_complex():
        x, y = COORDS[(step // max(1, len(actions))) % len(COORDS)]
        action.set_data({"x": x, "y": y})
    return action

def collect_game(arc, game_id: str, seed: int, budget: int) -> list[dict]:
    from arcengine import GameAction, GameState
    env = arc.make(game_id, seed=seed, save_recording=False)
    if env is None:
        raise RuntimeError(f"Could not create {game_id}")
    raw = env.reset()
    if raw is None:
        raise RuntimeError(f"Reset failed {game_id}")
    rows = []
    for step in range(budget):
        pre = _frame(raw)
        pre_state = getattr(getattr(raw, "state", None), "name", str(getattr(raw, "state", None)))
        if getattr(raw, "state", None) in [GameState.NOT_PLAYED, GameState.GAME_OVER]:
            action = GameAction.RESET
        else:
            action = choose_coverage_action(env, step)
        payload = _action_payload(action)
        nxt = env.step(action, data=payload)
        if nxt is None:
            break
        rows.append({
            "game_id": canonical_game_id(game_id),
            "game_versioned_id": game_id,
            "game_fold": game_fold(game_id),
            "seed": seed,
            "step": step,
            "pre_frame": pre,
            "post_frame": _frame(nxt),
            "action_id": int(action.value),
            "action_name": action.name,
            "action_data": payload,
            "pre_state": pre_state,
            "post_state": getattr(getattr(nxt, "state", None), "name", str(getattr(nxt, "state", None))),
            "levels_completed": int(getattr(nxt, "levels_completed", 0)),
            "win_levels": int(getattr(nxt, "win_levels", 0)),
        })
        raw = nxt
        if getattr(nxt, "state", None) is GameState.WIN:
            break
    return rows

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--environment-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--budget", type=int, default=80)
    ap.add_argument("--seeds", default="73000,73001,73002,73003")
    ap.add_argument("--games", default="")
    args = ap.parse_args()

    import arc_agi
    from arc_agi import OperationMode

    arc = arc_agi.Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(args.environment_dir),
    )
    envs = arc.get_environments()
    ids = sorted({e.game_id for e in envs})
    if args.games:
        wanted = {x.strip() for x in args.games.split(",") if x.strip()}
        ids = [x for x in ids if canonical_game_id(x) in wanted or x in wanted]
    if not ids:
        raise SystemExit("No local ARC-AGI-3 environments found")

    catalog = {
        "game_ids": ids,
        "canonical_game_ids": sorted({canonical_game_id(x) for x in ids}),
    }
    catalog["catalog_sha256"] = hashlib.sha256(
        json.dumps(catalog["game_ids"], separators=(",",":"), sort_keys=True).encode()
    ).hexdigest()

    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        f.write(json.dumps({"_meta": catalog}) + "\n")
        for gid in ids:
            for seed in seeds:
                for row in collect_game(arc, gid, seed, args.budget):
                    f.write(json.dumps(row, separators=(",",":")) + "\n")
    print(json.dumps({"status":"COLLECTED","output":str(args.output),**catalog}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
