"""Intervention and scenario schemas. Validation is strict; nothing is silently clamped."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from nexus.config import MAX_HORIZON_MONTHS, MAX_INTERVENTIONS
from nexus.domain.state import DRIVERS


class Intervention(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    variable: Literal["gasoline_price", "electricity_price", "real_income", "unemployment"]
    operation: Literal["multiply", "add"]
    value: float = Field(allow_inf_nan=False)
    start_month: int = Field(default=0, ge=0, le=MAX_HORIZON_MONTHS - 1)
    duration_months: int = Field(default=12, ge=1, le=MAX_HORIZON_MONTHS)

    @model_validator(mode="after")
    def _check(self):
        if self.operation == "multiply" and not (0.0 < self.value <= 10.0):
            raise ValueError("multiply value must be in (0, 10]")
        if self.operation == "add":
            if self.variable != "unemployment":
                raise ValueError("add is only supported for unemployment (percentage points)")
            if not (-50.0 <= self.value <= 50.0):
                raise ValueError("unemployment add must be within [-50, 50] points")
        return self


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9 _\-\.\+%]+$")
    interventions: tuple[Intervention, ...] = Field(default=(), max_length=MAX_INTERVENTIONS)

    @field_validator("interventions")
    @classmethod
    def _unique(cls, v):
        keys = [(i.variable, i.start_month) for i in v]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate intervention on same variable and start month")
        return v


BASELINE = Scenario(name="baseline")
assert set(DRIVERS) == {"gasoline_price", "electricity_price", "real_income", "unemployment"}
