#!/usr/bin/env python3
"""Offline WMR-R2 evaluator. Imports neither arc_agi nor arcengine."""
from __future__ import annotations
import argparse, hashlib, json, random, time
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch
from torch import nn

COLORS = 16
ACTION_SLOTS = 8

def load_rows(path: Path):
    meta, rows = {}, []
    with path.open() as f:
        for line in f:
            obj = json.loads(line)
            if "_meta" in obj:
                meta = obj["_meta"]
            else:
                rows.append(obj)
    return meta, rows

def to_frame(x):
    a = np.asarray(x, dtype=np.int64)
    if a.ndim != 2:
        raise ValueError(f"Expected 2D frame, got {a.shape}")
    return a

def changed_metrics(pre, truth, pred):
    changed = truth != pre
    pred_changed = pred != pre
    tp = np.logical_and(changed, pred_changed).sum()
    fp = np.logical_and(~changed, pred_changed).sum()
    fn = np.logical_and(changed, ~pred_changed).sum()
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    changed_acc = float((pred[changed] == truth[changed]).mean()) if changed.any() else 1.0
    return float(f1), changed_acc

def action_tensor(row, h, w):
    aid = int(row.get("action_id", 0))
    out = np.zeros((ACTION_SLOTS + 3, h, w), dtype=np.float32)
    if 0 <= aid < ACTION_SLOTS:
        out[aid] = 1.0
    data = row.get("action_data") or {}
    x = int(data.get("x", -1)) if data.get("x") is not None else -1
    y = int(data.get("y", -1)) if data.get("y") is not None else -1
    if 0 <= x < w and 0 <= y < h:
        out[ACTION_SLOTS, y, x] = 1.0
    out[ACTION_SLOTS + 1] = (x / max(1, w - 1)) if x >= 0 else -1.0
    out[ACTION_SLOTS + 2] = (y / max(1, h - 1)) if y >= 0 else -1.0
    return out

def encode(row):
    pre = to_frame(row["pre_frame"])
    h, w = pre.shape
    onehot = np.eye(COLORS, dtype=np.float32)[np.clip(pre,0,COLORS-1)]
    onehot = np.transpose(onehot, (2,0,1))
    x = np.concatenate([onehot, action_tensor(row,h,w)], axis=0)
    y = to_frame(row["post_frame"])
    return torch.from_numpy(x), torch.from_numpy(y)

class TinyConv(nn.Module):
    def __init__(self, hidden=16):
        super().__init__()
        cin = COLORS + ACTION_SLOTS + 3
        self.net = nn.Sequential(
            nn.Conv2d(cin, hidden, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(hidden, hidden, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(hidden, COLORS, 1),
        )
    def forward(self, x):
        return self.net(x)

def transition_loss(model, batch, device):
    xs, ys = zip(*(encode(r) for r in batch))
    x = torch.stack(xs).to(device)
    y = torch.stack(ys).long().to(device)
    return nn.functional.cross_entropy(model(x), y)

def predict(model, row, device):
    x, y = encode(row)
    x = x.unsqueeze(0).to(device)
    truth = y.numpy()
    t0 = time.perf_counter()
    with torch.no_grad():
        logits = model(x)
        ce = nn.functional.cross_entropy(
            logits, y.unsqueeze(0).long().to(device)
        ).item()
        pred = logits.argmax(1)[0].cpu().numpy()
    ms = (time.perf_counter() - t0) * 1000
    pre = to_frame(row["pre_frame"])
    f1, chacc = changed_metrics(pre, truth, pred)
    return {
        "cross_entropy": float(ce),
        "pixel_accuracy": float((pred == truth).mean()),
        "changed_pixel_f1": f1,
        "changed_pixel_accuracy": chacc,
        "exact_frame_match": int(np.array_equal(pred, truth)),
        "prediction_ms": ms,
    }

def stable_seed(game_id, seed, arm):
    h = hashlib.sha256(f"{game_id}|{seed}|{arm}".encode()).hexdigest()
    return int(h[:8], 16)

class ProgramCatalog:
    """Diagnostic-only fixed executable transform catalog."""
    def __init__(self):
        self.error = defaultdict(lambda: defaultdict(float))
        self.count = defaultdict(lambda: defaultdict(int))
        self.names = [
            "identity","shift_x_p1","shift_x_m1","shift_y_p1","shift_y_m1",
            "shift_x_p2","shift_x_m2","shift_y_p2","shift_y_m2",
            "rot90","rot180","rot270","flip_x","flip_y",
        ]
    def apply(self, name, a):
        if name == "identity": return a.copy()
        if name == "shift_x_p1": return np.roll(a,1,axis=1)
        if name == "shift_x_m1": return np.roll(a,-1,axis=1)
        if name == "shift_y_p1": return np.roll(a,1,axis=0)
        if name == "shift_y_m1": return np.roll(a,-1,axis=0)
        if name == "shift_x_p2": return np.roll(a,2,axis=1)
        if name == "shift_x_m2": return np.roll(a,-2,axis=1)
        if name == "shift_y_p2": return np.roll(a,2,axis=0)
        if name == "shift_y_m2": return np.roll(a,-2,axis=0)
        if name == "rot90": return np.rot90(a,1).copy()
        if name == "rot180": return np.rot90(a,2).copy()
        if name == "rot270": return np.rot90(a,3).copy()
        if name == "flip_x": return np.fliplr(a).copy()
        if name == "flip_y": return np.flipud(a).copy()
        raise KeyError(name)
    def key(self,row):
        d=row.get("action_data") or {}
        x=d.get("x",-1); y=d.get("y",-1)
        return (
            int(row.get("action_id",0)),
            int(x) if x is not None else -1,
            int(y) if y is not None else -1,
        )
    def predict(self,row):
        k=self.key(row)
        scored=[]
        for n in self.names:
            c=self.count[k][n]
            e=self.error[k][n] / max(1,c)
            scored.append((e if c else (0.0 if n=="identity" else 1.0), n))
        name=min(scored)[1]
        return self.apply(name,to_frame(row["pre_frame"])),name
    def update(self,row):
        k=self.key(row)
        pre=to_frame(row["pre_frame"])
        truth=to_frame(row["post_frame"])
        for n in self.names:
            p=self.apply(n,pre)
            self.error[k][n]+=float((p!=truth).mean())
            self.count[k][n]+=1

def eval_program_catalog(seq):
    cat=ProgramCatalog()
    out=[]
    for row in seq:
        t0=time.perf_counter()
        pred,name=cat.predict(row)
        ms=(time.perf_counter()-t0)*1000
        truth=to_frame(row["post_frame"])
        pre=to_frame(row["pre_frame"])
        f1,chacc=changed_metrics(pre,truth,pred)
        out.append({
            **{k:row[k] for k in ["game_id","game_fold","seed","step"]},
            "arm":"PROGRAM_CATALOG_REPAIR_DIAGNOSTIC",
            "cross_entropy":None,
            "pixel_accuracy":float((pred==truth).mean()),
            "changed_pixel_f1":f1,
            "changed_pixel_accuracy":chacc,
            "exact_frame_match":int(np.array_equal(pred,truth)),
            "prediction_ms":ms,
            "update_ms":0.0,
            "catalog_program":name,
        })
        cat.update(row)
    return out

def eval_neural(seq, arm, device):
    torch.manual_seed(123456)
    np.random.seed(123456)
    model=TinyConv(hidden=16).to(device)
    opt=torch.optim.Adam(model.parameters(),lr=1e-3)
    buffer=[]
    weights=[]
    rng=random.Random(stable_seed(seq[0]["game_id"],seq[0]["seed"],arm))
    out=[]
    for row in seq:
        metrics=predict(model,row,device)
        priority=max(1e-3, metrics["cross_entropy"])
        buffer.append(row)
        weights.append(priority)
        bs=min(8,len(buffer))
        if arm=="RECENT_ONLY_GENERIC":
            batch=[row for _ in range(bs)]
        elif arm=="UNIFORM_REPLAY_GENERIC":
            batch=[buffer[rng.randrange(len(buffer))] for _ in range(bs)]
        elif arm=="COUNTEREXAMPLE_PRIORITY_GENERIC":
            idx=rng.choices(range(len(buffer)),weights=weights,k=bs)
            batch=[buffer[i] for i in idx]
        else:
            raise ValueError(arm)
        t0=time.perf_counter()
        model.train()
        opt.zero_grad(set_to_none=True)
        loss=transition_loss(model,batch,device)
        loss.backward()
        opt.step()
        update_ms=(time.perf_counter()-t0)*1000
        out.append({
            **{k:row[k] for k in ["game_id","game_fold","seed","step"]},
            "arm":arm,
            **metrics,
            "update_ms":update_ms,
            "train_loss":float(loss.item()),
        })
    return out, sum(p.numel() for p in model.parameters())

def summarize(rows):
    groups=defaultdict(list)
    for r in rows:
        groups[(r["arm"],int(r["game_fold"]))].append(r)
    out=[]
    for (arm,fold),g in sorted(groups.items()):
        vals=lambda k:[x[k] for x in g if x.get(k) is not None]
        out.append({
            "arm":arm,"fold":fold,"n":len(g),
            "mean_cross_entropy":float(np.mean(vals("cross_entropy"))) if vals("cross_entropy") else None,
            "mean_pixel_accuracy":float(np.mean(vals("pixel_accuracy"))),
            "mean_changed_pixel_f1":float(np.mean(vals("changed_pixel_f1"))),
            "mean_changed_pixel_accuracy":float(np.mean(vals("changed_pixel_accuracy"))),
            "exact_frame_match_rate":float(np.mean(vals("exact_frame_match"))),
        })
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--device",default="cpu")
    args=ap.parse_args()

    if "environment_files" in str(args.input).lower():
        raise SystemExit(
            "RUN_INVALID_SOURCE_LEAKAGE: evaluator input path must not be environment_files"
        )
    meta,rows=load_rows(args.input)
    if not rows:
        raise SystemExit("No transitions")
    required={
        "game_id","game_fold","seed","step","pre_frame","post_frame",
        "action_id","action_data",
    }
    miss=required-set(rows[0])
    if miss:
        raise SystemExit(f"Missing fields: {sorted(miss)}")

    seqs=defaultdict(list)
    for r in rows:
        seqs[(r["game_id"],int(r["seed"]))].append(r)

    all_results=[]
    params={}
    for _,seq in sorted(seqs.items()):
        seq=sorted(seq,key=lambda r:int(r["step"]))
        all_results += eval_program_catalog(seq)
        for arm in [
            "RECENT_ONLY_GENERIC",
            "UNIFORM_REPLAY_GENERIC",
            "COUNTEREXAMPLE_PRIORITY_GENERIC",
        ]:
            rr,p=eval_neural(seq,arm,args.device)
            all_results += rr
            params[arm]=p

    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w") as f:
        for r in all_results:
            f.write(json.dumps(r,separators=(",",":"))+"\n")

    report={
        "meta":meta,
        "parameter_counts":params,
        "confirmatory_fold":0,
        "summary":summarize(all_results),
        "scientific_note":(
            "Program catalog diagnostic is non-promoting; primary causal pair is "
            "uniform vs counterexample-priority generic replay."
        ),
    }
    args.output.with_suffix(".summary.json").write_text(
        json.dumps(report,indent=2)+"\n"
    )
    print(json.dumps({
        "status":"EVALUATED",
        "rows":len(all_results),
        "output":str(args.output),
    },indent=2))

if __name__=="__main__":
    main()
