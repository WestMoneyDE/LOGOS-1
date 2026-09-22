import Link from "next/link";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { RecordsOnly } from "@/components/ros/records-only";
import { cn } from "cn";

const TONE: Record<string, string> = { gestuetzt: "border-l-emerald-600", widerlegt: "border-l-rose-600", offen: "border-l-sky-600", blockiert: "border-l-zinc-400" };

export default async function Insights() {
  const { t } = await getT(); const d = await rosGet("/api/ros/insights");
  if (d === null) return <Shell title={t("ins_title")}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  const groups: [string, string][] = [["gestuetzt", t("ins_supported")], ["widerlegt", t("ins_falsified")], ["offen", t("ins_open")], ["blockiert", t("ins_blocked")]];
  return (
    <Shell title={t("ins_title")} subtitle={t("ins_subtitle")} help={t("ins_subtitle")}>
      <p className="mb-4 font-mono text-xs text-muted-foreground">{d.n_claims} Claims · {groups.map(([k, label]) => `${label} ${d.counts[k]}`).join(" · ")} · {d.version}</p>
      {groups.map(([key, label]) => d.counts[key] > 0 && (
        <Section key={key} title={label} hint={`${d.counts[key]}`}>
          <ul className="grid gap-2" aria-label={label}>
            {d.groups[key].map((e: any) => (
              <li key={e.claim_id} className={cn("border border-l-4 p-3 text-sm", TONE[key])} data-claim={e.claim_id}>
                <div className="flex flex-wrap items-baseline gap-2">
                  <Link href={`/claims/${e.claim_id}`} className="font-mono text-xs underline">{e.claim_id}</Link>
                  <span className="font-mono text-[0.6rem] uppercase tracking-widest text-muted-foreground">{e.track} · {e.kind}</span>
                </div>
                <p className="mt-1">{e.sentence}</p>
                <p className="mt-1 text-xs text-muted-foreground"><span className="font-semibold">{t("ins_certainty")} </span>{e.certainty}</p>
                {(e.artifacts?.length > 0 || e.experiments?.length > 0) && <p className="mt-1 break-all font-mono text-[0.6rem] text-muted-foreground">Belege: {[...(e.experiments ?? []), ...(e.artifacts ?? [])].slice(0, 6).join(" · ")}</p>}
              </li>))}
          </ul>
        </Section>))}
      <Section title={t("ins_learned")} hint={`${d.learned.length} seit ${d.since}`}>
        <ul className="grid gap-1 text-sm">{d.learned.map((x: any) => <li key={x.kind + x.id} className="border border-border px-3 py-1.5"><span className="mr-2 font-mono text-[0.6rem] uppercase tracking-widest text-muted-foreground">{x.kind}</span>{x.text} <span className="font-mono text-[0.65rem] text-muted-foreground">{String(x.at ?? "").slice(0, 10)}</span></li>)}</ul>
      </Section>
      <Section title="Regeln dieser Seite"><ul className="list-disc pl-5 text-xs text-muted-foreground">{d.rules.map((r: string) => <li key={r}>{r}</li>)}</ul></Section>
    </Shell>
  );
}
