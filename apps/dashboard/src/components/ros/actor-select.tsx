"use client";
import type { Actor } from "@/lib/ros";

/** Localhost single-user: the founder may act as `agent` to exercise the autonomy boundary; the API rejects gated events for agents. */
export function ActorSelect({ value, onChange, label }: { value: Actor; onChange: (a: Actor) => void; label: string }) {
  return (
    <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">{label}
      <select aria-label={label} className="border border-border bg-background px-2 py-1 font-mono text-xs" value={value} onChange={(e) => onChange(e.target.value as Actor)}>
        <option value="founder">founder</option><option value="agent">agent</option>
      </select>
    </label>
  );
}
