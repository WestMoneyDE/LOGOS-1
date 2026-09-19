import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell } from "@/components/shell";
import { ClaimsTable } from "@/components/tables/claims-table";

export default async function Claims() {
  const { t } = await getT();
  const r = await api("/api/registries/claims");
  return <Shell title={t("claims_title")} subtitle={`${r.count} Claims. ${t("claims_subtitle")}`}>
    <ClaimsTable rows={r.claims} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title") }} />
  </Shell>;
}
