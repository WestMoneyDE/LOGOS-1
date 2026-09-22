import { Badge } from "@/components/ui/badge";
import { cn } from "cn";

const STATUS: Record<string, string> = {
  SUPPORTED: "text-emerald-700 dark:text-emerald-400", PARTIALLY_SUPPORTED: "text-amber-700 dark:text-amber-400", FALSIFIED: "text-rose-700 dark:text-rose-400",
  INVALID_MEASUREMENT: "text-orange-700 dark:text-orange-400", VALIDATED_IN_FIXTURE: "text-sky-700 dark:text-sky-400", OBSERVED: "text-violet-700 dark:text-violet-400",
  PROPOSED: "text-muted-foreground", READY_FOR_DETERMINISTIC_TEST: "text-muted-foreground", READY_FOR_INFERENCE_TEST: "text-muted-foreground", INCONCLUSIVE: "text-muted-foreground",
  BLOCKED_BY_GOVERNANCE: "text-zinc-500", BLOCKED_BY_INFERENCE: "text-zinc-500", EXTERNALLY_REPLICATED: "text-emerald-800", PREREGISTERED: "text-sky-600",
};
export function StatusBadge({ status }: { status: string }) {
  return <Badge className={cn("font-mono", STATUS[status] ?? "text-foreground")} title="status of hypothesis (not strength of evidence)">{status}</Badge>;
}
export function StrengthBadge({ strength }: { strength: string }) {
  const level = ["PRELIMINARY", "LOW", "LOW_TO_MEDIUM", "MEDIUM", "MEDIUM_TO_HIGH", "HIGH", "INDEPENDENTLY_REPLICATED"].indexOf(strength);
  return (
    <span className="inline-flex items-center gap-1.5 text-[0.625rem] font-semibold tracking-widest uppercase text-muted-foreground" title="strength of evidence (independent of status)">
      <span className="inline-flex gap-0.5">{[0, 1, 2, 3, 4, 5, 6].map((i) => <span key={i} className={cn("h-2 w-1.5", i <= level ? "bg-foreground" : "bg-border")} />)}</span>
      {strength}
    </span>
  );
}
const KIND: Record<string, string> = { THEORY: "border-violet-400", EMPIRICAL_SCIENCE: "border-emerald-500", DETERMINISTIC_ENGINEERING: "border-sky-500", GOVERNANCE: "border-amber-500", SPECULATION: "border-rose-400" };
export function KindBadge({ kind }: { kind: string }) {
  return <span className={cn("rounded-none border-l-2 pl-1.5 text-[0.625rem] font-semibold tracking-widest uppercase text-muted-foreground", KIND[kind] ?? "border-border")}>{kind.replace("_", " ")}</span>;
}
export function VerdictBadge({ verdict }: { verdict: string }) {
  const c = verdict.includes("FALSIFIED") ? "text-rose-700" : verdict.includes("INVALID") ? "text-orange-700" : verdict.includes("PARTIAL") ? "text-amber-700" : verdict.includes("SUPPORTED") || verdict.includes("VALIDATED") ? "text-emerald-700" : "text-foreground";
  return <Badge className={cn("font-mono normal-case tracking-normal", c)}>{verdict}</Badge>;
}
export function Severity({ s }: { s: string }) {
  const c = s.startsWith("CRITICAL") ? "text-rose-700" : s.startsWith("HIGH") ? "text-orange-700" : s.startsWith("MEDIUM") ? "text-amber-700" : "text-muted-foreground";
  return <span className={cn("font-mono text-xs", c)}>{s}</span>;
}
