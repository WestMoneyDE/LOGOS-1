"use client";
import Link from "next/link";
import { cn } from "cn";
import { DataTable, Detail, type Col } from "@/components/data-table";
import { RUN_STATE_TONE, type RosRun } from "@/lib/ros";
import { Badge } from "@/components/ui/badge";

export function RunsTable({ rows, labels }: { rows: RosRun[]; labels: { search: string; columns: string; rows: string; detail: string } }) {
  const columns: Col<RosRun>[] = [
    { id: "id", meta: { className: "whitespace-nowrap" }, header: "Run", accessorKey: "run_id", cell: ({ getValue }) => <Link href={`/runs/${getValue()}`} className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{getValue() as string}</Link> },
    { id: "kind", meta: { className: "whitespace-nowrap" }, header: "Art", accessorKey: "kind", cell: ({ getValue }) => <span className="font-mono text-xs">{getValue() as string}</span> },
    { id: "state", meta: { className: "whitespace-nowrap" }, header: "Zustand", accessorKey: "state", cell: ({ getValue }) => <Badge className={cn("font-mono", RUN_STATE_TONE[getValue() as string])}>{getValue() as string}</Badge> },
    { id: "thesis", meta: { className: "whitespace-nowrap" }, header: "These", accessorKey: "thesis_id", cell: ({ getValue }) => getValue() ? <Link href={`/theses/${getValue()}`} className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{getValue() as string}</Link> : "—" },
    { id: "events", meta: { className: "whitespace-nowrap" }, header: "Ereignisse", accessorKey: "n_events" },
    { id: "started", meta: { className: "whitespace-nowrap" }, header: "Start", accessorKey: "started", cell: ({ getValue }) => <span className="font-mono text-xs">{getValue() ? String(getValue()).slice(0, 19).replace("T", " ") : "—"}</span> },
    { id: "stop", header: "Stop-Grund", accessorKey: "stop_reason", cell: ({ getValue }) => <span className="font-mono text-xs">{(getValue() as string) || "—"}</span> },
  ];
  return <DataTable columns={columns} rows={rows} getRowId={(r) => r.run_id} storageKey="ros-runs" labels={labels} searchKeys={["run_id", "kind", "state", "thesis_id", "branch", "stop_reason"]}
    renderDetail={(r) => <Detail rows={[["Branch", r.branch ? <code key="b" className="break-all font-mono text-[0.7rem]">{r.branch}</code> : "—"], ["Worktree", r.worktree ? <code key="w" className="break-all font-mono text-[0.7rem]">{r.worktree}</code> : "—"], ["Job", String(r.job_id ?? "—")], ["Beendet", r.finished ?? "—"],
      ["Zusammenfassung", r.summary ? <code key="s" className="break-all font-mono text-[0.7rem]">{JSON.stringify(r.summary).slice(0, 600)}</code> : "—"], ["Konsole", <Link key="l" className="underline" href={`/runs/${r.run_id}`}>/runs/{r.run_id}</Link>]]} />} />;
}
