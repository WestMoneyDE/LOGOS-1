import Link from "next/link";
import { notFound } from "next/navigation";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { RunConsole } from "@/components/ros/run-console";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; const { t } = await getT();
  const d = await rosGet(`/api/ros/runs/${id}`); const wc = await rosGet("/api/ros/workers/control");
  if (d === null) return <Shell title={id}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  if (!d.run) notFound();
  const r = d.run;
  const keys = ["ros_start", "ros_pause", "ros_resume", "ros_stop", "ros_live", "ros_finished", "ros_no_events", "ros_notes", "ros_note_placeholder", "ros_add_note", "console_packet", "console_result", "console_feed", "console_empty_waiting", "console_empty_host", "console_empty_quota", "console_empty_queued", "console_reads", "console_writes", "console_searches", "console_web", "console_skill", "console_says", "console_thinks", "console_tool_result"] as const;
  const l = Object.fromEntries(keys.map((k) => [k, t(k)]));
  return (
    <Shell title={`${t("ros_console")} — ${r.run_id}`} subtitle={`${r.kind} · ${r.thesis_id ?? "—"} · job #${r.job_id ?? "—"} · ${r.branch ?? ""}`} help={t("help_runs")}>
      <RunConsole run={r} job={d.job} initial={d.events} hostAlive={!!wc?.host?.alive} l={l} />
      <Section title="Links">
        <ul className="flex flex-wrap gap-3 text-xs">{r.thesis_id && <li><Link className="underline" href={`/theses/${r.thesis_id}`}>{r.thesis_id}</Link></li>}<li><Link className="underline" href={`/traces/${r.run_id}`}>Trace</Link></li><li><Link className="underline" href="/queue">/queue</Link></li><li><Link className="underline" href="/runs">/runs</Link></li>{r.worktree && <li><code className="font-mono">{r.worktree}</code></li>}</ul>
      </Section>
    </Shell>
  );
}
