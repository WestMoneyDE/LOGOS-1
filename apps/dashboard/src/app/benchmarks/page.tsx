import { rosGet } from "@/lib/ros";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { SuiteCard } from "@/components/ros/benchmarks";
import { RecordsOnly } from "@/components/ros/records-only";

export default async function Benchmarks() {
  const { t } = await getT(); const b = await rosGet("/api/ros/benchmarks");
  return (
    <Shell title={t("ros_bench_title")} subtitle={t("ros_bench_subtitle")}>
      {b === null ? <RecordsOnly text={t("ros_records_only")} /> : (<>
        <p className="mb-4 font-mono text-xs text-muted-foreground">definition {b.definitions.version} · sha {b.definitions.sha256.slice(0, 12)} · modes {b.definitions.modes.join(" | ")} · {b.definitions.status}</p>
        <div className="grid gap-4 xl:grid-cols-2">{Object.entries(b.suites).map(([sid, d]: any) => <SuiteCard key={sid} suite={sid} data={d} status={(b.suite_rows.find((r: any) => r.suite_id === sid) || {}).status ?? "—"} labels={{ run: t("ros_bench_run"), freeze: t("ros_bench_freeze"), approve: t("ros_bench_approve"), gates: t("ros_bench_gates") }} />)}</div>
        <Section title={t("ros_bench_mom")}><Table head={["Suite", "Status", "Grund / Deltas"]} rows={Object.entries(b.mom).map(([sid, m]: any) => [sid, m.status, m.status === "COMPARABLE" ? m.deltas.map((d: any) => `${d.metric}: ${d.pp} pp [${d.ci95?.map((x: number) => x.toFixed(3)).join(", ")}]`).join("; ") : String(m.reason)])} className="mt-4 max-w-4xl" /></Section>
        <Section title={t("ros_bench_snapshots")} hint={`${b.snapshots.length}`}>{b.snapshots.length === 0 ? <p className="text-xs text-muted-foreground">—</p> : <Table head={["Snapshot", "Suite", "Modus", "Monat", "SHA-256", "Gates"]} rows={b.snapshots.map((s: any) => [s.snapshot_id, s.suite_id, s.mode, s.month, s.sha256.slice(0, 16), s.payload.gates?.verdict ?? "—"])} />}</Section>
      </>)}
    </Shell>
  );
}
