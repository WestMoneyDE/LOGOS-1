import { api } from "@/lib/api";
import { Shell, Table } from "@/components/shell";

export default async function OpenQuestions() {
  const r = await api("/api/registries/open_questions");
  return <Shell title="Research questions queue" subtitle={`Priority by ${r.priority_rule}.`}>
    <Table head={["id", "question", "track", "why important", "current evidence", "missing", "minimal decisive experiment", "dependency", "blocked by", "leverage"]} rows={r.questions.map((q: any) => [q.question_id, q.question, q.track, q.why_important, q.current_evidence, q.missing, q.minimal_decisive_experiment, q.dependency, q.blocked_by, q.leverage])} />
  </Shell>;
}
