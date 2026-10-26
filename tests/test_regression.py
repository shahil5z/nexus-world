"""Deterministic regression fixtures. Regenerate deliberately with: python -m tests.make_fixtures"""
import json
from pathlib import Path

import numpy as np

from nexus.domain.scenario import Scenario
from tests.conftest import GAS30

FIX = Path(__file__).parent / "fixtures" / "regression.json"


def compute(engine):
    s = Scenario.model_validate(GAS30)
    det = engine.run_deterministic(s, 12)
    mc = engine.run_scenarios([s], 200, 12, seed=42)
    return {"det_vmt": det["gas30"].trajectories["vmt"][0].tolist(),
            "det_burden_low": det["gas30"].trajectories["energy_burden_low_income"][0].tolist(),
            "mc_vmt_mean": mc["gas30"].trajectories["vmt"].mean(axis=0).tolist(),
            "mc_vmt_p95": np.percentile(mc["gas30"].trajectories["vmt"], 95, axis=0).tolist()}


def test_matches_fixture(engine):
    exp = json.loads(FIX.read_text())
    got = compute(engine)
    for k in exp:
        assert np.allclose(got[k], exp[k], rtol=1e-9, atol=0), k
