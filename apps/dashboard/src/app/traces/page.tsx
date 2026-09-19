import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { TracesTable } from "@/components/ros/traces-table";
import { RecordsOnly } from "@/components/ros/records-only";
import { TracesStats } from "@/components/ros/traces-stats";

export default async function Traces() {
  const { t } = await getT(); const d = await rosGet("/api/ros/traces?limit=200"); const st = await rosGet("/api/ros/traces/stats?limit=300");
  return (
    <Shell title={t("ros_traces_title")} subtitle={t("ros_traces_subtitle")} help={t("help_traces")}>
      {d === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <p className="mb-4 font-mono text-xs text-muted-foreground">MLflow {d.mlflow_ui} · experiment {d.experiment} · <a className="underline" href={d.mlflow_ui} target="_blank" rel="noreferrer">{t("ros_mlflow_open")}</a></p>
        {st && <Section title={t("traces_stats")} hint={st.version}><TracesStats s={st} labels={{ perDay: t("traces_per_day"), tokens: t("traces_tokens"), phases: t("traces_phases"), tools: t("traces_tools"), theses: t("traces_theses") }} /></Section>}
        <Section title="Runs" hint={`${d.runs.length}`}><TracesTable rows={d.runs} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title"), open: t("ros_mlflow_open") }} /></Section></>)}
    </Shell>
  );
}
