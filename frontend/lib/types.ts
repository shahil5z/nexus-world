// Types mirror the FastAPI responses. Only fields the UI reads are declared.
export type Driver = "gasoline_price" | "electricity_price" | "real_income" | "unemployment";
export type Metric = "vmt" | "fuel_gallons" | "co2_kt" | "fuel_spend" | "energy_burden_mean" | "energy_burden_low_income";
export type Tier = "HIGH" | "MEDIUM" | "LOW" | "OOD";
export type Verdict = "OK" | "CAUTION" | "BLOCK";

export interface Intervention {
  variable: Driver;
  operation: "multiply" | "add";
  value: number;
  start_month: number;
  duration_months: number;
}
export interface Scenario { name: string; interventions: Intervention[] }

export interface Stats { mean: number; median: number; std: number; min: number; max: number; n: number;
  p5: number; p10: number; p25: number; p50: number; p75: number; p90: number; p95: number }
export interface MetricSummary { level: Stats; delta?: Stats; pct_delta?: Stats }
export type Summary = Record<string, Record<Metric, MetricSummary>>;

export interface Band { p5: number[]; p10: number[]; p25: number[]; median: number[]; p75: number[]; p90: number[]; p95: number[] }

export interface GuardResult {
  tier: Tier;
  months_by_tier: Record<Tier, number>;
  max_mahalanobis: number;
  train_mahalanobis_p95: number;
  train_mahalanobis_p99: number;
  isolation_forest_anomalies: number;
  out_of_range_features: { feature: string; min_seen: number; max_seen: number; train_min: number; train_max: number }[];
  meaning: string;
}

export interface Meta { run_id: string; seed: number | null; engine_version: string; data_version: string;
  model_version: string; as_of: string; compute_ms?: number }

export interface MonteCarloResponse {
  mode: "monte_carlo"; range_type: string; months: string[]; n_paths: number;
  bands: Record<Metric, Record<string, Band>>; summary: Summary; reality_guard: GuardResult; meta: Meta;
}
export interface ValidateResponse { valid: boolean; reality_guard: GuardResult;
  limits: { max_horizon_months: number; max_paths: number; max_scenarios: number }; meta: Meta }
export interface CompareResponse { scenarios: string[]; n_paths: number; summary: Summary;
  reality_guard: Record<string, GuardResult>; meta: Meta }

export interface TraceEvent { seq: number; timestamp: string; t_ms: number; agent: string; action: string;
  tool: string | null; status: string; summary: string; duration_ms: number | null; warnings: string[] }

export interface EvidenceItem { id: string; label: string; value: number; display: string; unit: string;
  tool: string; tool_call_id: string; run_id: string; path: string }
export interface Claim { field: string; text: string; evidence_id: string | null; tool?: string;
  tool_call_id?: string; run_id?: string; value?: number; source?: string }

export interface Explanation {
  executive_result: string; key_outcomes: string[]; scenario: string; baseline: string; counterfactual: string;
  uncertainty: string; key_modeled_drivers: string; critique: string; assumptions: string[]; limitations: string[];
  recommendation: string | null; evidence_ids_used: string[];
}

export interface SessionSlot { scenario: Scenario; horizon_months: number; run_id: string }
export interface SessionPublic { baseline: Scenario & { immutable: boolean }; slots: Record<string, SessionSlot>; turns: number }

export interface AnalyzeRecord {
  run_id: string; kind: "analyze"; created_utc: string; session_id: string; seed: number; n_paths: number;
  status: "ok" | "rejected" | "needs_clarification" | "invalid" | "not_executed" | "partial" | "error";
  mode: "agentic" | "engine_only_fallback" | "partial_fallback"; model: string | null;
  versions: Record<string, string | boolean>;
  explanation: Explanation | null; warnings: string[]; session: SessionPublic; trace: TraceEvent[];
  metrics: { llm_calls: number; tool_calls: number; tokens: { input: number; output: number; total: number };
    llm_ms: number; tool_ms: number; elapsed_ms: number };
  intent?: { action: string; interventions: Intervention[] } | null;
  scenario?: Scenario; horizon_months?: number; slot?: string; exploratory?: boolean;
  guard?: GuardResult; evidence_sheet?: EvidenceItem[];
  grounding?: { ok: boolean; claims: Claim[]; ungrounded_numbers: { field: string; text: string }[] };
  explanation_source?: "llm" | "template";
  critic?: { verdict: Verdict; deterministic: { verdict: Verdict; reasons: { level: string; reason: string }[] };
    llm?: { verdict: Verdict; reasons: string[]; evidence_ids: string[] } | null };
  outputs?: { tool_call_id: string; summary: Summary };
  rejection?: { stage: string; reason: unknown };
}

export interface ArenaRow { rank: number; candidate: string; score: number; normalized: Record<string, number>;
  pareto: "non-dominated" | "dominated"; dominated_by: string[]; tier: Tier | "UNKNOWN"; exploratory: boolean;
  median_pct_delta: Record<string, number>; p10_p90_pct_delta: Record<string, [number, number]> }
export interface ArenaRecord { run_id: string; kind: "policy_arena"; created_utc: string; weights: {
  normalized: Record<string, number>; source: "user" | "default"; default: string }; scoring: string;
  ranking: ArenaRow[]; excluded_ood: string[]; n_paths: number; horizon_months: number; seed: number;
  metrics: { tool_calls: number; tool_ms: number; elapsed_ms: number }; note: string }

export interface Health { status: string; engine_version: string; data_version: string; model_version: string }
export interface AgentStatus { llm_configured: boolean; mode: string; model: string; openai_agents_version: string;
  live_check: { checked: boolean; ok?: boolean; error?: string; latency_ms?: number; cached_age_s?: number };
  prompt_version: string; budget: Record<string, number> }

export interface CausalGraph { version: string; description: string; edge_types: Record<string, string>; nodes: string[];
  edges: { from: string; to: string; type: "learned" | "identity" | "assumption"; feature?: string; lag_months?: number | null }[] }
