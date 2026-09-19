import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { QuotaReset } from "@/components/ros/governor-panel";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Quotas() {
  const { t } = await getT(); const g = await rosGet("/api/ros/governor"); const q = await rosGet("/api/ros/queue?limit=500");
  return (
    <Shell title={t("ros_quotas_title")} subtitle={t("ros_quotas_subtitle")}>
      {g === null || q === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <Section title={t("ros_quota")} hint={g.quota.state}><div className="mb-2"><QuotaReset label={t("ros_quota_reset")} /></div><Table head={["Feld", "Wert"]} rows={Object.entries(g.quota).map(([k, v]) => [k, String(v)])} className="max-w-xl" /></Section>
        <Section title="Jobs nach Zustand"><Table head={["Zustand", "Anzahl"]} rows={Object.entries(q.stats).map(([k, v]) => [k, String(v)])} className="max-w-xl" /></Section>
        <Section title={t("ros_caps")}><Table head={["Cap", "Wert"]} rows={Object.entries(g.caps).map(([k, v]) => [k, String(v)])} className="max-w-xl" /></Section>
      </>)}
    </Shell>
  );
}
