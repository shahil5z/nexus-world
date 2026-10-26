import type { AgentStatus, AnalyzeRecord, ArenaRecord, CompareResponse, Health, MonteCarloResponse, Scenario,
  TraceEvent, ValidateResponse } from "./types";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function call<T>(path: string, init?: RequestInit, timeoutMs = 120_000): Promise<T> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(`/api${path}`, { ...init, signal: ctl.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
    const body = await r.json().catch(() => null);
    if (!r.ok) {
      const e = body?.error;
      const detail = Array.isArray(body?.detail) ? body.detail.map((d: { msg: string }) => d.msg).join("; ") : body?.detail;
      throw new ApiError(r.status, e?.code ?? "http_error", e?.message ?? detail ?? `request failed (${r.status})`);
    }
    return body as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if ((e as Error).name === "AbortError") throw new ApiError(0, "timeout", "request timed out");
    throw new ApiError(0, "network", "backend unreachable");
  } finally {
    clearTimeout(t);
  }
}

const post = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => call<Health>("/health", undefined, 10_000),
  agentStatus: () => call<AgentStatus>("/agent/status", undefined, 20_000),
  suggestions: () => call<{ suggestions: string[] }>("/agent/suggestions", undefined, 10_000),
  modelEvaluate: () => call<Record<string, unknown>>("/model/evaluate", undefined, 20_000),
  validate: (scenario: Scenario, horizon_months: number) =>
    call<ValidateResponse>("/simulation/validate", post({ scenario, horizon_months })),
  monteCarlo: (scenario: Scenario, horizon_months: number, n_paths: number, seed: number) =>
    call<MonteCarloResponse>("/simulation/monte-carlo", post({ scenario, horizon_months, n_paths, seed })),
  compare: (scenarios: Scenario[], horizon_months: number, n_paths: number, seed: number) =>
    call<CompareResponse>("/scenario/compare", post({ scenarios, horizon_months, n_paths, seed })),
  run: (id: string) => call<AnalyzeRecord | ArenaRecord>(`/runs/${encodeURIComponent(id)}`, undefined, 15_000),
  arena: (body: unknown) => call<ArenaRecord>("/agent/policy-arena", post(body)),
};

export type StreamMsg =
  | { type: "trace"; stage: string | null; event: TraceEvent }
  | { type: "result"; result: AnalyzeRecord }
  | { type: "error"; error: string };

/** Streams real trace events from the backend while the agent pipeline runs. */
export async function analyzeStream(body: { question: string; session_id?: string | null; n_paths: number; seed: number },
  onMsg: (m: StreamMsg) => void, signal?: AbortSignal): Promise<AnalyzeRecord> {
  let r: Response;
  try {
    r = await fetch("/api/agent/analyze/stream", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), signal });
  } catch {
    throw new ApiError(0, "network", "backend unreachable");
  }
  if (!r.ok || !r.body) {
    const b = await r.json().catch(() => null);
    throw new ApiError(r.status, b?.error?.code ?? "http_error", b?.error?.message ?? `request failed (${r.status})`);
  }
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  let result: AnalyzeRecord | null = null;
  for (;;) {
    const { done, value } = await reader.read();
    if (value) buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i).trim();
      buf = buf.slice(i + 1);
      if (!line) continue;
      const m = JSON.parse(line) as StreamMsg;
      onMsg(m);
      if (m.type === "result") result = m.result;
      if (m.type === "error") throw new ApiError(500, "pipeline_error", m.error);
    }
    if (done) break;
  }
  if (!result) throw new ApiError(0, "stream_incomplete", "stream ended without a result");
  return result;
}
