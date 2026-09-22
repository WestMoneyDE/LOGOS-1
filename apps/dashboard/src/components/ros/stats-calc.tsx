"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";

const PRESETS: Record<string, string> = { wilson: '{"k": 45, "n": 60}', newcombe: '{"k1": 45, "n1": 60, "k2": 30, "n2": 60}', bootstrap_mean: '{"xs": [1.2, 0.8, 1.5, 1.1, 0.9], "reps": 2000, "seed": 0}', cohens_h: '{"p1": 0.75, "p2": 0.5}', pp_delta: '{"p_new": 0.75, "p_old": 0.5}', relative_change: '{"new": 12, "old": 10}', error_reduction: '{"err_new": 0.1, "err_old": 0.25}', efficiency: '{"successes": 40, "cost": 120}', confusion: '{"tp": 40, "fp": 3, "fn": 5, "tn": 52}', calibration: '{"pairs": [[0.9, 1], [0.8, 1], [0.3, 0], [0.6, 1], [0.2, 0]], "bins": 5}', mcnemar_exact: '{"b": 7, "c": 2}' };

export function StatsCalc({ methods, label }: { methods: Record<string, string[]>; label: string }) {
  const [method, setMethod] = useState("wilson"); const [args, setArgs] = useState(PRESETS.wilson); const [out, setOut] = useState<any>(null); const [err, setErr] = useState<string | null>(null);
  return (
    <div className="max-w-3xl">
      <div className="flex flex-wrap items-center gap-2">
        <select aria-label="method" className="border border-border bg-background px-2 py-1 font-mono text-xs" value={method} onChange={(e) => { setMethod(e.target.value); setArgs(PRESETS[e.target.value] ?? "{}"); }}>{Object.keys(methods).map((m) => <option key={m}>{m}</option>)}</select>
        <span className="font-mono text-[0.65rem] text-muted-foreground">args: {(methods[method] ?? []).join(", ")}</span>
      </div>
      <textarea aria-label="args" className="mt-2 h-20 w-full border border-border bg-background p-2 font-mono text-xs" value={args} onChange={(e) => setArgs(e.target.value)} />
      <Button size="sm" className="mt-2" onClick={async () => { try { const r = await fetch(`${API}/api/ros/statistics/compute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ method, args: JSON.parse(args) }) }); const d = await r.json(); if (r.ok) { setOut(d); setErr(null); } else { setErr(JSON.stringify(d.detail)); setOut(null); } } catch (e: any) { setErr(String(e)); } }}>{label}</Button>
      {err && <p className="mt-2 font-mono text-xs text-rose-700" role="status">{err}</p>}
      {out && <pre className="mt-2 max-h-80 overflow-auto border border-border bg-muted/20 p-2 font-mono text-[0.7rem]" role="status">{JSON.stringify(out, null, 1)}</pre>}
    </div>
  );
}
