import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";

export default async function QA() {
  const { t } = await getT();
  const q = await api("/api/qa/last-run");
  const s = q.last_run ?? {};
  const cards: [string, string][] = [["Letzter Lauf", s.startTime ? new Date(s.startTime).toLocaleString("de-DE") : "kein Lauf"], ["Dauer", s.duration ? `${Math.round(s.duration / 1000)} s` : "—"], ["erwartet / unerwartet / flaky", `${s.expected ?? 0} / ${s.unexpected ?? 0} / ${s.flaky ?? 0}`],
    ["Routen × Viewports", String(q.routes.length)], ["Verstöße (Overflow / Clipping / Konsole / Requests)", String(q.violations.length)], ["Browser-Matrix", q.projects.join(", ") || "—"]];
  return (
    <Shell title={t("nav_qa")} subtitle="Route-Inventar des letzten Playwright-Laufs: Status, Seiten-Overflow, abgeschnittene Inhalte, Konsolenfehler, fehlgeschlagene Requests, Dauer — je Viewport (§93–94).">
      <Section title="Zusammenfassung"><div className="grid gap-3 md:grid-cols-3">{cards.map(([k, v]) => <div key={k} className="border border-border p-3"><div className="text-[0.65rem] uppercase tracking-widest text-muted-foreground">{k}</div><div className="mt-1 font-heading text-lg font-semibold">{v}</div></div>)}</div></Section>
      {q.violations.length > 0 && <Section title="Verstöße"><Table head={["Route", "Viewport", "Overflow", "Clipping", "Konsole", "Requests"]} rows={q.violations.map((r: any) => [r.route, r.project, r.overflow?.overflow ? `${r.overflow.scrollWidth} > ${r.overflow.innerWidth}` : "—", (r.clipped ?? []).join("; ") || "—", (r.consoleErrors ?? []).join("; ") || "—", (r.failedRequests ?? []).join("; ") || "—"])} /></Section>}
      <Section title="Routen" hint="alle Viewports"><Table head={["Route", "Viewport", "Status", "Overflow", "Clipping", "Konsole", "Dauer"]} rows={q.routes.map((r: any) => [r.route, `${r.project} ${r.viewport?.width}×${r.viewport?.height}`, String(r.status), r.overflow?.overflow ? "JA" : "nein", String((r.clipped ?? []).length), String((r.consoleErrors ?? []).length), `${r.durationMs} ms`])} /></Section>
      <Section title="Screenshots" hint="apps/dashboard/e2e/results/screenshots"><ul className="columns-2 text-xs md:columns-3">{q.screenshots.map((p: string) => <li key={p} className="font-mono">{p}</li>)}</ul></Section>
    </Shell>
  );
}
