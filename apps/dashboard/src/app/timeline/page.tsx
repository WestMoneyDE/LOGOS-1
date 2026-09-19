import { api } from "@/lib/api";
import { Shell, Section, Table } from "@/components/shell";
import { VerdictBadge } from "@/components/badges";

export default async function Timeline() {
  const t = await api("/api/timeline");
  return (
    <Shell title="Scientific timeline" subtitle="hypothesis → prereg → run → counterexample → repair → independent validation → rerun → verdict → next question">
      <Section title="Work-order closures (chronological)"><Table head={["closed", "order", "kind", "verdict", "successor"]} rows={t.closures.map((c: any) => [c.date ?? "—", c.order_id, c.kind ?? "—", c.verdict ? <VerdictBadge key="v" verdict={c.verdict} /> : "—", c.successor ?? "—"])} /></Section>
      <Section title="Experiment chain"><Table head={["experiment", "order", "verdict", "next"]} rows={t.experiments.map((e: any) => [e.experiment_id, e.order_id, <VerdictBadge key="v" verdict={e.verdict} />, e.next || "—"])} /></Section>
    </Shell>
  );
}
