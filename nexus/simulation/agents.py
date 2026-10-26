"""Household-type agents (vectorized). All parameters below are documented ASSUMPTIONS, not estimates.

State: share of VMT, kWh use, income. Observation: real price changes. Behavior: type-specific
elasticity multiplier around the aggregate learned response. Action: miles driven and kWh used.
Response: energy burden. The allocation is aggregate-consistent (types sum to national VMT).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

N_HOUSEHOLDS = 131e6          # ASSUMPTION: approximate number of US households
BASE_KWH = 860.0              # ASSUMPTION: average residential kWh per household per month
ELEC_ELASTICITY = -0.10       # ASSUMPTION: short-run household electricity price elasticity

INCOME = {"low": (0.35, 0.75, 1.4, 0.85), "middle": (1.0, 1.0, 1.0, 1.0), "high": (2.4, 1.2, 0.7, 1.2)}
#            (relative income, relative VMT, elasticity multiplier, relative kWh)
LOCATION = {"urban": (0.35, 0.75, 1.2), "suburban": (0.40, 1.0, 1.0), "rural": (0.25, 1.35, 0.7)}
#            (share within income group, relative VMT, elasticity multiplier)


@dataclass(frozen=True)
class HouseholdTypes:
    names: tuple[str, ...]
    weight: np.ndarray
    rel_income: np.ndarray
    rel_vmt: np.ndarray
    elast_mult: np.ndarray
    rel_kwh: np.ndarray
    low_income_mask: np.ndarray


def household_types() -> HouseholdTypes:
    rows = []
    for inc, (ri, rv_i, em_i, rk) in INCOME.items():
        for loc, (share, rv_l, em_l) in LOCATION.items():
            rows.append((f"{inc}_{loc}", share / 3.0, ri, rv_i * rv_l, em_i * em_l, rk, inc == "low"))
    names, w, ri, rv, em, rk, low = zip(*rows)
    return HouseholdTypes(tuple(names), np.array(w), np.array(ri), np.array(rv), np.array(em), np.array(rk), np.array(low))


def household_response(hh: HouseholdTypes, vmt_total, gas_price, elec_price, income_nominal_total_monthly,
                       dlp, dle, price_coef):
    """All inputs are [P] arrays. Returns dict of [P, K] arrays plus [P] aggregates."""
    # Behavior: type deviation from the aggregate response, normalized so the national total is preserved.
    tilt = np.exp(np.outer(price_coef * dlp, hh.elast_mult - 1.0))           # [P, K]
    raw = hh.weight * hh.rel_vmt * tilt
    share = raw / raw.sum(axis=1, keepdims=True)
    miles_per_hh = (vmt_total[:, None] * 1e6) * share / (hh.weight * N_HOUSEHOLDS)
    gallons_per_hh = miles_per_hh / _mpg()
    kwh = BASE_KWH * hh.rel_kwh * np.exp(ELEC_ELASTICITY * dle)[:, None]
    income_scale = income_nominal_total_monthly / N_HOUSEHOLDS / np.sum(hh.weight * hh.rel_income)
    income_hh = income_scale[:, None] * hh.rel_income
    spend = gallons_per_hh * gas_price[:, None] + kwh * elec_price[:, None]
    burden = spend / income_hh
    mean_burden = burden @ hh.weight
    low = hh.low_income_mask
    low_burden = burden[:, low] @ (hh.weight[low] / hh.weight[low].sum())
    return {"miles_per_hh": miles_per_hh, "burden": burden, "energy_burden_mean": mean_burden,
            "energy_burden_low_income": low_burden}


def _mpg():
    from nexus.config import FLEET_MPG
    return FLEET_MPG
