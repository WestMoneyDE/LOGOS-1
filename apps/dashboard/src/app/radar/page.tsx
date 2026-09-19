import { PhasePlaceholder } from "@/components/phase-placeholder";

export default function Page() {
  return <PhasePlaceholder title="Radar" phase={6} spec="§15–16 Radar Inbox + Radar-to-Work-Order" will={["RAW → PARSED → DEDUPLICATED → SOURCE_CHECKED → TRACK_MAPPED → CLAIM_IMPACT_ANALYZED → EVIDENCE_STRENGTH_ASSIGNED → ACTION_PROPOSED → REVIEWED", "Diff-Ansicht BEFORE / PROPOSED / EVIDENCE / WHY / WHAT WOULD FALSIFY IT"]} />;
}
