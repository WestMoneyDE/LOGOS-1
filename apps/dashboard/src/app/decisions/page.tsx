import { PhasePlaceholder } from "@/components/phase-placeholder";

export default function Page() {
  return <PhasePlaceholder title="Entscheidungen" phase={2} spec="§42 Decision / Gate Center" will={["WAITING · APPROVED · REJECTED · DEFERRED · SUPERSEDED", "was passiert bei Freigabe / Ablehnung; blockierte Work Orders"]} />;
}
