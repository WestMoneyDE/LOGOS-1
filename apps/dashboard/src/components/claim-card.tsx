import Link from "next/link";
import type { Claim } from "@/lib/api";
import { KindBadge, StatusBadge, StrengthBadge } from "@/components/badges";
import { Src } from "@/components/shell";

export function ClaimCard({ c, full = false }: { c: Claim; full?: boolean }) {
  return (
    <article className="min-w-0 border border-border p-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link href={`/claims/${c.claim_id}`} className="font-mono text-xs text-muted-foreground hover:text-foreground">{c.claim_id}</Link>
        <KindBadge kind={c.kind} /><StatusBadge status={c.status} /><StrengthBadge strength={c.evidence_strength} />
      </div>
      <h3 className="mt-2 font-heading text-base font-semibold">{c.title}</h3>
      <p className="mt-1 text-sm">{c.statement}</p>
      <p className="mt-2 text-xs text-muted-foreground"><span className="font-semibold uppercase tracking-widest">Scope</span> — {c.scope}</p>
      {full && (
        <dl className="mt-4 grid min-w-0 gap-3 text-sm md:grid-cols-2 [&>div]:min-w-0">
          <Row k="Falsification test">{c.falsification_test}</Row>
          <Row k="Next falsification test">{c.next_falsification_test || "none named"}</Row>
          <Row k="Evidence strength basis">{c.evidence_strength_basis}</Row>
          <Row k="Preregistration"><code className="break-all font-mono text-xs">{c.preregistration}</code></Row>
          <Row k="Supporting artifacts"><ul>{c.supporting_artifacts.map((a) => <li key={a}><Src path={a} /></li>)}</ul></Row>
          <Row k="Counterevidence">{c.counterevidence.length ? <ul className="list-disc pl-4">{c.counterevidence.map((x) => <li key={x}>{x}</li>)}</ul> : "none recorded"}</Row>
          <Row k="Known limitations">{c.known_limitations.length ? <ul className="list-disc pl-4">{c.known_limitations.map((x) => <li key={x}>{x}</li>)}</ul> : "none recorded"}</Row>
          <Row k="External replication">{c.external_replication}</Row>
          <Row k="Publication target">{c.publication_target}</Row>
          <Row k="Last updated">{c.last_updated}</Row>
        </dl>
      )}
    </article>
  );
}
function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return <div><dt className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{k}</dt><dd className="mt-0.5">{children}</dd></div>;
}
