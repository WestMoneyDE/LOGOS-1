"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import { errText, rosPost } from "@/lib/ros";

export type L = Record<string, string>;
const STAGES_DE = ["Idee", "Sichtung", "Vorarbeiten", "Frage", "Hypothese", "Messung", "Prereg-Entwurf"];
const STAGE_KEYS = ["IDEA", "TRIAGE", "PRIOR_ART", "QUESTION_DEFINED", "HYPOTHESIS_DEFINED", "METRICS_DEFINED", "PREREG_DRAFT"];

function Lamp({ on, stopping }: { on: boolean; stopping?: boolean }) {
  return <span className={cn("inline-block h-2.5 w-2.5 rounded-full", on ? (stopping ? "bg-amber-500 animate-pulse" : "bg-emerald-600 animate-pulse") : "bg-zinc-400")} />;
}

export function WorkerSwitch({ which, label, status, l }: { which: "host" | "docker"; label: string; status: any; l: L }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const alive = !!status?.alive; const stopping = !!status?.stop_requested && alive;
  const act = async (a: "start" | "stop") => { setBusy(true); const r = await rosPost(`/api/ros/workers/${which}/${a}`, {}); setBusy(false); setMsg(r.ok ? (r.data.note ?? a) : errText(r)); router.refresh(); };
  return (
    <div className="flex flex-wrap items-center gap-3 border border-border p-3" data-worker={which}>
      <Lamp on={alive} stopping={stopping} /><span className="font-medium">{label}</span>
      <span className="font-mono text-xs text-muted-foreground">{alive ? (stopping ? l.ls_stopping : l.ls_alive) : l.ls_dead}{status?.current_job ? ` · job #${status.current_job}` : ""}{which === "docker" && status && !status.container_running ? " · container aus" : ""}</span>
      <span className="grow" />
      {!alive && <Button size="sm" disabled={busy} onClick={() => act("start")}>▶ {l.ls_start}</Button>}
      {alive && <Button size="sm" variant="outline" disabled={busy || stopping} onClick={() => act("stop")}>■ {l.ls_stop}</Button>}
      {msg && <span className="basis-full font-mono text-[0.65rem] text-muted-foreground" role="status">{msg}</span>}
    </div>
  );
}

export function MasterSwitch({ on, l }: { on: boolean; l: L }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null);
  return (
    <div className={cn("flex flex-wrap items-center gap-3 border-2 p-3", on ? "border-emerald-600" : "border-border")} data-master={on ? "on" : "off"}>
      <span className="text-lg font-semibold">{l.ls_master}</span>
      <button aria-label={l.ls_master} role="switch" aria-checked={on} className={cn("relative h-7 w-14 rounded-full transition", on ? "bg-emerald-600" : "bg-zinc-300")} onClick={async () => { const r = await rosPost("/api/ros/autopilot/master", { enabled: !on }); setMsg(r.ok ? null : errText(r)); router.refresh(); }}>
        <span className={cn("absolute top-0.5 h-6 w-6 rounded-full bg-white transition", on ? "left-7" : "left-0.5")} />
      </button>
      <span className={cn("font-mono text-sm font-semibold", on ? "text-emerald-700" : "text-muted-foreground")}>{on ? l.ls_on : l.ls_off}</span>
      <p className="basis-full text-xs text-muted-foreground">{l.ls_master_hint}</p>
      {msg && <span className="font-mono text-xs text-rose-700" role="status">{msg}</span>}
    </div>
  );
}

export function ThesisCard({ t, states, l }: { t: any; states: string[]; l: L }) {
  const router = useRouter(); const [msg, setMsg] = useState<string | null>(null); const [on, setOn] = useState(!!t.autopilot?.enabled);
  const idx = STAGE_KEYS.indexOf(t.state); const beyond = idx < 0 && states.indexOf(t.state) > states.indexOf("PREREG_DRAFT"); const ap = t.autopilot ?? {};
  const open = (t.open_jobs ?? [])[0];
  const next = t.state === "PREREG_DRAFT" ? "Prereg prüfen und einfrieren (🔒) — dann Work Order freigeben" : ap.paused ? `${l.ls_paused}: ${ap.paused}` : open ? `${open.kind} · ${open.state}` : ap.enabled ? l.ls_waiting : l.ls_work_on;
  return (
    <article className="flex flex-col gap-2 border border-border p-3" data-thesis={t.thesis_id}>
      <header className="flex flex-wrap items-baseline justify-between gap-2"><Link href={`/theses/${t.thesis_id}`} className="font-semibold hover:underline">{t.title}</Link><span className="font-mono text-[0.65rem] text-muted-foreground">{t.thesis_id} · {t.track}</span></header>
      <ol className="flex flex-wrap gap-1 text-[0.65rem]">
        {STAGES_DE.map((s, i) => <li key={s} className={cn("border px-1.5 py-0.5", i < idx ? "border-emerald-600 bg-emerald-600 text-white" : i === idx ? "border-foreground bg-foreground text-background" : "border-border text-muted-foreground")}>{i + 1}. {s}</li>)}
        <li className={cn("border border-dashed px-1.5 py-0.5", t.state === "PREREG_DRAFT" || beyond ? "border-amber-600 text-amber-700" : "border-border text-muted-foreground")}>🔒 {l.ls_ceiling}</li>
      </ol>
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <label className="inline-flex cursor-pointer items-center gap-2"><input type="checkbox" checked={on} disabled={t.state === "PREREG_DRAFT" || beyond} onChange={async (e) => { const v = e.target.checked; setOn(v); const r = await rosPost(`/api/ros/autopilot/theses/${t.thesis_id}`, { enabled: v, reason: "leitstand" }); if (!r.ok) { setOn(!v); setMsg(errText(r)); } else { setMsg(null); router.refresh(); } }} /> {l.ls_work_on}</label>
        <span className={cn("font-mono", open?.state === "running" ? "text-emerald-700" : "text-muted-foreground")}>{open?.state === "running" ? `● ${l.ls_agent_working}` : ""}</span>
        <span className="grow" />
        <span className="text-muted-foreground">{l.ls_next_for_you}: <span className="text-foreground">{next}</span></span>
      </div>
      {msg && <span className="font-mono text-[0.65rem] text-rose-700" role="status">{msg}</span>}
    </article>
  );
}

const TOOL_VERB: Record<string, string> = { Read: "console_reads", Write: "console_writes", Edit: "console_writes", Glob: "console_searches", Grep: "console_searches", WebSearch: "console_web", WebFetch: "console_web", Skill: "console_skill" };
export function feedLine(e: any, l: L): string[] {
  const p = e.payload ?? {};
  if (e.kind === "agent.batch") return (p.items ?? []).map((i: any) => i.kind === "agent.tool" ? `🔧 ${l[TOOL_VERB[i.tool] ?? "console_searches"] ?? i.tool} ${i.tool}: ${i.target}` : i.kind === "agent.text" ? `💬 ${l.console_says}: ${i.text}` : i.kind === "agent.thinking" ? `🧠 ${l.console_thinks}: ${i.text}` : `↩ ${l.console_tool_result}${i.is_error ? " ✗" : ""} (${i.bytes} B)`);
  if (e.kind === "agent.init") return [`▶ Claude ${p.model ?? ""} · tools ${(p.tools ?? []).join(", ")}`];
  if (e.kind === "agent.result") return [`■ ${p.subtype ?? ""} · ${p.num_turns ?? "—"} turns`];
  if (e.kind === "phase") return [`⏱ ${p.phase}`];
  if (e.kind === "thesis.event") return [`➡ ${p.proposed} → ${p.applied ? p.to : `nicht angewendet (${p.reason})`}`];
  if (e.kind === "done") return [`✅ ${p.summary ?? "done"}`];
  if (e.kind === "error") return [`✗ ${p.reason}`];
  if (e.kind === "claude.result") return [`🏁 ${p.status} · ${p.resolved_model ?? "—"} · ${p.latency_s ?? "—"} s`];
  return [`${e.kind}`];
}

export function LiveTicker({ initialRun, initialEvents, l }: { initialRun: any; initialEvents: any[]; l: L }) {
  const [run, setRun] = useState(initialRun); const [events, setEvents] = useState(initialEvents);
  useEffect(() => {
    const id = setInterval(async () => { try { const r = await fetch(`${API}/api/ros/leitstand`); if (r.ok) { const d = await r.json(); setRun(d.live_run); setEvents(d.live_events); } } catch {} }, 3000);
    return () => clearInterval(id);
  }, []);
  const lines = events.flatMap((e) => feedLine(e, l).map((t, i) => ({ k: `${e.seq}-${i}`, t, at: String(e.at).slice(11, 19) })));
  return (
    <div className="border border-border bg-muted/20 p-3" aria-label="live ticker">
      <div className="mb-1 flex items-baseline justify-between text-[0.65rem] uppercase tracking-widest text-muted-foreground"><span>{l.ls_live}</span>{run && <Link className="font-mono normal-case tracking-normal underline" href={`/runs/${run.run_id}`}>{run.run_id} · {run.state}</Link>}</div>
      {lines.length === 0 ? <p className="text-xs text-muted-foreground">{l.ls_live_empty}</p> : <ul className="font-mono text-[0.7rem]">{lines.slice(-8).map((x) => <li key={x.k} className="truncate"><span className="text-muted-foreground">{x.at}</span> {x.t}</li>)}</ul>}
    </div>
  );
}

export function FirstSteps({ fs, l }: { fs: any; l: L }) {
  const items = [["auth", l.ls_step_1, "/system/claude"], ["thesis", l.ls_step_2, "/theses"], ["host_running", l.ls_step_3, "#workers"], ["autopilot", l.ls_step_4, "#master"]] as const;
  if (items.every(([k]) => fs[k])) return null;
  return <ol className="grid gap-1 border border-dashed border-border p-3 text-sm sm:grid-cols-2" aria-label="first steps">{items.map(([k, label, href], i) => <li key={k} className={cn(fs[k] ? "text-muted-foreground line-through" : "")}>{fs[k] ? "✓" : `${i + 1}.`} <a href={href} className="hover:underline">{label}</a> <span className="font-mono text-[0.6rem]">{fs[k] ? l.ls_done : l.ls_todo}</span></li>)}</ol>;
}
