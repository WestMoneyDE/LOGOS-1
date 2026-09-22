import Link from "next/link";
import { api } from "@/lib/api";
import { Shell, Table } from "@/components/shell";
import { StatusBadge } from "@/components/badges";

export default async function Falsification() {
  const r = await api("/api/falsification");
  return <Shell title="What could prove us wrong?" subtitle="For every active claim: the falsification criterion, its test status, and the result that would change our mind. More important than any success metric.">
    <Table head={["claim", "track", "status", "falsification criterion (what would change our mind)", "counterevidence so far", "next test"]} rows={r.map((c: any) => [<Link key="c" href={`/claims/${c.claim_id}`} className="underline">{c.title}</Link>, c.track, <StatusBadge key="s" status={c.status} />, c.falsification_test, c.counterevidence.join("; ") || "none", c.next_falsification_test || "—"])} />
  </Shell>;
}
