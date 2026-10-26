"""FastAPI backend. No LLM involved. Training is offline (training/train_all.py), never an endpoint."""
from __future__ import annotations

import json
import os
import logging
import sys
import threading
import time
import uuid
from collections import defaultdict, deque

import numpy as np
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from nexus.config import ENGINE_VERSION, MAX_HORIZON_MONTHS, MAX_PATHS, MAX_SCENARIOS
from nexus.api.schemas import CompareRequest, MonteCarloRequest, RunRequest
from nexus.data.pipeline import FEATURES
from nexus.domain.scenario import Scenario
from nexus.domain.state import VARIABLES
from nexus.guard.reality import RealityGuard
from nexus.ml.inference import ModelUnavailableError
from nexus.simulation import montecarlo as mc
from nexus.simulation.engine import ScenarioError, SimulationEngine
from nexus.validation.invariants import InvariantViolation

MAX_BODY_BYTES = 64 * 1024
RATE_LIMIT = (30, 60.0)  # compute requests (POST) per window seconds, per client IP (in-memory, per instance)
READ_RATE_LIMIT = (120, 60.0)  # cheap GET requests (status, runs, knowledge) per window seconds, per client IP

log = logging.getLogger("nexus")
if not log.handlers:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)


def jlog(**kw):
    log.info(json.dumps(kw, default=str))


from nexus.services import get_backtests, get_engine, get_guard  # noqa: E402


# API docs are off unless NEXUS_ENABLE_DOCS=1 (local development only).
_DOCS = os.environ.get("NEXUS_ENABLE_DOCS") == "1"
app = FastAPI(
    title="NEXUS // WORLD API",
    version=ENGINE_VERSION,
    docs_url="/docs" if _DOCS else None,
    redoc_url="/redoc" if _DOCS else None,
    openapi_url="/openapi.json" if _DOCS else None,
)

try:  # agent layer is optional: the engine API works without openai-agents installed
    from nexus.agentic.api import router as _agent_router
    app.include_router(_agent_router)
except ImportError:  # pragma: no cover
    _agent_router = None
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def err(status, code, message, run_id, details=None):
    body = {"error": {"code": code, "message": message, "run_id": run_id}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


def client_ip(request: Request) -> str:
    """On Vercel the platform sets x-real-ip; elsewhere trust only the socket peer (headers are spoofable)."""
    if os.environ.get("VERCEL") and request.headers.get("x-real-ip"):
        return request.headers["x-real-ip"]
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def guard_requests(request: Request, call_next):
    run_id = uuid.uuid4().hex[:12]
    request.state.run_id = run_id
    t0 = time.perf_counter()
    cl = request.headers.get("content-length")
    if cl is not None and (not cl.isdigit() or int(cl) > MAX_BODY_BYTES):
        return err(413, "payload_too_large", f"body must be <= {MAX_BODY_BYTES} bytes", run_id)
    ip = client_ip(request)
    limit, window = RATE_LIMIT if request.method == "POST" else READ_RATE_LIMIT
    now = time.monotonic()
    with _lock:
        q = _hits[f"{request.method == 'POST'}:{ip}"]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return err(429, "rate_limited", "too many requests, retry later", run_id)
        q.append(now)
    try:
        resp = await call_next(request)
    except Exception as e:  # noqa: BLE001 - never leak stack traces
        jlog(event="error", run_id=run_id, path=request.url.path, error_type=type(e).__name__)
        resp = err(500, "internal_error", "unexpected server error", run_id)
    resp.headers["X-Run-Id"] = run_id
    jlog(event="request", run_id=run_id, method=request.method, path=request.url.path, status=resp.status_code,
         duration_ms=round((time.perf_counter() - t0) * 1000, 2), seed=getattr(request.state, "seed", None),
         **getattr(request.state, "versions", {}))
    return resp


@app.exception_handler(RequestValidationError)
async def _validation(request: Request, exc: RequestValidationError):
    details = [{"loc": [str(x) for x in e.get("loc", [])], "msg": e.get("msg", "")} for e in exc.errors()][:20]
    return err(422, "invalid_request", "request failed validation", request.state.run_id, details)


@app.exception_handler(ScenarioError)
async def _scenario(request: Request, exc: ScenarioError):
    return err(422, "invalid_scenario", str(exc), request.state.run_id)


@app.exception_handler(InvariantViolation)
async def _invariant(request: Request, exc: InvariantViolation):
    return err(422, "invariant_violation", f"simulation rejected: {exc.name}", request.state.run_id)


@app.exception_handler(ModelUnavailableError)
async def _nomodel(request: Request, exc: ModelUnavailableError):
    return err(503, "model_unavailable", "model artifacts not available", request.state.run_id)


def _meta(request: Request, seed=None, **extra):
    e = get_engine()
    v = e.version_info()
    request.state.versions, request.state.seed = v, seed
    return {"run_id": request.state.run_id, "seed": seed, **v, "as_of": e.world.as_of, **extra}


def _guard(scenario: Scenario, horizon: int) -> dict:
    e = get_engine()
    res = e.run_deterministic(scenario, horizon)[scenario.name]
    return get_guard().assess(res.features.reshape(-1, len(FEATURES)))


def _round(x):
    return np.round(np.asarray(x, float), 6).tolist()


@app.get("/health")
def health(request: Request):
    try:
        e = get_engine()
        return {"status": "ok", "engine_version": ENGINE_VERSION, "data_version": e.data_version,
                "model_version": e.models.card.get("model_version"), "llm_required": False}
    except ModelUnavailableError:
        return JSONResponse(status_code=503, content={"status": "degraded", "reason": "model artifacts missing"})


@app.post("/simulation/validate")
def validate(req: RunRequest, request: Request):
    g = _guard(req.scenario, req.horizon_months)
    return {"valid": True, "scenario": req.scenario.model_dump(), "reality_guard": g,
            "limits": {"max_horizon_months": MAX_HORIZON_MONTHS, "max_paths": MAX_PATHS, "max_scenarios": MAX_SCENARIOS},
            "meta": _meta(request)}


@app.post("/simulation/run")
def run(req: RunRequest, request: Request):
    e = get_engine()
    t0 = time.perf_counter()
    res = e.run_deterministic(req.scenario, req.horizon_months)
    b, s = res["baseline"], res[req.scenario.name]
    series = {m: {"baseline": _round(b.trajectories[m][0]), "scenario": _round(s.trajectories[m][0])}
              for m in mc.SUMMARY_METRICS + ("gasoline_price", "electricity_price", "real_income", "unemployment")}
    return {"mode": "deterministic", "months": s.months, "series": series,
            "invariants_checked": len(s.checks),
            "reality_guard": get_guard().assess(s.features.reshape(-1, len(FEATURES))),
            "initial_state": e.world.model_dump(mode="json"),
            "meta": _meta(request, compute_ms=round((time.perf_counter() - t0) * 1000, 2))}


@app.post("/simulation/monte-carlo")
def monte_carlo(req: MonteCarloRequest, request: Request):
    e = get_engine()
    t0 = time.perf_counter()
    res = e.run_scenarios([req.scenario], req.n_paths, req.horizon_months, req.seed)
    name = req.scenario.name
    decomposition = mc.decompose(e, req.scenario, req.n_paths, req.horizon_months, req.seed) if req.decompose else None
    bands = {m: {k: band_series(res[k].trajectories[m]) for k in res} for m in mc.SUMMARY_METRICS}
    return {"mode": "monte_carlo", "range_type": "percentile ranges of simulated paths (not confidence intervals)",
            "months": res[name].months, "n_paths": req.n_paths, "bands": bands, "summary": mc.compare(res),
            "uncertainty_decomposition": decomposition,
            "reality_guard": _guard(req.scenario, req.horizon_months),
            "meta": _meta(request, seed=req.seed, compute_ms=round((time.perf_counter() - t0) * 1000, 2))}


def band_series(x):
    return {k: _round(v) for k, v in mc.band_series(x).items()}


@app.post("/scenario/compare")
def compare(req: CompareRequest, request: Request):
    e = get_engine()
    t0 = time.perf_counter()
    res = e.run_scenarios(req.scenarios, req.n_paths, req.horizon_months, req.seed)
    return {"mode": "comparison", "range_type": "percentile ranges of simulated paths (not confidence intervals)",
            "scenarios": list(res), "n_paths": req.n_paths, "summary": mc.compare(res),
            "reality_guard": {s.name: _guard(s, req.horizon_months) for s in req.scenarios},
            "meta": _meta(request, seed=req.seed, compute_ms=round((time.perf_counter() - t0) * 1000, 2))}


def _var(v):
    d = v.model_dump()
    d["valid_range"] = [None if abs(x) == float("inf") else x for x in d["valid_range"]]  # null = unbounded
    return d


@app.get("/model/status")
def model_status(request: Request):
    e = get_engine()
    c = e.models.card
    return {"model_version": c.get("model_version"), "trained_utc": c.get("trained_utc"), "features": c.get("features"),
            "target": c.get("target"), "transition_model": "ridge" + ("+tf_ensemble" if e.models.tf_selected else ""),
            "tensorflow": {k: v for k, v in c.get("tensorflow", {}).items() if k != "training_history"},
            "variables": [_var(v) for v in VARIABLES.values()], "meta": _meta(request)}


@app.get("/model/evaluate")
def model_evaluate(request: Request):
    c = get_engine().models.card
    from nexus.config import MODELS_DIR
    vr = MODELS_DIR / "validation_report.json"
    probes = json.loads(vr.read_text()).get("reality_guard_probes") if vr.exists() else None
    return {"holdout_metrics": c.get("metrics"), "ridge": c.get("ridge"), "backtests": get_backtests(),
            "reality_guard_probes": probes,
            "tensorflow": {k: v for k, v in c.get("tensorflow", {}).items() if k != "training_history"},
            "notes": ["val is used for model selection; test is reported once", "metrics are on g (YoY log VMT growth)"],
            "meta": _meta(request)}
