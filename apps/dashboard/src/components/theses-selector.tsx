"use client";
import { useState } from "react";
import { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { StatusBadge, StrengthBadge } from "@/components/badges";

export function ThesesSelector({ claims, active }: { claims: any[]; active: string[] }) {
  const [sel, setSel] = useState<string[]>(active); const [saved, setSaved] = useState<string | null>(null);
  const toggle = (id: string) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  return (
    <div>
      <div className="grid gap-2">
        {claims.filter((c) => ["hypothesis", "invariant", "architecture"].includes(c.claim_type)).map((c) => (
          <label key={c.claim_id} className="flex cursor-pointer items-start gap-3 border border-border p-3 text-sm hover:bg-muted/40">
            <input type="checkbox" className="mt-1" checked={sel.includes(c.claim_id)} onChange={() => toggle(c.claim_id)} />
            <span className="flex-1"><span className="font-mono text-xs text-muted-foreground">{c.claim_id}</span> <span className="font-semibold">{c.title}</span><br /><span className="text-xs text-muted-foreground">next falsification test: {c.next_falsification_test || "none named"}</span><br /><StatusBadge status={c.status} /> <StrengthBadge strength={c.evidence_strength} /></span>
          </label>
        ))}
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Button onClick={async () => { const r = await fetch(`${API}/api/theses/active`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ active: sel }) }); setSaved(r.ok ? `saved ${sel.length} selected (${new Date().toLocaleTimeString()})` : `error ${r.status}`); }}>Save selection</Button>
        {saved && <span className="text-xs text-muted-foreground">{saved}</span>}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">Selected theses appear on the overview with their next falsification test. Running them in parallel means several governed orders — each with its own preregistration, gates and caps; the dashboard records the intent, it does not start inference.</p>
    </div>
  );
}
