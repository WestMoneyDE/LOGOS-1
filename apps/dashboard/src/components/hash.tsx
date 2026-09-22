"use client";
import { useState } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/** Short hash with copy button; the full value lives in the tooltip and in the inspector (never a 64-char column). */
export function Hash({ value, n = 10 }: { value: string; n?: number }) {
  const [done, setDone] = useState(false);
  if (!value) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <Tooltip><TooltipTrigger render={<code className="font-mono text-xs" />}>{value.slice(0, n)}</TooltipTrigger><TooltipContent><code className="font-mono text-xs">{value}</code></TooltipContent></Tooltip>
      <button type="button" aria-label="copy" title="copy" className="text-[0.6rem] text-muted-foreground hover:text-foreground" onClick={async () => { try { await navigator.clipboard.writeText(value); setDone(true); setTimeout(() => setDone(false), 1200); } catch {} }}>{done ? "✓" : "⧉"}</button>
    </span>
  );
}
