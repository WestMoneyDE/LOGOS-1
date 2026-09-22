"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import { errText, rosPost } from "@/lib/ros";

type Step = { id: string; title: string; explain: string; founder: boolean; state: string; enabled: boolean; work_order_id?: string | null };
const TONE: Record<string, string> = { done: "border-emerald-600 bg-emerald-600/5", failed: "border-rose-600 bg-rose-600/5", running: "border-sky-600 bg-sky-600/5", open: "border-border" };
const MARK: Record<string, string> = { done: "✓", failed: "✗", running: "●", open: "○" };

/** The five (well: seven) governed steps from a drafted preregistration to a decided verdict. Every founder step is marked 🔒 and explained in one sentence. */
export function GateChain({ thesisId, chain, labels }: { thesisId: string; chain: any; labels: Record<string, string> }) {
  const router = useRouter(); const [busy, setBusy] = useState<string | null>(null); const [out, setOut] = useState<any>(null); const [msg, setMsg] = useState<string | null>(null);
  const call = async (id: string) => {
    setBusy(id); setMsg(null); setOut(null);
    const path = id === "prereg_validate" ? `/api/ros/theses/${thesisId}/prereg/validate`
      : id === "prereg_freeze" ? `/api/ros/theses/${thesisId}/prereg/freeze`
      : id === "work_order_approve" ? `/api/ros/work-orders/${chain.work_order?.work_order_id}/transition`
      : id === "dry_run" ? `/api/ros/theses/${thesisId}/dry-run`
      : id === "ready_to_run" ? `/api/ros/theses/${thesisId}/advance`
      : id === "measurement" ? `/api/ros/theses/${thesisId}/measurement/enqueue` : "";
    const body = id === "work_order_approve" ? { event: "approve", prereg_hash: chain.prereg_hash } : id === "ready_to_run" ? { event: "ready_to_run", reason: "founder" } : {};
    const r = await rosPost(path, body); setBusy(null);
    if (!r.ok) { setMsg(errText(r)); return; }
    setOut({ id, data: r.data }); router.refresh();
  };
  return (
    <div className="min-w-0">
      <ol className="grid gap-2" aria-label="gate chain">
        {chain.steps.map((s: Step, i: number) => (
          <li key={s.id} className={cn("border border-l-4 p-3 text-sm", TONE[s.state] ?? "border-border")} data-gate={s.id} data-state={s.state}>
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-mono text-xs text-muted-foreground">{i + 1}.</span>
              <span className="font-semibold">{MARK[s.state] ?? "○"} {s.title}</span>
              {s.founder && <span className="font-mono text-[0.6rem] uppercase tracking-widest text-amber-700">{labels.founder}</span>}
              <span className="grow" />
              {s.enabled && s.id !== "verdict" && <Button size="sm" variant={s.founder ? "default" : "outline"} disabled={busy === s.id} onClick={() => call(s.id)}>{busy === s.id ? "…" : s.founder ? `🔒 ${labels.run}` : labels.run}</Button>}
              {s.id === "verdict" && s.enabled && <Link className="text-xs underline" href={`/measurements?thesis=${thesisId}`}>{labels.open_measurement}</Link>}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{s.explain}</p>
          </li>))}
      </ol>
      {msg && <p className="mt-2 font-mono text-xs text-rose-700" role="status">{msg}</p>}
      {out && <GateResult out={out} labels={labels} />}
      {chain.prereg_hash && <p className="mt-2 font-mono text-[0.65rem] text-muted-foreground">Prereg <span title={chain.prereg_hash}>{chain.prereg_hash.slice(0, 16)}</span> · {labels.frozen_in_lab}</p>}
    </div>
  );
}

function GateResult({ out, labels }: { out: any; labels: Record<string, string> }) {
  const d = out.data;
  if (out.id === "prereg_validate") {
    const issues = [...(d.file_issues ?? []), ...(d.contract_issues ?? []), ...(d.governance_issues ?? [])];
    return (
      <div className="mt-2 border border-border p-3 text-sm" role="status">
        <div className={cn("font-semibold", d.passed ? "text-emerald-700" : "text-rose-700")}>{d.passed ? labels.check_ok : labels.check_failed}</div>
        {d.passed ? <p className="mt-1 text-xs text-muted-foreground">{labels.planned}: {d.planned_invocations} · Dataset {String(d.dataset_hash).slice(0, 12)} · Prompts {String(d.prompt_bundle_hash).slice(0, 12)} · Pin {d.model_pin}</p>
          : <ul className="mt-1 list-disc pl-5 text-xs">{issues.map((i: string) => <li key={i}>{i}</li>)}</ul>}
      </div>);
  }
  if (out.id === "dry_run") {
    return (
      <div className="mt-2 border border-border p-3 text-sm" role="status">
        <div className={cn("font-semibold", d.passed ? "text-emerald-700" : "text-rose-700")}>{d.passed ? labels.dry_ok : labels.dry_failed}{d.drift?.length ? ` · ${d.drift.join(", ")}` : ""}</div>
        <ul className="mt-1 grid gap-0.5 text-xs sm:grid-cols-2">{Object.entries(d.checks ?? {}).map(([k, v]: any) => <li key={k} className={v ? "text-emerald-700" : "text-rose-700"}>{v ? "✓" : "✗"} {d.texts?.[k] ?? k}</li>)}</ul>
        <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground">{labels.counters}: {d.counters_unchanged ? "0 Modellaufrufe im Trockenlauf" : "Zähler verändert!"}</p>
      </div>);
  }
  if (out.id === "measurement") {
    return <div className="mt-2 border border-border p-3 text-sm" role="status">{labels.measurement_queued}: job #{d.job?.job_id} · {d.planned} {labels.data_points} · {d.job?.state}</div>;
  }
  return <div className="mt-2 border border-border p-3 font-mono text-xs" role="status">{JSON.stringify(d).slice(0, 300)}</div>;
}
