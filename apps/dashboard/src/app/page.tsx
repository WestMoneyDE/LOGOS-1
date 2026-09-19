import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Section, Table } from "@/components/shell";
import { VerdictBadge } from "@/components/badges";

export default async function Overview() {
  const o = await api("/api/overview");
  const c = o.counts;
  return (
    <Shell title="LOGOS-1" subtitle="Research program for agentic AI authority, provenance, memory and evaluation. Deterministic core, empirical tracks, falsified hypotheses, active experiments, publication candidates — every statement linked to a record.">
      <Section title="Current state">
        <div className="grid gap-3 md:grid-cols-4">
          <Stat k="claims" v={Object.values(c.claims_by_status as Record<string, number>).reduce((a, b) => a + b, 0)} sub={fmt(c.claims_by_status)} />
          <Stat k="experiments" v={Object.values(c.experiments_by_verdict as Record<string, number>).reduce((a, b) => a + b, 0)} sub={`${c.negative_results} negative results preserved`} />
          <Stat k="invariants" v={c.invariants} sub={fmt(c.invariants_by_status)} />
          <Stat k="papers" v={Object.values(c.papers_by_status as Record<string, number>).reduce((a, b) => a + b, 0)} sub={fmt(c.papers_by_status)} />
        </div>
      </Section>
      <Section title="Chain head" hint="latest closure → next order (not executed)">
        {o.latest_closure && <Table head={["latest closure", "verdict", "next work order", "integrity violations"]} rows={[[<Link key="l" href="/timeline" className="underline">{o.latest_closure.id}</Link>, o.latest_closure.verdict ? <VerdictBadge verdict={o.latest_closure.verdict} /> : "—", <code key="n" className="font-mono text-xs">{o.next_work_order ?? "—"}</code>, String(o.integrity_violations)]]} />}
      </Section>
      {o.open_decisions.length > 0 && <Section title="Open founder decisions"><ul className="list-disc pl-5 text-sm">{o.open_decisions.map((d: any, i: number) => <li key={i}><span className="font-mono text-xs text-muted-foreground">{d.order_id}</span> — {d.text}</li>)}</ul></Section>}
      <Section title="Research tracks">
        <div className="grid gap-3 md:grid-cols-2">
          {Object.entries(o.tracks as Record<string, any>).map(([id, t]) => (
            <Link key={id} href={`/tracks/${id}`} className="border border-border p-4 hover:bg-muted/40">
              <div className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground">{id} · {c.claims_by_track[id] ?? 0} claims</div>
              <div className="mt-1 font-heading font-semibold">{t.title}</div>
              <p className="mt-1 text-sm text-muted-foreground">{t.question}</p>
            </Link>
          ))}
        </div>
      </Section>
      <Section title="Research principles"><p className="text-sm">{o.principles.join(" · ")}</p></Section>
      <Section title="What LOGOS-1 does not claim"><ul className="list-disc pl-5 text-sm">{o.does_not_claim.map((x: string) => <li key={x}>{x}</li>)}</ul></Section>
      {o.active_theses.length > 0 && <Section title="Theses selected for work"><p className="text-sm">{o.active_theses.join(", ")} — <Link href="/theses" className="underline">manage</Link></p></Section>}
    </Shell>
  );
}
function Stat({ k, v, sub }: { k: string; v: number; sub: string }) {
  return <div className="border border-border p-4"><div className="text-[0.65rem] uppercase tracking-widest text-muted-foreground">{k}</div><div className="font-heading text-3xl font-semibold">{v}</div><div className="mt-1 text-xs text-muted-foreground">{sub}</div></div>;
}
function fmt(o: Record<string, number>) { return Object.entries(o).map(([k, v]) => `${v} ${k}`).join(" · "); }
