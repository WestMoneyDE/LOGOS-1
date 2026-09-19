import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { PreflightButton, QuotaReset } from "@/components/ros/governor-panel";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function ClaudeAuth() {
  const { t } = await getT(); const g = await rosGet("/api/ros/governor");
  return (
    <Shell title={t("ros_claude_title")} subtitle={t("ros_claude_subtitle")}>
      {g === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <Section title={t("ros_attestation")} hint={g.attestation.present ? `${g.attestation.fresh ? "fresh" : "STALE"} · ${g.attestation.age_h} h` : "—"}>
          <div className="mb-3"><PreflightButton label={t("ros_preflight")} /></div>
          <Table head={["Feld", "Wert"]} rows={[["auth_class", g.attestation.auth_class ?? "—"], ["cli_version", g.attestation.cli_version ?? "—"], ...Object.entries(g.attestation.auth ?? {}).map(([k, v]) => [k, String(v)]), ["at", g.attestation.at ?? "—"], ["ttl_h", String(g.attestation_ttl_h)]]} className="max-w-2xl" />
        </Section>
        <Section title={t("ros_contamination")}><Table head={["Variable", "Präsenz"]} rows={Object.entries(g.contamination_presence as Record<string, boolean>).map(([k, v]) => [k, v ? "PRESENT" : "absent"])} className="max-w-2xl" /></Section>
        <Section title={t("ros_quota")} hint={g.quota.state}><div className="mb-2"><QuotaReset label={t("ros_quota_reset")} /></div><p className="font-mono text-xs text-muted-foreground">{JSON.stringify(g.quota)}</p></Section>
        <Section title={t("ros_caps")} hint={g.cap_change_path}><Table head={["Cap", "Wert"]} rows={Object.entries(g.caps).map(([k, v]) => [k, String(v)])} className="max-w-2xl" /><p className="mt-1 text-xs text-muted-foreground">model pin source: {g.model_pin_source}</p></Section>
      </>)}
    </Shell>
  );
}
