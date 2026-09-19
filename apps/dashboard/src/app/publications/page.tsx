import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Table } from "@/components/shell";

export default async function Publications() {
  const r = await api("/api/registries/publications");
  return <Shell title="LOGOS-1 paper series" subtitle="Publication readiness per candidate. Status changes only when every listed criterion is met; no automatic promotion.">
    <Table head={["paper", "tracks", "status", "criteria met", "missing for preprint", "claims"]} rows={r.papers.map((p: any) => [<Link key="p" href={`/publications/${p.paper_id}`} className="underline">{p.paper_id} — {p.title}</Link>, p.tracks.join(", "), <code key="s" className="font-mono text-xs">{p.manuscript_status}</code>, `${p.criteria_met.length}/${p.criteria_preprint.length}`, p.missing_for_preprint.join(", ") || "none", p.claims.join(", ")])} />
  </Shell>;
}
