import type { RosEvent } from "@/lib/ros";
import { ThesisState } from "@/components/ros/state-badge";

export function EventLog({ events }: { events: RosEvent[] }) {
  return (
    <div className="overflow-x-auto border border-border">
      <table className="w-full text-xs">
        <thead className="bg-muted/50 text-left text-[0.6rem] uppercase tracking-widest text-muted-foreground"><tr><th className="px-2 py-1.5">#</th><th className="px-2 py-1.5">Zeit</th><th className="px-2 py-1.5">Event</th><th className="px-2 py-1.5">Von → Nach</th><th className="px-2 py-1.5">Actor</th><th className="px-2 py-1.5">Grund / Quelle</th></tr></thead>
        <tbody>{events.map((e) => (
          <tr key={e.event_id} className="border-t border-border align-top">
            <td className="px-2 py-1.5 font-mono text-muted-foreground">{e.event_id}</td><td className="whitespace-nowrap px-2 py-1.5 font-mono">{e.at.replace("T", " ").slice(0, 19)}</td><td className="px-2 py-1.5 font-mono">{e.event}</td>
            <td className="whitespace-nowrap px-2 py-1.5">{e.from_state ?? "—"} → <ThesisState state={e.to_state} /></td><td className="px-2 py-1.5 font-mono">{e.actor}</td>
            <td className="px-2 py-1.5">{e.reason}{e.source_record && <span className="ml-1 font-mono text-[0.65rem] text-muted-foreground">{e.source_record}</span>}{e.git_commit && <code className="ml-1 font-mono text-[0.65rem]">{e.git_commit.slice(0, 10)}</code>}</td>
          </tr>))}</tbody>
      </table>
    </div>
  );
}
