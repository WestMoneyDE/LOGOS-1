"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { errText, rosPost } from "@/lib/ros";

const TONE: Record<string, string> = { VALIDATED: "border-l-emerald-600", FALSIFIED: "border-l-rose-600", DRAFT: "border-l-amber-500" };
export function RepoChain({ orders, label, hint }: { orders: any[]; label: string; hint: string }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-2"><Button size="sm" variant="outline" onClick={async () => { const r = await rosPost("/api/ros/repo-orders/import", {}); setMsg(r.ok ? `${r.data.documents} Dokumente · neu ${r.data.new} · aktualisiert ${r.data.updated} · Kanten ${r.data.edges_added}` : errText(r)); if (r.ok) router.refresh(); }}>{label}</Button>{msg && <span className="font-mono text-xs text-muted-foreground" role="status">{msg}</span>}</div>
      <p className="mb-2 text-xs text-muted-foreground">{hint}</p>
      <ol className="grid gap-1 text-xs md:grid-cols-2" aria-label="repository chain">{orders.map((o: any) => <li key={o.work_order_id} className={cn("border border-border border-l-4 px-2 py-1", TONE[o.state] ?? "border-l-border")}><span className="font-mono font-semibold">{o.work_order_id.replace("REPO:", "")}</span> <span className="font-mono text-muted-foreground">{o.state}</span>{o.origin?.closed && <span className="text-muted-foreground"> · {String(o.origin.closed).slice(0, 10)}</span>}{o.origin?.verdict && <span className="block truncate font-mono text-[0.65rem] text-muted-foreground">{o.origin.verdict}</span>}{o.thesis_id && <span className="block font-mono text-[0.65rem]">↳ {o.thesis_id}</span>}</li>)}</ol>
    </div>
  );
}
