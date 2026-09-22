import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";

export default async function Health() {
  const { t } = await getT();
  const h = await api("/api/health");
  const rows: [string, string][] = [["Lab (Postgres/MinIO)", h.records_only ? `records-only: ${h.lab_error ?? ""}` : "OK"], ["Git", `${h.git.branch} @ ${h.git.head}${h.git.dirty ? " (dirty)" : ""}, unpushed ${h.git.unpushed}`],
    ["Integrität (Registries)", `${h.integrity_violations.length} Verstöße`], ["Zeit", h.time]];
  return (
    <Shell title={t("nav_health")} subtitle="Zustand der Datenquellen; MLflow / Worker / Claude-Auth / Playwright folgen in Phase 3–4.">
      <Section title="Quellen"><Table head={["Komponente", "Status"]} rows={rows.map(([k, v]) => [k, v])} /></Section>
      <Section title="Zähler"><Table head={["Kennzahl", "Wert"]} rows={Object.entries(h.counts as Record<string, any>).map(([k, v]) => [k, typeof v === "object" ? JSON.stringify(v) : String(v)])} /></Section>
    </Shell>
  );
}
