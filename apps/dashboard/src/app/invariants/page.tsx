import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { InvariantGraph } from "@/components/invariant-graph";
import { InvariantsTable } from "@/components/tables/invariants-table";

export default async function Invariants() {
  const { t } = await getT();
  const r = await api("/api/registries/invariants"); const g = await api("/api/invariants/graph");
  return (
    <Shell title={t("nav_invariants")} subtitle={`${r.count} Invarianten (CANONICAL aus GAMMA.md, PROPOSED aus dem Research Radar). Relationen: ${r.relation_vocabulary.join(", ")}.`}>
      <Section title="Invariantengraph" hint="Knoten anklicken: Definition, Herkunft, Evidenz, Gegenbeispiele, Experimente"><InvariantGraph nodes={g.nodes} edges={g.edges} invariants={r.invariants} /></Section>
      <Section title="Alle Invarianten"><InvariantsTable rows={r.invariants} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title") }} /></Section>
    </Shell>
  );
}
