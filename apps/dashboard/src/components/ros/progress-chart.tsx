"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { errText, rosPost } from "@/lib/ros";

const cfg = { supported_or_partial: { label: "supported / partial", color: "#059669" }, falsified: { label: "falsified", color: "#e11d48" }, invalid_measurement: { label: "invalid measurement", color: "#ea580c" }, agent_runs: { label: "agent runs", color: "#7c3aed" } } satisfies ChartConfig;

export function ProgressChart({ series }: { series: any[] }) {
  const data = series.map((m) => ({ month: m.month, ...m.verdicts, agent_runs: m.agent_runs }));
  return (
    <div className="border border-border p-3">
      <div className="mb-1 text-[0.6rem] text-muted-foreground">Zählungen je Monat (Closures nach Verdict-Klasse, Agenten-Läufe) · keine Prozentwerte ohne eingefrorene Vergleichsbasis</div>
      <ChartContainer config={cfg} className="h-48 w-full"><BarChart data={data} accessibilityLayer><CartesianGrid vertical={false} /><XAxis dataKey="month" fontSize={11} tickLine={false} axisLine={false} /><YAxis allowDecimals={false} width={24} fontSize={11} /><ChartTooltip content={<ChartTooltipContent />} /><ChartLegend content={<ChartLegendContent />} />{(Object.keys(cfg) as (keyof typeof cfg)[]).map((k) => <Bar key={k} dataKey={k} fill={`var(--color-${k})`} />)}</BarChart></ChartContainer>
    </div>
  );
}

export function FreezeMonth({ month, label }: { month: string; label: string }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  return <span className="inline-flex items-center gap-2"><Button size="sm" variant="outline" onClick={async () => { const r = await rosPost(`/api/ros/progress/freeze?month=${month}`, {}); setMsg(r.ok ? `${r.data.month} frozen ${r.data.sha256.slice(0, 12)}` : errText(r)); if (r.ok) router.refresh(); }}>🔒 {label}</Button>{msg && <span className="font-mono text-xs text-muted-foreground" role="status">{msg}</span>}</span>;
}
