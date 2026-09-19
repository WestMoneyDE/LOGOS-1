"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import { errText, rosPost, type RosRun, type RosRunEvent } from "@/lib/ros";

const KIND_TONE: Record<string, string> = { gate: "text-sky-700", phase: "text-muted-foreground", worktree: "text-violet-700", packet: "text-violet-700", "claude.invoke": "text-amber-700", "claude.result": "text-amber-800", artifact: "text-emerald-700", commit: "text-emerald-800", "thesis.event": "text-indigo-700", quota: "text-rose-700", stop: "text-rose-700", error: "text-rose-700", done: "text-emerald-900", note: "text-foreground" };
const PHASES = ["gate", "worktree", "packet", "claude", "verify", "done"];

function Line({ e }: { e: RosRunEvent }) {
  const p = e.payload ?? {};
  const text = e.kind === "phase" ? `phase → ${p.phase}` : e.kind === "gate" ? `gate ${p.passed ? "PASS" : "FAIL"} ${p.passed ? "" : JSON.stringify(Object.entries(p.checks ?? {}).filter(([, v]) => !v).map(([k]) => k))}`
    : e.kind === "claude.invoke" ? `claude -p · model ${p.requested_model} · max-turns ${p.max_turns} · tools ${(p.allowed_tools ?? []).join(",")} · #${p.invocation}`
    : e.kind === "claude.result" ? `${p.status} · resolved ${p.resolved_model ?? "—"} (${p.evidence_class ?? "—"}) · turns ${p.turns ?? "—"} · ${p.latency_s ?? "—"} s${p.reason_code ? ` · ${p.reason_code}` : ""}`
    : e.kind === "artifact" ? `${p.path ?? p.kind} · ${(p.sha256 ?? "").slice(0, 12)}` : e.kind === "commit" ? `${(p.sha ?? "—").slice(0, 10)} on ${p.branch} (${(p.files ?? []).length} files)`
    : e.kind === "thesis.event" ? `${p.proposed} → ${p.applied ? p.to : `not applied (${p.reason})`}` : e.kind === "worktree" ? `${p.branch} @ ${(p.base ?? "").slice(0, 10)}` : e.kind === "packet" ? `prompt ${(p.prompt_sha256 ?? "").slice(0, 12)} · ${p.prompt_bytes} B · notes ${(p.notes_consumed ?? []).length} · state ${p.state}`
    : e.kind === "done" ? `done · ${p.proposed_event ?? "—"} → ${p.applied_state ?? "—"} · prior art ${p.needs_prior_art ? "requested" : "no"}` : JSON.stringify(p).slice(0, 300);
  return (
    <li className="grid grid-cols-[6rem_8rem_1fr] gap-2 border-t border-border px-2 py-1 font-mono text-[0.7rem]">
      <span className="text-muted-foreground">{e.at.slice(11, 19)}</span><span className={cn("font-semibold", KIND_TONE[e.kind])}>{e.kind}</span><span className="min-w-0 break-words">{text}</span>
    </li>
  );
}

export function RunConsole({ run, job, initial, labels }: { run: RosRun; job: any; initial: RosRunEvent[]; labels: { start: string; pause: string; resume: string; stop: string; live: string; finished: string; none: string; notes: string; notePlaceholder: string; addNote: string } }) {
  const router = useRouter(); const [events, setEvents] = useState<RosRunEvent[]>(initial); const [state, setState] = useState(run.state); const [msg, setMsg] = useState<string | null>(null); const [note, setNote] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (state !== "running") return;
    const last = events.length ? events[events.length - 1].seq : 0;
    const es = new EventSource(`${API}/api/ros/runs/${run.run_id}/stream?after=${last}`);
    const onEv = (ev: MessageEvent) => { try { const e = JSON.parse(ev.data); setEvents((xs) => (xs.some((x) => x.seq === e.seq) ? xs : [...xs, e])); } catch {} };
    ["phase", "gate", "worktree", "packet", "claude.invoke", "claude.result", "artifact", "commit", "thesis.event", "quota", "stop", "error", "note", "done"].forEach((k) => es.addEventListener(k, onEv as any));
    es.addEventListener("state", (ev: MessageEvent) => { try { const s = JSON.parse(ev.data); setState(s.state); if (s.state !== "running") { es.close(); router.refresh(); } } catch {} });
    es.onerror = () => { es.close(); };
    return () => es.close();
  }, [run.run_id, state]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { endRef.current?.scrollIntoView({ block: "nearest" }); }, [events.length]);
  const phase = [...events].reverse().find((e) => e.kind === "phase")?.payload?.phase ?? (state === "running" ? "gate" : "done");
  const act = async (a: string) => { if (!job) return; const r = await rosPost(a === "stop" ? `/api/ros/runs/${run.run_id}/stop` : `/api/ros/queue/${job.job_id}/${a}`, {}); setMsg(r.ok ? `${a}: ${r.data.state}` : errText(r)); if (r.ok) router.refresh(); };
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn("inline-flex items-center gap-1 font-mono text-xs", state === "running" ? "text-emerald-700" : "text-muted-foreground")}><span className={cn("inline-block h-2 w-2 rounded-full", state === "running" ? "animate-pulse bg-emerald-600" : "bg-zinc-400")} />{state === "running" ? labels.live : `${labels.finished} · ${state}`}</span>
        <ol className="ml-2 flex flex-wrap gap-1 font-mono text-[0.6rem]">{PHASES.map((p) => <li key={p} className={cn("border px-1.5 py-0.5", p === phase ? "border-foreground bg-foreground text-background" : "border-border text-muted-foreground")}>{p}</li>)}</ol>
        <span className="grow" />
        {job && ["queued", "running"].includes(job.state) && <Button size="sm" variant="outline" onClick={() => act("pause")}>{labels.pause}</Button>}
        {job && job.state === "paused" && <Button size="sm" variant="outline" onClick={() => act("resume")}>{labels.resume}</Button>}
        {job && ["queued", "running", "paused", "waiting_governance", "waiting_quota"].includes(job.state) && <Button size="sm" variant="destructive" onClick={() => act("stop")}>{labels.stop}</Button>}
      </div>
      {msg && <p className="mt-1 font-mono text-xs text-muted-foreground" role="status">{msg}</p>}
      <div className="mt-3 max-h-[60vh] overflow-y-auto border border-border bg-muted/20">
        {events.length === 0 ? <p className="p-3 text-xs text-muted-foreground">{labels.none}</p> : <ul aria-label="run events">{events.map((e) => <Line key={e.seq} e={e} />)}</ul>}
        <div ref={endRef} />
      </div>
      {run.thesis_id && (
        <div className="mt-3 flex max-w-2xl gap-2">
          <input className="h-8 grow border border-border bg-background px-2 text-xs" placeholder={labels.notePlaceholder} value={note} onChange={(e) => setNote(e.target.value)} aria-label={labels.notes} />
          <Button size="sm" disabled={!note.trim()} onClick={async () => { const r = await rosPost("/api/ros/notes", { thesis_id: run.thesis_id, run_id: run.run_id, text: note, decision_flag: false }); if (r.ok) { setNote(""); setMsg(`note #${r.data.note_id} → next job`); } }}>{labels.addNote}</Button>
        </div>)}
    </div>
  );
}
