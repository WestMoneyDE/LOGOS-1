import { rosGet, type RosRun } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { RunsTable } from "@/components/ros/runs-table";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Runs() {
  const { t } = await getT(); const r = await rosGet<{ runs: RosRun[] }>("/api/ros/runs?limit=200"); const g = await rosGet("/api/ros/governor");
  return (
    <Shell title={t("ros_runs_title")} subtitle={t("ros_runs_subtitle")} help={t("help_runs")}>
      {r === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        {g && <p className="mb-4 font-mono text-xs text-muted-foreground">claude sessions {g.running.claude}/{g.caps.max_parallel_claude_sessions} · deterministic {g.running.deterministic}/{g.caps.max_parallel_deterministic_jobs} · quota {g.quota.state} · auth {g.attestation.auth_class ?? "—"}{g.attestation.fresh ? "" : " (stale)"} · dispatch {g.can_dispatch.claude[1]}</p>}
        <Section title="Runs" hint={`${r.runs.length}`}><RunsTable rows={r.runs} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title") }} /></Section></>)}
    </Shell>
  );
}
