"""Typed world-state schema and the variable registry (name, type, unit, range, source, update)."""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VariableSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    dtype: Literal["float"] = "float"
    unit: str
    description: str
    valid_range: tuple[float, float]  # physical/definitional validity, not a plausibility claim
    source: str
    update: str
    intervenable: bool = False


INF = math.inf
VARIABLES: dict[str, VariableSpec] = {v.name: v for v in [
    VariableSpec(name="gasoline_price", unit="USD/gallon (nominal)", description="US city average retail price, unleaded regular",
                 valid_range=(0.0, INF), source="BLS APU00007471A via FRED", update="exogenous driver path (held flat or block-bootstrapped) times intervention", intervenable=True),
    VariableSpec(name="electricity_price", unit="USD/kWh (nominal)", description="US city average residential electricity price",
                 valid_range=(0.0, INF), source="BLS APU000072610 via FRED", update="exogenous driver path times intervention", intervenable=True),
    VariableSpec(name="real_income", unit="billion chained 2017 USD, SAAR", description="Real disposable personal income",
                 valid_range=(0.0, INF), source="BEA DSPIC96 via FRED", update="exogenous driver path times intervention", intervenable=True),
    VariableSpec(name="unemployment", unit="percent", description="Civilian unemployment rate",
                 valid_range=(0.0, 100.0), source="BLS UNRATE via FRED", update="exogenous driver path plus intervention", intervenable=True),
    VariableSpec(name="cpi", unit="index 1982-84=100", description="CPI all urban consumers, held at last observed value in simulation",
                 valid_range=(0.0, INF), source="BLS CPIAUCSL via FRED", update="held constant (prices are simulated in real terms)"),
    VariableSpec(name="vmt", unit="million vehicle miles per month", description="Vehicle miles traveled, all US roads",
                 valid_range=(0.0, INF), source="FHWA TRFVOLUSM227NFWA via FRED; simulated by learned transition", update="log vmt(t) = log vmt(t-12) + predicted YoY growth + residual noise"),
    VariableSpec(name="fuel_gallons", unit="million gallons per month", description="Implied motor fuel use",
                 valid_range=(0.0, INF), source="derived rule", update="vmt / FLEET_MPG (assumption 22 mpg)"),
    VariableSpec(name="co2_kt", unit="thousand metric tons CO2 per month", description="Implied tailpipe CO2",
                 valid_range=(0.0, INF), source="derived rule", update="fuel_gallons * 8.887 kg/gal"),
    VariableSpec(name="fuel_spend", unit="million USD per month (nominal)", description="Implied motor fuel spending",
                 valid_range=(0.0, INF), source="derived rule", update="fuel_gallons * gasoline_price"),
    VariableSpec(name="energy_burden_mean", unit="share of household income", description="Household-weighted mean of (fuel + electricity spend) / income",
                 valid_range=(0.0, 1.0), source="household-type agents (assumption-based)", update="agent rule"),
    VariableSpec(name="energy_burden_low_income", unit="share of household income", description="Mean energy burden of low-income household types",
                 valid_range=(0.0, 1.0), source="household-type agents (assumption-based)", update="agent rule"),
]}
OUTPUT_METRICS = ["vmt", "fuel_gallons", "co2_kt", "fuel_spend", "gasoline_price", "electricity_price",
                  "energy_burden_mean", "energy_burden_low_income"]
DRIVERS = ["gasoline_price", "electricity_price", "real_income", "unemployment"]


class HouseholdTypeState(BaseModel):
    name: str
    weight: float = Field(ge=0, le=1)
    monthly_vmt_miles: float = Field(ge=0)
    energy_burden: float = Field(ge=0)


class WorldState(BaseModel):
    """Snapshot of the modeled world at one month."""
    model_config = ConfigDict(frozen=True)
    as_of: str
    variables: dict[str, float]
    households: list[HouseholdTypeState]
    data_version: str
    imputed_months: list[str] = []
    notes: list[str] = []
