"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { API } from "@/lib/api";
import { errText, rosPost } from "@/lib/ros";

type Edit = { registry: string; entity_id: string; field: string; value: any; reason: string; origin?: any };

function Diff({ pv, labels }: { pv: any; labels: Record<string, string> }) {
  const fmt = (v: any) => Array.isArray(v) ? v.map((x) => `• ${x}`).join("\n") : v === null || v === undefined ? "—" : String(v);
  return (
    <div className="mt-2 border border-border p-3 text-sm" role="status">
      <div className={cn("font-semibold", pv.ok ? "text-emerald-700" : "text-rose-700")}>{pv.ok ? labels.ok : labels.failed}</div>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        <div><div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground">{labels.before}</div><pre className="mt-1 whitespace-pre-wrap break-words border border-border bg-muted/20 p-2 font-mono text-[0.7rem]">{fmt(pv.before)}</pre></div>
        <div><div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground">{labels.after}</div><pre className="mt-1 whitespace-pre-wrap break-words border border-border bg-emerald-600/5 p-2 font-mono text-[0.7rem]">{fmt(pv.after)}</pre></div>
      </div>
      {pv.issues?.length > 0 && <ul className="mt-2 list-disc pl-5 text-xs text-rose-700">{pv.issues.map((i: string) => <li key={i}>{i}</li>)}</ul>}
      <p className="mt-1 font-mono text-[0.6rem] text-muted-foreground">{pv.file} · {String(pv.file_sha256_before).slice(0, 12)} · {pv.label}</p>
    </div>
  );
}

export function RegistryEditor({ proposals, editable, labels }: { proposals: any[]; editable: Record<string, Record<string, string>>; labels: Record<string, string> }) {
  const router = useRouter();
  const [edit, setEdit] = useState<Edit>({ registry: "claims", entity_id: "", field: "status", value: "", reason: "" });
  const [pv, setPv] = useState<any>(null); const [msg, setMsg] = useState<string | null>(null);
  const check = async (e: Edit) => { setMsg(null); const r = await rosPost("/api/ros/registry/preview", e); if (r.ok) { setPv(r.data); setEdit(e); } else { setPv(null); setMsg(errText(r)); } };
  const apply = async () => { const r = await rosPost("/api/ros/registry/apply", edit); setMsg(r.ok ? `${labels.applied}: ${r.data.registry}:${r.data.entity_id}.${r.data.field}` : errText(r)); if (r.ok) { setPv(null); router.refresh(); } };
  return (
    <div className="min-w-0">
      {proposals.length > 0 && (
        <ul className="grid gap-2" aria-label="proposals">
          {proposals.map((p: any, i: number) => (
            <li key={i} className={cn("border border-border p-3 text-sm", p.already_applied && "opacity-60")} data-proposal={`${p.entity_id}.${p.field}`}>
              <div className="flex flex-wrap items-baseline gap-2"><span className="font-mono text-xs">{p.registry}:{p.entity_id}.{p.field}</span><span className="grow" />{p.already_applied ? <span className="font-mono text-[0.65rem] text-emerald-700">{labels.applied}</span> : <Button size="sm" variant="outline" onClick={() => check({ registry: p.registry, entity_id: p.entity_id, field: p.field, value: p.value, reason: p.reason, origin: p.source })}>{labels.preview}</Button>}</div>
              <p className="mt-1 text-xs">{p.reason}</p>
              <p className="mt-1 break-all font-mono text-[0.6rem] text-muted-foreground">{p.draft}</p>
            </li>))}
        </ul>)}

      <details className="mt-3 border border-dashed border-border p-3">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-widest text-muted-foreground">{labels.manual}</summary>
        <div className="mt-2 grid gap-2 md:grid-cols-4">
          <select aria-label="registry" className="border border-border bg-background px-2 py-1 font-mono text-xs" value={edit.registry} onChange={(e) => setEdit({ ...edit, registry: e.target.value, field: Object.keys(editable[e.target.value])[0] })}>{Object.keys(editable).map((r) => <option key={r}>{r}</option>)}</select>
          <Input aria-label="entity" className="h-8 font-mono text-xs" placeholder="LOGOS-…" value={edit.entity_id} onChange={(e) => setEdit({ ...edit, entity_id: e.target.value })} />
          <select aria-label="field" className="border border-border bg-background px-2 py-1 font-mono text-xs" value={edit.field} onChange={(e) => setEdit({ ...edit, field: e.target.value })}>{Object.keys(editable[edit.registry] ?? {}).map((f) => <option key={f}>{f}</option>)}</select>
          <Input aria-label="value" className="h-8 font-mono text-xs" placeholder="neuer Wert" value={typeof edit.value === "string" ? edit.value : JSON.stringify(edit.value)} onChange={(e) => setEdit({ ...edit, value: e.target.value })} />
          <Textarea aria-label="reason" className="md:col-span-4 text-xs" placeholder={labels.reason} value={edit.reason} onChange={(e) => setEdit({ ...edit, reason: e.target.value })} />
        </div>
        <p className="mt-1 text-[0.65rem] text-muted-foreground">{Object.entries(editable[edit.registry] ?? {}).map(([f, l]) => `${f}: ${l}`).join(" · ")}</p>
        <Button size="sm" className="mt-2" onClick={() => check(edit)}>{labels.preview}</Button>
      </details>

      {pv && <Diff pv={pv} labels={labels} />}
      {pv?.ok && <Button size="sm" className="mt-2" onClick={apply}>🔒 {labels.apply}</Button>}
      {msg && <p className="mt-2 font-mono text-xs" role="status">{msg}</p>}
    </div>
  );
}

export function RevertButton({ index, label }: { index: number; label: string }) {
  const [out, setOut] = useState<any>(null);
  return <span className="inline-flex items-center gap-2"><Button size="sm" variant="ghost" onClick={async () => { const r = await fetch(`${API}/api/ros/registry/revert-proposal?index=${index}`, { method: "POST" }); setOut(await r.json()); }}>{label}</Button>{out && <span className="font-mono text-[0.65rem] text-muted-foreground" role="status">{out.field}: {JSON.stringify(out.value).slice(0, 60)} — {out.note}</span>}</span>;
}
