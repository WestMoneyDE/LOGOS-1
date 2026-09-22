"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { errText, rosPost } from "@/lib/ros";

const TONE: Record<string, string> = { ACTION_PROPOSED: "border-l-amber-500", ACCEPTED: "border-l-emerald-600", REJECTED: "border-l-rose-600", DEFERRED: "border-l-zinc-400", RAW: "border-l-sky-500" };

export function RadarCard({ item, pipeline, labels }: { item: any; pipeline: string[]; labels: { accept: string; reject: string; defer: string; ai: string; reprocess: string; drafts: string; aiProposal: string } }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null); const p = item.payload ?? {}; const d = p.action?.delta ?? null;
  const act = async (path: string, body: any = {}) => { const r = await rosPost(path, body); setMsg(r.ok ? (r.data.state ?? `job #${r.data.job_id} ${r.data.state}`) : errText(r)); if (r.ok) router.refresh(); };
  const open = item.state === "ACTION_PROPOSED" || item.state === "DEFERRED";
  const idx = pipeline.indexOf(item.state);
  return (
    <article className={cn("border border-border border-l-4 p-3 text-sm", TONE[item.state] ?? "border-l-border")} data-radar={item.radar_id}>
      <header className="flex flex-wrap items-baseline justify-between gap-2"><span className="font-mono text-xs">#{item.radar_id} · {p.kind} · <span className="font-semibold">{item.state}</span></span><span className="font-mono text-[0.65rem] text-muted-foreground">{String(item.updated_at).slice(0, 16).replace("T", " ")}{p.source ? ` · ${p.source}` : ""}</span></header>
      <ol className="mt-1 flex flex-wrap gap-0.5 font-mono text-[0.55rem]">{pipeline.map((s, i) => <li key={s} className={cn("border px-1", i <= idx ? "border-foreground text-foreground" : "border-border text-muted-foreground")}>{s}</li>)}</ol>
      <p className="mt-2">{p.text}</p>
      {p.track_map && <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground">track {p.track_map.track ?? "—"} · source {p.source?.source_class} · {p.evidence?.proposed_evidence_strength} · claims {(p.claim_impact?.impacted_claims ?? []).map((c: any) => c.claim_id).join(", ") || "—"}{p.dedup?.is_duplicate ? ` · DUPLICATE ${p.dedup.duplicates[0]}` : ""}</p>}
      {d && (
        <dl className="mt-2 grid gap-x-4 gap-y-1 text-xs md:grid-cols-2">
          <div><dt className="font-semibold text-muted-foreground">BEFORE</dt><dd className="font-mono text-[0.65rem]">{JSON.stringify(d.BEFORE)}</dd></div>
          <div><dt className="font-semibold text-sky-700">PROPOSED ({p.action.delta_kind})</dt><dd>{d.PROPOSED}</dd></div>
          <div><dt className="font-semibold text-muted-foreground">EVIDENCE</dt><dd className="break-all font-mono text-[0.65rem]">{(d.EVIDENCE?.sources ?? []).join(" ") || "—"} ({d.EVIDENCE?.class})</dd></div>
          <div><dt className="font-semibold text-muted-foreground">WHY</dt><dd>{d.WHY}</dd></div>
          <div className="md:col-span-2"><dt className="font-semibold text-rose-700">WHAT WOULD FALSIFY IT</dt><dd>{d.WHAT_WOULD_FALSIFY_IT}</dd></div>
        </dl>)}
      {item.proposal && <div className="mt-2 border border-dashed border-border p-2 text-xs"><div className="font-semibold">{labels.aiProposal} · {item.proposal.model_resolved ?? "—"} · {item.proposal.evidence_class ?? "—"} · prompt {String(item.proposal.prompt_sha256).slice(0, 10)} · {item.proposal.valid ? "valid" : "INVALID"}</div><pre className="mt-1 max-h-40 overflow-auto font-mono text-[0.65rem]">{JSON.stringify(item.proposal.proposal, null, 1)}</pre></div>}
      {p.drafts?.length > 0 && <p className="mt-2 font-mono text-[0.65rem]">{labels.drafts}: {p.drafts.map((x: any) => x.path ?? `${x.kind} ${x.id ?? ""} ${x.state ?? ""}${x.error ? ` (${x.error})` : ""}`).join(" · ")}</p>}
      <div className="mt-2 flex flex-wrap gap-2">
        {open && <Button size="sm" onClick={() => act(`/api/ros/radar/${item.radar_id}/review`, { verdict: "ACCEPTED", reason: "ui" })}>🔒 {labels.accept}</Button>}
        {open && <Button size="sm" variant="outline" onClick={() => act(`/api/ros/radar/${item.radar_id}/review`, { verdict: "REJECTED", reason: "ui" })}>{labels.reject}</Button>}
        {item.state === "ACTION_PROPOSED" && <Button size="sm" variant="ghost" onClick={() => act(`/api/ros/radar/${item.radar_id}/review`, { verdict: "DEFERRED", reason: "ui" })}>{labels.defer}</Button>}
        {open && !item.proposal && <Button size="sm" variant="ghost" onClick={() => act(`/api/ros/radar/${item.radar_id}/ai-proposal`)}>{labels.ai}</Button>}
        {open && <Button size="sm" variant="ghost" onClick={() => act(`/api/ros/radar/${item.radar_id}/process`)}>{labels.reprocess}</Button>}
      </div>
      {msg && <p className="mt-1 font-mono text-xs text-muted-foreground" role="status">{msg}</p>}
    </article>
  );
}
