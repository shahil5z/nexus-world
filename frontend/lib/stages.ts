import type { TraceEvent } from "./types";

/** Backend pipeline stages, in order. Names match the stage labels emitted by /agent/analyze/stream. */
export const STAGES = [
  { key: "input_guardrail", label: "Input guardrail" },
  { key: "intent", label: "Intent (Supervisor)" },
  { key: "validation", label: "Domain validation" },
  { key: "reality_guard", label: "Reality Guard" },
  { key: "simulation", label: "Monte Carlo simulation" },
  { key: "evaluation", label: "Model evaluation" },
  { key: "critique", label: "Model Critic" },
  { key: "explanation", label: "Explanation" },
  { key: "grounding", label: "Evidence grounding" },
] as const;
export type StageKey = (typeof STAGES)[number]["key"];
export type StageState = "pending" | "active" | "done" | "error" | "skipped";

// Mirror of STAGE_OF in nexus/agentic/api.py (lookup order: tool, then action, then agent).
const STAGE_OF: Record<string, StageKey> = {
  check_input: "input_guardrail", Supervisor: "intent", IntentFallback: "intent", validate_scenario: "validation",
  run_reality_guard: "reality_guard", run_monte_carlo: "simulation", run_counterfactual: "simulation",
  compare_scenarios: "simulation", get_model_evaluation: "evaluation", ModelCritic: "critique", critic_rules: "critique",
  model_critic: "critique", Explanation: "explanation", template_explanation: "explanation", grounding_check: "grounding",
};

export function stageOf(e: Pick<TraceEvent, "tool" | "action" | "agent">): StageKey | null {
  return STAGE_OF[e.tool ?? ""] ?? STAGE_OF[e.action] ?? STAGE_OF[e.agent] ?? null;
}

/** Derives stage states only from trace events that actually arrived. No estimated progress. */
export function stageStates(events: TraceEvent[], running: boolean): Record<StageKey, StageState> {
  const out = Object.fromEntries(STAGES.map((s) => [s.key, "pending"])) as Record<StageKey, StageState>;
  let last: StageKey | null = null;
  for (const e of events) {
    const s = stageOf(e);
    if (!s) continue;
    last = s;
    if (e.status === "error" || e.status === "rejected" || e.status === "blocked") out[s] = "error";
    else if (e.status === "failed") out[s] = running ? "active" : "error";
    else if (out[s] !== "error" || e.action === "grounding_check") out[s] = "done";
  }
  if (running && last && out[last] === "done") {
    const idx = STAGES.findIndex((x) => x.key === last);
    const next = STAGES.slice(idx + 1).find((x) => out[x.key] === "pending");
    if (next) out[next.key] = "active";
  }
  if (!running) for (const k of Object.keys(out) as StageKey[]) if (out[k] === "pending") out[k] = "skipped";
  return out;
}
