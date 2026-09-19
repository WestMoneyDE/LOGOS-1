import { api } from "@/lib/api";
import { Shell, Section, Table, Src } from "@/components/shell";
import { KindBadge, VerdictBadge } from "@/components/badges";

export default async function ExperimentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const d = await api(`/api/experiments/${id}`); const e = d.experiment;
  const rows: [string, React.ReactNode][] = [["order", e.order_id], ["verdict", <VerdictBadge key="v" verdict={e.verdict} />], ["kind", <KindBadge key="k" kind={e.kind} />], ["question", e.scientific_question], ["hypothesis", e.hypothesis],
    ["model / provider", e.model_provider], ["sample size", e.sample_size || "—"], ["controls", e.controls || "—"], ["metrics", e.metrics.join("; ") || "—"], ["construct status", e.construct_status || "—"],
    ["prereg hash", <code key="p" className="font-mono text-xs">{e.prereg_hash || "— (deterministic order: prereg recorded in the closure)"}</code>], ["run id", <code key="r" className="font-mono text-xs">{e.run_id || "—"}</code>], ["artifact hash", <code key="a" className="font-mono text-xs">{e.artifact_hash || "—"}</code>],
    ["commit / PR", `${e.commit || "—"} / ${e.pr ? "#" + e.pr : "—"}`], ["record", <Src key="s" path={e.record} />], ["next experiment", e.next_experiment || "—"], ["lab run status", d.lab_run ? `${d.lab_run.run_status} · verdict ${d.lab_run.scientific_verdict ?? "none"} · git ${d.lab_run.git_sha}` : "not in lab / records-only"]];
  return (
    <Shell title={e.experiment_id} subtitle={e.order_id}>
      <Table head={["field", "value"]} rows={rows.map(([k, v]) => [k, v])} />
      <Section title="Limitations">{e.limitations.length ? <ul className="list-disc pl-5 text-sm">{e.limitations.map((l: string) => <li key={l}>{l}</li>)}</ul> : <p className="text-sm text-muted-foreground">none recorded</p>}</Section>
      {d.closure?.closure_block && <Section title="Closure block (verbatim from the record)"><pre className="overflow-x-auto border border-border bg-muted/30 p-3 text-xs">{d.closure.closure_block}</pre></Section>}
    </Shell>
  );
}
