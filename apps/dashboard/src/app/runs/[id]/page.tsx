import Link from "next/link";
import { notFound } from "next/navigation";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { RunConsole } from "@/components/ros/run-console";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; const { t } = await getT();
  const d = await rosGet(`/api/ros/runs/${id}`);
  if (d === null) return <Shell title={id}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  if (!d.run) notFound();
  const r = d.run;
  return (
    <Shell title={`${t("ros_console")} — ${r.run_id}`} subtitle={`${r.kind} · ${r.thesis_id ?? "—"} · job #${r.job_id ?? "—"} · ${r.branch ?? ""}`}>
      <RunConsole run={r} job={d.job} initial={d.events} labels={{ start: t("ros_start"), pause: t("ros_pause"), resume: t("ros_resume"), stop: t("ros_stop"), live: t("ros_live"), finished: t("ros_finished"), none: t("ros_no_events"), notes: t("ros_notes"), notePlaceholder: t("ros_note_placeholder"), addNote: t("ros_add_note") }} />
      <Section title="Links">
        <ul className="flex flex-wrap gap-3 text-xs">{r.thesis_id && <li><Link className="underline" href={`/theses/${r.thesis_id}`}>{r.thesis_id}</Link></li>}<li><Link className="underline" href="/queue">/queue</Link></li><li><Link className="underline" href="/runs">/runs</Link></li>{r.worktree && <li><code className="font-mono">{r.worktree}</code></li>}</ul>
      </Section>
    </Shell>
  );
}
