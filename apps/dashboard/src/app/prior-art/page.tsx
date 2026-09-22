import { api } from "@/lib/api";
import { Shell, Table } from "@/components/shell";

export default async function PriorArt() {
  const r = await api("/api/registries/prior_art");
  return <Shell title="Prior-art registry" subtitle={`${r.rule} — ${r.search_status}`}>
    <Table head={["id", "citation", "track", "supports", "does not support", "novelty", "notes"]} rows={r.citations.map((c: any) => [<code key="i" className="font-mono text-xs">{c.citation_id}</code>, <span key="c">{c.authors} ({c.year}). <em>{c.title}</em>. {c.venue}. <a className="underline" href={c.url}>{c.url}</a></span>, c.research_track, c.claim_supported, c.claim_not_supported, <code key="n" className="font-mono text-xs">{c.novelty_status}</code>, c.notes])} />
  </Shell>;
}
