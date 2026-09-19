import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Table, Src } from "@/components/shell";
import { KindBadge, VerdictBadge } from "@/components/badges";

export default async function Experiments() {
  const r = await api("/api/registries/experiments");
  return <Shell title="Experiment registry" subtitle={`${r.count} experiments, repairs and validations. ${r.note}`}>
    <Table head={["id", "track", "verdict", "kind", "negative", "prereg", "run", "record"]} rows={r.experiments.map((e: any) => [<Link key="e" href={`/experiments/${e.experiment_id}`} className="font-mono text-xs underline">{e.experiment_id}</Link>, e.research_track, <VerdictBadge key="v" verdict={e.verdict} />, <KindBadge key="k" kind={e.kind} />, e.negative_result ? "yes" : "", <code key="p" className="font-mono text-[0.65rem]">{e.prereg_hash.slice(0, 12) || "—"}</code>, <code key="r" className="font-mono text-[0.65rem]">{e.run_id.replace(/^.*-run-/, "run-") || "—"}</code>, <Src key="s" path={e.record} />])} />
  </Shell>;
}
