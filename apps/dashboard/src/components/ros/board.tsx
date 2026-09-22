"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { ActorSelect } from "@/components/ros/actor-select";
import { errText, rosPost, type Actor, type RosThesis, THESIS_STATE_TONE } from "@/lib/ros";

const COLUMNS = ["IDEA", "TRIAGE", "PRIOR_ART", "QUESTION_DEFINED", "HYPOTHESIS_DEFINED", "METRICS_DEFINED", "PREREG_DRAFT", "PREREG_FROZEN", "WORK_ORDER_READY", "DRY_RUN", "READY_TO_RUN", "RUNNING", "ANALYSIS", "VERDICT", "REPLICATION", "PUBLICATION_CANDIDATE", "CLOSED", "BLOCKED_BY_GOVERNANCE", "BLOCKED_BY_DEPENDENCY", "INVALID_MEASUREMENT", "FALSIFIED", "INCONCLUSIVE", "SUPERSEDED"];
/** Which event moves a thesis from `from` to `to` on a drop — mirrors control/state_machines.py (the API is the authority; unknown pairs are rejected there). */
const EVENT: Record<string, string> = {
  "IDEA>TRIAGE": "triage", "TRIAGE>PRIOR_ART": "start_prior_art", "TRIAGE>QUESTION_DEFINED": "define_question", "PRIOR_ART>QUESTION_DEFINED": "define_question", "QUESTION_DEFINED>HYPOTHESIS_DEFINED": "define_hypothesis",
  "HYPOTHESIS_DEFINED>METRICS_DEFINED": "define_metrics", "METRICS_DEFINED>PREREG_DRAFT": "draft_prereg", "PREREG_DRAFT>PREREG_FROZEN": "freeze_prereg", "PREREG_FROZEN>WORK_ORDER_READY": "approve_work_order",
  "WORK_ORDER_READY>DRY_RUN": "dry_run", "DRY_RUN>READY_TO_RUN": "ready_to_run", "DRY_RUN>BLOCKED_BY_GOVERNANCE": "dry_run_failed", "READY_TO_RUN>RUNNING": "start_run", "RUNNING>ANALYSIS": "finish_run", "RUNNING>BLOCKED_BY_GOVERNANCE": "hard_stop",
  "ANALYSIS>VERDICT": "record_verdict", "ANALYSIS>INVALID_MEASUREMENT": "invalid_measurement", "ANALYSIS>INCONCLUSIVE": "inconclusive", "VERDICT>FALSIFIED": "falsified", "VERDICT>REPLICATION": "request_replication",
  "REPLICATION>PUBLICATION_CANDIDATE": "publication_candidate", "PUBLICATION_CANDIDATE>CLOSED": "close", "FALSIFIED>CLOSED": "close", "INVALID_MEASUREMENT>METRICS_DEFINED": "repair_instrument", "INCONCLUSIVE>HYPOTHESIS_DEFINED": "redesign",
  "BLOCKED_BY_GOVERNANCE>WORK_ORDER_READY": "unblock", "BLOCKED_BY_DEPENDENCY>WORK_ORDER_READY": "unblock",
};

export function Board({ theses, labels }: { theses: RosThesis[]; labels: { actor: string } }) {
  const router = useRouter(); const [actor, setActor] = useState<Actor>("founder"); const [msg, setMsg] = useState<string | null>(null); const [drag, setDrag] = useState<string | null>(null);
  const drop = async (to: string) => {
    if (!drag) return; const t = theses.find((x) => x.thesis_id === drag); setDrag(null); if (!t || t.state === to) return;
    const event = EVENT[`${t.state}>${to}`] ?? (to === "SUPERSEDED" ? "supersede" : null);
    if (!event) { setMsg(`${t.state} → ${to}: kein Übergang`); return; }
    const r = await rosPost(`/api/ros/theses/${t.thesis_id}/advance`, { event, reason: "board" }, actor); setMsg(r.ok ? `${t.thesis_id}: ${event} → ${r.data.state}` : errText(r)); if (r.ok) router.refresh();
  };
  const nonEmpty = COLUMNS.filter((c) => theses.some((t) => t.state === c) || COLUMNS.indexOf(c) < 8);
  return (
    <div className="min-w-0">
      <div className="mb-3 flex flex-wrap items-center gap-3"><ActorSelect value={actor} onChange={setActor} label={labels.actor} />{msg && <span className="font-mono text-xs text-muted-foreground" role="status">{msg}</span>}</div>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {nonEmpty.map((c) => (
          <div key={c} className="w-44 shrink-0 border border-border bg-muted/20" onDragOver={(e) => e.preventDefault()} onDrop={() => drop(c)} data-column={c}>
            <div className={cn("border-b border-border px-2 py-1 font-mono text-[0.6rem] uppercase tracking-widest", THESIS_STATE_TONE[c])}>{c}</div>
            <div className="flex min-h-16 flex-col gap-1 p-1">
              {theses.filter((t) => t.state === c).map((t) => (
                <div key={t.thesis_id} draggable onDragStart={() => setDrag(t.thesis_id)} className="cursor-grab border border-border bg-background p-2 text-xs shadow-xs active:cursor-grabbing">
                  <Link href={`/theses/${t.thesis_id}`} className="font-mono text-[0.65rem] underline">{t.thesis_id}</Link><div className="mt-0.5 line-clamp-3 font-medium">{t.title}</div><div className="mt-1 text-[0.6rem] text-muted-foreground">{t.track}</div>
                </div>))}
            </div>
          </div>))}
      </div>
    </div>
  );
}
