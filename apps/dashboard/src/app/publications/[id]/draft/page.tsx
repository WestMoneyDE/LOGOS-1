import Link from "next/link";
import { notFound } from "next/navigation";
import { rosGetMaybe } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { PaperExport } from "@/components/ros/paper-export";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function PaperDraft({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params; const { t } = await getT();
  const d = await rosGetMaybe(`/api/ros/papers/${id}/draft`);
  if (d === null) return <Shell title={id}><RecordsOnly text={t("ros_records_only")} /></Shell>;
  if (d === "NOT_FOUND" || !(d as any)?.doc) notFound();
  const doc = (d as any).doc;
  return (
    <Shell title={`${t("pp_title")} — ${doc.paper_id}`} subtitle={t("pp_subtitle")} help={t("pp_subtitle")}>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <PaperExport paperId={doc.paper_id} label={t("pp_export")} />
        <span className="font-mono text-xs text-muted-foreground">sha {doc.sha256.slice(0, 16)} · Reifegrad im Register: {doc.manuscript_status_in_registry} · Kriterien {doc.readiness?.met}/{doc.readiness?.of}</span>
      </div>
      <Section title="Markdown"><pre className="max-w-5xl overflow-x-auto whitespace-pre-wrap border border-border bg-muted/20 p-3 font-mono text-[0.72rem] leading-relaxed" aria-label="paper draft">{(d as any).markdown}</pre></Section>
      <p className="text-xs text-muted-foreground">{doc.rule} · <Link className="underline" href="/publications">Publikationen</Link></p>
    </Shell>
  );
}
