import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell } from "@/components/shell";
import { ExperimentsTable } from "@/components/tables/experiments-table";

export default async function Experiments() {
  const { t } = await getT();
  const r = await api("/api/registries/experiments");
  return <Shell title={t("nav_experiments")} subtitle={`${r.count} Experimente, Repairs und Validierungen. ${r.note}`}>
    <ExperimentsTable rows={r.experiments} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title") }} />
  </Shell>;
}
