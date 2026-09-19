import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Section, Table, Src } from "@/components/shell";
import { VerdictBadge } from "@/components/badges";

export default async function Negative() {
  const d = await api("/api/negative-results");
  const why: Record<string, string> = {
    "EXP-RAD-R1": "why it matters: a memory-claimed effect reached Γ's canonical fields — the single most dangerous authority leak found; learned: one canonical effect owner; changed next: MBG repair + validation + Option A decision",
    "EXP-CPA-R1": "why it matters: the first real-model run stopped on a false drift; learned: instrument evidence must be documented, never map order; changed next: resolver contract, repair order",
    "EXP-CPA-RERUN": "why it matters: H1 falsified with a floor — the model did not attribute visible sources; learned: SourceSeen ≠ SourceReliedOn ≠ SourceCausallyInfluencedAction; changed next: attribution-floor order",
    "EXP-BSP-R1": "why it matters: prose rendering silently dropped binding modality; learned: typed envelopes; changed next: repair R1",
    "EXP-BSP-VAL-R1": "why it matters: the repair itself defaulted authority_origin to human (DENY→ALLOW); learned: independent validation is mandatory; changed next: repair R2",
  };
  return (
    <Shell title="Negative results" subtitle="Falsified hypotheses, invalid measurements, failed repairs and residual findings — shown with equal weight.">
      <Section title="Experiments with negative verdicts"><Table head={["id", "verdict", "hypothesis", "why the result matters / what was learned / what changed next", "record"]} rows={d.experiments.map((e: any) => [<Link key="e" href={`/experiments/${e.experiment_id}`} className="font-mono text-xs underline">{e.experiment_id}</Link>, <VerdictBadge key="v" verdict={e.verdict} />, e.hypothesis, why[e.experiment_id] ?? e.limitations.join("; "), <Src key="r" path={e.record} />])} /></Section>
      <Section title="Counterexamples"><Table head={["id", "name", "severity", "repair", "remaining risk"]} rows={d.counterexamples.map((c: any) => [c.ce_id, c.name, c.severity, c.repair, c.remaining_risk])} /></Section>
      <Section title="Lab negative-result records" hint={d.records_only ? "lab unreachable — records-only mode" : "from the research repository (Postgres)"}><Table head={["id", "hypothesis / finding", "what falsified it", "run"]} rows={d.lab_negative_results.slice(0, 60).map((n: any) => [<code key="i" className="font-mono text-[0.65rem]">{n.negative_id}</code>, n.hypothesis, n.what_falsified_it, <code key="r" className="font-mono text-[0.65rem]">{n.run_id}</code>])} /></Section>
    </Shell>
  );
}
