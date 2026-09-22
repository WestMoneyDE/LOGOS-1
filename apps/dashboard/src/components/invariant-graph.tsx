"use client";
import { useState } from "react";
import { StatusBadge } from "@/components/badges";

type Node = { id: string; label: string; track: string; status: string; class: string };
type Edge = { from: string; to: string; rel: string };
const TRACKS = ["authority", "provenance", "cognitive-provenance", "measurement", "memory", "trajectory", "governance"];
const REL: Record<string, string> = { supports: "#059669", depends_on: "#0284c7", refines: "#7c3aed", contradicts: "#e11d48", falsified_by: "#e11d48", validated_by: "#059669", scoped_by: "#a16207" };

export function InvariantGraph({ nodes, edges, invariants }: { nodes: Node[]; edges: Edge[]; invariants: any[] }) {
  const [sel, setSel] = useState<string | null>(null);
  const W = 1000, rowH = 34, colW = W / TRACKS.length;
  const pos: Record<string, { x: number; y: number }> = {};
  TRACKS.forEach((t, ci) => nodes.filter((n) => n.track === t).forEach((n, ri) => { pos[n.id] = { x: ci * colW + colW / 2, y: 40 + ri * rowH }; }));
  const H = 40 + rowH * Math.max(...TRACKS.map((t) => nodes.filter((n) => n.track === t).length), 1) + 20;
  const inv = invariants.find((i) => i.invariant_id === sel);
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full border border-border bg-background">
        {TRACKS.map((t, ci) => <text key={t} x={ci * colW + colW / 2} y={16} textAnchor="middle" className="fill-muted-foreground" fontSize="10" fontFamily="monospace">{t}</text>)}
        {edges.filter((e) => pos[e.from] && pos[e.to]).map((e, i) => <line key={i} x1={pos[e.from].x} y1={pos[e.from].y} x2={pos[e.to].x} y2={pos[e.to].y} stroke={REL[e.rel] ?? "#888"} strokeWidth={sel && (e.from === sel || e.to === sel) ? 2 : 0.8} opacity={sel ? (e.from === sel || e.to === sel ? 0.9 : 0.12) : 0.45} />)}
        {nodes.map((n) => <g key={n.id} onClick={() => setSel(n.id)} className="cursor-pointer"><circle cx={pos[n.id].x} cy={pos[n.id].y} r={sel === n.id ? 7 : 5} fill={n.status === "FALSIFIED" ? "#e11d48" : n.status === "SUPPORTED" || n.status === "VALIDATED_IN_FIXTURE" ? "#059669" : "#9ca3af"} /><text x={pos[n.id].x + 9} y={pos[n.id].y + 4} fontSize="9" className="fill-foreground">{n.label.length > 34 ? n.label.slice(0, 33) + "…" : n.label}</text></g>)}
      </svg>
      <div className="border border-border p-4 text-sm">
        {inv ? (<>
          <div className="font-mono text-xs text-muted-foreground">{inv.invariant_id} · {inv.class}</div>
          <div className="mt-1 font-heading font-semibold">{inv.statement}</div>
          <div className="mt-2"><StatusBadge status={inv.status} /></div>
          <dl className="mt-3 space-y-2 text-xs">
            <D k="definition">{inv.definition}</D><D k="origin">{inv.origin}</D>
            <D k="evidence">{inv.evidence.join("; ") || "none"}</D><D k="counterexamples">{inv.counterexamples.join(", ") || "none"}</D>
            <D k="experiments">{inv.experiments.join(", ") || "none"}</D><D k="publication relevance">{inv.publication_relevance}</D>
          </dl>
        </>) : <p className="text-muted-foreground">Select an invariant.</p>}
        <div className="mt-4 flex flex-wrap gap-2 text-[0.65rem] text-muted-foreground">{Object.entries(REL).map(([k, c]) => <span key={k}><span style={{ background: c }} className="mr-1 inline-block h-2 w-3 align-middle" />{k}</span>)}</div>
      </div>
    </div>
  );
}
function D({ k, children }: { k: string; children: React.ReactNode }) { return <div><dt className="font-semibold uppercase tracking-widest text-muted-foreground">{k}</dt><dd className="break-words">{children}</dd></div>; }
