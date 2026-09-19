import { api } from "@/lib/api";
import { rosGet, type RosDecision } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { DecisionCard } from "@/components/ros/decisions";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Decisions() {
  const { t } = await getT();
  const ros = await rosGet<{ decisions: RosDecision[] }>("/api/ros/decisions"); const closures = await api("/api/closures");
  const openQ = (closures.closures ?? closures).flatMap((c: any) => (c.open_decisions ?? []).map((q: string) => ({ id: c.id, q })));
  const labels = { approve: t("ros_approve"), reject: t("ros_reject"), defer: t("ros_defer"), ifApproved: t("ros_if_approved"), ifRejected: t("ros_if_rejected"), blocks: t("ros_blocks") };
  return (
    <Shell title={t("ros_decisions_title")} subtitle={t("ros_decisions_subtitle")} help={t("help_decisions")}>
      <Section title="Gate-Center" hint="ros_decisions">
        {ros === null ? <RecordsOnly text={t("ros_records_only")} /> : ros.decisions.length === 0 ? <p className="text-xs text-muted-foreground">—</p> : <div className="grid gap-2 xl:grid-cols-2">{ros.decisions.map((d) => <DecisionCard key={d.decision_id} d={d} labels={labels} />)}</div>}
      </Section>
      <Section title={t("ros_open_from_closures")} hint={`${openQ.length}`}>
        <ul className="flex max-w-4xl flex-col gap-2 text-sm">{openQ.map((x: any, i: number) => <li key={i} className="border border-border border-l-4 border-l-amber-500 p-3"><span className="font-mono text-xs text-muted-foreground">{x.id}</span><p className="mt-1">{x.q}</p></li>)}</ul>
      </Section>
    </Shell>
  );
}
