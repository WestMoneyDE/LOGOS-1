import Link from "next/link";
import { notFound } from "next/navigation";
import { rosGet, rosGetMaybe } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { MeasurementView } from "@/components/ros/measurement-view";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function MeasurementPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; const { t } = await getT();
  const d = await rosGetMaybe(`/api/ros/measurements/${id}`);
  if (d === null) return <Shell title={id}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  if (d === "NOT_FOUND" || !(d as any)?.measurement) notFound();
  const labels = { rates: t("meas_rates"), proposal: t("meas_proposal"), frozen_rule: t("meas_frozen_rule"), items: t("meas_items"), decide_hint: t("meas_decide_hint"), missing_note: t("meas_missing_note"), data_points: t("gate_data_points") };
  return (
    <Shell title={`${t("meas_title")} — ${d.measurement.measurement_id}`} subtitle={t("meas_subtitle")} help={t("meas_subtitle")}>
      <MeasurementView initial={d} labels={labels} />
      <Section title="Links"><ul className="flex flex-wrap gap-3 text-xs"><li><Link className="underline" href={`/theses/${d.measurement.thesis_id}`}>{d.measurement.thesis_id}</Link></li><li><Link className="underline" href={`/runs/${d.measurement.run_id}`}>Run-Konsole</Link></li><li><Link className="underline" href={`/traces/${d.measurement.run_id}`}>Trace</Link></li><li><Link className="underline" href="/measurements">alle Messläufe</Link></li></ul></Section>
    </Shell>
  );
}
