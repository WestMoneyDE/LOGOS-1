"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bar, BarChart, CartesianGrid, ErrorBar, XAxis, YAxis } from "recharts";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { API } from "@/lib/api";
import { errText, rosPost } from "@/lib/ros";

const cfg = { rate: { label: "Trefferquote", color: "#0284c7" } } satisfies ChartConfig;
const VERDICT_TONE: Record<string, string> = { SUPPORTED: "text-emerald-700", FALSIFIED: "text-rose-700", INCONCLUSIVE: "text-amber-700", INVALID_MEASUREMENT: "text-orange-700" };

export function MeasurementView({ initial, labels }: { initial: any; labels: Record<string, string> }) {
  const router = useRouter(); const [d, setD] = useState(initial); const [msg, setMsg] = useState<string | null>(null);
  const m = d.measurement; const running = m.state === "running";
  useEffect(() => {
    if (!running) return;
    const id = setInterval(async () => { try { const r = await fetch(`${API}/api/ros/measurements/${m.measurement_id}`); if (r.ok) setD(await r.json()); } catch {} }, 2500);
    return () => clearInterval(id);
  }, [running, m.measurement_id]);
  const rates = Object.values(d.rates ?? {}) as any[];
  const chart = rates.filter((r) => typeof r.rate === "number").map((r) => ({ arm: `${r.arm} (n=${r.n_scored})`, rate: r.rate, err: r.ci95 ? [r.rate - r.ci95[0], r.ci95[1] - r.rate] : [0, 0] }));
  const summary = m.summary ?? {}; const proposal = summary.proposal;
  const decide = async (verdict: string) => { const r = await rosPost(`/api/ros/measurements/${m.measurement_id}/verdict`, { verdict, reason: "Leitstand" }); setMsg(r.ok ? `${verdict} · ${r.data.draft.path}` : errText(r)); if (r.ok) router.refresh(); };
  const pct = Math.round((d.progress.done / Math.max(1, d.progress.planned)) * 100);
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-3">
        <span className={cn("font-mono text-xs", running ? "text-emerald-700" : "text-muted-foreground")}>{running ? "● läuft" : m.state}</span>
        <div className="h-2 w-64 bg-muted" aria-label="progress"><div className="h-2 bg-foreground" style={{ width: `${pct}%` }} /></div>
        <span className="font-mono text-xs">{d.progress.done} / {d.progress.planned} {labels.data_points}</span>
        {m.stop_reason && <span className="font-mono text-xs text-amber-700">Stopp: {m.stop_reason}</span>}
        {m.invalid_reason && <span className="font-mono text-xs text-orange-700">ungültig: {m.invalid_reason}</span>}
      </div>
      <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground">Prereg {String(m.prereg_hash).slice(0, 12)} · Datensatz {String(m.dataset_hash).slice(0, 12)} · Prompts {String(m.prompt_bundle_hash).slice(0, 12)} · Pin {m.model_pin} · Lauf <Link className="underline" href={`/runs/${m.run_id}`}>{m.run_id}</Link></p>

      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        <section className="border border-border p-3">
          <div className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{labels.rates}</div>
          {chart.length === 0 ? <p className="mt-1 text-xs text-muted-foreground">—</p> : (
            <ChartContainer config={cfg} className="mt-2 h-40 w-full"><BarChart data={chart} accessibilityLayer><CartesianGrid vertical={false} /><XAxis dataKey="arm" fontSize={10} tickLine={false} axisLine={false} /><YAxis domain={[0, 1]} width={32} fontSize={10} /><ChartTooltip content={<ChartTooltipContent />} /><Bar dataKey="rate" fill="var(--color-rate)"><ErrorBar dataKey="err" width={4} strokeWidth={1} /></Bar></BarChart></ChartContainer>)}
          <table className="mt-2 w-full text-xs"><thead className="text-left text-[0.6rem] uppercase tracking-widest text-muted-foreground"><tr><th>Arm</th><th>Treffer</th><th>bewertet</th><th>fehlend</th><th>Quote</th><th>95 %-KI</th></tr></thead>
            <tbody>{rates.map((r: any) => <tr key={r.arm} className="border-t border-border"><td className="font-mono">{r.arm}</td><td>{r.k}</td><td>{r.n_scored}</td><td>{r.missing}</td><td className="font-mono">{typeof r.rate === "number" ? r.rate.toFixed(3) : r.rate}</td><td className="font-mono">{r.ci95 ? `[${r.ci95[0].toFixed(3)}, ${r.ci95[1].toFixed(3)}]` : "—"}</td></tr>)}</tbody></table>
          <p className="mt-1 text-[0.6rem] text-muted-foreground">{labels.missing_note}</p>
        </section>

        <section className="border border-border p-3">
          <div className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{labels.proposal}</div>
          {proposal ? (<>
            <p className={cn("mt-1 font-mono text-sm font-semibold", VERDICT_TONE[proposal.verdict])}>{proposal.verdict}</p>
            <p className="mt-1 text-xs">{proposal.why}</p>
            <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground">{labels.frozen_rule}: {JSON.stringify(proposal.rule)}{summary.primary_metric ? ` · ${summary.primary_metric} (${summary.scorer})` : ""}</p>
            {m.state !== "running" && (
              <div className="mt-3">
                <p className="text-xs text-muted-foreground">{labels.decide_hint}</p>
                <div className="mt-1 flex flex-wrap gap-2">{["SUPPORTED", "FALSIFIED", "INCONCLUSIVE", "INVALID_MEASUREMENT"].map((v) => <Button key={v} size="sm" variant={v === proposal.verdict ? "default" : "outline"} onClick={() => decide(v)}>🔒 {v}</Button>)}</div>
              </div>)}
          </>) : <p className="mt-1 text-xs text-muted-foreground">—</p>}
          {msg && <p className="mt-2 font-mono text-xs" role="status">{msg}</p>}
        </section>
      </div>

      <section className="mt-3 border border-border">
        <div className="border-b border-border px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{labels.items} ({d.items.length})</div>
        <div className="max-h-80 overflow-y-auto">
          <table className="w-full text-xs"><thead className="sticky top-0 bg-muted/60 text-left text-[0.6rem] uppercase tracking-widest text-muted-foreground"><tr><th className="px-2 py-1">#</th><th className="px-2 py-1">Item</th><th className="px-2 py-1">Arm</th><th className="px-2 py-1">Status</th><th className="px-2 py-1">Bewertung</th><th className="px-2 py-1">Antwort</th><th className="px-2 py-1">s</th></tr></thead>
            <tbody>{d.items.map((i: any) => <tr key={i.row_id} className="border-t border-border align-top"><td className="px-2 py-1 font-mono">{i.invocation}</td><td className="px-2 py-1 font-mono">{i.item_id}</td><td className="px-2 py-1 font-mono">{i.arm}</td><td className={cn("px-2 py-1 font-mono", i.status !== "OK" && "text-rose-700")}>{i.status}</td><td className={cn("px-2 py-1 font-mono", i.score === true ? "text-emerald-700" : i.score === false ? "text-rose-700" : "text-muted-foreground")}>{i.score === true ? "Treffer" : i.score === false ? "daneben" : "nicht bewertbar"}</td><td className="max-w-md px-2 py-1"><span className="line-clamp-2 break-words">{i.answer}</span></td><td className="px-2 py-1 font-mono">{i.latency_s?.toFixed?.(1)}</td></tr>)}</tbody></table>
        </div>
      </section>
    </div>
  );
}
