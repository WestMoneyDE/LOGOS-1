import { api } from "@/lib/api";
import { Shell, Table, Src } from "@/components/shell";
import { Severity } from "@/components/badges";

export default async function Counterexamples() {
  const r = await api("/api/registries/claims");
  return <Shell title="Counterexample registry" subtitle="Failure discovered is scientific progress: counterexample → violated assumption → severity → repair → validation → remaining risk.">
    <Table head={["id", "counterexample", "experiment", "violated assumption", "severity", "repair", "validation", "remaining risk", "what was learned", "source"]} rows={r.counterexamples.map((c: any) => [<code key="c" className="font-mono text-xs">{c.ce_id}</code>, c.name, c.experiment, c.violated_assumption, <Severity key="s" s={c.severity} />, c.repair, c.validation, c.remaining_risk, c.learned, <Src key="p" path={c.source} />])} />
  </Shell>;
}
