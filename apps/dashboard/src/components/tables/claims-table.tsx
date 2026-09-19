"use client";
import Link from "next/link";
import type { Claim } from "@/lib/api";
import { DataTable, Detail, type Col } from "@/components/data-table";
import { KindBadge, StatusBadge, StrengthBadge } from "@/components/badges";

export function ClaimsTable({ rows, labels }: { rows: Claim[]; labels: { search: string; columns: string; rows: string; detail: string } }) {
  const columns: Col<Claim>[] = [
    { id: "id", meta: { className: "whitespace-nowrap" }, header: "ID", accessorKey: "claim_id", cell: ({ row }) => <Link href={`/claims/${row.original.claim_id}`} className="font-mono text-xs underline" onClick={(e) => e.stopPropagation()}>{row.original.claim_id}</Link> },
    { id: "title", header: "Claim", accessorKey: "title", cell: ({ getValue }) => <span className="font-medium">{getValue() as string}</span> },
    { id: "track", meta: { className: "whitespace-nowrap" }, header: "Track", accessorKey: "track" },
    { id: "type", meta: { className: "whitespace-nowrap" }, header: "Typ", accessorKey: "claim_type" },
    { id: "status", meta: { className: "whitespace-nowrap" }, header: "Status", accessorKey: "status", cell: ({ getValue }) => <StatusBadge status={getValue() as string} /> },
    { id: "strength", meta: { className: "whitespace-nowrap" }, header: "Evidenzstärke", accessorKey: "evidence_strength", cell: ({ getValue }) => <StrengthBadge strength={getValue() as string} /> },
    { id: "kind", meta: { className: "whitespace-nowrap" }, header: "Art", accessorKey: "kind", cell: ({ getValue }) => <KindBadge kind={getValue() as string} /> },
    { id: "next", header: "Nächster Test", accessorKey: "next_falsification_test", cell: ({ getValue }) => <span className="text-xs">{(getValue() as string) || "—"}</span> },
  ];
  return (
    <DataTable columns={columns} rows={rows} getRowId={(r) => r.claim_id} storageKey="claims" labels={labels} searchKeys={["claim_id", "title", "statement", "track", "status", "evidence_strength", "scope", "publication_target"]}
      renderDetail={(c) => <Detail rows={[["Aussage", c.statement], ["Status", <StatusBadge key="s" status={c.status} />], ["Evidenzstärke", <StrengthBadge key="e" strength={c.evidence_strength} />], ["Basis der Stärke", c.evidence_strength_basis], ["Geltungsbereich", c.scope], ["Falsifikationstest", c.falsification_test], ["Nächster Test", c.next_falsification_test || "—"],
        ["Preregistration", <code key="p" className="break-all font-mono text-xs">{c.preregistration}</code>], ["Artefakte", <ul key="a" className="list-disc pl-4">{c.supporting_artifacts.map((x) => <li key={x}><code className="break-all font-mono text-[0.7rem]">{x}</code></li>)}</ul>],
        ["Gegenevidenz", c.counterevidence.length ? <ul key="c" className="list-disc pl-4">{c.counterevidence.map((x) => <li key={x}>{x}</li>)}</ul> : "—"], ["Limitationen", c.known_limitations.length ? <ul key="l" className="list-disc pl-4">{c.known_limitations.map((x) => <li key={x}>{x}</li>)}</ul> : "—"], ["Externe Replikation", c.external_replication], ["Publikationsziel", c.publication_target], ["Aktualisiert", c.last_updated]]} />} />
  );
}
