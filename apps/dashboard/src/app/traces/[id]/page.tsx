import Link from "next/link";
import { notFound } from "next/navigation";
import { rosGet, rosGetMaybe } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { Waterfall, Rescore, MlflowFetch } from "@/components/ros/trace-view";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function TracePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; const { t } = await getT();
  const d = await rosGetMaybe(`/api/ros/runs/${id}/trace`); const at = await rosGet(`/api/ros/runs/${id}/all-traces`).catch(() => null);
  if (d === null) return <Shell title={id}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  if (d === "NOT_FOUND" || !(d as any)?.run) notFound();
  const r = d.run; const inv = d.invocations[0];
  return (
    <Shell title={`Trace — ${r.run_id}`} subtitle={`${r.kind} · ${r.thesis_id ?? "—"} · ${r.state} · ${d.n_events} events`}>
      {at && <Section title={t("obs_all_traces")}>
        <ul className="grid gap-1 text-xs md:grid-cols-2">
          <li>MLflow: <span className="font-mono">{at.mlflow?.run_id ?? "—"}</span> {at.mlflow?.reachable ? <a className="underline" href={at.mlflow.ui} target="_blank" rel="noreferrer">öffnen</a> : <span className="text-muted-foreground">({JSON.stringify(at.mlflow?.detail ?? {}).slice(0, 80)})</span>}</li>
          <li>Langfuse: <span className="font-mono">{at.langfuse?.trace_id ?? "—"}</span> {at.langfuse?.reachable ? <a className="underline" href={at.langfuse.ui} target="_blank" rel="noreferrer">öffnen</a> : <span className="text-muted-foreground">nicht verknüpft</span>}</li>
          <li>OTel: <span className="font-mono">{(at.otel?.trace_ids ?? []).length} Spans</span> · <a className="underline" href={at.otel?.zpages} target="_blank" rel="noreferrer">zPages</a></li>
          <li>Branch: <span className="break-all font-mono">{at.branch ?? "—"}</span> @ {String(at.commit ?? "").slice(0, 10)}</li>
          <li className="md:col-span-2 break-all">Artefakte: <span className="font-mono">{(at.artifacts ?? []).map((a: any) => a.artifact_id.split(":").pop()).join(" · ") || "—"}</span></li>
          {at.telemetry_degraded?.length > 0 && <li className="md:col-span-2 text-amber-700">Telemetrie degradiert: {at.telemetry_degraded.join(" · ")}</li>}
        </ul>
      </Section>}
      <Section title={t("ros_waterfall")}><Waterfall bars={d.waterfall} /></Section>
      <div className="grid gap-8 xl:grid-cols-2">
        <Section title={t("ros_invocation")}>
          {inv ? <Table head={["Feld", "Wert"]} rows={[["requested_model", inv.invoke.requested_model], ["resolved_model", inv.result.resolved_model ?? "—"], ["evidence_class", inv.result.evidence_class ?? "—"], ["status", inv.result.status], ["reason_code", inv.result.reason_code ?? "—"], ["turns", String(inv.result.turns ?? "—")], ["latency_s", String(inv.result.latency_s ?? "—")], ["max_turns", String(inv.invoke.max_turns)], ["allowed_tools", (inv.invoke.allowed_tools ?? []).join(", ")], ["disallowed_tools", (inv.invoke.disallowed_tools ?? []).join(", ")], ["usage", JSON.stringify(inv.result.usage ?? {})], ["stdout_sha256", inv.result.stdout_sha256 ?? "—"], ["cli_version", inv.result.cli_version ?? "—"]]} /> : <p className="text-xs text-muted-foreground">—</p>}
        </Section>
        <Section title={t("ros_links")}>
          <Table head={["Ziel", "ID"]} rows={[["MLflow run", d.links[0]?.mlflow_run_id ?? "—"], ["MLflow UI", d.mlflow_ui ? <a key="m" className="underline" href={d.mlflow_ui} target="_blank" rel="noreferrer">{t("ros_mlflow_open")}</a> : "—"], ["OTel traces", d.links.filter((l: any) => l.trace_id).map((l: any) => l.trace_id).join(", ") || "—"], ["Langfuse", d.telemetry.langfuse_trace_id ?? "—"], ["Stack", d.telemetry.stack ?? "—"], ["Branch", r.branch ?? "—"]]} />
          {d.telemetry.degraded?.length > 0 && <p className="mt-2 text-xs text-amber-700">{t("ros_degraded")}: {d.telemetry.degraded.join(" · ")}</p>}
          <div className="mt-2"><MlflowFetch runId={r.run_id} /></div>
        </Section>
        <Section title={t("ros_artifacts")} hint={`${d.artifacts.length}`}><Table head={["Artefakt", "Art", "SHA-256"]} rows={d.artifacts.map((a: any) => [a.artifact_id.split(":").pop(), a.kind, <code key={a.artifact_id} className="break-all font-mono text-[0.65rem]">{a.sha256}</code>])} /></Section>
        <Section title={t("ros_rescore")}><Rescore runId={r.run_id} label={t("ros_rescore")} hint={t("ros_rescore_hint")} /></Section>
      </div>
      <p className="text-xs"><Link className="underline" href={`/runs/${r.run_id}`}>{t("ros_console")}</Link> · <Link className="underline" href="/traces">/traces</Link></p>
    </Shell>
  );
}
