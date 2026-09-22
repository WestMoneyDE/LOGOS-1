import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Section, Table } from "@/components/shell";
import { ExportButton } from "@/components/export-button";

export default async function Paper({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const r = await api("/api/registries/publications"); const p = r.papers.find((x: any) => x.paper_id === id);
  if (!p) return <Shell title="unknown paper">—</Shell>;
  return (
    <Shell title={p.title} subtitle={`${p.paper_id} · ${p.manuscript_status} · missing for preprint: ${p.missing_for_preprint.join(", ") || "none"}`}>
      <Section title="Research question"><p className="text-sm">{p.research_question}</p></Section>
      <Section title="Core contribution"><p className="text-sm">{p.core_contribution}</p></Section>
      <Section title="Claims"><p className="text-sm">{p.claims.map((c: string) => <Link key={c} href={`/claims/${c}`} className="mr-3 underline">{c}</Link>)}</p></Section>
      <Section title="Readiness criteria"><Table head={["criterion", "preprint", "met"]} rows={p.criteria_submission.map((c: string) => [c, p.criteria_preprint.includes(c) ? "required" : "submission only", p.criteria_met.includes(c) ? "✓" : "—"])} /></Section>
      <Section title="Open blockers"><ul className="list-disc pl-5 text-sm">{p.open_blockers.map((b: string) => <li key={b}>{b}</li>)}</ul></Section>
      <Section title="Required experiments"><ul className="list-disc pl-5 text-sm">{p.required_experiments.map((b: string) => <li key={b}>{b}</li>)}</ul></Section>
      <Section title="Required related work / replication"><p className="text-sm">{p.required_related_work.join(", ")} · {p.required_replication.join("; ")}</p></Section>
      <Section title="Draft outline"><ol className="list-decimal pl-5 text-sm">{p.draft_outline.map((o: string) => <li key={o}>{o}</li>)}</ol></Section>
      <Section title="Export (Markdown research brief; no claim inflation)"><ExportButton paperId={p.paper_id} /></Section>
    </Shell>
  );
}
