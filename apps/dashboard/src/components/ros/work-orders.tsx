"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DataTable, Detail, type Col } from "@/components/data-table";
import { WoState } from "@/components/ros/state-badge";
import { ActorSelect } from "@/components/ros/actor-select";
import { errText, rosPost, type Actor, type RosWorkOrder } from "@/lib/ros";

const EVENTS: Record<string, { event: string; gate?: boolean }[]> = {
  DRAFT: [{ event: "approve", gate: true }, { event: "supersede" }], APPROVED: [{ event: "dependencies_met" }, { event: "block" }, { event: "supersede" }], READY: [{ event: "start" }, { event: "block" }, { event: "supersede" }],
  BLOCKED: [{ event: "unblock", gate: true }, { event: "supersede" }], RUNNING: [{ event: "validated" }, { event: "falsified" }, { event: "fail" }, { event: "supersede" }], FAILED: [{ event: "retry" }, { event: "supersede" }],
};

function Actions({ wo, actor }: { wo: RosWorkOrder; actor: Actor }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className="flex flex-wrap gap-1">
      {(EVENTS[wo.state] ?? []).map((e) => <Button key={e.event} size="sm" variant={e.gate ? "default" : "outline"} disabled={e.gate && actor !== "founder"} onClick={async () => { const r = await rosPost(`/api/ros/work-orders/${wo.work_order_id}/transition`, { event: e.event, reason: "ui" }, actor); setMsg(r.ok ? `${e.event} → ${r.data.state}` : errText(r)); if (r.ok) router.refresh(); }}>{e.gate ? "🔒 " : ""}{e.event}</Button>)}
      {msg && <span className="w-full font-mono text-xs text-muted-foreground" role="status">{msg}</span>}
    </div>
  );
}

export function WorkOrdersTable({ rows, ready, blocked, labels }: { rows: RosWorkOrder[]; ready: string[]; blocked: { work_order_id: string; waiting_on: string[] }[]; labels: { search: string; columns: string; rows: string; detail: string; actor: string; ready: string; blocked: string } }) {
  const [actor, setActor] = useState<Actor>("founder");
  const waiting = Object.fromEntries(blocked.map((b) => [b.work_order_id, b.waiting_on]));
  const columns: Col<RosWorkOrder>[] = [
    { id: "id", meta: { className: "whitespace-nowrap" }, header: "Work Order", accessorKey: "work_order_id", cell: ({ getValue }) => <span className="font-mono text-xs">{getValue() as string}</span> },
    { id: "thesis", meta: { className: "whitespace-nowrap" }, header: "These", accessorKey: "thesis_id", cell: ({ getValue }) => getValue() ? <Link href={`/theses/${getValue()}`} className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{getValue() as string}</Link> : "—" },
    { id: "state", meta: { className: "whitespace-nowrap" }, header: "Zustand", accessorKey: "state", cell: ({ row }) => <span className="inline-flex items-center gap-1"><WoState state={row.original.state} />{ready.includes(row.original.work_order_id) && <span className="text-[0.6rem] uppercase tracking-widest text-emerald-700">{labels.ready}</span>}{waiting[row.original.work_order_id] && <span className="text-[0.6rem] text-amber-700">{labels.blocked} {waiting[row.original.work_order_id].join(", ")}</span>}</span> },
    { id: "question", header: "Frage", accessorFn: (r) => r.spec?.question ?? "", cell: ({ getValue }) => <span className="text-xs">{getValue() as string}</span> },
    { id: "parents", header: "Abhängig von", accessorFn: (r) => (r.parents ?? []).join(", "), cell: ({ getValue }) => <span className="font-mono text-[0.65rem]">{(getValue() as string) || "—"}</span> },
    { id: "by", meta: { className: "whitespace-nowrap" }, header: "Erstellt von", accessorKey: "created_by" },
    { id: "approved", meta: { className: "whitespace-nowrap" }, header: "Freigabe", accessorFn: (r) => r.approved_by ? `${r.approved_by} ${String(r.approved_at).slice(0, 10)}` : "" , cell: ({ getValue }) => <span className="font-mono text-xs">{(getValue() as string) || "—"}</span> },
  ];
  return (
    <div>
      <div className="mb-3"><ActorSelect value={actor} onChange={setActor} label={labels.actor} /></div>
      <DataTable columns={columns} rows={rows} getRowId={(r) => r.work_order_id} storageKey="ros-work-orders" labels={labels} searchKeys={["work_order_id", "thesis_id", "state", "created_by"]}
        renderDetail={(w) => <Detail rows={[["Zustand", <WoState key="s" state={w.state} />], ["Aktionen", <Actions key="a" wo={w} actor={actor} />], ["Frage", w.spec.question], ["Scope", String(w.spec.scope)], ["Hypothese", w.spec.hypothesis], ["Falsifikationskriterium", w.spec.falsification_criterion],
          ["Metriken", Array.isArray(w.spec.metrics) ? w.spec.metrics.join(", ") : String(w.spec.metrics)], ["Governance", <code key="g" className="break-all font-mono text-[0.7rem]">{JSON.stringify(w.spec.governance)}</code>], ["Caps", <code key="c" className="break-all font-mono text-[0.7rem]">{JSON.stringify(w.spec.caps)}</code>],
          ["Prereg-Hash", w.prereg_hash ? <code key="p" className="break-all font-mono text-[0.7rem]">{w.prereg_hash}</code> : "—"], ["Abhängig von", (w.parents ?? []).join(", ") || "—"], ["Angelegt", `${w.created_by} · ${w.created_at}`]]} />} />
    </div>
  );
}

export function CreateWorkOrder({ theses, required, label }: { theses: { thesis_id: string; title: string }[]; required: string[]; label: string }) {
  const router = useRouter(); const [open, setOpen] = useState(false); const [msg, setMsg] = useState<string | null>(null);
  const [f, setF] = useState<Record<string, string>>({ work_order_id: "", thesis_id: theses[0]?.thesis_id ?? "", question: "", scope: "", hypothesis: "", falsification_criterion: "", metrics: "", governance: "subscription-only; cost_cap 0; pin claude-opus-5", caps: "invocations ≤ 100; max_concurrent_sessions 1" });
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF((s) => ({ ...s, [k]: e.target.value }));
  if (!open) return <Button size="sm" variant="outline" onClick={() => setOpen(true)}>{label}</Button>;
  return (
    <div className="max-w-3xl border border-border p-3 text-sm">
      <div className="grid gap-2 md:grid-cols-2">
        <Input placeholder="work_order_id (z. B. WO-LOGOS-AUTH-001-R1)" value={f.work_order_id} onChange={set("work_order_id")} />
        <select className="border border-border bg-background px-2 py-1 font-mono text-xs" value={f.thesis_id} onChange={set("thesis_id")}>{theses.map((t) => <option key={t.thesis_id} value={t.thesis_id}>{t.thesis_id}</option>)}</select>
        {["question", "scope", "hypothesis", "falsification_criterion"].map((k) => <Textarea key={k} className="md:col-span-2" placeholder={k} value={f[k]} onChange={set(k)} />)}
        <Input placeholder="metrics (kommagetrennt)" value={f.metrics} onChange={set("metrics")} /><Input placeholder="governance" value={f.governance} onChange={set("governance")} /><Input placeholder="caps" value={f.caps} onChange={set("caps")} />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Pflichtfelder: {required.join(", ")}. Entwurf bleibt DRAFT bis zur Founder-Freigabe.</p>
      <div className="mt-2 flex items-center gap-2">
        <Button size="sm" onClick={async () => { const spec = { question: f.question, scope: f.scope, hypothesis: f.hypothesis, falsification_criterion: f.falsification_criterion, metrics: f.metrics.split(",").map((x) => x.trim()).filter(Boolean), governance: { text: f.governance }, caps: { text: f.caps } }; const r = await rosPost("/api/ros/work-orders", { work_order_id: f.work_order_id, thesis_id: f.thesis_id || null, spec }); setMsg(r.ok ? "ok" : errText(r)); if (r.ok) { setOpen(false); router.refresh(); } }}>Anlegen</Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>Abbrechen</Button>{msg && msg !== "ok" && <span className="font-mono text-xs text-rose-700">{msg}</span>}
      </div>
    </div>
  );
}
