import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";

export default async function Governance() {
  const { t } = await getT();
  const g = await api("/api/governance-record");
  return (
    <Shell title={t("nav_governance")} subtitle={`Status: ${g.status}. Aktive Provider-/Billing-Grenzen und Flag-Whitelist aus INFERENCE-GOVERNANCE.json; Superseded-Blöcke bleiben Geschichte.`}>
      <Section title="Aktive Gates (G1–G4)"><Table head={["Gate", "Entscheidung", "Kern"]} rows={g.gates.map((x: any) => [x.id, x.decision, x.summary])} /></Section>
      <Section title="Caps"><Table head={["Cap", "Wert"]} rows={Object.entries(g.caps as Record<string, any>).map(([k, v]) => [k, String(v)])} /></Section>
      <Section title="Erlaubte CLI-Flags"><p className="font-mono text-xs">{g.allowed_flags.join("  ")}</p><p className="mt-1 text-xs text-muted-foreground">verboten: {g.forbidden_flags.join(", ")}</p></Section>
      <Section title="Superseded (Geschichte)"><Table head={["Block", "Status", "Superseded by"]} rows={g.superseded.map((x: any) => [x.id, x.status, x.superseded_by])} /></Section>
      <Section title="Offene Governance-Fragen"><ul className="list-disc pl-5 text-sm">{g.open.map((x: string) => <li key={x}>{x}</li>)}</ul></Section>
    </Shell>
  );
}
