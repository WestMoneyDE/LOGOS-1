import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Section, Table } from "@/components/shell";
import { ClaimCard } from "@/components/claim-card";
import { VerdictBadge } from "@/components/badges";

export default async function ClaimPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const d = await api(`/api/claims/${id}`);
  return (
    <Shell title={d.claim.title} subtitle={`${d.claim.claim_id} · ${d.claim.track} · ${d.claim.claim_type}`}>
      <ClaimCard c={d.claim} full />
      <Section title="Evidence graph" hint="claim ← supported_by → artifact · tested_by → experiment · challenged_by → counterevidence · constrained_by → limitation">
        <Table head={["relation", "node", "kind"]} rows={d.evidence_graph.edges.map((e: any) => [e.rel, e.to, d.evidence_graph.nodes.find((n: any) => n.id === e.to)?.kind ?? ""])} />
      </Section>
      <Section title="Experiments on this track"><Table head={["id", "verdict", "record"]} rows={d.experiments.map((e: any) => [<Link key="e" href={`/experiments/${e.experiment_id}`} className="font-mono text-xs underline">{e.experiment_id}</Link>, <VerdictBadge key="v" verdict={e.verdict} />, e.record])} /></Section>
      <Section title="Replication">{d.replication.length ? <Table head={["finding", "count", "missing", "notes"]} rows={d.replication.map((r: any) => [r.finding, r.count, r.missing.join(", "), r.notes])} /> : <p className="text-sm text-muted-foreground">no replication record</p>}</Section>
      <Section title="Papers"><p className="text-sm">{d.papers.length ? d.papers.map((p: string) => <Link key={p} href={`/publications/${p}`} className="mr-3 underline">{p}</Link>) : "none"}</p></Section>
    </Shell>
  );
}
