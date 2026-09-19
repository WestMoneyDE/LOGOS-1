import { PhasePlaceholder } from "@/components/phase-placeholder";

export default function Page() {
  return <PhasePlaceholder title="Work Orders" phase={2} spec="§12–13 Work Order Factory + DAG" will={["Work-Order-DRAFTs aus Thesen, Radar, Negativergebnissen", "Pflichtfelder (Frage, Scope, Hypothese, Falsifikationskriterium, Metriken, Governance, Caps)", "Founder-APPROVE vor jeder Ausführung", "Abhängigkeits-DAG (READY / RUNNING / BLOCKED / FAILED / VALIDATED / FALSIFIED / SUPERSEDED)"]} />;
}
