"""Simulation engine.

Separation of concerns:
- Deterministic rules: `transition` (learned + accounting identities) and `derive` (identities, agents).
- Stochastic parts: `sample_inputs` draws every random quantity up front from one seeded generator.
  With stochastic sources switched off, the engine is a pure deterministic function of the scenario.
- Counterfactuals: the baseline driver path is built once and never mutated; each scenario gets a
  copy with its interventions applied, and all scenarios share the same random inputs (common
  random numbers), so differences isolate the intervention.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from nexus.config import (CO2_KG_PER_GALLON, DEFAULT_SEED, ENGINE_VERSION, FLEET_MPG, MAX_HORIZON_MONTHS,
                          MAX_PATHS)
from nexus.data.pipeline import FEATURES, REAL_BASE_DATE, run_pipeline
from nexus.domain.scenario import BASELINE, Scenario
from nexus.domain.state import DRIVERS, HouseholdTypeState, WorldState
from nexus.ml.inference import ModelBundle, load_models
from nexus.rng import make_rng
from nexus.simulation.agents import household_response, household_types
from nexus.validation.invariants import InvariantViolation, check_identities, check_trajectories

HIST = 24                         # months of history kept in the state buffer (features need t-18)
BLOCK = 12                        # block length for the driver bootstrap
EXCLUDE_FROM_DRIVER_POOL = ("2020-03-01", "2021-06-01")  # ASSUMPTION: pandemic regime excluded
SOURCES = ("drivers", "parameters", "noise", "structural")
DRIVER_COLS = ["real_gasoline_price", "real_electricity_price", "real_income", "unemployment"]


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class StochasticInputs:
    driver_shocks: np.ndarray   # [P, H, 4] monthly log changes of drivers
    noise: np.ndarray           # [P, H] transition noise on g
    coef_idx: np.ndarray        # [P] bootstrap coefficient draw (or -1 for point estimate)
    member_idx: np.ndarray      # [P] ensemble member (or -1 for ensemble mean)
    seed: int | None
    sources: tuple[str, ...]


@dataclass
class RunResult:
    scenario: str
    months: list[str]
    trajectories: dict[str, np.ndarray]          # metric -> [P, H]
    checks: list[str] = field(default_factory=list)
    features: np.ndarray | None = None           # [P, H, F] model inputs actually used
    features: np.ndarray | None = None              # [P, H, F] model inputs seen by the transition


class SimulationEngine:
    def __init__(self, levels: pd.DataFrame | None = None, models: ModelBundle | None = None, data_version=None):
        if levels is None:
            levels, _, _, report = run_pipeline()
            data_version = report.data_hash
        self.levels = levels
        self.models = models or load_models()
        self.data_version = data_version or "unknown"
        self.hh = household_types()
        self._driver_pool = self._build_driver_pool()
        self.world = self.initialize()

    # ---------- initialization ----------
    def initialize(self) -> WorldState:
        lv = self.levels
        last = lv.index[-1]
        buf = lv.loc[:last].iloc[-HIST:].copy()
        imputed = []
        cols = DRIVER_COLS + ["vmt", "cpi", "gasoline_price", "electricity_price"]
        if buf[cols].isna().any().any():
            # Single-month gaps in the state buffer only are filled by explicit linear interpolation
            # and recorded. Training data is never interpolated.
            na = buf[cols].isna().any(axis=1)
            imputed = [str(d.date()) for d in buf.index[na]]
            if buf[cols].isna().astype(int).rolling(2).sum().max().max() > 1:
                raise InvariantViolation("state_buffer", "consecutive missing months in state history")
            if na.iloc[-1] or na.iloc[0]:
                raise InvariantViolation("state_buffer", "missing value at buffer edge")
            buf[cols] = buf[cols].interpolate(method="linear", limit=1)
        self._buf = buf
        self._log_hist = np.log(buf[DRIVER_COLS].to_numpy())            # [HIST, 4]
        self._log_vmt_hist = np.log(buf["vmt"].to_numpy())               # [HIST]
        self._cpi = float(buf["cpi"].iloc[-1])
        self._base_cpi = float(lv.loc[REAL_BASE_DATE, "cpi"])
        self._cpi2017 = float(lv.loc["2017-01-01":"2017-12-01", "cpi"].mean())
        self._start = last + pd.offsets.MonthBegin(1)
        row = buf.iloc[-1]
        variables = {"gasoline_price": float(row["gasoline_price"]), "electricity_price": float(row["electricity_price"]),
                     "real_income": float(row["real_income"]), "unemployment": float(row["unemployment"]),
                     "cpi": float(row["cpi"]), "vmt": float(row["vmt"])}
        dlp = np.array([self._log_hist[-1, 0] - self._log_hist[-13, 0]])
        dle = np.array([self._log_hist[-1, 1] - self._log_hist[-13, 1]])
        d = self._derive_point(np.array([[row["vmt"]]]), np.array([[row["real_gasoline_price"]]]),
                               np.array([[row["real_electricity_price"]]]), np.array([[row["real_income"]]]),
                               dlp[:, None], dle[:, None])
        variables.update({k: float(d[k][0, 0]) for k in ("fuel_gallons", "co2_kt", "fuel_spend",
                                                          "energy_burden_mean", "energy_burden_low_income")})
        hh = [HouseholdTypeState(name=n, weight=float(w), monthly_vmt_miles=float(m), energy_burden=float(b))
              for n, w, m, b in zip(self.hh.names, self.hh.weight, d["_miles"][0], d["_burden"][0])]
        return WorldState(as_of=str(last.date()), variables=variables, households=hh, data_version=self.data_version,
                          imputed_months=imputed,
                          notes=["CPI held at last observed value; nominal and real price changes coincide in simulation"])

    def _build_driver_pool(self) -> np.ndarray:
        x = np.log(self.levels[DRIVER_COLS]).diff()
        a, b = EXCLUDE_FROM_DRIVER_POOL
        x = x[~((x.index >= a) & (x.index <= b))].dropna()
        return x.to_numpy()

    # ---------- stochastic part (all randomness lives here) ----------
    def sample_inputs(self, n_paths: int, horizon: int, seed: int | None = DEFAULT_SEED,
                      sources: tuple[str, ...] = SOURCES) -> StochasticInputs:
        if not (1 <= horizon <= MAX_HORIZON_MONTHS) or not (1 <= n_paths <= MAX_PATHS):
            raise ScenarioError("horizon or n_paths out of limits")
        unknown = set(sources) - set(SOURCES)
        if unknown:
            raise ScenarioError(f"unknown uncertainty sources: {sorted(unknown)}")
        rng = make_rng(seed if seed is not None else DEFAULT_SEED)
        P, H = n_paths, horizon
        # Draw everything unconditionally in a fixed order so switching a source off does not shift
        # the random stream of the others (needed for the uncertainty decomposition).
        pool = self._driver_pool
        n_blocks = int(np.ceil(H / BLOCK))
        starts = rng.integers(0, len(pool) - BLOCK, size=(P, n_blocks))
        idx = (starts[:, :, None] + np.arange(BLOCK)).reshape(P, -1)[:, :H]
        shocks = pool[idx]
        res = self.models.linear.residuals
        noise = rng.choice(res, size=(P, H), replace=True)
        coef_idx = rng.integers(0, len(self.models.linear.boot_coef), size=P)
        m = self.models.mlp.n_members if self.models.mlp is not None else 1
        member_idx = rng.integers(0, m, size=P)
        if "drivers" not in sources:
            shocks = np.zeros_like(shocks)
        if "noise" not in sources:
            noise = np.zeros_like(noise)
        if "parameters" not in sources:
            coef_idx = np.full(P, -1)
        if "structural" not in sources:
            member_idx = np.full(P, -1)
        return StochasticInputs(shocks, noise, coef_idx, member_idx, seed, tuple(sources))

    def deterministic_inputs(self, horizon: int) -> StochasticInputs:
        return self.sample_inputs(1, horizon, DEFAULT_SEED, sources=())

    # ---------- interventions (pure functions on copies) ----------
    def baseline_drivers(self, inputs: StochasticInputs) -> np.ndarray:
        """[P, H, 4] log driver levels for the baseline. Returned array is marked read-only."""
        base = self._log_hist[-1] + np.cumsum(inputs.driver_shocks, axis=1)
        base.setflags(write=False)
        return base

    @staticmethod
    def apply_intervention(drivers: np.ndarray, scenario: Scenario) -> np.ndarray:
        out = np.array(drivers, copy=True)  # the baseline is never mutated
        H = out.shape[1]
        for iv in scenario.interventions:
            j = DRIVERS.index(iv.variable)
            if iv.start_month >= H:
                raise ScenarioError(f"intervention on {iv.variable} starts after the horizon")
            sl = slice(iv.start_month, min(H, iv.start_month + iv.duration_months))
            if iv.operation == "multiply":
                out[:, sl, j] += np.log(iv.value)
            else:  # add percentage points to unemployment, in level space
                lvl = np.exp(out[:, sl, j]) + iv.value
                if np.any(lvl <= 0) or np.any(lvl > 100):
                    raise ScenarioError("unemployment intervention leaves the valid range (0, 100] percent")
                out[:, sl, j] = np.log(lvl)
        return out

    # ---------- deterministic transition ----------
    def _coefs(self, inputs: StochasticInputs):
        lin = self.models.linear
        if inputs.coef_idx[0] < 0:
            P = len(inputs.coef_idx)
            return np.tile(lin.coef, (P, 1)), np.full(P, lin.intercept)
        return lin.boot_coef[inputs.coef_idx], lin.boot_intercept[inputs.coef_idx]

    def step(self, t: int, logd: np.ndarray, logv: np.ndarray, coef, intercept, inputs: StochasticInputs):
        """Advance one month at absolute buffer index t (deterministic given inputs). Writes logv[:, t]."""
        X = np.stack([
            logd[:, t, 0] - logd[:, t - 12, 0],
            logd[:, t - 6, 0] - logd[:, t - 18, 0],
            logd[:, t, 1] - logd[:, t - 12, 1],
            logd[:, t, 2] - logd[:, t - 12, 2],
            np.exp(logd[:, t, 3]) - np.exp(logd[:, t - 12, 3]),
            logv[:, t - 1] - logv[:, t - 13],
        ], axis=1)
        g = np.einsum("pf,pf->p", X, coef) + intercept
        if self.models.tf_selected:
            members = self.models.mlp.predict_members(X)          # [M, P]
            mi = inputs.member_idx
            g = g + np.where(mi < 0, members.mean(axis=0), members[np.maximum(mi, 0), np.arange(len(mi))])
        g = g + inputs.noise[:, t - HIST]
        logv[:, t] = logv[:, t - 12] + g
        return X, g

    def run(self, scenario: Scenario, inputs: StochasticInputs, baseline: np.ndarray | None = None) -> RunResult:
        P, H = inputs.noise.shape
        base = self.baseline_drivers(inputs) if baseline is None else baseline
        drivers = self.apply_intervention(base, scenario)
        logd = np.concatenate([np.broadcast_to(self._log_hist, (P, HIST, 4)), drivers], axis=1)
        logv = np.concatenate([np.broadcast_to(self._log_vmt_hist, (P, HIST)), np.zeros((P, H))], axis=1)
        coef, intercept = self._coefs(inputs)
        feats = np.zeros((P, H, len(FEATURES)))
        for h in range(H):
            X, _ = self.step(HIST + h, logd, logv, coef, intercept, inputs)
            feats[:, h] = X
        res = self.collect(scenario.name, H, logd[:, HIST:], logv[:, HIST:], feats[..., 0], feats[..., 2])
        res.features = feats
        return res

    # ---------- collection (deterministic identities and agents) ----------
    def _derive_point(self, vmt, rgas, relec, rinc, dlp, dle):
        P, H = vmt.shape
        nom = self._cpi / self._base_cpi
        gas, elec = rgas * nom, relec * nom
        fuel = vmt / FLEET_MPG
        inc_total = rinc * 1e9 / 12.0 * (self._cpi / self._cpi2017)
        price_coef = float(self.models.linear.coef[0])
        resp = [household_response(self.hh, vmt[:, h], gas[:, h], elec[:, h], inc_total[:, h], dlp[:, h], dle[:, h],
                                   price_coef) for h in range(H)]
        return {"vmt": vmt, "fuel_gallons": fuel, "co2_kt": fuel * CO2_KG_PER_GALLON, "fuel_spend": fuel * gas,
                "gasoline_price": gas, "electricity_price": elec,
                "energy_burden_mean": np.stack([r["energy_burden_mean"] for r in resp], axis=1),
                "energy_burden_low_income": np.stack([r["energy_burden_low_income"] for r in resp], axis=1),
                "_miles": resp[-1]["miles_per_hh"], "_burden": resp[-1]["burden"]}

    def collect(self, name, H, logd, logv, dlp, dle) -> RunResult:
        d = np.exp(logd)
        out = self._derive_point(np.exp(logv), d[..., 0], d[..., 1], d[..., 2], dlp, dle)
        out = {k: v for k, v in out.items() if not k.startswith("_")}
        out["real_income"], out["unemployment"] = d[..., 2], d[..., 3]
        checks = check_trajectories(out) + check_identities(out, FLEET_MPG, CO2_KG_PER_GALLON)
        months = [str(m.date()) for m in pd.date_range(self._start, periods=H, freq="MS")]
        return RunResult(name, months, out, checks)

    # ---------- convenience ----------
    def run_scenarios(self, scenarios: list[Scenario], n_paths: int, horizon: int, seed: int | None = DEFAULT_SEED,
                      sources: tuple[str, ...] = SOURCES) -> dict[str, RunResult]:
        names = [s.name for s in scenarios]
        if len(set(names)) != len(names):
            raise ScenarioError("scenario names must be unique")
        if any(s.name == "baseline" and s.interventions for s in scenarios):
            raise ScenarioError("the name 'baseline' is reserved for the unmodified world")
        inputs = self.sample_inputs(n_paths, horizon, seed, sources)
        base = self.baseline_drivers(inputs)
        results = {"baseline": self.run(BASELINE, inputs, base)}
        for s in scenarios:
            if s.name != "baseline":
                results[s.name] = self.run(s, inputs, base)
        return results

    def run_deterministic(self, scenario: Scenario, horizon: int) -> dict[str, RunResult]:
        if scenario.name == "baseline" and scenario.interventions:
            raise ScenarioError("the name 'baseline' is reserved for the unmodified world")
        inputs = self.deterministic_inputs(horizon)
        base = self.baseline_drivers(inputs)
        return {"baseline": self.run(BASELINE, inputs, base), scenario.name: self.run(scenario, inputs, base)}

    def version_info(self) -> dict:
        return {"engine_version": ENGINE_VERSION, "data_version": self.data_version,
                "model_version": self.models.card.get("model_version", "unknown"), "tf_in_loop": self.models.tf_selected}
