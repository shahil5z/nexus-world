import numpy as np
import pytest
from pydantic import ValidationError

from nexus.domain.scenario import BASELINE, Intervention, Scenario
from nexus.domain.state import VARIABLES
from nexus.simulation import montecarlo as mc
from nexus.simulation.engine import SOURCES, ScenarioError
from nexus.validation.invariants import InvariantViolation, check_trajectories

GAS = Scenario(name="gas30", interventions=(Intervention(variable="gasoline_price", operation="multiply", value=1.3,
                                                         duration_months=12),))


def test_variable_registry_complete():
    for v in VARIABLES.values():
        assert v.unit and v.description and v.source and v.update
        assert v.valid_range[0] < v.valid_range[1]


def test_world_state_typed(engine):
    w = engine.world
    assert w.as_of == "2026-08-01" and w.imputed_months == ["2025-10-01"]
    assert abs(sum(h.weight for h in w.households) - 1) < 1e-12 and len(w.households) == 9
    for k, val in w.variables.items():
        lo, hi = VARIABLES[k].valid_range
        assert lo <= val <= hi, k


def test_same_seed_identical(engine):
    a = engine.run_scenarios([GAS], 200, 24, seed=7)
    b = engine.run_scenarios([GAS], 200, 24, seed=7)
    for k in a:
        for m in a[k].trajectories:
            assert np.array_equal(a[k].trajectories[m], b[k].trajectories[m])


def test_different_seed_differs(engine):
    a = engine.run_scenarios([GAS], 200, 24, seed=1)["baseline"].trajectories["vmt"]
    b = engine.run_scenarios([GAS], 200, 24, seed=2)["baseline"].trajectories["vmt"]
    assert not np.array_equal(a, b)


def test_baseline_never_mutated(engine):
    inputs = engine.sample_inputs(50, 24, 3)
    base = engine.baseline_drivers(inputs)
    snap = base.copy()
    engine.run(GAS, inputs, base)
    assert np.array_equal(base, snap)
    with pytest.raises(ValueError):
        base[0, 0, 0] = 1.0  # read-only


def test_counterfactual_isolated_before_start(engine):
    s = Scenario(name="late", interventions=(Intervention(variable="gasoline_price", operation="multiply", value=1.5,
                                                          start_month=6, duration_months=6),))
    r = engine.run_scenarios([s], 100, 24, 5)
    b, c = r["baseline"].trajectories["vmt"], r["late"].trajectories["vmt"]
    assert np.array_equal(b[:, :6], c[:, :6])
    assert not np.allclose(b[:, 6:], c[:, 6:])


def test_null_intervention_equals_baseline(engine):
    s = Scenario(name="noop", interventions=(Intervention(variable="gasoline_price", operation="multiply", value=1.0),))
    r = engine.run_scenarios([s], 100, 12, 5)
    assert np.allclose(r["baseline"].trajectories["vmt"], r["noop"].trajectories["vmt"])


def test_price_increase_lowers_vmt_raises_burden(engine):
    d = engine.run_deterministic(GAS, 24)
    assert np.all(d["gas30"].trajectories["vmt"][0, :12] < d["baseline"].trajectories["vmt"][0, :12])
    assert np.all(d["gas30"].trajectories["energy_burden_low_income"][0, :12] >
                  d["baseline"].trajectories["energy_burden_low_income"][0, :12])


def test_deterministic_mode_has_no_randomness(engine):
    a = engine.run_deterministic(GAS, 12)["gas30"].trajectories["vmt"]
    b = engine.run_deterministic(GAS, 12)["gas30"].trajectories["vmt"]
    assert np.array_equal(a, b)


def test_sources_off_zero_spread(engine):
    r = engine.run_scenarios([GAS], 50, 12, 1, sources=())
    v = r["gas30"].trajectories["vmt"]
    assert np.allclose(v, v[0])


def test_mc_stats_and_naming(engine):
    r = engine.run_scenarios([GAS], 300, 12, 42)
    c = mc.compare(r)
    s = c["gas30"]["vmt"]["delta"]
    assert s["p5"] <= s["p25"] <= s["median"] <= s["p75"] <= s["p95"] and s["min"] <= s["p5"] and s["max"] >= s["p95"]
    u = c["gas30"]["vmt"]["delta_uncertainty"]
    assert u["kind"] == "percentile_range" and u["n"] == 300 and u["spread"] >= 0


def test_decomposition_runs(engine):
    d = mc.decompose(engine, GAS, 100, 12, 42)
    assert set(d["without"]) == set(SOURCES)


def test_invariant_fails_safely():
    with pytest.raises(InvariantViolation):
        check_trajectories({"vmt": np.array([[1.0, np.nan]])})
    with pytest.raises(InvariantViolation):
        check_trajectories({"vmt": np.array([[1.0, -1.0]])})


def test_unemployment_out_of_range_rejected(engine):
    s = Scenario(name="u", interventions=(Intervention(variable="unemployment", operation="add", value=-10.0),))
    with pytest.raises(ScenarioError):
        engine.run_deterministic(s, 12)


@pytest.mark.parametrize("bad", [
    {"variable": "gasoline_price", "operation": "multiply", "value": 0},
    {"variable": "gasoline_price", "operation": "multiply", "value": 11},
    {"variable": "gasoline_price", "operation": "add", "value": 1},
    {"variable": "cpi", "operation": "multiply", "value": 2},
    {"variable": "gasoline_price", "operation": "multiply", "value": float("nan")},
    {"variable": "gasoline_price", "operation": "multiply", "value": 2, "start_month": 36},
    {"variable": "gasoline_price", "operation": "multiply", "value": 2, "extra": 1},
])
def test_bad_interventions_rejected(bad):
    with pytest.raises(ValidationError):
        Intervention.model_validate(bad)


def test_limits(engine):
    with pytest.raises(ScenarioError):
        engine.sample_inputs(5000, 12, 1)
    with pytest.raises(ScenarioError):
        engine.sample_inputs(10, 37, 1)
