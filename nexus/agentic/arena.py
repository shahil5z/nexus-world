"""Policy Arena: simulate candidate interventions, rank them in Python with explicit user-visible weights.

The LLM never chooses weights or ranks. Default weights are documented in DEFAULT_WEIGHTS.
All objectives are minimized on the median percent change vs the shared baseline (common random numbers).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from nexus.domain.scenario import Scenario

OBJECTIVES = {"co2_kt": "CO2 emissions", "vmt": "vehicle miles traveled", "fuel_spend": "motor fuel spending",
              "energy_burden_mean": "mean household energy burden",
              "energy_burden_low_income": "low-income household energy burden"}
DEFAULT_WEIGHTS = {"co2_kt": 0.5, "energy_burden_low_income": 0.5}


class ArenaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[Scenario] = Field(min_length=2, max_length=6)
    weights: dict[str, float] | None = None
    horizon_months: int = Field(default=24, ge=1, le=36)
    n_paths: int = Field(default=300, ge=50, le=600)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    include_exploratory: bool = False
    explain: bool = False

    @field_validator("weights")
    @classmethod
    def _w(cls, w):
        if w is None:
            return None
        bad = set(w) - set(OBJECTIVES)
        if bad:
            raise ValueError(f"unknown objectives: {sorted(bad)}")
        if any((not isinstance(v, (int, float))) or v < 0 or v != v or v == float("inf") for v in w.values()):
            raise ValueError("weights must be finite and non-negative")
        if sum(w.values()) <= 0:
            raise ValueError("at least one weight must be positive")
        return w

    @model_validator(mode="after")
    def _names(self):
        n = [c.name for c in self.candidates]
        if len(set(n)) != len(n) or "baseline" in n:
            raise ValueError("candidate names must be unique and not 'baseline'")
        return self


def normalize(w: dict | None) -> tuple[dict, str]:
    src = "user" if w else "default"
    w = dict(w or DEFAULT_WEIGHTS)
    tot = sum(w.values())
    return {k: v / tot for k, v in w.items() if v > 0}, src


def pareto(points: dict[str, dict[str, float]], objs: list[str]) -> dict[str, list[str]]:
    """For each candidate, the list of candidates that dominate it (all objectives <=, one <)."""
    out = {}
    for a, pa in points.items():
        out[a] = [b for b, pb in points.items() if b != a and all(pb[o] <= pa[o] for o in objs)
                  and any(pb[o] < pa[o] for o in objs)]
    return out


def rank(medians: dict[str, dict[str, float]], weights: dict[str, float]) -> list[dict]:
    objs = list(weights)
    norm = {}
    for o in objs:
        vals = [m[o] for m in medians.values()]
        lo, hi = min(vals), max(vals)
        for c, m in medians.items():
            norm.setdefault(c, {})[o] = 0.0 if hi == lo else (m[o] - lo) / (hi - lo)
    scores = {c: sum(weights[o] * norm[c][o] for o in objs) for c in medians}
    dom = pareto(medians, list(OBJECTIVES))
    order = sorted(medians, key=lambda c: (scores[c], c))
    return [{"rank": i + 1, "candidate": c, "score": round(scores[c], 6),
             "normalized": {o: round(v, 6) for o, v in norm[c].items()},
             "pareto": "non-dominated" if not dom[c] else "dominated", "dominated_by": dom[c]}
            for i, c in enumerate(order)]
