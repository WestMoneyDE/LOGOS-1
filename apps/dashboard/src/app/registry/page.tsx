import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { RegistryEditor, RevertButton } from "@/components/ros/registry-edit";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Registry() {
  const { t } = await getT();
  const p = await rosGet("/api/ros/registry/proposals"); const cl = await rosGet("/api/ros/registry/changelog?limit=50");
  if (p === null) return <Shell title={t("reg_title")}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  const labels = { preview: t("reg_preview"), apply: t("reg_apply"), before: t("reg_before"), after: t("reg_after"), reason: t("reg_reason"), ok: t("reg_ok"), failed: t("reg_failed"), applied: t("reg_applied"), manual: t("reg_manual") };
  return (
    <Shell title={t("reg_title")} subtitle={t("reg_subtitle")} help={t("reg_subtitle")}>
      <Section title={t("reg_proposals")} hint={`${p.n}`}>
        {p.n === 0 && <p className="mb-2 text-sm text-muted-foreground">Keine offenen Vorschläge — Vorschläge entstehen aus entschiedenen Messläufen (Verdict-Entwürfe).</p>}
        <RegistryEditor proposals={p.proposals} editable={p.editable} labels={labels} />
      </Section>
      <Section title={t("reg_changelog")} hint={`${cl?.changes?.length ?? 0}`}>
        {(cl?.changes?.length ?? 0) === 0 ? <p className="text-xs text-muted-foreground">— · {cl?.file}</p> : (<>
          <Table head={["Zeitpunkt", "Wer", "Feld", "vorher → nachher", "Begründung", "Datei-Hash"]} rows={cl.changes.map((c: any, i: number) => [
            String(c.at).slice(0, 19).replace("T", " "), c.actor, <span key="f" className="font-mono text-xs">{c.registry}:{c.entity_id}.{c.field}</span>,
            <span key="v" className="break-all font-mono text-[0.65rem]">{JSON.stringify(c.before).slice(0, 60)} → {JSON.stringify(c.after).slice(0, 60)}</span>,
            <span key="r" className="text-xs">{c.reason}</span>, <span key="h" className="font-mono text-[0.6rem]">{String(c.file_sha256_before).slice(0, 8)}→{String(c.file_sha256_after).slice(0, 8)}</span>])} />
          <div className="mt-2"><RevertButton index={0} label={t("reg_revert")} /></div></>)}
      </Section>
    </Shell>
  );
}
