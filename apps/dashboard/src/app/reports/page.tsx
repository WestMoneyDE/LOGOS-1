import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { ReportFreeze } from "@/components/ros/report-freeze";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Reports({ searchParams }: { searchParams: Promise<{ month?: string }> }) {
  const { t } = await getT(); const sp = await searchParams; const month = sp.month ?? new Date().toISOString().slice(0, 7);
  const r = await rosGet(`/api/ros/reports/${month}`); const list = await rosGet("/api/ros/reports"); const pr = await rosGet("/api/ros/paper-readiness");
  return (
    <Shell title={`${t("ros_reports_title")} help={t("help_reports")} — ${month}`} subtitle={t("ros_reports_subtitle")}>
      {r === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <div className="mb-4 flex flex-wrap items-center gap-3"><ReportFreeze month={month} label={t("ros_reports_freeze")} frozen={r.frozen} /><span className="font-mono text-xs text-muted-foreground">sha {r.doc.sha256.slice(0, 16)} · {r.doc.version}</span></div>
        <Section title="Markdown"><pre className="max-w-5xl overflow-x-auto whitespace-pre-wrap border border-border bg-muted/20 p-3 font-mono text-[0.72rem] leading-relaxed" aria-label="monthly report">{r.markdown}</pre></Section>
        {pr && <Section title={t("ros_paper_title")} hint={t("ros_paper_subtitle")}>
          <Table head={["Paper", "Kriterien", "Status", "offene Blocker", "Claims"]} rows={pr.papers.map((p: any) => [`${p.paper_id} — ${p.title.slice(0, 60)}`, `${p.met}/${p.of}`, p.manuscript_status, p.open_blockers.join("; ") || "—", p.claims.map((c: any) => `${c.claim_id} ${c.status}/${c.strength}`).join(", ")])} />
          <ul className="mt-2 grid gap-1 text-[0.65rem] font-mono md:grid-cols-2">{pr.papers.map((p: any) => <li key={p.paper_id}>{p.paper_id}: {Object.entries(p.checks).map(([k, v]: any) => <span key={k} className={v ? "text-emerald-700" : "text-rose-700"}>{v ? "✓" : "✗"} {k} </span>)}</li>)}</ul>
        </Section>}
        {list && <Section title="Berichte" hint={`${list.reports.length}`}>{list.reports.length === 0 ? <p className="text-xs text-muted-foreground">—</p> : <Table head={["Monat", "Pfad", "eingefroren", "SHA-256"]} rows={list.reports.map((x: any) => [x.month, x.path, x.frozen ? "ja" : "nein", x.sha256 ? x.sha256.slice(0, 16) : "—"])} className="max-w-3xl" />}</Section>}
      </>)}
    </Shell>
  );
}
