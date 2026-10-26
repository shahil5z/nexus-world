"""Runtime agent trace. Records actions, never prompts, model inputs or secrets."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from agents import RunHooks


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Tracer:
    def __init__(self):
        self.events: list[dict] = []
        self.t0 = time.perf_counter()
        self.llm_calls = 0
        self.tool_calls = 0
        self.tokens = {"input": 0, "output": 0, "total": 0}
        self.llm_ms = 0.0
        self.tool_ms = 0.0
        self.listener = None  # optional callable(event) used for streaming stage updates

    def add(self, agent: str, action: str, status: str = "ok", tool: str | None = None, summary: str = "",
            duration_ms: float | None = None, warnings: list[str] | None = None, **extra) -> dict:
        ev = {"seq": len(self.events) + 1, "timestamp": _now(), "t_ms": round((time.perf_counter() - self.t0) * 1000, 1),
              "agent": agent, "action": action, "tool": tool, "status": status, "summary": summary[:240],
              "duration_ms": None if duration_ms is None else round(duration_ms, 1), "warnings": warnings or []}
        ev.update(extra)
        self.events.append(ev)
        if self.listener is not None:
            self.listener(ev)
        return ev

    def step(self, agent, action, tool=None):
        return _Step(self, agent, action, tool)

    def stats(self) -> dict:
        return {"llm_calls": self.llm_calls, "tool_calls": self.tool_calls, "tokens": self.tokens,
                "llm_ms": round(self.llm_ms, 1), "tool_ms": round(self.tool_ms, 1),
                "elapsed_ms": round((time.perf_counter() - self.t0) * 1000, 1)}


class _Step:
    def __init__(self, tr, agent, action, tool):
        self.tr, self.agent, self.action, self.tool = tr, agent, action, tool
        self.status, self.summary, self.warnings = "ok", "", []

    def __enter__(self):
        self.t = time.perf_counter()
        return self

    def __exit__(self, et, ev, tb):
        if et is not None:
            self.status, self.summary = "error", f"{et.__name__}"
        self.tr.add(self.agent, self.action, self.status, self.tool, self.summary,
                    (time.perf_counter() - self.t) * 1000, self.warnings)
        return False


class BudgetExceeded(RuntimeError):
    pass


class TraceHooks(RunHooks[Any]):
    """Agents SDK lifecycle hooks feeding the Tracer and enforcing call/token budgets."""

    def __init__(self, tracer: Tracer, budget):
        self.tr, self.budget = tracer, budget
        self._llm_t: dict[int, float] = {}
        self._tool_t: dict[str, float] = {}

    async def on_agent_start(self, context, agent):
        self.tr.add(agent.name, "agent_start")

    async def on_agent_end(self, context, agent, output):
        self.tr.add(agent.name, "agent_end", summary=type(output).__name__)

    async def on_handoff(self, context, from_agent, to_agent):
        self.tr.add(from_agent.name, "handoff", summary=f"to {to_agent.name}")

    async def on_llm_start(self, context, agent, system_prompt, input_items):
        if self.tr.llm_calls >= self.budget.max_llm_calls:
            self.tr.add(agent.name, "llm_call", "blocked", summary="LLM call budget exhausted")
            raise BudgetExceeded("llm call budget exhausted")
        if self.tr.tokens["total"] >= self.budget.max_total_tokens:
            self.tr.add(agent.name, "llm_call", "blocked", summary="token budget exhausted")
            raise BudgetExceeded("token budget exhausted")
        self.tr.llm_calls += 1
        self._llm_t[id(agent)] = time.perf_counter()

    async def on_llm_end(self, context, agent, response):
        dt = (time.perf_counter() - self._llm_t.pop(id(agent), time.perf_counter())) * 1000
        self.tr.llm_ms += dt
        u = getattr(response, "usage", None)
        i, o = (getattr(u, "input_tokens", 0) or 0), (getattr(u, "output_tokens", 0) or 0)
        self.tr.tokens["input"] += i; self.tr.tokens["output"] += o; self.tr.tokens["total"] += i + o
        self.tr.add(agent.name, "llm_call", duration_ms=dt, summary=f"tokens in={i} out={o}")

    async def on_tool_start(self, context, agent, tool):
        key = getattr(context, "tool_call_id", None) or tool.name
        self._tool_t[key] = time.perf_counter()

    async def on_tool_end(self, context, agent, tool, result):
        key = getattr(context, "tool_call_id", None) or tool.name
        dt = (time.perf_counter() - self._tool_t.pop(key, time.perf_counter())) * 1000
        status, summary = "ok", ""
        if isinstance(result, str) and result.startswith('{"status": "error"'):
            status = "error"
        if tool.name in ("model_critic",):
            summary = "agent-as-tool call"
        self.tr.add(agent.name, "tool_call", status, tool.name, summary or f"{len(str(result))} chars", dt)


class ContextHooks(RunHooks[Any]):
    """Static hooks object for nested agent-as-tool runs; forwards to the per-request TraceHooks on the context."""

    def _h(self, context):
        return getattr(getattr(context, "context", None), "hooks", None)

    async def on_agent_start(self, context, agent):
        if (h := self._h(context)): await h.on_agent_start(context, agent)

    async def on_agent_end(self, context, agent, output):
        if (h := self._h(context)): await h.on_agent_end(context, agent, output)

    async def on_llm_start(self, context, agent, system_prompt, input_items):
        if (h := self._h(context)): await h.on_llm_start(context, agent, system_prompt, input_items)

    async def on_llm_end(self, context, agent, response):
        if (h := self._h(context)): await h.on_llm_end(context, agent, response)

    async def on_tool_start(self, context, agent, tool):
        if (h := self._h(context)): await h.on_tool_start(context, agent, tool)

    async def on_tool_end(self, context, agent, tool, result):
        if (h := self._h(context)): await h.on_tool_end(context, agent, tool, result)
