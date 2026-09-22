"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import { errText, rosPost } from "@/lib/ros";

/** Enqueue a thesis_advance job, preview the §75 gate, founder Start. One Claude invocation per job; nothing runs without the host daemon. */
export function AgentJob({ thesisId, jobs, labels }: { thesisId: string; jobs: any[]; labels: { enqueue: string; hint: string; gate: string; start: string; stop: string } }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null); const [gate, setGate] = useState<any>(null);
  const open = jobs.find((j) => ["waiting_governance", "queued", "running", "paused", "waiting_quota"].includes(j.state) && ["thesis_advance", "prior_art"].includes(j.kind));
  return (
    <div className="border border-dashed border-border p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        {!open && <Button size="sm" onClick={async () => { const r = await rosPost(`/api/ros/theses/${thesisId}/agent-job`, {}); setMsg(r.ok ? `job #${r.data.job_id} ${r.data.state}` : errText(r)); if (r.ok) router.refresh(); }}>{labels.enqueue}</Button>}
        {open && <span className="font-mono text-xs">job #{open.job_id} · {open.kind} · <span className="font-semibold">{open.state}</span></span>}
        {open && open.state === "waiting_governance" && <Button size="sm" variant="outline" onClick={async () => { const r = await fetch(`${API}/api/ros/queue/${open.job_id}/gate`); setGate(await r.json()); }}>{labels.gate}</Button>}
        {open && open.state === "waiting_governance" && <Button size="sm" onClick={async () => { const r = await rosPost(`/api/ros/queue/${open.job_id}/start`, {}); setMsg(r.ok ? `🔒 start → ${r.data.state}` : errText(r)); if (r.ok) router.refresh(); }}>🔒 {labels.start}</Button>}
        {open && <Button size="sm" variant="destructive" onClick={async () => { const r = await rosPost(`/api/ros/queue/${open.job_id}/stop`, {}); setMsg(r.ok ? `stop → ${r.data.state}` : errText(r)); if (r.ok) router.refresh(); }}>{labels.stop}</Button>}
        <Link href="/runs" className="text-xs underline">/runs</Link>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{labels.hint}</p>
      {gate && <ul className="mt-2 grid gap-x-4 font-mono text-[0.7rem] sm:grid-cols-2">{Object.entries(gate.checks ?? {}).map(([k, v]) => <li key={k} className={v ? "text-emerald-700" : "text-rose-700"}>{v ? "✓" : "✗"} {k}</li>)}</ul>}
      {msg && <p className="mt-1 font-mono text-xs text-muted-foreground" role="status">{msg}</p>}
    </div>
  );
}
