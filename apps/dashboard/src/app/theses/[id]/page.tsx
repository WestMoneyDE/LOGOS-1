import Link from "next/link";
import { notFound } from "next/navigation";
import { rosGet, rosGetMaybe } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { ThesisLifecycle } from "@/components/ros/thesis-lifecycle";
import { EventLog } from "@/components/ros/event-log";
import { Notes } from "@/components/ros/notes";
import { ThesisState, WoState, JobState } from "@/components/ros/state-badge";
import { RecordsOnly } from "@/components/ros/records-only";
import { AgentJob } from "@/components/ros/agent-job";
import { GateChain } from "@/components/ros/gate-chain";

export default async function ThesisWorkspace({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; const { t } = await getT();
  const d = await rosGetMaybe(`/api/ros/theses/${id}`); const chainRaw = await rosGetMaybe(`/api/ros/theses/${id}/gates`); const chain = chainRaw === "NOT_FOUND" ? null : chainRaw; const meas = await rosGet(`/api/ros/measurements?thesis_id=${id}`);
  if (d === null) return <Shell title={id} help={t("help_theses")}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  if (d === "NOT_FOUND" || !(d as any)?.thesis) notFound();
  const th = d.thesis;
  return (
    <Shell title={`${th.thesis_id} — ${th.title}`} subtitle={`${th.track} · Claims: ${th.claim_ids.join(", ") || "—"} · Owner ${th.owner}`}>
      <Section title={t("ros_lifecycle")} hint={`${t("ros_agent_ceiling")}: ${d.agent_ceiling}`}>
        <div className="mb-2"><ThesisState state={th.state} /></div>
        <ThesisLifecycle thesisId={th.thesis_id} state={th.state} available={d.available_events} agentCeiling={d.agent_ceiling} labels={{ available: t("ros_available"), actor: t("ros_actor"), gate: t("ros_founder_gate"), reason: t("ros_reason"), apply: t("ros_apply"), ceiling: t("ros_agent_ceiling") }} />
      </Section>
      <Section title="Agent" hint="thesis_advance">
        <AgentJob thesisId={th.thesis_id} jobs={d.jobs} labels={{ enqueue: t("ros_agent_job"), hint: t("ros_agent_job_hint"), gate: t("ros_gate_preview"), start: t("ros_start"), stop: t("ros_stop") }} />
        {d.runs.length > 0 && <ul className="mt-2 flex flex-wrap gap-2 text-xs">{d.runs.map((r: any) => <li key={r.run_id}><Link className="font-mono underline" href={`/runs/${r.run_id}`}>{r.run_id}</Link> <span className="text-muted-foreground">{r.state}</span></li>)}</ul>}
      </Section>
      {chain && <Section title={t("gate_title")} hint={t("gate_hint")}>
        <GateChain thesisId={th.thesis_id} chain={chain} labels={{ founder: t("gate_founder"), run: t("gate_run"), check_ok: t("gate_check_ok"), check_failed: t("gate_check_failed"), planned: t("gate_planned"), dry_ok: t("gate_dry_ok"), dry_failed: t("gate_dry_failed"), counters: t("gate_counters"), frozen_in_lab: t("gate_frozen_in_lab"), measurement_queued: t("gate_measurement_queued"), data_points: t("gate_data_points"), open_measurement: t("gate_open_measurement") }} />
        {meas?.measurements?.length > 0 && <ul className="mt-2 flex flex-wrap gap-2 text-xs">{meas.measurements.map((m: any) => <li key={m.measurement_id}><Link className="font-mono underline" href={`/measurements/${m.measurement_id}`}>{m.measurement_id}</Link> <span className="text-muted-foreground">{m.state} · {m.executed}/{m.planned} · {m.summary?.proposal?.verdict ?? "—"}</span></li>)}</ul>}
      </Section>}
      <div className="grid gap-8 xl:grid-cols-2">
        <Section title="Work Orders" hint={`${d.work_orders.length}`}>
          {d.work_orders.length === 0 ? <p className="text-xs text-muted-foreground">— <Link href="/work-orders" className="underline">/work-orders</Link></p> : <ul className="flex flex-col gap-1 text-sm">{d.work_orders.map((w: any) => <li key={w.work_order_id} className="flex flex-wrap items-center gap-2 border border-border p-2"><span className="font-mono text-xs">{w.work_order_id}</span><WoState state={w.state} /><span className="text-xs text-muted-foreground">{w.spec.question}</span></li>)}</ul>}
        </Section>
        <Section title="Jobs" hint={`${d.jobs.length}`}>
          {d.jobs.length === 0 ? <p className="text-xs text-muted-foreground">— <Link href="/queue" className="underline">/queue</Link></p> : <ul className="flex flex-col gap-1 text-sm">{d.jobs.map((j: any) => <li key={j.job_id} className="flex flex-wrap items-center gap-2 border border-border p-2"><span className="font-mono text-xs">#{j.job_id} {j.kind}</span><JobState state={j.state} />{j.locked_by && <span className="font-mono text-xs text-muted-foreground">{j.locked_by}</span>}</li>)}</ul>}
        </Section>
        <Section title={t("nav_decisions")} hint={`${d.decisions.length}`}>
          {d.decisions.length === 0 ? <p className="text-xs text-muted-foreground">—</p> : <ul className="flex flex-col gap-1 text-sm">{d.decisions.map((x: any) => <li key={x.decision_id} className="border border-border p-2"><span className="font-mono text-xs">{x.decision_id} · {x.kind} · {x.state}</span><br />{x.why}</li>)}</ul>}
        </Section>
        <Section title={t("ros_notes")}><Notes thesisId={th.thesis_id} notes={d.notes} labels={{ placeholder: t("ros_note_placeholder"), add: t("ros_add_note"), flag: t("ros_decision_flag") }} /></Section>
      </div>
      <Section title={t("ros_events")} hint={`${d.events.length}`}><EventLog events={d.events} /></Section>
    </Shell>
  );
}
