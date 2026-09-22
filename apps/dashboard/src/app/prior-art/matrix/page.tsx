import Link from "next/link";
import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { PriorArtMatrix, BriefMerge } from "@/components/ros/prior-art-matrix";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function PriorArtMatrixPage() {
  const { t } = await getT();
  const m = await rosGet("/api/ros/prior-art/matrix"); const b = await rosGet("/api/ros/prior-art/briefs");
  if (m === null) return <Shell title={t("pa_matrix")}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  const labels = { citations: t("pa_citations"), novelty: t("pa_novelty"), open: t("pa_open"), missing: t("pa_missing"), start_research: t("pa_start_research"), merge: t("pa_merge") };
  return (
    <Shell title={t("pa_matrix")} subtitle={t("pa_subtitle")} help={t("pa_subtitle")}>
      <p className="mb-4 font-mono text-xs text-muted-foreground">{m.n_citations} Quellen · {m.n_open_tasks} offene Aufgaben · {m.n_briefs} Berichte · Regel: mindestens {m.min_per_track} Quellen je Spur · {m.version}</p>
      <Section title={t("pa_matrix")}><PriorArtMatrix m={m} tasks={b?.tasks ?? []} labels={labels} /></Section>
      <Section title={t("pa_briefs")} hint={`${b?.briefs?.length ?? 0}`}>
        {(b?.briefs?.length ?? 0) === 0 ? <p className="text-sm text-muted-foreground">Noch keine Berichte. „{t("pa_start_research")}" reiht einen Agenten-Job ein; nach deinem Start schreibt der Agent den Bericht.</p>
          : <div className="grid gap-2">{b.briefs.map((x: any) => <BriefMerge key={x.brief_id} brief={x} labels={labels} />)}</div>}
      </Section>
      <Section title={t("pa_closest")}>
        <Table head={["Claim", "Spur", "Quellen", "Nächstliegend", "Neuheit"]} rows={m.claims.map((c: any) => [
          <Link key="l" className="font-mono text-xs underline" href={`/claims/${c.claim_id}`}>{c.claim_id}</Link>, c.track, String(c.n_related),
          <span key="p" className="text-xs">{c.closest_prior_art.map((x: any) => x.citation_id).join(", ") || t("pa_no_source")}</span>,
          <span key="n" className="text-xs">{c.novelty_statement}</span>])} />
      </Section>
    </Shell>
  );
}
