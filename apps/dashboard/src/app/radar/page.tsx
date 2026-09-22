import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { RadarCard } from "@/components/ros/radar-card";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Radar() {
  const { t } = await getT(); const d = await rosGet("/api/ros/radar"); const att = await rosGet("/api/ros/attention");
  const labels = { accept: t("ros_radar_accept"), reject: t("ros_radar_reject"), defer: t("ros_radar_defer"), ai: t("ros_radar_ai"), reprocess: t("ros_radar_reprocess"), drafts: t("ros_radar_drafts"), aiProposal: t("ros_radar_ai_proposal") };
  return (
    <Shell title={t("ros_radar_title")} subtitle={t("ros_radar_subtitle")} help={t("help_radar")}>
      {d === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        {att && <Section title={t("ros_attention")} hint={`${att.n}`}><ul className="flex flex-col gap-1 text-xs">{att.items.map((a: any) => <li key={a.kind + a.id} className="border border-border border-l-4 border-l-amber-500 px-2 py-1"><a className="underline" href={a.href}>{a.kind}</a> · {a.text}</li>)}</ul></Section>}
        <Section title="Radar" hint={`${d.items.length}`}>{d.items.length === 0 ? <p className="text-xs text-muted-foreground">—</p> : <div className="grid gap-2 xl:grid-cols-2">{d.items.map((i: any) => <RadarCard key={i.radar_id} item={i} pipeline={d.pipeline} labels={labels} />)}</div>}</Section>
      </>)}
    </Shell>
  );
}
