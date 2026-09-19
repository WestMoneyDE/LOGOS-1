"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bar, BarChart, CartesianGrid, ErrorBar, XAxis, YAxis } from "recharts";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { errText, rosPost } from "@/lib/ros";

type Row = { metric: string; mode: string; status: string; n: number | null; k?: number; value: number | string | null; ci95: [number, number] | null; recorded_at: string | null };
const cfg = { value: { label: "rate", color: "#0284c7" } } satisfies ChartConfig;

function Actions({ suite, labels }: { suite: string; labels: { run: string; freeze: string; approve: string } }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  const act = async (path: string, body: any = {}) => { const r = await rosPost(path, body); setMsg(r.ok ? `${path.split("/").pop()}: ${r.data.state ?? r.data.status ?? r.data.snapshot_id ?? "ok"}` : errText(r)); if (r.ok) router.refresh(); };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button size="sm" variant="outline" onClick={() => act(`/api/ros/benchmarks/${suite}/run`)}>{labels.run}</Button>
      <Button size="sm" variant="outline" onClick={() => act(`/api/ros/benchmarks/${suite}/snapshot`, { mode: "DETERMINISTIC" })}>🔒 {labels.freeze}</Button>
      <Button size="sm" variant="ghost" onClick={() => act(`/api/ros/benchmarks/${suite}/approve`)}>🔒 {labels.approve}</Button>
      {msg && <span className="font-mono text-xs text-muted-foreground" role="status">{msg}</span>}
    </div>
  );
}

export function SuiteCard({ suite, data, status, labels }: { suite: string; data: { rows: Row[]; gates: { verdict: string; failures: any[] }; track: string; fixtures: string[] }; status: string; labels: { run: string; freeze: string; approve: string; gates: string } }) {
  const det = data.rows.filter((r) => r.mode === "DETERMINISTIC" && r.status === "OK");
  const chart = det.map((r) => ({ metric: r.metric, value: Number(r.value), err: r.ci95 ? [Number(r.value) - r.ci95[0], r.ci95[1] - Number(r.value)] : [0, 0], n: r.n }));
  return (
    <section className="border border-border p-3" data-suite={suite}>
      <header className="flex flex-wrap items-baseline justify-between gap-2"><h3 className="font-mono text-sm font-semibold">{suite}</h3><span className={cn("font-mono text-[0.65rem]", status === "APPROVED" ? "text-emerald-700" : "text-amber-700")}>{status}</span></header>
      <p className="mt-1 text-[0.65rem] text-muted-foreground">track {data.track} · fixtures: {data.fixtures.join(", ")}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs"><span className="font-semibold">{labels.gates}:</span><span className={cn("font-mono", data.gates.verdict === "PASS" ? "text-emerald-700" : "text-rose-700")}>{data.gates.verdict}</span>{data.gates.failures.map((f: any) => <span key={f.id} className="font-mono text-rose-700">{f.id} {f.metric}={String(f.observed)}</span>)}</div>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-xs"><thead className="bg-muted/50 text-left text-[0.6rem] uppercase tracking-widest text-muted-foreground"><tr><th className="px-2 py-1">Modus</th><th className="px-2 py-1">Metrik</th><th className="px-2 py-1">N</th><th className="px-2 py-1">Wert</th><th className="px-2 py-1">95 %-KI (Wilson)</th><th className="px-2 py-1">Stand</th></tr></thead>
          <tbody>{data.rows.map((r) => <tr key={r.mode + r.metric} className="border-t border-border"><td className="px-2 py-1 font-mono">{r.mode}</td><td className="px-2 py-1 font-mono">{r.metric}</td><td className="px-2 py-1 font-mono">{r.n ?? "—"}</td><td className={cn("px-2 py-1 font-mono", r.status !== "OK" && "text-muted-foreground")}>{r.status === "OK" ? (typeof r.value === "number" ? r.value.toFixed(3) : String(r.value)) : r.status}</td><td className="px-2 py-1 font-mono">{r.ci95 ? `[${r.ci95[0].toFixed(3)}, ${r.ci95[1].toFixed(3)}]` : "—"}</td><td className="px-2 py-1 font-mono text-muted-foreground">{r.recorded_at ? String(r.recorded_at).slice(0, 16).replace("T", " ") : "—"}</td></tr>)}</tbody></table>
      </div>
      {chart.length > 0 && (
        <div className="mt-2">
          <div className="mb-1 text-[0.6rem] text-muted-foreground">n = {chart.map((c) => c.n).join(", ")} · 95 %-KI Wilson · ros-stats/1 · Modus DETERMINISTIC (nicht mit Agenten-Modi vergleichbar)</div>
          <ChartContainer config={cfg} className="h-32 w-full">
            <BarChart data={chart} accessibilityLayer><CartesianGrid vertical={false} /><XAxis dataKey="metric" fontSize={10} tickLine={false} axisLine={false} /><YAxis domain={[0, 1]} width={28} fontSize={10} /><ChartTooltip content={<ChartTooltipContent />} /><Bar dataKey="value" fill="var(--color-value)"><ErrorBar dataKey="err" width={4} strokeWidth={1} /></Bar></BarChart>
          </ChartContainer>
        </div>)}
      <div className="mt-3"><Actions suite={suite} labels={labels} /></div>
    </section>
  );
}
