import { rosGet, type RosThesis } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell } from "@/components/shell";
import { Board } from "@/components/ros/board";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function BoardPage() {
  const { t } = await getT(); const ros = await rosGet<{ theses: RosThesis[] }>("/api/ros/theses");
  return (
    <Shell title={t("ros_board_title")} subtitle={t("ros_board_subtitle")}>
      {ros === null ? <RecordsOnly text={t("ros_records_only")} /> : <Board theses={ros.theses} labels={{ actor: t("ros_actor") }} />}
    </Shell>
  );
}
