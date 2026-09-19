"use client";
import Link from "next/link";
import { cn } from "cn";
import { DataTable, Detail, type Col } from "@/components/data-table";
import { RUN_STATE_TONE, type RosRun } from "@/lib/ros";
import { Badge } from "@/components/ui/badge";

type Row = RosRun & { links: { mlflow_run_id: string | null; otel_trace_ids: string[] }; mlflow_ui: string | null; telemetry_degraded: string[] };

export function TracesTable({ rows, labels }: { rows: Row[]; labels: { search: string; columns: string; rows: string; detail: string; open: string } }) {
  const columns: Col<Row>[] = [
    { id: "id", meta: { className: "whitespace-nowrap" }, header: "Run", accessorKey: "run_id", cell: ({ getValue }) => <Link href={`/traces/${getValue()}`} className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{getValue() as string}</Link> },
    { id: "state", meta: { className: "whitespace-nowrap" }, header: "Zustand", accessorKey: "state", cell: ({ getValue }) => <Badge className={cn("font-mono", RUN_STATE_TONE[getValue() as string])}>{getValue() as string}</Badge> },
    { id: "thesis", meta: { className: "whitespace-nowrap" }, header: "These", accessorKey: "thesis_id", cell: ({ getValue }) => <span className="font-mono text-xs">{(getValue() as string) || "—"}</span> },
    { id: "mlflow", header: "MLflow", accessorFn: (r) => r.links.mlflow_run_id ?? "", cell: ({ row }) => row.original.links.mlflow_run_id ? (row.original.mlflow_ui ? <a href={row.original.mlflow_ui} target="_blank" rel="noreferrer" className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{row.original.links.mlflow_run_id.slice(0, 12)}</a> : <span className="font-mono text-xs">{row.original.links.mlflow_run_id.slice(0, 12)}</span>) : "—" },
    { id: "otel", meta: { className: "whitespace-nowrap" }, header: "OTel-Traces", accessorFn: (r) => r.links.otel_trace_ids.length },
    { id: "events", meta: { className: "whitespace-nowrap" }, header: "Ereignisse", accessorKey: "n_events" },
    { id: "degraded", meta: { className: "whitespace-nowrap" }, header: "Telemetrie", accessorFn: (r) => r.telemetry_degraded.length, cell: ({ getValue }) => (getValue() as number) ? <span className="text-xs text-amber-700">degraded ×{getValue() as number}</span> : <span className="text-xs text-emerald-700">ok</span> },
    { id: "started", meta: { className: "whitespace-nowrap" }, header: "Start", accessorKey: "started", cell: ({ getValue }) => <span className="font-mono text-xs">{getValue() ? String(getValue()).slice(0, 19).replace("T", " ") : "—"}</span> },
  ];
  return <DataTable columns={columns} rows={rows} getRowId={(r) => r.run_id} storageKey="ros-traces" labels={labels} searchKeys={["run_id", "thesis_id", "state", "kind"]}
    renderDetail={(r) => <Detail rows={[["Kind", r.kind], ["MLflow", r.links.mlflow_run_id ?? "—"], ["OTel", <ul key="o" className="list-disc pl-4 font-mono text-[0.65rem]">{r.links.otel_trace_ids.map((t) => <li key={t}>{t}</li>)}</ul>], ["Degradiert", r.telemetry_degraded.length ? <ul key="d" className="list-disc pl-4 text-xs">{r.telemetry_degraded.map((x) => <li key={x}>{x}</li>)}</ul> : "—"], ["Explorer", <Link key="l" className="underline" href={`/traces/${r.run_id}`}>/traces/{r.run_id}</Link>]]} />} />;
}
