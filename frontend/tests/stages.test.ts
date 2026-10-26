import { describe, expect, it } from "vitest";
import { stageOf, stageStates } from "../lib/stages";
import type { TraceEvent } from "../lib/types";

const ev = (seq: number, agent: string, action: string, tool: string | null, status = "ok"): TraceEvent =>
  ({ seq, timestamp: "2026-10-26T10:00:00Z", t_ms: seq, agent, action, tool, status, summary: "", duration_ms: 1, warnings: [] });

describe("stages", () => {
  it("maps trace events like the backend STAGE_OF", () => {
    expect(stageOf(ev(1, "InputGuardrail", "check_input", null))).toBe("input_guardrail");
    expect(stageOf(ev(2, "pipeline", "tool_call", "run_monte_carlo"))).toBe("simulation");
    expect(stageOf(ev(3, "pipeline", "critic_rules", null))).toBe("critique");
    expect(stageOf(ev(4, "pipeline", "grounding_check", null))).toBe("grounding");
  });
  it("derives states only from received events", () => {
    const s = stageStates([ev(1, "InputGuardrail", "check_input", null)], true);
    expect(s.input_guardrail).toBe("done");
    expect(s.intent).toBe("active");
    expect(s.simulation).toBe("pending");
  });
  it("marks unrun stages as skipped after completion and errors as error", () => {
    const s = stageStates([ev(1, "InputGuardrail", "check_input", null, "rejected")], false);
    expect(s.input_guardrail).toBe("error");
    expect(s.simulation).toBe("skipped");
  });
});
