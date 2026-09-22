import { api } from "@/lib/api";
import { Shell, Section } from "@/components/shell";

export default async function P7() {
  const inv = (await api("/api/registries/invariants")).invariants.find((i: any) => i.invariant_id === "INV-P7");
  return (
    <Shell title="P7 — Functional Evidence Boundary" subtitle="A deliberately sober page.">
      <Section title="Functional research tracks touched by LOGOS-1"><ul className="list-disc pl-5 text-sm"><li>functional organization (typed authority, provenance, memory)</li><li>belief-state geometry (RD-11; Decodable ≠ CausallyUsed)</li><li>persistent state (recurrent state, RULER freeze)</li><li>self-organization and social emergence (RD-12/13; consciousness_adjacent deltas SPECIFIED only)</li></ul></Section>
      <Section title="Boundary"><p className="text-sm font-semibold">None of this establishes phenomenal consciousness.</p><p className="mt-2 text-sm">{inv?.definition}</p><p className="mt-2 text-xs text-muted-foreground">origin: {inv?.origin}</p></Section>
    </Shell>
  );
}
