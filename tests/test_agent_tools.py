"""Phase 3: allowlisted tools tested directly (valid, invalid, boundary, malicious, limits)."""
import json

import pytest

from nexus.agentic.config import BUDGET
from nexus.agentic.tools import REGISTRY, AgentContext, call_tool

GAS20 = {"name": "gas20", "interventions": [{"variable": "gasoline_price", "operation": "multiply", "value": 1.2,
                                             "start_month": 0, "duration_months": 12}]}


@pytest.fixture
def ctx():
    return AgentContext(run_id="NEXUS-2026-test0001", tracer=None, budget=BUDGET)


def test_envelope_shape(ctx):
    env = call_tool("list_variables", {}, ctx)
    assert set(env) >= {"status", "tool", "run_id", "tool_call_id", "data", "warnings", "limitations", "metadata"}
    assert env["status"] == "ok" and env["run_id"] == ctx.run_id and env["tool_call_id"].endswith("T01")
    assert env["metadata"]["data_version"]


@pytest.mark.parametrize("name,args", [
    ("get_world_state", {}), ("get_causal_context", {"variable": "gasoline_price"}), ("get_model_status", {}),
    ("get_model_evaluation", {}), ("validate_scenario", {"scenario": GAS20}), ("run_reality_guard", {"scenario": GAS20}),
    ("run_counterfactual", {"scenario": GAS20}), ("run_monte_carlo", {"scenario": GAS20, "n_paths": 50}),
    ("compare_scenarios", {"scenarios": [GAS20], "n_paths": 50})])
def test_valid_calls(ctx, name, args):
    env = call_tool(name, args, ctx)
    assert env["status"] == "ok", env.get("error")
    json.dumps(env)  # serializable, no inf/nan objects


def test_monte_carlo_values_and_determinism(ctx):
    a = call_tool("run_monte_carlo", {"scenario": GAS20, "n_paths": 100, "seed": 7}, ctx)
    b = call_tool("run_monte_carlo", {"scenario": GAS20, "n_paths": 100, "seed": 7}, ctx)
    assert b["metadata"]["cached"] is True
    assert a["data"]["summary"] == b["data"]["summary"]
    d = a["data"]["summary"]["gas20"]["vmt"]["pct_delta"]
    assert d["p10"] <= d["median"] <= d["p90"] < 0


@pytest.mark.parametrize("name,args,code", [
    ("run_monte_carlo", {"scenario": GAS20, "n_paths": 5000}, "invalid_arguments"),
    ("run_monte_carlo", {"scenario": GAS20, "n_paths": 49}, "invalid_arguments"),
    ("run_monte_carlo", {"scenario": GAS20, "horizon_months": 37}, "invalid_arguments"),
    ("validate_scenario", {"scenario": {"name": "x", "interventions": [{"variable": "co2_kt", "operation": "multiply", "value": 2}]}}, "invalid_arguments"),
    ("validate_scenario", {"scenario": {"name": "x", "interventions": [{"variable": "gasoline_price", "operation": "multiply", "value": -1}]}}, "invalid_arguments"),
    ("validate_scenario", {"scenario": {"name": "x", "interventions": [{"variable": "gasoline_price", "operation": "add", "value": 1}]}}, "invalid_arguments"),
    ("validate_scenario", {"scenario": {"name": "x", "interventions": [{"variable": "gasoline_price", "operation": "multiply", "value": 1.1, "start_month": 30}]}, "horizon_months": 24}, "invalid_scenario"),
    ("validate_scenario", {"scenario": GAS20, "extra": 1}, "invalid_arguments"),
    ("get_causal_context", {"variable": "nope"}, "invalid_scenario"),
    ("compare_scenarios", {"scenarios": [GAS20] * 4}, "invalid_arguments"),
])
def test_invalid_and_boundary(ctx, name, args, code):
    env = call_tool(name, args, ctx)
    assert env["status"] == "error" and env["error"]["code"] == code and "data" not in env


def test_boundaries_accepted(ctx):
    s = {"name": "edge", "interventions": [{"variable": "unemployment", "operation": "add", "value": 50, "duration_months": 36}]}
    assert call_tool("validate_scenario", {"scenario": s, "horizon_months": 36}, ctx)["status"] == "ok"
    assert call_tool("run_monte_carlo", {"scenario": GAS20, "n_paths": 1000, "horizon_months": 36}, ctx)["status"] == "ok"


@pytest.mark.parametrize("name,args", [
    ("__import__('os').system('ls')", {}), ("exec", {"code": "print(1)"}), ("run_python", {}),
    ("validate_scenario", "{not json"), ("validate_scenario", ["a"]),
    ("validate_scenario", {"scenario": {"name": "x; rm -rf /", "interventions": []}}),
    ("validate_scenario", {"scenario": {"name": "x", "interventions": [{"variable": "gasoline_price", "operation": "multiply", "value": "1e309"}]}}),
])
def test_malicious(ctx, name, args):
    env = call_tool(name, args, ctx)
    assert env["status"] == "error"
    assert env["error"]["code"] in ("tool_not_allowed", "invalid_arguments")


def test_tool_budget_limit():
    from dataclasses import replace
    c = AgentContext(run_id="NEXUS-2026-test0002", tracer=None, budget=replace(BUDGET, max_tool_calls=3))
    codes = [call_tool("list_variables", {}, c)["status"] for _ in range(5)]
    assert codes[:3] == ["ok"] * 3 and codes[3:] == ["error"] * 2


def test_registry_allowlist_is_closed():
    assert set(REGISTRY) == {"list_variables", "get_world_state", "get_causal_context", "validate_scenario",
                             "run_reality_guard", "run_counterfactual", "run_monte_carlo", "compare_scenarios",
                             "get_model_status", "get_model_evaluation", "assess_evidence"}


def test_causal_context_marks_assumptions_and_external_knowledge(ctx):
    d = call_tool("get_causal_context", {}, ctx)["data"]
    assert {e["type"] for e in d["edges"]} <= {"learned", "identity", "assumption"}
    assert all(n["citation"].startswith("https://fred.stlouisfed.org/") for n in d["external_knowledge"]["notes"])
    assert any(e.get("coefficient_sign") == "negative" for e in d["edges"] if e["from"] == "gasoline_price")
