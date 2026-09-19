import { api } from "@/lib/api";
import { Shell, Section, Table, Src } from "@/components/shell";
import { KindBadge, StatusBadge } from "@/components/badges";
import { InvariantGraph } from "@/components/invariant-graph";

export default async function Invariants() {
  const r = await api("/api/registries/invariants"); const g = await api("/api/invariants/graph");
  return (
    <Shell title="Invariant registry" subtitle={`${r.count} invariants (CANONICAL from GAMMA.md, PROPOSED from the research radar). Relations: ${r.relation_vocabulary.join(", ")}.`}>
      <Section title="Invariant graph" hint="click a node for definition, origin, evidence, counterexamples, experiments"><InvariantGraph nodes={g.nodes} edges={g.edges} invariants={r.invariants} /></Section>
      <Section title="All invariants"><Table head={["id", "statement", "track", "class", "status", "kind", "origin", "relations"]} rows={r.invariants.map((i: any) => [<code key="i" className="font-mono text-xs">{i.invariant_id}</code>, i.statement, i.track, i.class, <StatusBadge key="s" status={i.status} />, <KindBadge key="k" kind={i.kind} />, <Src key="o" path={i.origin} />, i.relations.map((x: any) => `${x.type} → ${x.target}`).join("; ")])} /></Section>
    </Shell>
  );
}
