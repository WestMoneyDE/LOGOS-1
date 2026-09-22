"use client";
import Link from "next/link";
import { DataTable, Detail, type Col } from "@/components/data-table";
import { ThesisState } from "@/components/ros/state-badge";
import type { RosThesis } from "@/lib/ros";

export function RosThesesTable({ rows, labels }: { rows: RosThesis[]; labels: { search: string; columns: string; rows: string; detail: string } }) {
  const columns: Col<RosThesis>[] = [
    { id: "id", meta: { className: "whitespace-nowrap" }, header: "These", accessorKey: "thesis_id", cell: ({ row }) => <Link href={`/theses/${row.original.thesis_id}`} className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{row.original.thesis_id}</Link> },
    { id: "title", header: "Titel", accessorKey: "title", cell: ({ getValue }) => <span className="font-medium">{getValue() as string}</span> },
    { id: "track", meta: { className: "whitespace-nowrap" }, header: "Track", accessorKey: "track" },
    { id: "state", meta: { className: "whitespace-nowrap" }, header: "Zustand", accessorKey: "state", cell: ({ getValue }) => <ThesisState state={getValue() as string} /> },
    { id: "wos", meta: { className: "whitespace-nowrap" }, header: "Work Orders", accessorKey: "n_work_orders" },
    { id: "jobs", meta: { className: "whitespace-nowrap" }, header: "Offene Jobs", accessorKey: "n_open_jobs" },
    { id: "updated", meta: { className: "whitespace-nowrap" }, header: "Aktualisiert", accessorKey: "updated_at", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 16).replace("T", " ")}</span> },
  ];
  return <DataTable columns={columns} rows={rows} getRowId={(r) => r.thesis_id} storageKey="ros-theses" labels={labels} searchKeys={["thesis_id", "title", "track", "state"]}
    renderDetail={(t) => <Detail rows={[["Claims", t.claim_ids.join(", ") || "—"], ["Zustand", <ThesisState key="s" state={t.state} />], ["Owner", t.owner], ["Angelegt", t.created_at], ["Workspace", <Link key="l" className="underline" href={`/theses/${t.thesis_id}`}>/theses/{t.thesis_id}</Link>]]} />} />;
}
