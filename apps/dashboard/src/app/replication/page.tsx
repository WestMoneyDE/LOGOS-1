import { api } from "@/lib/api";
import { Shell, Section, Table } from "@/components/shell";

export default async function Replication() {
  const r = await api("/api/registries/replication");
  return (
    <Shell title="Replication layer" subtitle={r.note}>
      <Section title="Per finding" hint="counts are not quality scores; the tooltip-style notes say which replication is missing"><Table head={["finding", "claim", "count", "same model", "different seed", "different model", "different provider", "external researcher", "what is missing", "external validation needs"]} rows={r.replications.map((x: any) => [x.finding, x.claim_id, x.count, ...r.levels.map((l: string) => (x.levels[l] ? "✓" : "—")), x.notes, x.external_validation_needs.join(", ")])} /></Section>
      <Section title="External validation queue"><ul className="list-disc pl-5 text-sm">{r.external_validation_queue.map((q: string) => <li key={q}>{q}</li>)}</ul></Section>
    </Shell>
  );
}
