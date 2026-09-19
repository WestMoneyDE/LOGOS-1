"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import { errText, rosPost, type RosRun, type RosRunEvent } from "@/lib/ros";
import { feedLine, type L } from "@/components/ros/leitstand";

const PHASES = ["gate", "worktree", "packet", "claude", "verify", "done"];
const KINDS = ["phase", "gate", "worktree", "packet", "claude.invoke", "claude.result", "artifact", "commit", "thesis.event", "quota", "stop", "error", "note", "done", "agent.init", "agent.batch", "agent.result", "work_order.draft", "autopilot"];

export function RunConsole({ run, job, initial, hostAlive, l }: { run: RosRun; job: any; initial: RosRunEvent[]; hostAlive: boolean; l: L }) {
  const router = useRouter(); const [events, setEvents] = useState<RosRunEvent[]>(initial); const [state, setState] = useState(run.state); const [msg, setMsg] = useState<string | null>(null); const [note, setNote] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (state !== "running") return;
    const last = events.length ? events[events.length - 1].seq : 0;
    const es = new EventSource(`${API}/api/ros/runs/${run.run_id}/stream?after=${last}`);
    const onEv = (ev: MessageEvent) => { try { const e = JSON.parse(ev.data); setEvents((xs) => (xs.some((x) => x.seq === e.seq) ? xs : [...xs, e])); } catch {} };
    KINDS.forEach((k) => es.addEventListener(k, onEv as any));
    es.addEventListener("state", (ev: MessageEvent) => { try { const s = JSON.parse(ev.data); setState(s.state); if (s.state !== "running") { es.close(); router.refresh(); } } catch {} });
    es.onerror = () => es.close();
    return () => es.close();
  }, [run.run_id, state]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { endRef.current?.scrollIntoView({ block: "nearest" }); }, [events.length]);
  const phase = [...events].reverse().find((e) => e.kind === "phase")?.payload?.phase ?? (state === "running" ? "gate" : "done");
  const packet = events.find((e) => e.kind === "packet")?.payload; const invoke = events.find((e) => e.kind === "claude.invoke")?.payload; const done = events.find((e) => e.kind === "done")?.payload; const err = [...events].reverse().find((e) => e.kind === "error")?.payload; const cr = events.find((e) => e.kind === "claude.result")?.payload;
  const feed = events.filter((e) => e.kind.startsWith("agent.") || ["thesis.event", "commit", "work_order.draft", "error", "stop", "quota", "claude.result", "done"].includes(e.kind)).flatMap((e) => feedLine(e, l).map((t, i) => ({ k: `${e.seq}-${i}`, t, at: String(e.at).slice(11, 19), kind: e.kind })));
  const act = async (a: string) => { if (!job) return; const r = await rosPost(a === "stop" ? `/api/ros/runs/${run.run_id}/stop` : `/api/ros/queue/${job.job_id}/${a}`, {}); setMsg(r.ok ? `${a}: ${r.data.state}` : errText(r)); if (r.ok) router.refresh(); };
  const explain = events.length === 0 && job ? (job.state === "waiting_governance" ? l.console_empty_waiting : job.state === "waiting_quota" ? l.console_empty_quota : !hostAlive ? l.console_empty_host : l.console_empty_queued) : null;
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn("inline-flex items-center gap-1 font-mono text-xs", state === "running" ? "text-emerald-700" : "text-muted-foreground")}><span className={cn("inline-block h-2 w-2 rounded-full", state === "running" ? "animate-pulse bg-emerald-600" : "bg-zinc-400")} />{state === "running" ? l.ros_live : `${l.ros_finished} · ${state}`}</span>
        <ol className="ml-2 flex flex-wrap gap-1 font-mono text-[0.6rem]">{PHASES.map((p) => <li key={p} className={cn("border px-1.5 py-0.5", p === phase ? "border-foreground bg-foreground text-background" : "border-border text-muted-foreground")}>{p}</li>)}</ol>
        <span className="grow" />
        {job && job.state === "waiting_governance" && <Button size="sm" onClick={() => act("start")}>🔒 {l.ros_start}</Button>}
        {job && ["queued", "running"].includes(job.state) && <Button size="sm" variant="outline" onClick={() => act("pause")}>{l.ros_pause}</Button>}
        {job && job.state === "paused" && <Button size="sm" variant="outline" onClick={() => act("resume")}>{l.ros_resume}</Button>}
        {job && ["queued", "running", "paused", "waiting_governance", "waiting_quota"].includes(job.state) && <Button size="sm" variant="destructive" onClick={() => act("stop")}>■ {l.ros_stop}</Button>}
      </div>
      {msg && <p className="mt-1 font-mono text-xs text-muted-foreground" role="status">{msg}</p>}
      {explain && <div className="mt-3 border border-dashed border-amber-500 p-3 text-sm" role="note">{explain} {!hostAlive && <Link className="underline" href="/#workers">Leitstand</Link>}</div>}
      <div className="mt-3 grid gap-3 xl:grid-cols-[2fr_1fr]">
        <div className="min-w-0">
          <div className="mb-1 text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{l.console_feed}</div>
          <div className="max-h-[60vh] overflow-y-auto border border-border bg-muted/20">
            {feed.length === 0 ? <p className="p-3 text-xs text-muted-foreground">{l.ros_no_events}</p> : <ul aria-label="agent feed" className="p-1">{feed.map((x) => <li key={x.k} className={cn("grid grid-cols-[4.5rem_1fr] gap-2 border-t border-border/50 px-1 py-1 text-[0.75rem]", x.kind === "error" && "text-rose-700", x.kind === "thesis.event" && "text-indigo-700", x.kind === "commit" && "text-emerald-800")}><span className="font-mono text-muted-foreground">{x.at}</span><span className="min-w-0 whitespace-pre-wrap break-words">{x.t}</span></li>)}</ul>}
            <div ref={endRef} />
          </div>
        </div>
        <div className="flex min-w-0 flex-col gap-3 text-xs">
          <div className="border border-border p-2"><div className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{l.console_packet}</div>
            {packet ? <ul className="mt-1 space-y-0.5"><li>Stufe: <span className="font-mono">{packet.state}</span></li><li>erlaubte Ereignisse: <span className="font-mono">{(packet.allowed_events ?? []).join(", ") || "—"}</span></li><li>Schreibrechte: <span className="break-all font-mono">{(packet.allowed_prefixes ?? []).join(", ")}</span></li>{invoke && <li>Modell {invoke.requested_model} · max {invoke.max_turns} turns · Tools {(invoke.allowed_tools ?? []).join(", ")}{invoke.skills?.length ? ` · Skills ${invoke.skills.join(", ")}` : ""}</li>}<li>Prompt {String(packet.prompt_sha256 ?? "").slice(0, 12)} · {packet.prompt_bytes} B · Notizen {(packet.notes_consumed ?? []).length}</li></ul> : <p className="mt-1 text-muted-foreground">—</p>}
          </div>
          <div className="border border-border p-2"><div className="text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">{l.console_result}</div>
            {done ? <ul className="mt-1 space-y-0.5"><li>{done.summary}</li><li>Dateien: <span className="break-all font-mono">{(done.files ?? []).join(", ") || "—"}</span></li><li>Vorschlag: <span className="font-mono">{done.proposed_event ?? "—"}</span> → <span className="font-mono">{done.applied_state ?? "nicht angewendet"}</span></li>{done.work_order_draft && <li>Work-Order-Entwurf: <Link className="font-mono underline" href="/work-orders">{done.work_order_draft}</Link></li>}{done.needs_prior_art && <li>Vorarbeiten angefordert (Job #{done.prior_art_job})</li>}{cr && <li>{cr.status} · {cr.resolved_model} ({cr.evidence_class}) · {cr.latency_s} s · {cr.turns} turns</li>}<li>Branch <span className="break-all font-mono">{done.branch}</span> @ {String(done.commit ?? "").slice(0, 10)}</li></ul>
              : err ? <p className="mt-1 text-rose-700">{err.reason}{err.files ? `: ${err.files.join(", ")}` : ""}</p> : <p className="mt-1 text-muted-foreground">—</p>}
          </div>
          {run.thesis_id && <div className="flex gap-2"><input className="h-8 grow border border-border bg-background px-2 text-xs" placeholder={l.ros_note_placeholder} value={note} onChange={(e) => setNote(e.target.value)} aria-label={l.ros_notes} /><Button size="sm" disabled={!note.trim()} onClick={async () => { const r = await rosPost("/api/ros/notes", { thesis_id: run.thesis_id, run_id: run.run_id, text: note, decision_flag: false }); if (r.ok) { setNote(""); setMsg(`note #${r.data.note_id} → next job`); } }}>{l.ros_add_note}</Button></div>}
        </div>
      </div>
    </div>
  );
}
