"use client";
import type { Invariant } from "@/lib/api";
import { DataTable, Detail, type Col } from "@/components/data-table";
import { KindBadge, StatusBadge } from "@/components/badges";

export function InvariantsTable({ rows, labels }: { rows: Invariant[]; labels: { search: string; columns: string; rows: string; detail: string } }) {
  const columns: Col<Invariant>[] = [
    { id: "id", meta: { className: "whitespace-nowrap" }, header: "ID", accessorKey: "invariant_id", cell: ({ getValue }) => <code className="font-mono text-xs">{getValue() as string}</code> },
    { id: "statement", header: "Invariante", accessorKey: "statement", cell: ({ getValue }) => <span className="font-medium">{getValue() as string}</span> },
    { id: "track", meta: { className: "whitespace-nowrap" }, header: "Track", accessorKey: "track" },
    { id: "class", meta: { className: "whitespace-nowrap" }, header: "Klasse", accessorKey: "class" },
    { id: "status", meta: { className: "whitespace-nowrap" }, header: "Status", accessorKey: "status", cell: ({ getValue }) => <StatusBadge status={getValue() as string} /> },
    { id: "kind", meta: { className: "whitespace-nowrap" }, header: "Art", accessorKey: "kind", cell: ({ getValue }) => <KindBadge kind={getValue() as string} /> },
    { id: "rel", meta: { className: "whitespace-nowrap" }, header: "Relationen", accessorFn: (r) => r.relations.length, cell: ({ row }) => String(row.original.relations.length) },
  ];
  return (
    <DataTable columns={columns} rows={rows} getRowId={(r) => r.invariant_id} storageKey="invariants" labels={labels} searchKeys={["invariant_id", "statement", "track", "class", "status", "definition", "origin"]}
      renderDetail={(i) => <Detail rows={[["Definition", i.definition], ["Herkunft", <code key="o" className="break-all font-mono text-xs">{i.origin}</code>], ["Status", <StatusBadge key="s" status={i.status} />], ["Evidenz", <ul key="e" className="list-disc pl-4">{i.evidence.map((x) => <li key={x}><code className="break-all font-mono text-[0.7rem]">{x}</code></li>)}</ul>],
        ["Gegenbeispiele", i.counterexamples.join(", ") || "—"], ["Experimente", i.experiments.join(", ") || "—"], ["Relationen", i.relations.map((r) => `${r.type} → ${r.target}`).join("; ") || "—"], ["Publikationsrelevanz", i.publication_relevance]]} />} />
  );
}
