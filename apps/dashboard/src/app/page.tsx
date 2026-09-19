import Link from "next/link";
import { api } from "@/lib/api";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { StatCards } from "@/components/stat-cards";
import { VerdictMix } from "@/components/charts/verdict-mix";
import { RecordsOnly } from "@/components/ros/records-only";
import { CreateThesis } from "@/components/ros/create-thesis";
import { WorkerSwitch, MasterSwitch, ThesisCard, LiveTicker, FirstSteps } from "@/components/ros/leitstand";
import { NotifySwitch } from "@/components/ros/notify";

export default async function Leitstand() {
  const { t, locale } = await getT(); const de = locale === "de";
  const ls = await rosGet("/api/ros/leitstand"); const cc = await api("/api/command-center"); const claims = (await api("/api/registries/claims")).claims;
  const keys = ["ls_running", "ls_theses", "ls_decisions", "ls_first_steps", "ls_master", "ls_on", "ls_off", "ls_master_hint", "ls_host", "ls_docker", "ls_start", "ls_stop", "ls_alive", "ls_dead", "ls_stopping", "ls_work_on", "ls_paused", "ls_ceiling", "ls_no_theses", "ls_add_thesis", "ls_live", "ls_live_empty", "ls_step_1", "ls_step_2", "ls_step_3", "ls_step_4", "ls_done", "ls_todo", "ls_last_result", "ls_next_for_you", "ls_agent_working", "ls_waiting", "ls_stage", "console_reads", "console_writes", "console_searches", "console_web", "console_skill", "console_says", "console_thinks", "console_tool_result"] as const;
  const l = Object.fromEntries(keys.map((k) => [k, t(k)]));
  const s = cc.stats;
  return (
    <Shell title={t("ls_title")} subtitle={t("ls_subtitle")} help={t("help_home")}>
      {ls === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <FirstSteps fs={ls.first_steps} l={l} />
        <Section title={t("ls_running")}>
          <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
            <div className="flex flex-col gap-3" id="workers"><WorkerSwitch which="host" label={t("ls_host")} status={ls.host} l={l} /><WorkerSwitch which="docker" label={t("ls_docker")} status={ls.docker} l={l} /><div id="master"><MasterSwitch on={!!ls.autopilot.master} l={l} /></div><div className="border border-border p-3"><NotifySwitch label={t("notify_on")} hint={t("notify_hint")} /></div></div>
            <LiveTicker initialRun={ls.live_run} initialEvents={ls.live_events} l={l} />
          </div>
          <p className="mt-2 font-mono text-[0.65rem] text-muted-foreground">Agenten-Sitzungen {ls.governor.running.agent ?? 0}/{ls.governor.caps.max_parallel_agent_sessions} · Messläufe {ls.governor.running.measurement ?? 0}/{ls.governor.caps.max_parallel_claude_sessions} · Quota {ls.governor.quota.state} · Auth {ls.governor.attestation.auth_class ?? "—"}{ls.governor.attestation.fresh ? "" : " (Preflight nötig)"} · Pin {ls.governor.caps.model_pin}</p>
        </Section>
        <Section title={t("ls_theses")} hint={`${ls.theses.length}`}>
          {ls.theses.length === 0 ? <p className="mb-3 text-sm text-muted-foreground">{t("ls_no_theses")}</p> : <div className="grid gap-3 xl:grid-cols-2">{ls.theses.map((th: any) => <ThesisCard key={th.thesis_id} t={th} states={ls.states} l={l} />)}</div>}
          <details className="mt-3 text-sm"><summary className="cursor-pointer text-xs font-semibold uppercase tracking-widest text-muted-foreground">{t("ls_add_thesis")}</summary>
            <ul className="mt-2 grid gap-1 md:grid-cols-2">{claims.filter((c: any) => ["hypothesis", "invariant", "architecture"].includes(c.claim_type) && !ls.theses.some((th: any) => (th.claim_ids ?? []).includes(c.claim_id))).map((c: any) => <li key={c.claim_id} className="flex flex-wrap items-center gap-2 border border-border p-2 text-xs"><span className="font-mono">{c.claim_id}</span><span className="grow">{c.title}</span><CreateThesis claim={c} existing={false} label={t("ls_add_thesis")} /></li>)}</ul>
          </details>
        </Section>
        <Section title={t("ls_decisions")} hint={`${ls.attention.length}`}>
          {ls.attention.length === 0 ? <p className="text-sm text-muted-foreground">—</p> : <ul className="grid gap-1 text-sm">{ls.attention.map((a: any) => <li key={a.kind + a.id} className="border border-border border-l-4 border-l-amber-500 px-3 py-1.5"><span className="mr-2 font-mono text-[0.6rem] uppercase tracking-widest text-muted-foreground">{a.kind}</span><Link href={a.href} className="hover:underline">{a.text}</Link></li>)}</ul>}
        </Section>
        <Section title={de ? "Stand der Forschung (Zählung)" : "State of research (counts)"}>
          <StatCards items={[{ label: de ? "Aktive Thesen" : "Active theses", value: ls.theses.length, href: "/theses" }, { label: de ? "Läufe gesamt" : "Runs total", value: s.ros.running_jobs ?? 0, sub: de ? "gerade laufend" : "running now", href: "/runs" }, { label: de ? "Experimente diesen Monat" : "Experiments this month", value: s.experiments_this_month, href: "/experiments" }, { label: de ? "Negativergebnisse" : "Negative results", value: s.negative_results_this_month, href: "/negative-results" }, { label: de ? "Offene Gates" : "Open gates", value: s.blocked_gates, href: "/decisions" }]} />
          <div className="mt-3"><VerdictMix data={cc.verdict_mix} n={cc.n_closures} /></div>
          <p className="mt-2 text-xs text-muted-foreground">{de ? "Kette:" : "Chain:"} <span className="font-mono">{cc.latest_closure?.id}</span> → <span className="font-mono">{cc.next_work_order}</span> · <Link className="underline" href="/insights">{de ? "Was wissen wir jetzt?" : "What do we know?"}</Link> · <Link className="underline" href="/work-orders">Work Orders</Link> · <Link className="underline" href="/observability">{de ? "Beobachtung" : "Observability"}</Link></p>
        </Section>
      </>)}
    </Shell>
  );
}
