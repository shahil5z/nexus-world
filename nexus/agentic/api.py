"""FastAPI router for the agent layer."""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from nexus.agentic import runs
from nexus.agentic.arena import ArenaRequest
from nexus.agentic.config import BUDGET, model_name
from nexus.agentic.prompts import prompt_fingerprint
from nexus.agentic.schemas import AnalyzeRequest
from nexus.agentic.secrets import ensure_openai_key

router = APIRouter()
_STATUS = {"t": 0.0, "v": None}


@router.post("/agent/analyze")
async def analyze(req: AnalyzeRequest):
    from nexus.agentic.orchestrator import analyze as run
    return await run(req)


STAGE_OF = {"check_input": "input_guardrail", "Supervisor": "intent", "IntentFallback": "intent",
            "validate_scenario": "validation", "run_reality_guard": "reality_guard", "run_monte_carlo": "simulation",
            "run_counterfactual": "simulation", "compare_scenarios": "simulation", "get_model_evaluation": "evaluation",
            "ModelCritic": "critique", "critic_rules": "critique", "model_critic": "critique",
            "Explanation": "explanation", "template_explanation": "explanation", "grounding_check": "grounding"}


def stage_of(ev: dict) -> str | None:
    return STAGE_OF.get(ev.get("tool") or "") or STAGE_OF.get(ev.get("action") or "") or STAGE_OF.get(ev.get("agent") or "")


@router.post("/agent/analyze/stream")
async def analyze_stream(req: AnalyzeRequest):
    """NDJSON stream: one {"type":"trace", "stage", "event"} line per real trace event, then {"type":"result"}."""
    import asyncio
    import json

    from fastapi.responses import StreamingResponse

    from nexus.agentic.orchestrator import analyze as run
    q: asyncio.Queue = asyncio.Queue()

    def listen(ev):
        q.put_nowait({"type": "trace", "stage": stage_of(ev), "event": ev})

    async def gen():
        task = asyncio.create_task(run(req, listener=listen))
        while True:
            getter = asyncio.create_task(q.get())
            done, _ = await asyncio.wait({task, getter}, return_when=asyncio.FIRST_COMPLETED)
            if getter in done:
                yield json.dumps(getter.result(), default=str) + "\n"
                continue
            getter.cancel()
            while not q.empty():
                yield json.dumps(q.get_nowait(), default=str) + "\n"
            try:
                yield json.dumps({"type": "result", "result": task.result()}, default=str) + "\n"
            except Exception as e:  # noqa: BLE001
                yield json.dumps({"type": "error", "error": type(e).__name__}) + "\n"
            return

    return StreamingResponse(gen(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})


SUGGESTIONS = [
    "What happens if gasoline prices rise 20% for 12 months?",
    "What if electricity prices rise 15% for 12 months?",
    "What if unemployment rises 2 points for 12 months?",
    "What if real income falls 5% for 12 months?",
    "As an exploratory stress test, what if gasoline prices triple for 12 months?",
    "How accurate is the model?",
]


@router.get("/agent/suggestions")
def suggestions():
    return {"suggestions": SUGGESTIONS, "note": "each suggestion is covered by tests against the deterministic pipeline"}


@router.get("/knowledge/causal-graph")
def causal_graph():
    import json
    from pathlib import Path
    return json.loads((Path(__file__).parent / "knowledge" / "causal_graph.json").read_text(encoding="utf-8"))


@router.post("/agent/policy-arena")
async def policy_arena(req: ArenaRequest):
    from nexus.agentic.orchestrator import policy_arena as run
    try:
        return await run(req)
    except (RuntimeError, ValidationError) as e:
        raise HTTPException(422, f"arena failed: {e}")


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    if not (len(run_id) == 19 and run_id.startswith("NEXUS-")):
        raise HTTPException(422, "malformed run id")
    r = runs.get(run_id)
    if r is None:
        raise HTTPException(404, "run not found (runs are kept in memory per instance)")
    return r


@router.get("/agent/status")
async def status():
    import agents
    import openai
    key = ensure_openai_key() and os.environ.get("NEXUS_DISABLE_LLM") != "1"
    live = {"checked": False}
    if key:
        if time.time() - _STATUS["t"] > 300 or _STATUS["v"] is None:
            t0 = time.perf_counter()
            try:
                c = openai.AsyncOpenAI(timeout=10.0, max_retries=0)
                m = await c.models.retrieve(model_name())
                live = {"checked": True, "ok": True, "model_id": m.id}
            except Exception as e:  # noqa: BLE001 - only the class name is returned
                live = {"checked": True, "ok": False, "error": type(e).__name__}
            live["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            _STATUS.update(t=time.time(), v=live)
        live = {**_STATUS["v"], "cached_age_s": round(time.time() - _STATUS["t"], 1)}
    return {"llm_configured": bool(key), "mode": "agentic" if key and live.get("ok") else "engine_only_fallback",
            "model": model_name(), "openai_agents_version": getattr(agents, "__version__", "unknown"),
            "openai_version": openai.__version__, "live_check": live, **prompt_fingerprint(),
            "budget": BUDGET.__dict__}
