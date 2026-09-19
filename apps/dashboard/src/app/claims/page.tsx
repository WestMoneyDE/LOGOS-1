import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell } from "@/components/shell";
import { ClaimCard } from "@/components/claim-card";

export default async function Claims() {
  const { t } = await getT();
  const r = await api("/api/registries/claims");
  return <Shell title={t("claims_title")} subtitle={`${r.count} Claims. ${t("claims_subtitle")}`}><div className="grid gap-3">{r.claims.map((c: any) => <ClaimCard key={c.claim_id} c={c} />)}</div></Shell>;
}
