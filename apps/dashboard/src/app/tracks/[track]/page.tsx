import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Section, Table, Src } from "@/components/shell";
import { ClaimCard } from "@/components/claim-card";
import { KindBadge, Severity, StatusBadge, VerdictBadge } from "@/components/badges";

export default async function TrackPage({ params }: { params: Promise<{ track: string }> }) {
  const { track } = await params;
  const t = await api(`/api/tracks/${track}`);
  return (
    <Shell title={t.title} subtitle={t.question}>
      <Section title="Central thesis"><p className="text-sm">{t.thesis}</p></Section>
      <Section title="Claims" hint="CLAIM → definition → formalization → falsifiable hypothesis → evidence → counterevidence → limitations → status → next test → publication target"><div className="grid gap-3">{t.claims.map((c: any) => <ClaimCard key={c.claim_id} c={c} full />)}</div></Section>
      <Section title="Invariants"><Table head={["id", "statement", "class", "status", "kind", "origin"]} rows={t.invariants.map((i: any) => [<code key="i" className="font-mono text-xs">{i.invariant_id}</code>, i.statement, i.class, <StatusBadge key="s" status={i.status} />, <KindBadge key="k" kind={i.kind} />, <Src key="o" path={i.origin} />])} /></Section>
      <Section title="Experiments and tests" hint="negative results shown equally">
        <Table head={["id", "order", "verdict", "kind", "question", "record"]} rows={t.experiments.map((e: any) => [<Link key="e" href={`/experiments/${e.experiment_id}`} className="font-mono text-xs underline">{e.experiment_id}</Link>, e.order_id, <VerdictBadge key="v" verdict={e.verdict} />, <KindBadge key="k" kind={e.kind} />, e.scientific_question, <Src key="r" path={e.record} />])} />
      </Section>
      {t.counterexamples.length > 0 && <Section title="Counterexamples → repair → validation → residual risk"><Table head={["id", "counterexample", "violated assumption", "severity", "repair", "validation", "remaining risk"]} rows={t.counterexamples.map((c: any) => [<code key="c" className="font-mono text-xs">{c.ce_id}</code>, c.name, c.violated_assumption, <Severity key="s" s={c.severity} />, c.repair, c.validation, c.remaining_risk])} /></Section>}
      <Section title="Related work" hint="no 'we are the first' without a documented search"><Table head={["citation", "supports", "does not support", "novelty"]} rows={t.prior_art.map((p: any) => [<span key="p"><span className="font-mono text-xs text-muted-foreground">{p.citation_id}</span> {p.authors} ({p.year}). <em>{p.title}</em>. {p.venue}</span>, p.claim_supported, p.claim_not_supported, <code key="n" className="font-mono text-xs">{p.novelty_status}</code>])} /></Section>
      <Section title="Open questions"><Table head={["question", "why it matters", "missing", "minimal decisive experiment", "blocked by"]} rows={t.open_questions.map((q: any) => [q.question, q.why_important, q.missing, q.minimal_decisive_experiment, q.blocked_by])} /></Section>
      {t.paper && <Section title="Publication target"><p className="text-sm"><Link href={`/publications/${t.paper.paper_id}`} className="underline">{t.paper.title}</Link> — <code className="font-mono text-xs">{t.paper.manuscript_status}</code>; missing for preprint: {t.paper.missing_for_preprint.join(", ") || "none"}</p></Section>}
    </Shell>
  );
}
