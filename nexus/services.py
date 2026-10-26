"""Process-wide cached engine, guard and backtests (shared by the API and the agent tools)."""
from __future__ import annotations

from functools import lru_cache

from nexus.data.pipeline import FEATURES


@lru_cache(maxsize=1)
def get_engine():
    from nexus.simulation.engine import SimulationEngine
    return SimulationEngine()


@lru_cache(maxsize=1)
def get_guard():
    from nexus.data.pipeline import run_pipeline
    from nexus.guard.reality import RealityGuard
    _, _, splits, _ = run_pipeline()
    return RealityGuard.fit(splits["train"][FEATURES].to_numpy(), seed=42)


@lru_cache(maxsize=1)
def get_backtests() -> dict:
    from nexus.data.pipeline import make_features
    from nexus.validation.backtest import run_backtests
    e = get_engine()
    return run_backtests(e.levels, make_features(e.levels), e.models.card["ridge"]["alpha"])


def guard_scenario(scenario, horizon: int) -> dict:
    res = get_engine().run_deterministic(scenario, horizon)[scenario.name]
    return get_guard().assess(res.features.reshape(-1, len(FEATURES)))
