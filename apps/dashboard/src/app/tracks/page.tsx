import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Table } from "@/components/shell";

export default async function Tracks() {
  const o = await api("/api/overview");
  const rows = await Promise.all(Object.keys(o.tracks).map(async (id) => { const t = await api(`/api/tracks/${id}`); return [<Link key={id} href={`/tracks/${id}`} className="underline">{t.title}</Link>, t.question, `${t.completeness.claims} claims · ${t.completeness.experiments} experiments · ${t.completeness.invariants} invariants · ${t.completeness.counterexamples} counterexamples · ${t.completeness.prior_art} citations`, t.paper?.manuscript_status ?? "—"]; }));
  return <Shell title="Research tracks" subtitle="Six top-level tracks; the first milestone deepens Authority, Causal Provenance and Cognitive Provenance."><Table head={["track", "leading question", "coverage", "paper status"]} rows={rows} /></Shell>;
}
