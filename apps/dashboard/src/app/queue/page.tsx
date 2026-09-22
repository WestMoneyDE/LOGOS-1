import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { QueueTable, EnqueueForm } from "@/components/ros/queue-table";
import { RecordsOnly } from "@/components/ros/records-only";
import { StatCards } from "@/components/stat-cards";

export default async function Queue() {
  const { t } = await getT();
  const q = await rosGet("/api/ros/queue"); const st = await rosGet("/api/ros/status"); const th = await rosGet("/api/ros/theses");
  return (
    <Shell title={t("ros_queue_title")} subtitle={t("ros_queue_subtitle")} help={t("help_queue")}>
      {q === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <Section title="Status" hint={q.executor}><StatCards items={Object.entries(q.stats as Record<string, number>).map(([k, v]) => ({ label: k, value: v }))} /></Section>
        <Section title="Jobs" hint={`${q.jobs.length}`}>
          <div className="mb-3"><EnqueueForm theses={th?.theses ?? []} kinds={st?.job_kinds ?? []} label={t("ros_enqueue")} /></div>
          <QueueTable rows={q.jobs} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title"), pause: t("ros_pause"), resume: t("ros_resume"), stop: t("ros_stop"), retry: t("ros_retry") }} />
        </Section></>)}
    </Shell>
  );
}
