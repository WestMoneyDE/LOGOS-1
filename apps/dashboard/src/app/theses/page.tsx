import { api } from "@/lib/api";
import { Shell, Section } from "@/components/shell";
import { ThesesSelector } from "@/components/theses-selector";

export default async function Theses() {
  const claims = (await api("/api/registries/claims")).claims; const active = (await api("/api/theses/active")).active;
  return (
    <Shell title="Work on theses" subtitle="Select which theses to work on next — several at once. Selection is recorded in docs/research/dashboard/ACTIVE-THESES.json. Execution is not started here: each selected thesis needs its own governed work order (Part 3 of the dashboard roadmap).">
      <Section title="Selection"><ThesesSelector claims={claims} active={active.map((a: any) => a.claim.claim_id)} /></Section>
    </Shell>
  );
}
