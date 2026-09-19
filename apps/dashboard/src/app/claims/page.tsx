import { api } from "@/lib/api";
import { Shell } from "@/components/shell";
import { ClaimCard } from "@/components/claim-card";

export default async function Claims() {
  const r = await api("/api/registries/claims");
  return <Shell title="Claim registry" subtitle={`${r.count} claims. Status of hypothesis ≠ strength of evidence; both are shown. Statuses come only from the registry, never from free text.`}><div className="grid gap-3">{r.claims.map((c: any) => <ClaimCard key={c.claim_id} c={c} />)}</div></Shell>;
}
