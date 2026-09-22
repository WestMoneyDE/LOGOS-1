import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { StatsCalc } from "@/components/ros/stats-calc";

export default async function Statistics() {
  const { t } = await getT(); const m = await rosGet("/api/ros/statistics/methods");
  const methods = m?.methods ?? {};
  return (
    <Shell title={t("ros_stats_title")} subtitle={t("ros_stats_subtitle")}>
      <Section title="Rechner" hint={m?.version ?? "ros-stats/1"}><StatsCalc methods={methods} label={t("ros_stats_compute")} /></Section>
      <Section title="Methoden"><Table head={["Methode", "Argumente"]} rows={Object.entries(methods).map(([k, v]: any) => [k, v.join(", ")])} className="max-w-2xl" /><p className="mt-2 text-xs text-muted-foreground">{m?.rule}</p></Section>
    </Shell>
  );
}
