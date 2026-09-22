import Link from "next/link";
import { api } from "@/lib/api";
import { rosGet, type RosThesis } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { ThesesSelector } from "@/components/theses-selector";
import { CreateThesis } from "@/components/ros/create-thesis";
import { RosThesesTable } from "@/components/ros/theses-table";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Theses() {
  const { t } = await getT();
  const claims = (await api("/api/registries/claims")).claims; const active = (await api("/api/theses/active")).active;
  const ros = await rosGet<{ theses: RosThesis[] }>("/api/ros/theses");
  const existing = new Set((ros?.theses ?? []).flatMap((x) => x.claim_ids));
  return (
    <Shell title={t("ros_theses_title")} subtitle={t("ros_theses_subtitle")} help={t("help_theses")}>
      <Section title={t("ros_lifecycle")} hint="ros_theses">
        {ros === null ? <RecordsOnly text={t("ros_records_only")} /> : ros.theses.length === 0 ? <p className="text-sm text-muted-foreground">{t("ros_no_theses")}</p> : <RosThesesTable rows={ros.theses} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title") }} />}
        {ros !== null && active.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2 text-xs">{active.map((a: any) => (
            <li key={a.claim.claim_id} className="inline-flex items-center gap-2 border border-border px-2 py-1"><span className="font-mono">{a.claim.claim_id}</span>{existing.has(a.claim.claim_id) ? <Link href={`/theses/ROS-${a.claim.claim_id}`} className="underline">ROS-{a.claim.claim_id}</Link> : <CreateThesis claim={a.claim} existing={false} label={t("ros_create_thesis")} />}</li>))}
          </ul>)}
        <p className="mt-2 text-xs text-muted-foreground">Board: <Link href="/board" className="underline">/board</Link></p>
      </Section>
      <Section title="Selection" hint="ACTIVE-THESES.json"><ThesesSelector claims={claims} active={active.map((a: any) => a.claim.claim_id)} /></Section>
    </Shell>
  );
}
