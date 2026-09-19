import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { RecordsOnly } from "@/components/ros/records-only";
import { cn } from "cn";

export default async function Evals() {
  const { t } = await getT(); const d = await rosGet("/api/ros/evals");
  if (d === null) return <Shell title={t("ev_title")}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  const a = d.aggregate;
  return (
    <Shell title={t("ev_title")} subtitle={t("ev_subtitle")} help={t("ev_subtitle")}>
      <Section title={t("ev_results")} hint={`${d.n_theses} Thesen · ${a.version}`}>
        {d.n_theses === 0 ? <p className="text-sm text-muted-foreground">{t("ev_no_data")}</p> : (<>
          <Table head={["Stufe", "Dateien", "Treffer", "bewertbar", "Rate", "95 %-KI (Wilson)"]} rows={a.stages.map((r: any) => [
            <span key="s" className="font-mono text-xs">{r.stage}</span>, String(r.files ?? 0),
            r.status === "OK" ? String(r.k) : <span key="n" className="font-mono text-xs text-muted-foreground">NO_DATA</span>,
            r.status === "OK" ? String(r.n) : "—", r.status === "OK" ? (typeof r.rate === "number" ? r.rate.toFixed(3) : String(r.rate)) : "—",
            r.status === "OK" && r.ci95 ? `[${r.ci95[0].toFixed(3)}, ${r.ci95[1].toFixed(3)}]` : "—"])} />
          <p className="mt-2 font-mono text-xs">gesamt: {a.total.k}/{a.total.n} = {typeof a.total.rate === "number" ? a.total.rate.toFixed(3) : a.total.rate} {a.total.ci95 ? `[${a.total.ci95[0].toFixed(3)}, ${a.total.ci95[1].toFixed(3)}]` : ""} · fehlend {a.total.missing}</p>
          <p className="mt-1 text-xs text-muted-foreground">{a.note}</p></>)}
      </Section>
      <Section title={t("ev_profiles")}>
        <div className="grid gap-2 md:grid-cols-2">{Object.entries(d.profiles.stages).map(([stage, checks]: any) => (
          <div key={stage} className="border border-border p-2 text-xs"><div className="font-mono font-semibold">{stage} <span className="font-normal text-muted-foreground">({d.profiles.files[stage]})</span></div>
            <ul className="mt-1 list-disc pl-4">{checks.map((c: any) => <li key={c.check}>{c.text} <span className="font-mono text-[0.6rem] text-muted-foreground">{c.check}</span></li>)}</ul></div>))}</div>
        <p className="mt-2 text-xs text-muted-foreground">{d.profiles.rule}</p>
      </Section>
    </Shell>
  );
}
