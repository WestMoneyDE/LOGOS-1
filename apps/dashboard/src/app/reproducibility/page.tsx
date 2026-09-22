import { api } from "@/lib/api";
import { Shell, Table, Src } from "@/components/shell";

export default async function Repro() {
  const r = await api("/api/reproducibility");
  return <Shell title="Reproducibility" subtitle={r.records_only ? "lab unreachable — records-only mode" : "per completed run: commit, prereg hash, run id, artifact hash, provider/model, lab status"}>
    <Table head={["experiment", "run id", "commit", "prereg hash", "artifact hash", "model / provider", "lab status", "reproduce", "record"]} rows={r.runs.map((x: any) => [x.experiment_id, <code key="r" className="font-mono text-[0.65rem]">{x.run_id}</code>, x.commit ?? "—", <code key="p" className="font-mono text-[0.65rem]">{x.prereg_hash}</code>, <code key="a" className="font-mono text-[0.65rem]">{x.artifact_hash}</code>, x.model_provider, x.lab_status ?? "—", x.requires_live_inference ? "REQUIRES LIVE INFERENCE — " + x.instructions : x.instructions, <Src key="s" path={x.record} />])} />
  </Shell>;
}
