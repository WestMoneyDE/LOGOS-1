"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { errText, rosPost, type RosDecision } from "@/lib/ros";

const TONE: Record<string, string> = { WAITING: "border-amber-500", APPROVED: "border-emerald-600", REJECTED: "border-rose-600", DEFERRED: "border-zinc-400", SUPERSEDED: "border-zinc-300" };

export function DecisionCard({ d, labels }: { d: RosDecision; labels: { approve: string; reject: string; defer: string; ifApproved: string; ifRejected: string; blocks: string } }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  const act = async (event: string) => { const r = await rosPost(`/api/ros/decisions/${d.decision_id}/decide`, { event, reason: "ui" }); setMsg(r.ok ? r.data.state : errText(r)); if (r.ok) router.refresh(); };
  const open = d.state === "WAITING" || d.state === "DEFERRED";
  return (
    <article className={cn("border border-border border-l-4 p-3 text-sm", TONE[d.state])} data-decision={d.decision_id}>
      <header className="flex flex-wrap items-baseline justify-between gap-2"><span className="font-mono text-xs">{d.decision_id} · {d.kind} · <span className="font-semibold">{d.state}</span></span><span className="font-mono text-[0.65rem] text-muted-foreground">{d.subject_ref}</span></header>
      <p className="mt-1">{d.why}</p>
      {d.impact && <p className="mt-1 text-xs text-muted-foreground">{d.impact}</p>}
      <dl className="mt-2 grid gap-x-4 gap-y-1 text-xs md:grid-cols-2">
        <div><dt className="font-semibold text-emerald-700">{labels.ifApproved}</dt><dd>{d.if_approved || "—"}</dd></div>
        <div><dt className="font-semibold text-rose-700">{labels.ifRejected}</dt><dd>{d.if_rejected || "—"}</dd></div>
      </dl>
      {d.blocks.length > 0 && <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground">{labels.blocks}: {d.blocks.join(", ")}</p>}
      {open && <div className="mt-2 flex flex-wrap gap-2"><Button size="sm" onClick={() => act("approve")}>🔒 {labels.approve}</Button><Button size="sm" variant="outline" onClick={() => act("reject")}>{labels.reject}</Button>{d.state === "WAITING" && <Button size="sm" variant="ghost" onClick={() => act("defer")}>{labels.defer}</Button>}</div>}
      {d.decided_by && <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground">{d.decided_by} · {String(d.decided_at).slice(0, 19).replace("T", " ")}</p>}
      {msg && <p className="mt-1 font-mono text-xs" role="status">{msg}</p>}
    </article>
  );
}
