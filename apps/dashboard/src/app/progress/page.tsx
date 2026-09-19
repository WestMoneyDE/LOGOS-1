import { PhasePlaceholder } from "@/components/phase-placeholder";

export default function Page() {
  return <PhasePlaceholder title="Monatsfortschritt" phase={5} spec="§34 Monthly Progress" will={["Task Success, Falsifikationsrate, Replikationsabdeckung, Time-to-Verdict", "Immutable Monats-Snapshots; NOT_COMPARABLE statt künstlicher Prozente"]} />;
}
