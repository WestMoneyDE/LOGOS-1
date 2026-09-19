import { cookies } from "next/headers";
import { de, type Dict } from "./de";
import { en } from "./en";

export type Locale = "de" | "en";
export const DICTS: Record<Locale, Dict> = { de, en };

export async function getLocale(): Promise<Locale> {
  const c = (await cookies()).get("logos_locale")?.value;
  return c === "en" ? "en" : "de";
}

export async function getT() {
  const locale = await getLocale(); const d = DICTS[locale];
  return { locale, t: (k: keyof Dict) => d[k] as string };
}

export const NAV: { area: keyof Dict; items: { href: string; key: keyof Dict }[] }[] = [
  { area: "area_operate", items: [{ href: "/", key: "nav_command_center" }, { href: "/theses", key: "nav_theses" }, { href: "/board", key: "nav_board" }, { href: "/work-orders", key: "nav_work_orders" }, { href: "/queue", key: "nav_queue" }, { href: "/runs", key: "nav_runs" }, { href: "/decisions", key: "nav_decisions" }, { href: "/inbox", key: "nav_inbox" }, { href: "/radar", key: "nav_radar" }] },
  { area: "area_analyze", items: [{ href: "/traces", key: "nav_traces" }, { href: "/experiments", key: "nav_experiments" }, { href: "/benchmarks", key: "nav_benchmarks" }, { href: "/progress", key: "nav_progress" }, { href: "/statistics", key: "nav_statistics" }, { href: "/negative-results", key: "nav_negative" }, { href: "/counterexamples", key: "nav_counterexamples" }, { href: "/replication", key: "nav_replication" }] },
  { area: "area_knowledge", items: [{ href: "/claims", key: "nav_claims" }, { href: "/invariants", key: "nav_invariants" }, { href: "/falsification", key: "nav_graph" }, { href: "/prior-art", key: "nav_prior_art" }, { href: "/open-questions", key: "nav_open_questions" }, { href: "/timeline", key: "nav_timeline" }, { href: "/reproducibility", key: "nav_reproducibility" }, { href: "/p7", key: "nav_p7" }, { href: "/tracks", key: "nav_tracks" }] },
  { area: "area_publish", items: [{ href: "/publications", key: "nav_publications" }, { href: "/research", key: "nav_research" }] },
  { area: "area_system", items: [{ href: "/system/qa", key: "nav_qa" }, { href: "/system/health", key: "nav_health" }, { href: "/system/governance", key: "nav_governance" }, { href: "/system/claude", key: "nav_claude" }, { href: "/system/workers", key: "nav_workers" }, { href: "/system/quotas", key: "nav_quotas" }] },
];
