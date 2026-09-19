import Link from "next/link";
import { cn } from "cn";

type Node = { work_order_id: string; thesis_id: string | null; state: string; question: string | null; depth: number; ready: boolean };
type Edge = { child: string; parent: string; mandatory: boolean };
const TONE: Record<string, string> = { DRAFT: "stroke-muted-foreground", APPROVED: "stroke-sky-600", READY: "stroke-emerald-600", RUNNING: "stroke-emerald-700", BLOCKED: "stroke-amber-600", FAILED: "stroke-rose-600", VALIDATED: "stroke-emerald-800", FALSIFIED: "stroke-rose-800", SUPERSEDED: "stroke-zinc-400" };

/** Layered SVG: columns by depth (longest parent chain), edges parent → child. Pure render — the API computed depth/ready. */
export function DagView({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  if (!nodes.length) return <p className="text-xs text-muted-foreground">— keine Work Orders —</p>;
  const W = 190, H = 46, GX = 60, GY = 14; const cols: Node[][] = [];
  nodes.forEach((n) => (cols[n.depth] ??= []).push(n));
  const pos = new Map<string, { x: number; y: number }>();
  cols.forEach((c, d) => c.forEach((n, i) => pos.set(n.work_order_id, { x: d * (W + GX), y: i * (H + GY) })));
  const width = cols.length * (W + GX) - GX, height = Math.max(...cols.map((c) => c.length)) * (H + GY) - GY;
  return (
    <div className="overflow-x-auto border border-border p-2">
      <svg width={width + 2} height={height + 2} role="img" aria-label="work order DAG" className="text-xs">
        <defs><marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" className="fill-muted-foreground" /></marker></defs>
        {edges.map((e) => { const p = pos.get(e.parent), c = pos.get(e.child); if (!p || !c) return null; return <line key={`${e.parent}>${e.child}`} x1={p.x + W} y1={p.y + H / 2} x2={c.x} y2={c.y + H / 2} strokeDasharray={e.mandatory ? undefined : "4 3"} className="stroke-muted-foreground" strokeWidth={1} markerEnd="url(#arr)" />; })}
        {nodes.map((n) => { const p = pos.get(n.work_order_id)!; return (
          <g key={n.work_order_id} transform={`translate(${p.x + 1},${p.y + 1})`}>
            <rect width={W} height={H} className={cn("fill-background", TONE[n.state] ?? "stroke-border")} strokeWidth={n.ready ? 2 : 1} />
            <foreignObject width={W} height={H}><div className="flex h-full flex-col justify-center px-2 leading-tight"><Link href="/work-orders" className="truncate font-mono text-[0.65rem] underline">{n.work_order_id}</Link><span className="truncate font-mono text-[0.6rem] text-muted-foreground">{n.state}{n.ready ? " · READY" : ""}{n.thesis_id ? ` · ${n.thesis_id}` : ""}</span></div></foreignObject>
          </g>); })}
      </svg>
    </div>
  );
}
