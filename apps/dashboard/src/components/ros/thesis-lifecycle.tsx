"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ActorSelect } from "@/components/ros/actor-select";
import { errText, rosPost, type Actor, type Transition } from "@/lib/ros";

const MAIN_PATH = ["IDEA", "TRIAGE", "PRIOR_ART", "QUESTION_DEFINED", "HYPOTHESIS_DEFINED", "METRICS_DEFINED", "PREREG_DRAFT", "PREREG_FROZEN", "WORK_ORDER_READY", "DRY_RUN", "READY_TO_RUN", "RUNNING", "ANALYSIS", "VERDICT", "REPLICATION", "PUBLICATION_CANDIDATE", "CLOSED"];
const GATES = new Set(["PREREG_FROZEN", "WORK_ORDER_READY", "READY_TO_RUN"]);

export function ThesisLifecycle({ thesisId, state, available, agentCeiling, labels }: { thesisId: string; state: string; available: Transition[]; agentCeiling: string; labels: { available: string; actor: string; gate: string; reason: string; apply: string; ceiling: string } }) {
  const router = useRouter(); const [actor, setActor] = useState<Actor>("founder"); const [reason, setReason] = useState(""); const [msg, setMsg] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const idx = MAIN_PATH.indexOf(state); const ceilingIdx = MAIN_PATH.indexOf(agentCeiling);
  const fire = async (event: string) => {
    setBusy(true); const r = await rosPost(`/api/ros/theses/${thesisId}/advance`, { event, reason }, actor); setBusy(false);
    setMsg(r.ok ? `${event} → ${r.data.state}` : errText(r)); if (r.ok) { setReason(""); router.refresh(); }
  };
  return (
    <div className="min-w-0">
      <ol className="flex flex-wrap gap-1 text-[0.6rem] font-mono" aria-label="lifecycle">
        {MAIN_PATH.map((s, i) => (
          <li key={s} className={cn("border px-1.5 py-0.5", i === idx ? "border-foreground bg-foreground text-background" : i < idx ? "border-border text-muted-foreground line-through decoration-border" : "border-border text-muted-foreground", GATES.has(s) && "border-dashed")} title={GATES.has(s) ? labels.gate : i === ceilingIdx ? labels.ceiling : undefined}>
            {GATES.has(s) ? "🔒 " : ""}{s}{i === ceilingIdx ? " ▏" : ""}
          </li>
        ))}
      </ol>
      {idx < 0 && <p className="mt-2 font-mono text-xs">{state}</p>}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <ActorSelect value={actor} onChange={setActor} label={labels.actor} />
        <Input className="h-8 max-w-xs text-xs" placeholder={labels.reason} value={reason} onChange={(e) => setReason(e.target.value)} />
      </div>
      <div className="mt-2 flex flex-wrap gap-2" aria-label={labels.available}>
        {available.map((t) => (
          <Button key={t.event} size="sm" variant={t.founder_gate ? "default" : "outline"} disabled={busy || (t.founder_gate && actor !== "founder")} title={t.founder_gate ? labels.gate : undefined} onClick={() => fire(t.event)}>
            {t.founder_gate ? "🔒 " : ""}{t.event} → {t.to}
          </Button>
        ))}
      </div>
      {msg && <p className="mt-2 font-mono text-xs text-muted-foreground" role="status">{msg}</p>}
    </div>
  );
}
