import json

import numpy as np

from nexus.config import MODELS_DIR
from nexus.data.pipeline import FEATURES
from nexus.guard.reality import RealityGuard
from nexus.ml.inference import load_mlp_npz, load_models
from nexus.validation.backtest import run_backtests


def test_artifacts_load_without_pickle():
    m = load_models()
    assert m.linear.boot_coef.shape[1] == len(FEATURES)
    assert len(m.linear.residuals) > 100


def test_ridge_beats_naive_on_test():
    card = json.loads((MODELS_DIR / "model_card.json").read_text())
    t = card["metrics"]["test"]
    assert t["ridge"]["mae"] < t["seasonal_naive_zero_growth"]["mae"]
    assert t["ridge"]["mae"] < t["persistence_g_lag1"]["mae"]


def test_tf_decision_recorded_and_parity():
    card = json.loads((MODELS_DIR / "model_card.json").read_text())
    tf = card["tensorflow"]
    assert "selected" in tf
    if tf.get("attempted"):
        assert tf["numpy_parity_max_abs_diff"] < 1e-4
        ens = load_mlp_npz(MODELS_DIR / "tf_ensemble.npz")
        assert ens.n_members == tf["members"]


def test_guard_tiers(pipeline):
    _, _, splits, _ = pipeline
    X = splits["train"][FEATURES].to_numpy()
    g = RealityGuard.fit(X)
    assert g.assess(np.median(X, axis=0, keepdims=True))["tier"] == "HIGH"
    far = np.median(X, axis=0, keepdims=True).copy()
    far[0, 0] = 5.0
    assert g.assess(far)["tier"] == "OOD"


def test_guard_deterministic(pipeline):
    _, _, splits, _ = pipeline
    X = splits["train"][FEATURES].to_numpy()
    a, b = RealityGuard.fit(X).assess(X[:50]), RealityGuard.fit(X).assess(X[:50])
    assert a == b


def test_backtests_run(pipeline, engine):
    levels, feat, _, _ = pipeline
    bt = run_backtests(levels, feat, engine.models.card["ridge"]["alpha"])
    assert len(bt) == 3
    for v in bt.values():
        assert v["months"] == 24 and np.isfinite(v["engine_mape_pct"])
