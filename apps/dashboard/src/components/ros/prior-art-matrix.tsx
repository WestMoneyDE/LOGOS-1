"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { errText, rosPost } from "@/lib/ros";

const TONE: Record<string, string> = { rot: "border-l-rose-600", gelb: "border-l-amber-500", gruen: "border-l-emerald-600" };

export function PriorArtMatrix({ m, tasks, labels }: { m: any; tasks: any[]; labels: Record<string, string> }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  const commission = async (track: string) => {
    const t = tasks.find((x) => x.track === track) ?? tasks[0];
    if (!t) { setMsg("keine offene Aufgabe für diese Spur"); return; }
    const r = await rosPost(`/api/ros/prior-art/tasks/${t.task_id}/job`, {});
    setMsg(r.ok ? `Job #${r.data.job_id} (${t.task_id}) eingereiht — Start im Leitstand` : errText(r)); if (r.ok) router.refresh();
  };
  return (
    <div className="min-w-0">
      <div className="grid gap-2 xl:grid-cols-2" aria-label="prior art matrix">
        {m.tracks.map((r: any) => (
          <section key={r.track} className={cn("border border-l-4 p-3 text-sm", TONE[r.status])} data-track={r.track}>
            <header className="flex flex-wrap items-baseline gap-2"><span className="font-semibold">{r.track}</span><span className="text-xs text-muted-foreground">{r.title}</span><span className="grow" /><span className="font-mono text-xs">{r.citations} {labels.citations}</span></header>
            <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground">{labels.novelty}: {Object.entries(r.novelty).map(([k, v]) => `${k} ${v}`).join(" · ")} · {labels.open}: {r.open_tasks} · {r.last_brief ?? "keine Recherche"}</p>
            {r.missing.length > 0 && <ul className="mt-1 list-disc pl-5 text-xs text-muted-foreground">{r.missing.map((x: string) => <li key={x}>{x}</li>)}</ul>}
            <div className="mt-2"><Button size="sm" variant="outline" onClick={() => commission(r.track)}>{labels.start_research}</Button></div>
          </section>))}
      </div>
      {msg && <p className="mt-2 font-mono text-xs text-muted-foreground" role="status">{msg}</p>}
    </div>
  );
}

export function BriefMerge({ brief, labels }: { brief: any; labels: Record<string, string> }) {
  const router = useRouter(); const [diff, setDiff] = useState<any>(null); const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className="border border-border p-3 text-sm" data-brief={brief.brief_id}>
      <div className="flex flex-wrap items-baseline gap-2"><span className="font-mono text-xs">{brief.brief_id}</span><span className="text-xs text-muted-foreground">{brief.claim_id} · {brief.date} · {(brief.sources ?? []).length} Quellen</span><span className="grow" />
        <Button size="sm" variant="outline" onClick={async () => { const res = await rosPost(`/api/ros/prior-art/briefs/${brief.brief_id}/merge`, {}); setMsg(res.ok ? `${res.data.added.length} Zitate übernommen (${res.data.count} gesamt)` : errText(res)); if (res.ok) router.refresh(); }}>🔒 {labels.merge}</Button>
      </div>
      <p className="mt-1 text-xs">{brief.synthesis}</p>
      {msg && <p className="mt-1 font-mono text-xs" role="status">{msg}</p>}
    </div>
  );
}
