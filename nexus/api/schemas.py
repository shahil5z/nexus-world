from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nexus.config import DEFAULT_SEED, MAX_HORIZON_MONTHS, MAX_PATHS, MAX_SCENARIOS
from nexus.domain.scenario import Scenario

MAX_PATH_MONTHS = 100_000  # total work cap: n_paths * horizon * scenarios (incl. baseline)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunRequest(_Base):
    scenario: Scenario
    horizon_months: int = Field(default=24, ge=1, le=MAX_HORIZON_MONTHS)


class MonteCarloRequest(RunRequest):
    n_paths: int = Field(default=500, ge=10, le=MAX_PATHS)
    seed: int = Field(default=DEFAULT_SEED, ge=0, le=2**32 - 1)
    decompose: bool = False  # adds 5 extra runs (all sources, then each source off)

    @model_validator(mode="after")
    def _cap(self):
        runs = 2 * (6 if self.decompose else 1)
        if self.n_paths * self.horizon_months * runs > MAX_PATH_MONTHS:
            raise ValueError(f"n_paths * horizon_months * runs must be <= {MAX_PATH_MONTHS} (decompose uses 12 runs)")
        return self


class CompareRequest(_Base):
    scenarios: list[Scenario] = Field(min_length=1, max_length=MAX_SCENARIOS - 1)
    horizon_months: int = Field(default=24, ge=1, le=MAX_HORIZON_MONTHS)
    n_paths: int = Field(default=500, ge=10, le=MAX_PATHS)
    seed: int = Field(default=DEFAULT_SEED, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def _cap(self):
        names = [s.name for s in self.scenarios]
        if len(set(names)) != len(names) or "baseline" in names:
            raise ValueError("scenario names must be unique and not 'baseline' (baseline is always included)")
        if self.n_paths * self.horizon_months * (len(self.scenarios) + 1) > MAX_PATH_MONTHS:
            raise ValueError(f"n_paths * horizon_months * (scenarios + 1) must be <= {MAX_PATH_MONTHS}")
        return self
