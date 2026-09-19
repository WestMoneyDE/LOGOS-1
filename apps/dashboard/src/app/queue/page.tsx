import { PhasePlaceholder } from "@/components/phase-placeholder";

export default function Page() {
  return <PhasePlaceholder title="Warteschlange" phase={2} spec="§72 Backpressure / Quota" will={["queued · waiting quota · waiting dependency · waiting governance · running · paused · failed · done", "ConcurrencyGovernor mit governed cap aus INFERENCE-GOVERNANCE.json"]} />;
}
