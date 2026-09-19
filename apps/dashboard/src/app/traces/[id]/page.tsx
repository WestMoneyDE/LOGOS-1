import Link from "next/link";
import { notFound } from "next/navigation";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { Waterfall, Rescore, MlflowFetch } from "@/components/ros/trace-view";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function TracePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; const { t } = await getT();
  const d = await rosGet(`/api/ros/runs/${id}/trace`);
  if (d === null) return <Shell title={id}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  if (!d.run) notFound();
  const r = d.run; const inv = d.invocations[0];
  return (
    <Shell title={`Trace — ${r.run_id}`} subtitle={`${r.kind} · ${r.thesis_id ?? "—"} · ${r.state} · ${d.n_events} events`}>
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
