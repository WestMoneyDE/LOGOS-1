export const API = process.env.NEXT_PUBLIC_LOGOS_API ?? "http://127.0.0.1:8765";

export async function api<T = any>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export type Claim = {
  claim_id: string; title: string; track: string; claim_type: string; statement: string; status: string; evidence_strength: string; evidence_strength_basis: string;
  scope: string; preregistration: string; supporting_artifacts: string[]; counterevidence: string[]; known_limitations: string[]; falsification_test: string;
  next_falsification_test: string; external_replication: string; publication_target: string; kind: string; last_updated: string;
};
export type Experiment = {
  experiment_id: string; order_id: string; research_track: string; scientific_question: string; hypothesis: string; verdict: string; kind: string; record: string; prereg_hash: string;
  run_id: string; model_provider: string; sample_size: string; controls: string; metrics: string[]; construct_status: string; artifact_hash: string; limitations: string[]; next_experiment: string;
  commit: string; pr: number | null; invariants: string[]; negative_result: boolean; secondary_tracks?: string[];
};
export type Invariant = { invariant_id: string; statement: string; track: string; class: string; origin: string; status: string; definition: string; evidence: string[]; counterexamples: string[]; experiments: string[]; relations: { type: string; target: string }[]; publication_relevance: string; kind: string };
export type Counterexample = { ce_id: string; name: string; experiment: string; violated_assumption: string; severity: string; repair: string; validation: string; remaining_risk: string; source: string; learned: string };
export type Track = { title: string; question: string; thesis: string; paper: string };
