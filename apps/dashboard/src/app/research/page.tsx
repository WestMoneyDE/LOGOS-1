import { api } from "@/lib/api";
import { Shell, Section, Table } from "@/components/shell";

export default async function Research() {
  const r = await api("/api/research-queue");
  return (
    <Shell title="Deep-research queue" subtitle={`Related-work and novelty tasks derived from the claim registry. Run the project skill (${r.skill}), which wraps deep-research; briefs are validated and merged only after founder review.`}>
      <Section title="Tasks" hint="priority by publication leverage"><Table head={["task", "claim", "track", "question", "why", "priority"]} rows={r.tasks.map((t: any) => [<code key="t" className="font-mono text-xs">{t.task_id}</code>, t.claim_id ?? "—", t.track, t.question, t.why.join("; "), t.priority])} /></Section>
      <Section title="Research briefs" hint="docs/research/dashboard/research-briefs/">{r.briefs.length ? <Table head={["brief", "claim", "date", "sources", "novelty", "reviewed"]} rows={r.briefs.map((b: any) => [b.brief_id, b.claim_id, b.date, String((b.sources ?? []).length), b.novelty_assessment?.status ?? "—", b.reviewed_by_founder ? "yes" : "no"])} /> : <p className="text-sm text-muted-foreground">no briefs yet</p>}</Section>
      <Section title="How to run"><ol className="list-decimal pl-5 text-sm"><li>In Claude Code: <code className="font-mono text-xs">/logos-prior-art-research RQ-LOGOS-CP-001</code> (needs the firecrawl or exa MCP for deep-research; WebSearch/WebFetch fallback is recorded in limitations).</li><li>Review the brief; set <code className="font-mono text-xs">reviewed_by_founder: true</code>.</li><li>Merge via <code className="font-mono text-xs">logos_dashboard.research_intake.merge_brief</code> — validation refuses inflated novelty or forbidden phrases.</li></ol></Section>
    </Shell>
  );
}
