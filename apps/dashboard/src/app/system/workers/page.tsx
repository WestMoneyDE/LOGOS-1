import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Workers() {
  const { t } = await getT(); const w = await rosGet("/api/ros/workers"); const g = await rosGet("/api/ros/governor");
  return (
    <Shell title={t("ros_workers_title")} subtitle={t("ros_workers_subtitle")}>
      {w === null || g === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <Section title="Heartbeats" hint={`${w.workers.length}`}>
          {w.workers.length === 0 ? <p className="text-xs text-muted-foreground">— (python -m logos_dashboard.control.host_daemon --loop · docker compose --profile ros up ros-worker)</p> :
            <Table head={["Worker", "Art", "Host", "Kinds", "Zuletzt", "Job", "Status"]} rows={w.workers.map((x: any) => [x.worker_id, x.kind, x.host, x.kinds.join(","), String(x.last_seen).slice(0, 19).replace("T", " "), x.current_job ?? "—", x.alive ? t("ros_alive") : t("ros_dead")])} />}
        </Section>
        <Section title={t("ros_running")}><Table head={["Klasse", "laufend", "Cap"]} rows={[["claude", g.running.claude, g.caps.max_parallel_claude_sessions], ["deterministic", g.running.deterministic, g.caps.max_parallel_deterministic_jobs], ["active theses", g.running.active_theses, g.caps.max_active_theses]]} className="max-w-xl" /></Section>
      </>)}
    </Shell>
  );
}
