"use client";
import Link from "next/link";
import type { Experiment } from "@/lib/api";
import { DataTable, Detail, type Col } from "@/components/data-table";
import { Hash } from "@/components/hash";
import { KindBadge, VerdictBadge } from "@/components/badges";

export function ExperimentsTable({ rows, labels }: { rows: Experiment[]; labels: { search: string; columns: string; rows: string; detail: string } }) {
  const columns: Col<Experiment>[] = [
    { id: "id", meta: { className: "whitespace-nowrap" }, header: "ID", accessorKey: "experiment_id", cell: ({ row }) => <Link href={`/experiments/${row.original.experiment_id}`} className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{row.original.experiment_id}</Link> },
    { id: "track", meta: { className: "whitespace-nowrap" }, header: "Track", accessorKey: "research_track" },
    { id: "verdict", meta: { className: "whitespace-nowrap" }, header: "Verdict", accessorKey: "verdict", cell: ({ getValue }) => <VerdictBadge verdict={getValue() as string} /> },
    { id: "kind", meta: { className: "whitespace-nowrap" }, header: "Art", accessorKey: "kind", cell: ({ getValue }) => <KindBadge kind={getValue() as string} /> },
    { id: "negative", meta: { className: "whitespace-nowrap" }, header: "negativ", accessorKey: "negative_result", cell: ({ getValue }) => (getValue() ? "ja" : "") },
    { id: "prereg", meta: { className: "whitespace-nowrap" }, header: "Prereg", accessorKey: "prereg_hash", cell: ({ getValue }) => <Hash value={getValue() as string} /> },
    { id: "run", meta: { className: "whitespace-nowrap" }, header: "Run", accessorKey: "run_id", cell: ({ getValue }) => <code className="font-mono text-[0.65rem]">{String(getValue() ?? "").replace(/^.*-run-/, "run-") || "—"}</code> },
    { id: "order", header: "Order", accessorKey: "order_id" },
  ];
  return (
    <DataTable columns={columns} rows={rows} getRowId={(r) => r.experiment_id} storageKey="experiments" labels={labels} searchKeys={["experiment_id", "order_id", "verdict", "research_track", "hypothesis", "scientific_question", "prereg_hash", "run_id"]}
      renderDetail={(e) => <Detail rows={[["Order", e.order_id], ["Verdict", <VerdictBadge key="v" verdict={e.verdict} />], ["Frage", e.scientific_question], ["Hypothese", e.hypothesis], ["Modell / Provider", e.model_provider], ["Stichprobe", e.sample_size || "—"], ["Kontrollen", e.controls || "—"], ["Metriken", e.metrics.join("; ") || "—"], ["Konstrukt-Status", e.construct_status || "—"],
        ["Prereg-Hash", <code key="p" className="break-all font-mono text-xs">{e.prereg_hash || "—"}</code>], ["Run-ID", <code key="r" className="break-all font-mono text-xs">{e.run_id || "—"}</code>], ["Artefakt-Hash", <code key="a" className="break-all font-mono text-xs">{e.artifact_hash || "—"}</code>],
        ["Limitationen", e.limitations.length ? <ul key="l" className="list-disc pl-4">{e.limitations.map((x) => <li key={x}>{x}</li>)}</ul> : "—"], ["Nächstes Experiment", e.next_experiment || "—"], ["Record", <code key="s" className="break-all font-mono text-xs">{e.record}</code>], ["Commit / PR", `${e.commit || "—"} / ${e.pr ? "#" + e.pr : "—"}`]]} />} />
  );
}
