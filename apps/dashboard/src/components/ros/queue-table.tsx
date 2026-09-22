"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTable, Detail, type Col } from "@/components/data-table";
import { JobState } from "@/components/ros/state-badge";
import { errText, rosPost, type RosJob } from "@/lib/ros";

const ACTIONS: Record<string, string[]> = { queued: ["pause", "stop"], running: ["pause", "stop"], paused: ["resume", "stop"], failed: ["retry"], waiting_governance: ["stop"], waiting_quota: ["stop"], waiting_dependency: ["stop"] };

function JobActions({ job, labels }: { job: RosJob; labels: Record<string, string> }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className="flex flex-wrap gap-1">
      {(ACTIONS[job.state] ?? []).map((a) => <Button key={a} size="sm" variant="outline" onClick={async () => { const r = await rosPost(`/api/ros/queue/${job.job_id}/${a}`, {}); setMsg(r.ok ? r.data.state : errText(r)); if (r.ok) router.refresh(); }}>{labels[a] ?? a}</Button>)}
      {msg && <span className="w-full font-mono text-xs text-muted-foreground" role="status" aria-label="job-status">{msg}</span>}
    </div>
  );
}

export function QueueTable({ rows, labels }: { rows: RosJob[]; labels: { search: string; columns: string; rows: string; detail: string; pause: string; resume: string; stop: string; retry: string } }) {
  const columns: Col<RosJob>[] = [
    { id: "id", meta: { className: "whitespace-nowrap" }, header: "#", accessorKey: "job_id", cell: ({ getValue }) => <span className="font-mono text-xs">{getValue() as number}</span> },
    { id: "kind", meta: { className: "whitespace-nowrap" }, header: "Art", accessorKey: "kind", cell: ({ getValue }) => <span className="font-mono text-xs">{getValue() as string}</span> },
    { id: "state", meta: { className: "whitespace-nowrap" }, header: "Zustand", accessorKey: "state", cell: ({ getValue }) => <JobState state={getValue() as string} /> },
    { id: "thesis", meta: { className: "whitespace-nowrap" }, header: "These", accessorKey: "thesis_id", cell: ({ getValue }) => getValue() ? <Link href={`/theses/${getValue()}`} className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{getValue() as string}</Link> : "—" },
    { id: "wo", header: "Work Order", accessorKey: "work_order_id", cell: ({ getValue }) => <span className="font-mono text-xs">{(getValue() as string) || "—"}</span> },
    { id: "attempt", meta: { className: "whitespace-nowrap" }, header: "Versuch", accessorKey: "attempt" },
    { id: "locked", meta: { className: "whitespace-nowrap" }, header: "Worker", accessorKey: "locked_by", cell: ({ getValue }) => <span className="font-mono text-xs">{(getValue() as string) || "—"}</span> },
    { id: "updated", meta: { className: "whitespace-nowrap" }, header: "Aktualisiert", accessorKey: "updated_at", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 19).replace("T", " ")}</span> },
  ];
  return <DataTable columns={columns} rows={rows} getRowId={(r) => String(r.job_id)} storageKey="ros-queue" labels={labels} searchKeys={["kind", "state", "thesis_id", "work_order_id", "locked_by", "idempotency_key"]}
    renderDetail={(j) => <Detail rows={[["Zustand", <JobState key="s" state={j.state} />], ["Aktionen", <JobActions key="a" job={j} labels={labels as any} />], ["Idempotenzschlüssel", <code key="k" className="break-all font-mono text-[0.7rem]">{j.idempotency_key}</code>], ["Payload", <code key="p" className="break-all font-mono text-[0.7rem]">{JSON.stringify(j.payload)}</code>],
      ["Ergebnis", j.result ? <code key="r" className="break-all font-mono text-[0.7rem]">{JSON.stringify(j.result)}</code> : "—"], ["Fehler", j.error || "—"], ["Angelegt", j.created_at]]} />} />;
}

export function EnqueueForm({ theses, kinds, label }: { theses: { thesis_id: string }[]; kinds: string[]; label: string }) {
  const router = useRouter(); const [kind, setKind] = useState(kinds[0] ?? "tests"); const [thesis, setThesis] = useState(theses[0]?.thesis_id ?? ""); const [wo, setWo] = useState(""); const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <select aria-label="kind" className="border border-border bg-background px-2 py-1 font-mono" value={kind} onChange={(e) => setKind(e.target.value)}>{kinds.map((k) => <option key={k}>{k}</option>)}</select>
      <select aria-label="thesis" className="border border-border bg-background px-2 py-1 font-mono" value={thesis} onChange={(e) => setThesis(e.target.value)}><option value="">—</option>{theses.map((t) => <option key={t.thesis_id}>{t.thesis_id}</option>)}</select>
      <Input className="h-8 w-56 font-mono text-xs" placeholder="work_order_id" value={wo} onChange={(e) => setWo(e.target.value)} />
      <Button size="sm" onClick={async () => { const r = await rosPost("/api/ros/queue/enqueue", { kind, thesis_id: thesis || null, work_order_id: wo || null }); setMsg(r.ok ? `job ${r.data.job_id} ${r.data.state}${r.data.duplicate ? " (duplicate)" : ""}` : errText(r)); if (r.ok) router.refresh(); }}>{label}</Button>
      {msg && <span className="font-mono text-muted-foreground" role="status" aria-label="enqueue-status">{msg}</span>}
    </div>
  );
}
