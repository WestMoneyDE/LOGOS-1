import Link from "next/link";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { InboxForm } from "@/components/ros/inbox-form";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Inbox() {
  const { t } = await getT(); const d = await rosGet("/api/ros/inbox");
  return (
    <Shell title={t("ros_inbox_title")} subtitle={t("ros_inbox_subtitle")}>
      {d === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <Section title={t("ros_inbox_add")}><InboxForm kinds={d.kinds} labels={{ add: t("ros_inbox_add"), text: t("ros_inbox_text"), source: t("ros_inbox_source"), kind: t("ros_inbox_kind") }} /></Section>
        <Section title="Einträge" hint={`${d.items.length}`}>{d.items.length === 0 ? <p className="text-xs text-muted-foreground">—</p> : <Table head={["#", "Art", "Text", "Quelle", "Radar", "Status"]} rows={d.items.map((i: any) => [String(i.item_id), i.kind, <span key="t" className="text-xs">{i.text.slice(0, 160)}</span>, i.source ?? "—", i.radar_id ? <Link key="r" className="font-mono text-xs underline" href="/radar">#{i.radar_id}</Link> : "—", i.radar_state ?? i.state])} />}</Section>
      </>)}
    </Shell>
  );
}
