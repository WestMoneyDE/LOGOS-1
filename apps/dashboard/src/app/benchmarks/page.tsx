import { PhasePlaceholder } from "@/components/phase-placeholder";

export default function Page() {
  return <PhasePlaceholder title="Benchmarks" phase={5} spec="§28–33 Benchmark Lab" will={["BASELINE_AGENT vs LOGOS_AGENT vs LOGOS_ABLATION", "Scorecard mit N, 95%-KI, Vergleichbarkeits-Badge, Hard Safety Gates"]} />;
}
