import Link from "next/link";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Measurements({ searchParams }: { searchParams: Promise<{ thesis?: string }> }) {
  const { t } = await getT(); const sp = await searchParams;
  const d = await rosGet(`/api/ros/measurements${sp.thesis ? `?thesis_id=${sp.thesis}` : ""}`);
  return (
    <Shell title={t("meas_title")} subtitle={t("meas_subtitle")} help={t("meas_subtitle")}>
      {d === null ? <RecordsOnly text={t("ros_records_only")} /> : d.measurements.length === 0 ? <p className="text-sm text-muted-foreground">{t("meas_none")}</p> : (
        <Section title={t("meas_title")} hint={`${d.measurements.length}`}>
          <Table head={["Messlauf", "These", "Zustand", "Fortschritt", "Vorschlag", "Prereg", "Start"]} rows={d.measurements.map((m: any) => [
            <Link key="l" className="font-mono text-xs underline" href={`/measurements/${m.measurement_id}`}>{m.measurement_id}</Link>,
            <Link key="t" className="font-mono text-xs underline" href={`/theses/${m.thesis_id}`}>{m.thesis_id}</Link>,
            m.state, `${m.executed}/${m.planned}`, (m.summary?.proposal?.verdict ?? "—"), <code key="p" className="font-mono text-[0.65rem]">{String(m.prereg_hash).slice(0, 12)}</code>, String(m.started).slice(0, 19).replace("T", " ")])} />
        </Section>)}
    </Shell>
  );
}
