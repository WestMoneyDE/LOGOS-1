import { Badge } from "@/components/ui/badge";
import { cn } from "cn";
import { JOB_STATE_TONE, THESIS_STATE_TONE } from "@/lib/ros";

export function ThesisState({ state }: { state: string }) {
  return <Badge className={cn("font-mono", THESIS_STATE_TONE[state] ?? "text-foreground")}>{state}</Badge>;
}
export function JobState({ state }: { state: string }) {
  return <Badge className={cn("font-mono", JOB_STATE_TONE[state] ?? "text-foreground")}>{state}</Badge>;
}
export function WoState({ state }: { state: string }) {
  const tone: Record<string, string> = { DRAFT: "text-muted-foreground", APPROVED: "text-sky-700", READY: "text-emerald-700", RUNNING: "text-emerald-800", BLOCKED: "text-amber-700", FAILED: "text-rose-700", VALIDATED: "text-emerald-900", FALSIFIED: "text-rose-800", SUPERSEDED: "text-zinc-400" };
  return <Badge className={cn("font-mono", tone[state] ?? "text-foreground")}>{state}</Badge>;
}
