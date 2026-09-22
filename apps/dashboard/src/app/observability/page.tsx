import Link from "next/link";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { RecordsOnly } from "@/components/ros/records-only";
import { cn } from "cn";

export default async function Observability() {
  const { t } = await getT(); const d = await rosGet("/api/ros/observability?limit=25");
  return (
    <Shell title={t("obs_title")} subtitle={t("obs_subtitle")} help={t("obs_subtitle")}>
      {d === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <Section title={t("obs_systems")} hint={`${d.systems.filter((s: any) => s.state === "reachable").length}/${d.systems.length}`}>
          <div className="grid gap-2 md:grid-cols-2" aria-label="systems">
            {d.systems.map((s: any) => (
              <div key={s.system} className={cn("flex flex-wrap items-baseline gap-2 border border-l-4 p-2 text-sm", s.state === "reachable" ? "border-l-emerald-600" : "border-l-rose-600")} data-system={s.system}>
                <span className={cn("inline-block h-2 w-2 rounded-full", s.state === "reachable" ? "bg-emerald-600" : "bg-rose-600")} />
                <span className="font-medium">{s.system}</span>
                <span className="font-mono text-[0.6rem] uppercase tracking-widest text-muted-foreground">{s.criticality}</span>
                <span className="grow" />
                <a className="font-mono text-xs underline" href={s.link} target={s.link?.startsWith("http") ? "_blank" : undefined} rel="noreferrer">{t("obs_open")}</a>
                <span className="basis-full text-xs text-muted-foreground">{s.purpose}</span>
                <span className="basis-full break-all font-mono text-[0.6rem] text-muted-foreground">{s.state} · {JSON.stringify(s.detail).slice(0, 160)}</span>
              </div>))}
          </div>
          <p className="mt-2 text-[0.65rem] text-muted-foreground">{t("obs_keys")}</p>
        </Section>

        <Section title={t("obs_mlflow")} hint={d.mlflow.reachable ? `${d.mlflow.n} · ${d.mlflow.experiment_id}` : "nicht erreichbar"}>
          {!d.mlflow.reachable ? <p className="text-xs text-rose-700">nicht erreichbar: {JSON.stringify(d.mlflow.detail)}</p> :
            <Table head={["Run", "Status", "Modell", "Metriken", "MLflow"]} rows={d.mlflow.runs.slice(0, 12).map((r: any) => [
              <span key="n" className="font-mono text-xs">{r.name}</span>, r.status, <span key="m" className="font-mono text-xs">{r.params?.model_resolved || r.params?.model_requested || "—"}</span>,
              <span key="k" className="font-mono text-[0.65rem]">{Object.entries(r.metrics || {}).slice(0, 4).map(([k, v]: any) => `${k}=${typeof v === "number" ? v.toFixed(2) : v}`).join(" · ")}</span>,
              <a key="u" className="underline" href={r.ui} target="_blank" rel="noreferrer">{t("obs_open")}</a>])} />}
        </Section>

        <Section title={t("obs_langfuse")} hint={d.langfuse.reachable ? `${d.langfuse.n}` : "nicht erreichbar"}>
          {!d.langfuse.reachable ? <p className="text-xs text-rose-700">nicht erreichbar: {JSON.stringify(d.langfuse.detail)}</p> :
            <Table head={["Trace", "Name", "Session (Lauf)", "Beobachtungen", "Langfuse"]} rows={d.langfuse.traces.slice(0, 12).map((x: any) => [
              <span key="i" className="font-mono text-[0.65rem]">{String(x.trace_id).slice(0, 12)}</span>, x.name, <span key="s" className="font-mono text-xs">{x.session_id ?? "—"}</span>, String(x.observations ?? "—"),
              <a key="u" className="underline" href={x.ui} target="_blank" rel="noreferrer">{t("obs_open")}</a>])} />}
        </Section>

        <Section title={t("obs_otel")}><p className="text-xs text-muted-foreground">{d.otel.note} · <a className="underline" href={d.otel.zpages} target="_blank" rel="noreferrer">zPages</a></p></Section>

        <Section title={t("obs_runs")} hint={`${d.runs.length}`}>
          <Table head={["Lauf", "Art", "Zustand", "MLflow", "OTel", "Alle Spuren"]} rows={d.runs.map((r: any) => [
            <Link key="l" className="font-mono text-xs underline" href={`/runs/${r.run_id}`}>{r.run_id}</Link>, r.kind, r.state,
            <span key="m" className="font-mono text-[0.65rem]">{r.links.mlflow_run_id ? String(r.links.mlflow_run_id).slice(0, 10) : "—"}</span>,
            <span key="o" className="font-mono text-[0.65rem]">{r.links.otel.length}</span>,
            <Link key="t" className="underline" href={`/traces/${r.run_id}`}>{t("obs_all_traces")}</Link>])} />
        </Section>
      </>)}
    </Shell>
  );
}
