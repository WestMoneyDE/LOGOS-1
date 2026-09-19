import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { ProgressChart, FreezeMonth } from "@/components/ros/progress-chart";
import { RecordsOnly } from "@/components/ros/records-only";

const fmt = (r: any) => (r && typeof r === "object" ? (r.value === "NOT_DEFINED" ? "NOT_DEFINED" : `${(r.value * 100).toFixed(1)} % [${(r.ci95[0] * 100).toFixed(1)}, ${(r.ci95[1] * 100).toFixed(1)}] · n=${Array.isArray(r.n) ? r.n.join("/") : r.n}`) : String(r));

export default async function Progress() {
  const { t } = await getT(); const p = await rosGet("/api/ros/progress");
  return (
    <Shell title={t("ros_progress_title")} subtitle={t("ros_progress_subtitle")}>
      {p === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <Section title={p.current.month} hint={`${p.current.closures} Closures`}>
          <div className="mb-3"><FreezeMonth month={p.current.month} label={t("ros_progress_freeze")} /></div>
          <Table head={["Kennzahl", "Wert (Wilson 95 %-KI)"]} rows={[["Closures", String(p.current.closures)], ["supported / partial · falsified · invalid", `${p.current.verdicts.supported_or_partial} · ${p.current.verdicts.falsified} · ${p.current.verdicts.invalid_measurement}`], ["Falsifikationsrate", fmt(p.current.falsification_rate)], ["Invalid-Measurement-Rate", fmt(p.current.invalid_measurement_rate)], ["Replikationsabdeckung", fmt(p.current.replication_coverage)], ["Agenten-Läufe", String(p.current.agent_runs)], ["Agent-Run-Erfolg", fmt(p.current.agent_run_success)], ["Ø Laufzeit (s)", typeof p.current.mean_run_seconds === "number" ? p.current.mean_run_seconds.toFixed(1) : String(p.current.mean_run_seconds)], ["Neue Thesen", String(p.current.theses_created)], ["Time-to-Verdict", String(p.current.time_to_verdict)]]} className="max-w-3xl" />
        </Section>
        <Section title="Verlauf"><ProgressChart series={p.series} /></Section>
        <Section title="Eingefrorene Monate" hint={`${p.frozen.length}`}>{p.frozen.length === 0 ? <p className="text-xs text-muted-foreground">— · {p.comparability}</p> : <Table head={["Monat", "SHA-256", "von", "am"]} rows={p.frozen.map((f: any) => [f.month, f.sha256.slice(0, 16), f.frozen_by, String(f.created_at).slice(0, 19)])} className="max-w-2xl" />}</Section>
      </>)}
    </Shell>
  );
}
