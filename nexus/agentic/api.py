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
