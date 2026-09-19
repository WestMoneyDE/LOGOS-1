import { api } from "@/lib/api";
import { getT } from "@/i18n";
import { Shell, Section, Table } from "@/components/shell";
import { cn } from "cn";

export default async function EvidenceDebt() {
  const { t } = await getT(); const d = await api("/api/ros/evidence-debt");
  const tone: Record<string, string> = { HIGH: "text-rose-700", MEDIUM: "text-amber-700", LOW: "text-muted-foreground" };
  return (
    <Shell title={t("ros_debt_title")} subtitle={t("ros_debt_subtitle")}>
      <p className="mb-4 font-mono text-xs text-muted-foreground">n = {d.n} · HIGH {d.by_severity.HIGH} · MEDIUM {d.by_severity.MEDIUM} · LOW {d.by_severity.LOW} · {d.version}</p>
      <Section title="Positionen"><Table head={["Schwere", "Art", "Subjekt", "Befund", "Record"]} rows={d.items.map((i: any) => [<span key="s" className={cn("font-mono text-xs font-semibold", tone[i.severity])}>{i.severity}</span>, <span key="k" className="font-mono text-xs">{i.kind}</span>, <span key="j" className="font-mono text-xs">{i.subject}</span>, i.text, <code key="r" className="break-all font-mono text-[0.65rem]">{i.record}</code>])} /></Section>
      <p className="text-xs text-muted-foreground">{d.rule}</p>
    </Shell>
  );
}
