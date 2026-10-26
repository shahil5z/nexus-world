"""Allowlisted, typed tools wrapping the Phase 2 engine. Every call returns a standard envelope.

Success: {status, tool, run_id, tool_call_id, data, warnings, limitations, metadata}
Error:   {status: "error", tool, run_id, tool_call_id, error: {code, message}, warnings, limitations, metadata}
Tools are pure functions of validated input (Monte Carlo is seeded), so results are cached deterministically.
"""
from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from nexus.config import DEFAULT_SEED, MAX_HORIZON_MONTHS
from nexus.domain.scenario import Scenario
from nexus.domain.state import VARIABLES
from nexus.simulation import montecarlo as mc
from nexus.simulation.engine import ScenarioError
from nexus.validation.invariants import InvariantViolation

KNOW = Path(__file__).parent / "knowledge"
STANDING_LIMITATIONS = ["Simulation under stated assumptions, not a forecast.",
                        "Percentile ranges are spreads of simulated paths, not confidence intervals or probabilities."]


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoArgs(_Args):
    pass


class CausalArgs(_Args):
    variable: str | None = Field(default=None, max_length=40)


class ScenarioArgs(_Args):
    scenario: Scenario
    horizon_months: int = Field(default=24, ge=1, le=MAX_HORIZON_MONTHS)


class MonteCarloArgs(ScenarioArgs):
    n_paths: int = Field(default=500, ge=50, le=1000)
    seed: int = Field(default=DEFAULT_SEED, ge=0, le=2**32 - 1)


class CompareArgs(_Args):
    scenarios: list[Scenario] = Field(min_length=1, max_length=3)
    horizon_months: int = Field(default=24, ge=1, le=MAX_HORIZON_MONTHS)
    n_paths: int = Field(default=300, ge=50, le=600)
    seed: int = Field(default=DEFAULT_SEED, ge=0, le=2**32 - 1)


@dataclass
class ToolSpec:
    name: str
    description: str
    args: type[BaseModel]
    fn: Callable[[BaseModel, Any], tuple[dict, list[str]]]
    cacheable: bool = True


class ToolBudgetExceeded(RuntimeError):
    pass


@dataclass
class AgentContext:
    run_id: str
    tracer: Any
    budget: Any
    evidence: dict = field(default_factory=dict)       # tool_call_id -> envelope
    n_calls: int = 0
    critic_called: bool = False
    critic_output: Any = None
    sheet: list = field(default_factory=list)          # evidence sheet for critic / explainer
    hooks: Any = None
    deterministic: dict | None = None                  # deterministic critic verdict

    def next_id(self) -> str:
        self.n_calls += 1
        return f"{self.run_id}-T{self.n_calls:02d}"


_CACHE: "OrderedDict[str, dict]" = OrderedDict()
_CACHE_MAX = 256


def _versions() -> dict:
    from nexus.services import get_engine
    return get_engine().version_info()


# ---------------- tool implementations ----------------

def t_list_variables(a, ctx):
    return {"variables": [{"name": v.name, "unit": v.unit, "description": v.description, "intervenable": v.intervenable}
                          for v in VARIABLES.values()]}, []


def t_get_world_state(a, ctx):
    from nexus.services import get_engine
    w = get_engine().world
    warn = [f"months imputed in the state buffer: {w.imputed_months}"] if w.imputed_months else []
    return {"as_of": w.as_of, "variables": w.variables, "households": [h.model_dump() for h in w.households]}, warn


def t_get_causal_context(a: CausalArgs, ctx):
    g = json.loads((KNOW / "causal_graph.json").read_text())
    notes = json.loads((KNOW / "external_notes.json").read_text())
    from nexus.services import get_engine
    coef = get_engine().models.card["ridge"]["coef"]
    edges = g["edges"]
    if a.variable:
        if a.variable not in g["nodes"]:
            raise ScenarioError(f"unknown variable '{a.variable}'")
        edges = [e for e in edges if a.variable in (e["from"], e["to"])]
    for e in edges:
        if e["type"] == "learned":
            e["coefficient_sign"] = "negative" if coef[e["feature"]] < 0 else "positive"
    sel = [n for n in notes["notes"] if not a.variable or n["topic"] == a.variable]
    return {"graph_version": g["version"], "edges": edges, "edge_types": g["edge_types"],
            "external_knowledge": {"warning": notes["warning"], "notes": sel}}, \
        ["edges describe the simulator wiring, not proven real-world causation"]


def t_validate_scenario(a: ScenarioArgs, ctx):
    from nexus.services import get_engine
    e = get_engine()
    last = max((i.start_month for i in a.scenario.interventions), default=0)
    if last >= a.horizon_months:
        raise ScenarioError("an intervention starts after the horizon")
    res = e.run_deterministic(a.scenario, a.horizon_months)[a.scenario.name]  # domain checks + invariants
    return {"valid": True, "scenario": a.scenario.model_dump(mode="json"), "horizon_months": a.horizon_months,
            "invariants_checked": len(res.checks)}, []


def t_run_reality_guard(a: ScenarioArgs, ctx):
    from nexus.services import guard_scenario
    g = guard_scenario(a.scenario, a.horizon_months)
    warn = [] if g["tier"] in ("HIGH", "MEDIUM") else [f"Reality Guard tier {g['tier']}: inputs outside the training data"]
    return g, warn


def t_run_counterfactual(a: ScenarioArgs, ctx):
    from nexus.services import get_engine
    r = get_engine().run_deterministic(a.scenario, a.horizon_months)
    b, s = r["baseline"].trajectories, r[a.scenario.name].trajectories
    out = {}
    for m in mc.SUMMARY_METRICS:
        bm, sm = float(b[m][0].mean()), float(s[m][0].mean())
        out[m] = {"baseline_horizon_mean": bm, "scenario_horizon_mean": sm, "pct_delta": 100 * (sm - bm) / bm}
    return {"mode": "deterministic", "months": r[a.scenario.name].months, "metrics": out}, \
        ["deterministic path: no uncertainty; use run_monte_carlo for ranges"]


def t_run_monte_carlo(a: MonteCarloArgs, ctx):
    from nexus.services import get_engine
    res = get_engine().run_scenarios([a.scenario], a.n_paths, a.horizon_months, a.seed)
    summ = mc.compare(res)
    return {"mode": "monte_carlo", "n_paths": a.n_paths, "seed": a.seed, "horizon_months": a.horizon_months,
            "months": res[a.scenario.name].months, "summary": summ,
            "range_type": "percentile ranges of simulated paths (not confidence intervals)"}, []


def t_compare_scenarios(a: CompareArgs, ctx):
    from nexus.services import get_engine
    names = [s.name for s in a.scenarios]
    if len(set(names)) != len(names) or "baseline" in names:
        raise ScenarioError("scenario names must be unique and not 'baseline'")
    res = get_engine().run_scenarios(a.scenarios, a.n_paths, a.horizon_months, a.seed)
    return {"mode": "comparison", "n_paths": a.n_paths, "seed": a.seed, "scenarios": list(res),
            "summary": mc.compare(res)}, []


def t_get_model_status(a, ctx):
    from nexus.services import get_engine
    c = get_engine().models.card
    return {"model_version": c["model_version"], "data_version": c["data_version"], "features": c["features"],
            "target": c["target"], "transition_model": "ridge" + ("+tf" if get_engine().models.tf_selected else ""),
            "tensorflow_selected": c["tensorflow"].get("selected"), "ridge_alpha": c["ridge"]["alpha"]}, []


def t_get_model_evaluation(a, ctx):
    from nexus.services import get_backtests, get_engine
    c = get_engine().models.card
    keep = ("seasonal_naive_zero_growth", "persistence_g_lag1", "ridge")
    return {"holdout_mae": {s: {k: v["mae"] for k, v in c["metrics"][s].items() if k in keep} for s in c["metrics"]},
            "interval80_coverage": c["ridge"]["interval80_coverage"],
            "backtests": {k: {m: v[m] for m in ("window", "engine_mape_pct", "seasonal_naive_mape_pct",
                                                   "persistence_mape_pct", "engine_best")} for k, v in get_backtests().items()}}, []


def t_assess_evidence(a, ctx):
    from nexus.agentic.critic_rules import deterministic_verdict
    v = deterministic_verdict(ctx.evidence)
    ctx.deterministic = v
    return {**v, "evidence_sheet": ctx.sheet}, []


REGISTRY: dict[str, ToolSpec] = {t.name: t for t in [
    ToolSpec("list_variables", "List model variables with units and whether they can be intervened on.", NoArgs, t_list_variables),
    ToolSpec("get_world_state", "Current initial world state (last observed month).", NoArgs, t_get_world_state),
    ToolSpec("get_causal_context", "Modeled dependency edges (learned, identity, assumption) and cited external notes.", CausalArgs, t_get_causal_context),
    ToolSpec("validate_scenario", "Schema and domain validation of a scenario via a deterministic dry run.", ScenarioArgs, t_validate_scenario),
    ToolSpec("run_reality_guard", "Reliability tier (HIGH/MEDIUM/LOW/OOD) of the model for a scenario.", ScenarioArgs, t_run_reality_guard),
    ToolSpec("run_counterfactual", "Deterministic baseline vs scenario (no uncertainty).", ScenarioArgs, t_run_counterfactual),
    ToolSpec("run_monte_carlo", "Seeded Monte Carlo of baseline vs scenario with percentile ranges.", MonteCarloArgs, t_run_monte_carlo),
    ToolSpec("compare_scenarios", "Seeded comparison of up to 3 scenarios against the baseline.", CompareArgs, t_compare_scenarios),
    ToolSpec("get_model_status", "Model and data versions and the transition model in use.", NoArgs, t_get_model_status),
    ToolSpec("get_model_evaluation", "Holdout errors, interval coverage and shock-window backtests.", NoArgs, t_get_model_evaluation),
    ToolSpec("assess_evidence", "Deterministic critic verdict from the evidence gathered in this run.", NoArgs, t_assess_evidence, cacheable=False),
]}


def call_tool(name: str, raw_args: dict | str | None, ctx: AgentContext, caller: str = "pipeline") -> dict:
    tcid = ctx.next_id()
    t0 = time.perf_counter()
    meta = {"caller": caller, "cached": False}

    def fail(code, msg):
        env = {"status": "error", "tool": name, "run_id": ctx.run_id, "tool_call_id": tcid,
               "error": {"code": code, "message": msg[:300]}, "warnings": [], "limitations": [],
               "metadata": {**meta, "duration_ms": round((time.perf_counter() - t0) * 1000, 2)}}
        ctx.evidence[tcid] = env
        return env

    if ctx.n_calls > ctx.budget.max_tool_calls:
        return fail("tool_budget_exceeded", "tool call budget for this request is exhausted")
    spec = REGISTRY.get(name)
    if spec is None:
        return fail("tool_not_allowed", f"'{str(name)[:40]}' is not an allowlisted tool")
    try:
        if isinstance(raw_args, str):
            raw_args = json.loads(raw_args or "{}")
        if not isinstance(raw_args, (dict, type(None))):
            return fail("invalid_arguments", "arguments must be a JSON object")
        args = spec.args.model_validate(raw_args or {})
    except (ValidationError, json.JSONDecodeError) as e:
        msg = "; ".join(f"{'.'.join(map(str, x.get('loc', [])))}: {x.get('msg')}" for x in e.errors()[:5]) \
            if isinstance(e, ValidationError) else "malformed JSON"
        return fail("invalid_arguments", msg)
    key = name + ":" + args.model_dump_json()
    try:
        if spec.cacheable and key in _CACHE:
            data, warnings = _CACHE[key]["data"], _CACHE[key]["warnings"]
            _CACHE.move_to_end(key)
            meta["cached"] = True
        else:
            data, warnings = spec.fn(args, ctx)
            if spec.cacheable:
                _CACHE[key] = {"data": data, "warnings": warnings}
                if len(_CACHE) > _CACHE_MAX:
                    _CACHE.popitem(last=False)
    except ScenarioError as e:
        return fail("invalid_scenario", str(e))
    except InvariantViolation as e:
        return fail("invariant_violation", e.name)
    except Exception as e:  # noqa: BLE001 - tools never leak traces
        return fail("tool_failure", type(e).__name__)
    dt = (time.perf_counter() - t0) * 1000
    env = {"status": "ok", "tool": name, "run_id": ctx.run_id, "tool_call_id": tcid, "data": data,
           "warnings": warnings, "limitations": STANDING_LIMITATIONS,
           "metadata": {**meta, "duration_ms": round(dt, 2), "args": json.loads(args.model_dump_json()), **_versions()}}
    ctx.evidence[tcid] = env
    if ctx.tracer is not None:
        ctx.tracer.tool_calls += 1
        ctx.tracer.tool_ms += dt
        if caller == "pipeline":
            ctx.tracer.add("pipeline", "tool_call", "ok", name, f"{tcid}{' cached' if meta['cached'] else ''}", dt, warnings)
    return env


def sdk_tools(names: list[str]):
    """Expose allowlisted tools to an Agents SDK agent. Validation happens in call_tool, not the model."""
    from agents import FunctionTool

    def make(spec: ToolSpec):
        async def invoke(tool_ctx, args_json: str):
            env = call_tool(spec.name, args_json, tool_ctx.context, caller="llm")
            if spec.name == "assess_evidence" or env["status"] == "error":
                return json.dumps(env, default=str)
            return json.dumps({k: env[k] for k in ("status", "tool", "tool_call_id", "data", "warnings")}, default=str)[:12000]
        schema = spec.args.model_json_schema()
        return FunctionTool(name=spec.name, description=spec.description, params_json_schema=schema,
                            on_invoke_tool=invoke, strict_json_schema=False)

    for n in names:
        if n not in REGISTRY:
            raise KeyError(n)
    return [make(REGISTRY[n]) for n in names]
