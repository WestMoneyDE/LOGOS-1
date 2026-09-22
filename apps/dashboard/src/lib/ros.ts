import { API } from "@/lib/api";

export type Actor = "founder" | "agent" | "worker" | "system";
export type RosThesis = { thesis_id: string; claim_ids: string[]; title: string; track: string; state: string; owner: string; created_at: string; updated_at: string; n_work_orders?: number; n_open_jobs?: number; last_event_at?: string | null };
export type RosEvent = { event_id: number; thesis_id: string; from_state: string | null; to_state: string; event: string; actor: string; reason: string; source_record: string | null; git_commit: string | null; at: string };
export type RosWorkOrder = { work_order_id: string; thesis_id: string | null; state: string; spec: Record<string, any>; prereg_hash: string | null; approved_by: string | null; approved_at: string | null; created_by: string; created_at: string; parents?: string[] };
export type RosDecision = { decision_id: string; kind: string; subject_ref: string; state: string; why: string; impact: string; if_approved: string; if_rejected: string; blocks: string[]; decided_by: string | null; decided_at: string | null; created_at: string };
export type RosJob = { job_id: number; idempotency_key: string; kind: string; run_id: string | null; work_order_id: string | null; thesis_id: string | null; state: string; attempt: number; locked_by: string | null; locked_at: string | null; payload: any; result: any; error: string | null; created_at: string; updated_at: string };
export type Transition = { event: string; to: string; founder_gate: boolean };

/** GET that tolerates 503 records-only (returns null) so pages render a notice instead of crashing. */
export async function rosGet<T = any>(path: string): Promise<T | null> {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (r.status === 503) return null;
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

/** GET that separates the three cases the UI must distinguish: 503 records-only (null), 404 missing ("NOT_FOUND"), ok (data). */
export async function rosGetMaybe<T = any>(path: string): Promise<T | null | "NOT_FOUND"> {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (r.status === 503) return null;
  if (r.status === 404) return "NOT_FOUND";
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export async function rosPost(path: string, body: unknown, actor: Actor = "founder", method: "POST" | "DELETE" = "POST"): Promise<{ ok: boolean; status: number; data: any }> {
  const r = await fetch(`${API}${path}`, { method, headers: { "Content-Type": "application/json", "X-Logos-Actor": actor }, body: method === "POST" ? JSON.stringify(body ?? {}) : undefined });
  let data: any = null; try { data = await r.json(); } catch {}
  return { ok: r.ok, status: r.status, data };
}

export function errText(res: { status: number; data: any }): string {
  const d = res.data?.detail;
  if (d && typeof d === "object" && d.illegal_transition) return `${res.status}: ${d.reason} (${d.state} —${d.event}→ ? als ${d.actor})`;
  return `${res.status}: ${typeof d === "string" ? d : JSON.stringify(d ?? res.data)}`;
}

export const THESIS_STATE_TONE: Record<string, string> = {
  IDEA: "text-muted-foreground", TRIAGE: "text-muted-foreground", PRIOR_ART: "text-violet-700", QUESTION_DEFINED: "text-sky-700", HYPOTHESIS_DEFINED: "text-sky-700", METRICS_DEFINED: "text-sky-700",
  PREREG_DRAFT: "text-amber-700", PREREG_FROZEN: "text-amber-800", WORK_ORDER_READY: "text-emerald-700", DRY_RUN: "text-emerald-700", READY_TO_RUN: "text-emerald-800", RUNNING: "text-emerald-800",
  ANALYSIS: "text-indigo-700", VERDICT: "text-indigo-800", REPLICATION: "text-indigo-800", PUBLICATION_CANDIDATE: "text-emerald-900", CLOSED: "text-zinc-500",
  BLOCKED_BY_GOVERNANCE: "text-zinc-500", BLOCKED_BY_DEPENDENCY: "text-zinc-500", INVALID_MEASUREMENT: "text-orange-700", FALSIFIED: "text-rose-700", INCONCLUSIVE: "text-muted-foreground", SUPERSEDED: "text-zinc-400",
};
export const JOB_STATE_TONE: Record<string, string> = { queued: "text-sky-700", running: "text-emerald-700", paused: "text-amber-700", failed: "text-rose-700", done: "text-zinc-500", stopped: "text-zinc-500", waiting_quota: "text-amber-700", waiting_dependency: "text-amber-700", waiting_governance: "text-amber-800" };

export type RosRun = { run_id: string; job_id: number | null; work_order_id: string | null; thesis_id: string | null; kind: string; state: string; branch: string | null; worktree: string | null; started: string | null; finished: string | null; stop_reason: string | null; summary: any; created_at: string; n_events?: number };
export type RosRunEvent = { seq: number; run_id: string; at: string; kind: string; payload: any; privacy_class: string };
export const RUN_STATE_TONE: Record<string, string> = { running: "text-emerald-700", done: "text-zinc-600", failed: "text-rose-700", stopped: "text-zinc-500", waiting_quota: "text-amber-800" };
