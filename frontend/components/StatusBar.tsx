"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentStatus, Health } from "@/lib/types";

/** System status from /api/health and /api/agent/status. Nothing here is hardcoded. */
export function StatusBar({ onStatus }: { onStatus?: (s: AgentStatus | null) => void }) {
  const [h, setH] = useState<Health | null | "err">(null);
  const [a, setA] = useState<AgentStatus | null | "err">(null);
  useEffect(() => {
    api.health().then(setH).catch(() => setH("err"));
    api.agentStatus().then((s) => { setA(s); onStatus?.(s); }).catch(() => { setA("err"); onStatus?.(null); });
  }, [onStatus]);
  const engine = h === null ? <span className="tag">engine: checking</span> : h === "err" ? <span className="tag block">engine: unreachable</span>
    : <span className="tag ok" data-testid="engine-status"><span className="dot" />engine {h.status} / v{h.engine_version}</span>;
  let ai: React.ReactNode = <span className="tag">AI: checking</span>;
  if (a === "err") ai = <span className="tag block">AI status: unavailable</span>;
  else if (a) ai = a.llm_configured
    ? <span className="tag ok" data-testid="ai-status"><span className="dot" />AI agents: {a.model}</span>
    : <span className="tag caution" data-testid="ai-status"><span className="dot" />AI off: engine-only mode</span>;
  return (
    <div className="row" role="status" aria-label="System status" style={{ gap: 8 }}>
      {engine}{ai}
      {h && h !== "err" && <span className="tag">data {h.data_version}</span>}
      {a && a !== "err" && <span className="tag">prompts {a.prompt_version}</span>}
    </div>
  );
}
