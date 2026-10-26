// Browser-side run history. The server run store is in memory per instance, so the browser keeps its own copy
// of each run so that shared or revisited run links degrade gracefully.
import type { AnalyzeRecord, ArenaRecord } from "./types";

const KEY = "nexus.runs.v1";
const MAX = 25;

export interface HistoryItem { run_id: string; kind: "analyze" | "policy_arena" | "engine"; title: string;
  status: string; created_utc: string }

function read(): { items: HistoryItem[]; records: Record<string, unknown> } {
  if (typeof window === "undefined") return { items: [], records: {} };
  try {
    const v = JSON.parse(window.localStorage.getItem(KEY) ?? "null");
    if (v && Array.isArray(v.items)) return v;
  } catch { /* corrupted storage is ignored */ }
  return { items: [], records: {} };
}

export function listHistory(): HistoryItem[] { return read().items; }

export function saveRun(item: HistoryItem, record?: AnalyzeRecord | ArenaRecord) {
  const s = read();
  s.items = [item, ...s.items.filter((x) => x.run_id !== item.run_id)].slice(0, MAX);
  if (record) s.records[item.run_id] = record;
  for (const id of Object.keys(s.records)) if (!s.items.some((x) => x.run_id === id)) delete s.records[id];
  try { window.localStorage.setItem(KEY, JSON.stringify(s)); } catch {
    s.records = {};
    window.localStorage.setItem(KEY, JSON.stringify(s));
  }
  notifyHistory();
}

export function localRecord(id: string): AnalyzeRecord | ArenaRecord | null {
  return (read().records[id] as AnalyzeRecord | ArenaRecord) ?? null;
}

export const RUN_ID_RE = /^NEXUS-\d{4}-[0-9a-f]{8}$/;

const EVT = "nexus-history";
export function subscribeHistory(cb: () => void) {
  window.addEventListener("storage", cb);
  window.addEventListener(EVT, cb);
  return () => { window.removeEventListener("storage", cb); window.removeEventListener(EVT, cb); };
}
export const historySnapshot = () => window.localStorage.getItem(KEY) ?? "";
export const historyServerSnapshot = () => "";
export function parseHistory(raw: string): HistoryItem[] {
  try { const v = JSON.parse(raw); return Array.isArray(v?.items) ? v.items : []; } catch { return []; }
}
export const notifyHistory = () => window.dispatchEvent(new Event(EVT));
