import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section } from "@/components/shell";
import { WorkOrdersTable, CreateWorkOrder } from "@/components/ros/work-orders";
import { DagView } from "@/components/ros/dag-view";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function WorkOrders() {
  const { t } = await getT();
  const wos = await rosGet("/api/ros/work-orders"); const g = await rosGet("/api/ros/dag"); const th = await rosGet("/api/ros/theses");
  return (
    <Shell title={t("ros_work_orders_title")} subtitle={t("ros_work_orders_subtitle")}>
      {wos === null || g === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <Section title={t("ros_dag")} hint={`${wos.ready.length} ${t("ros_ready")}`}><DagView nodes={g.nodes} edges={g.edges} /></Section>
        <Section title="Work Orders" hint={`${wos.work_orders.length}`}>
          <div className="mb-3"><CreateWorkOrder theses={th?.theses ?? []} required={wos.required_fields} label={t("ros_new_wo")} /></div>
          <WorkOrdersTable rows={wos.work_orders} ready={wos.ready} blocked={wos.blocked} labels={{ search: t("search"), columns: t("columns"), rows: t("rows"), detail: t("inspector_title"), actor: t("ros_actor"), ready: t("ros_ready"), blocked: t("ros_blocked") }} />
        </Section></>)}
    </Shell>
  );
}
