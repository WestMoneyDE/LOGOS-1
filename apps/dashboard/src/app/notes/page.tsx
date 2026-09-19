import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { NotesBook } from "@/components/ros/notes-book";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Notes() {
  const { t } = await getT(); const d = await rosGet("/api/ros/notes");
  return (
    <Shell title={t("ros_notes_title")} subtitle={t("ros_notes_subtitle")}>
      {d === null ? <RecordsOnly text={t("ros_records_only")} /> : <Section title="Notizen" hint={`${d.notes.length}`}>{d.notes.length === 0 ? <p className="text-xs text-muted-foreground">—</p> : <NotesBook notes={d.notes} label={t("ros_notes_promote")} />}</Section>}
    </Shell>
  );
}
