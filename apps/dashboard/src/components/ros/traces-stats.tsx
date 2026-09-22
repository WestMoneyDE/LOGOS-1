"use client";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";

const dayCfg = { done: { label: "done", color: "#059669" }, failed: { label: "failed", color: "#e11d48" }, stopped: { label: "stopped", color: "#71717a" }, running: { label: "running", color: "#0284c7" }, waiting_quota: { label: "waiting quota", color: "#d97706" } } satisfies ChartConfig;
const tokCfg = { input: { label: "input", color: "#0284c7" }, cache: { label: "cache", color: "#94a3b8" }, output: { label: "output", color: "#7c3aed" } } satisfies ChartConfig;
const oneCfg = { v: { label: "value", color: "#0f766e" } } satisfies ChartConfig;

function Card({ title, n, children }: { title: string; n: string; children: React.ReactNode }) {
  return <div className="border border-border p-3"><div className="mb-1 flex items-baseline justify-between"><span className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{title}</span><span className="font-mono text-[0.6rem] text-muted-foreground">{n}</span></div>{children}</div>;
}

export function TracesStats({ s, labels }: { s: any; labels: { perDay: string; tokens: string; phases: string; tools: string; theses: string } }) {
  return (
    <div className="grid gap-3 xl:grid-cols-2" aria-label="trace statistics">
      <Card title={labels.perDay} n={`n = ${s.n_runs} runs`}><ChartContainer config={dayCfg} className="h-44 w-full"><BarChart data={s.per_day} accessibilityLayer><CartesianGrid vertical={false} /><XAxis dataKey="day" fontSize={10} tickLine={false} axisLine={false} /><YAxis allowDecimals={false} width={24} fontSize={10} /><ChartTooltip content={<ChartTooltipContent />} /><ChartLegend content={<ChartLegendContent />} />{(Object.keys(dayCfg) as (keyof typeof dayCfg)[]).map((k) => <Bar key={k} dataKey={k} stackId="a" fill={`var(--color-${k})`} />)}</BarChart></ChartContainer></Card>
      <Card title={labels.tokens} n={`n = ${s.tokens.length} · ${s.note}`}><ChartContainer config={tokCfg} className="h-44 w-full"><BarChart data={s.tokens} accessibilityLayer><CartesianGrid vertical={false} /><XAxis dataKey="run" fontSize={9} tickLine={false} axisLine={false} /><YAxis width={40} fontSize={10} /><ChartTooltip content={<ChartTooltipContent />} /><ChartLegend content={<ChartLegendContent />} />{(Object.keys(tokCfg) as (keyof typeof tokCfg)[]).map((k) => <Bar key={k} dataKey={k} stackId="t" fill={`var(--color-${k})`} />)}</BarChart></ChartContainer></Card>
      <Card title={labels.phases} n={`Latenz Ø ${typeof s.latency.value === "number" ? s.latency.value.toFixed(1) + " s" : s.latency.value} (${s.latency.method}, n=${s.latency.n})`}><ChartContainer config={oneCfg} className="h-44 w-full"><BarChart data={s.phases.map((p: any) => ({ phase: `${p.phase} (n=${p.n})`, v: p.mean_s }))} accessibilityLayer layout="vertical"><CartesianGrid horizontal={false} /><XAxis type="number" fontSize={10} /><YAxis type="category" dataKey="phase" width={120} fontSize={10} /><ChartTooltip content={<ChartTooltipContent />} /><Bar dataKey="v" fill="var(--color-v)" /></BarChart></ChartContainer></Card>
      <Card title={labels.tools} n={`n = ${s.tools.reduce((a: number, t: any) => a + t.n, 0)} calls`}><ChartContainer config={oneCfg} className="h-44 w-full"><BarChart data={s.tools.map((t: any) => ({ phase: t.tool, v: t.n }))} accessibilityLayer layout="vertical"><CartesianGrid horizontal={false} /><XAxis type="number" allowDecimals={false} fontSize={10} /><YAxis type="category" dataKey="phase" width={90} fontSize={10} /><ChartTooltip content={<ChartTooltipContent />} /><Bar dataKey="v" fill="var(--color-v)" /></BarChart></ChartContainer></Card>
      <Card title={labels.theses} n={`n = ${s.per_thesis.length}`}><ChartContainer config={oneCfg} className="h-44 w-full"><BarChart data={s.per_thesis.map((t: any) => ({ phase: t.thesis, v: t.runs }))} accessibilityLayer><CartesianGrid vertical={false} /><XAxis dataKey="phase" fontSize={9} tickLine={false} axisLine={false} /><YAxis allowDecimals={false} width={24} fontSize={10} /><ChartTooltip content={<ChartTooltipContent />} /><Bar dataKey="v" fill="var(--color-v)" /></BarChart></ChartContainer></Card>
    </div>
  );
}
