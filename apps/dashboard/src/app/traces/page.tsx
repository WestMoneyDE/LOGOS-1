import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { TracesTable } from "@/components/ros/traces-table";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Traces() {
  const { t } = await getT(); const d = await rosGet("/api/ros/traces?limit=200");
  return (
    <Shell title={t("ros_traces_title")} subtitle={t("ros_traces_subtitle")}>
      {d === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <p className="mb-4 font-mono text-xs text-muted-foreground">MLflow {d.mlflow_ui} · experiment {d.experiment} · <a className="underline" href={d.mlflow_ui} target="_blank" rel="noreferrer">{t("ros_mlflow_open")}</a></p>
        <Section title="Runs" hint={`${d.runs.length}`}><TracesTable rows={d.runs} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title"), open: t("ros_mlflow_open") }} /></Section></>)}
    </Shell>
  );
}
