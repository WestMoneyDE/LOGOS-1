"use client";
import { useState } from "react";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import { rosPost, errText } from "@/lib/ros";

const TONE: Record<string, string> = { worktree: "bg-violet-500", packet: "bg-violet-700", claude: "bg-amber-500", verify: "bg-emerald-600", prior_art_requested: "bg-sky-500" };

export function Waterfall({ bars }: { bars: { phase: string; start_s: number; end_s: number; duration_s: number }[] }) {
  const total = Math.max(0.001, ...bars.map((b) => b.end_s));
  if (!bars.length) return <p className="text-xs text-muted-foreground">—</p>;
  return (
    <ol className="flex flex-col gap-1" aria-label="waterfall">
      {bars.map((b) => (
        <li key={b.phase + b.start_s} className="grid grid-cols-[9rem_1fr_5rem] items-center gap-2 text-xs">
          <span className="font-mono">{b.phase}</span>
          <span className="relative h-4 bg-muted"><span className={cn("absolute top-0 h-4", TONE[b.phase] ?? "bg-foreground")} style={{ left: `${(b.start_s / total) * 100}%`, width: `${Math.max(0.5, ((b.end_s - b.start_s) / total) * 100)}%` }} /></span>
          <span className="text-right font-mono text-muted-foreground">{b.duration_s.toFixed(2)} s</span>
        </li>))}
    </ol>
  );
}

export function Rescore({ runId, label, hint }: { runId: string; label: string; hint: string }) {
  const [out, setOut] = useState<any>(null); const [err, setErr] = useState<string | null>(null);
  return (
    <div>
      <div className="flex items-center gap-2"><Button size="sm" variant="outline" onClick={async () => { const r = await rosPost(`/api/ros/runs/${runId}/rescore`, {}); if (r.ok) { setOut(r.data); setErr(null); } else { setErr(errText(r)); setOut(null); } }}>{label}</Button><span className="text-xs text-muted-foreground">{hint}</span></div>
      {err && <p className="mt-1 font-mono text-xs text-rose-700" role="status">{err}</p>}
      {out && <pre className="mt-2 max-h-72 overflow-auto border border-border bg-muted/20 p-2 font-mono text-[0.7rem]" role="status">{JSON.stringify(out, null, 1)}</pre>}
    </div>
  );
}

export function MlflowFetch({ runId }: { runId: string }) {
  const [ml, setMl] = useState<any>(null);
  return (
    <div>
      <Button size="sm" variant="ghost" onClick={async () => { const r = await fetch(`${API}/api/ros/runs/${runId}/trace?fetch_mlflow=true`); const d = await r.json(); setMl(d.mlflow ?? { error: "no mlflow run" }); }}>MLflow params/metrics laden</Button>
      {ml && <pre className="mt-2 max-h-72 overflow-auto border border-border bg-muted/20 p-2 font-mono text-[0.7rem]">{JSON.stringify(ml, null, 1)}</pre>}
    </div>
  );
}
