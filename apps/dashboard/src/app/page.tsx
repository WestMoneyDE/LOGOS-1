import Link from "next/link";
import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { StatCards } from "@/components/stat-cards";
import { VerdictMix } from "@/components/charts/verdict-mix";
import { StatusBadge, StrengthBadge, VerdictBadge } from "@/components/badges";

export default async function CommandCenter() {
  const { t, locale } = await getT();
  const cc = await api("/api/command-center"); const o = await api("/api/overview");
  const s = cc.stats; const de = locale === "de";
  const items = [
    { label: de ? "Aktive Thesen" : "Active theses", value: s.active_theses, href: "/theses" }, { label: de ? "Work Orders in Warteschlange" : "Queued work orders", value: s.queued_work_orders, pending: true, href: "/queue" },
    { label: de ? "Laufende Agenten" : "Running agents", value: s.running_agents, pending: true, href: "/runs" }, { label: de ? "Blockierte Gates" : "Blocked gates", value: s.blocked_gates, href: "/decisions" },
    { label: de ? "Experimente diesen Monat" : "Experiments this month", value: s.experiments_this_month, sub: de ? "Closures" : "closures", href: "/experiments" }, { label: de ? "Negativergebnisse diesen Monat" : "Negative results this month", value: s.negative_results_this_month, href: "/negative-results" },
    { label: "Benchmark-Delta", value: s.benchmark_delta, pending: true, href: "/benchmarks" }, { label: de ? "Replikationsschuld" : "Replication debt", value: s.replication_debt, sub: de ? "Befunde 0/5" : "findings 0/5", href: "/replication" },
    { label: de ? "Publikationskandidaten" : "Publication candidates", value: s.publication_candidates, href: "/publications" }, { label: de ? "Systemzustand" : "System health", value: s.integrity_violations === 0 && !s.records_only ? "OK" : (de ? "Achtung" : "attention"), sub: `${s.integrity_violations} ${de ? "Integritätsverstöße" : "integrity violations"}${s.records_only ? " · records-only" : ""}`, href: "/system/health" },
  ];
  return (
    <Shell title={t("nav_command_center")} subtitle={de ? "Forschungsprogramm für Autorität, Provenienz, Gedächtnis und Evaluation agentischer KI — deterministischer Kern, empirische Tracks, falsifizierte Hypothesen, aktive Experimente, Publikationskandidaten." : "Research program for agentic AI authority, provenance, memory and evaluation."}>
      <Section title={de ? "Kennzahlen" : "Key figures"}><StatCards items={items} /></Section>
      <div className="grid gap-6 lg:grid-cols-2">
        <Section title={de ? "Kette" : "Chain"} hint={de ? "letzte Closure → nächster Auftrag (nicht ausgeführt)" : "latest closure → next order (not executed)"}>
          {cc.latest_closure && <div className="border border-border p-3 text-sm"><div className="font-mono text-xs text-muted-foreground">{cc.latest_closure.id}</div><div className="mt-1">{cc.latest_closure.verdict ? <VerdictBadge verdict={cc.latest_closure.verdict} /> : "—"}</div><div className="mt-2 text-xs">{de ? "Nächster Auftrag" : "Next order"}: <code className="font-mono">{cc.next_work_order ?? "—"}</code></div></div>}
        </Section>
        <Section title={de ? "Aktive Forschung" : "Active research"} hint={de ? "vom Founder ausgewählte Thesen" : "theses selected by the founder"}>
          {cc.active_research.length ? <div className="grid gap-2">{cc.active_research.map((a: any) => <Link key={a.claim_id} href={`/claims/${a.claim_id}`} className="border border-border p-3 text-sm hover:bg-muted/30"><div className="font-mono text-xs text-muted-foreground">{a.claim_id} · {a.track}</div><div className="font-medium">{a.title}</div><div className="mt-1 flex flex-wrap gap-2"><StatusBadge status={a.status} /><StrengthBadge strength={a.strength} /></div><div className="mt-1 text-xs text-muted-foreground">{de ? "nächster Test" : "next test"}: {a.next_test || "—"} · {de ? "Risiko" : "risk"}: {a.risk || "—"}</div></Link>)}</div> : <p className="text-sm text-muted-foreground">{de ? "Keine These ausgewählt —" : "No thesis selected —"} <Link href="/theses" className="underline">{t("nav_theses")}</Link></p>}
        </Section>
      </div>
      <Section title={de ? "Forschungs-Alerts" : "Research alerts"}>{cc.alerts.length ? <ul className="grid gap-1 text-sm">{cc.alerts.map((a: any, i: number) => <li key={i} className="border border-border px-3 py-1.5"><span className="mr-2 font-mono text-[0.6rem] uppercase tracking-widest text-muted-foreground">{a.kind}</span><Link href={a.href} className="hover:underline">{a.text}</Link></li>)}</ul> : <p className="text-sm text-muted-foreground">{de ? "keine" : "none"}</p>}</Section>
      <Section title={de ? "Wissenschaftlicher Fortschritt" : "Scientific progress"}><VerdictMix data={cc.verdict_mix} n={cc.n_closures} /></Section>
      <Section title={de ? "Forschungsprinzipien" : "Research principles"}><p className="text-sm">{o.principles.join(" · ")}</p></Section>
      <Section title={de ? "Was LOGOS-1 nicht behauptet" : "What LOGOS-1 does not claim"}><ul className="list-disc pl-5 text-sm">{o.does_not_claim.map((x: string) => <li key={x}>{x}</li>)}</ul></Section>
    </Shell>
  );
}
