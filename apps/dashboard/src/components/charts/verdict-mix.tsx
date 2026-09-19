"use client";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";

const config = {
  supported: { label: "supported", color: "#059669" }, validated: { label: "validated / consolidated", color: "#0284c7" }, partial: { label: "partially supported", color: "#d97706" },
  falsified: { label: "falsified", color: "#e11d48" }, invalid: { label: "invalid measurement", color: "#ea580c" }, other: { label: "governance / other", color: "#9ca3af" },
} satisfies ChartConfig;

/** Verdict mix per closure month — counts of deterministic/governed orders; no CI (not a sample-based estimate). */
export function VerdictMix({ data, n }: { data: { month: string; supported: number; partial: number; falsified: number; invalid: number; validated: number; other: number }[]; n: number }) {
  return (
    <div className="border border-border p-3">
      <div className="mb-2 flex items-baseline justify-between"><div className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">Verdict-Mix je Monat</div><div className="text-[0.65rem] text-muted-foreground">n = {n} Closures · Zählung, kein KI (deterministische/governed Orders)</div></div>
      <ChartContainer config={config} className="h-56 w-full">
        <BarChart data={data} accessibilityLayer>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={11} />
          <YAxis allowDecimals={false} width={24} fontSize={11} />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          {(Object.keys(config) as (keyof typeof config)[]).map((k) => <Bar key={k} dataKey={k} stackId="a" fill={`var(--color-${k})`} />)}
        </BarChart>
      </ChartContainer>
    </div>
  );
}
