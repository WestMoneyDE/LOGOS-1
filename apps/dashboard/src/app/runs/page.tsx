import { PhasePlaceholder } from "@/components/phase-placeholder";

export default function Page() {
  return <PhasePlaceholder title="Live-Läufe" phase={3} spec="§25 Live Run View" will={["Run-Konsole mit Ereignisstrom (Phase, Claude-Aufruf, Tests, Artefakte, Quota)", "Start / Pause / Stop (graceful) je These", "Founder-Notizen in den nächsten Job-Kontext"]} />;
}
