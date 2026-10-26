"""Rolling-origin backtests over historical shock windows.

For each window, Ridge is refit on data strictly before the window start, then the engine's
transition rule is run in closed loop (g_lag1 from its own simulated VMT) using the OBSERVED
driver paths. This tests the dynamics, not driver forecasting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nexus.config import SHOCK_WINDOWS
from nexus.data.pipeline import FEATURES, TARGET


def closed_loop(levels: pd.DataFrame, feat: pd.DataFrame, start: str, end: str, coef, intercept):
    idx = levels.index
    t0, t1 = idx.get_loc(pd.Timestamp(start)), idx.get_loc(pd.Timestamp(end))
    logv = np.log(levels["vmt"].to_numpy()).copy()
    sim = logv.copy()
    preds = []
    for t in range(t0, t1 + 1):
        row = feat.loc[idx[t], FEATURES].to_numpy().copy() if idx[t] in feat.index else None
        if row is None:
            raise ValueError(f"missing feature row at {idx[t].date()}")
        row[-1] = sim[t - 1] - sim[t - 13]          # closed loop: own lagged growth
        g = float(row @ coef + intercept)
        sim[t] = sim[t - 12] + g
        preds.append(sim[t])
    actual = logv[t0:t1 + 1]
    return np.exp(np.array(preds)), np.exp(actual)


def closed_loop_persistence(levels, feat, start, end):
    """Persistence baseline: YoY growth held at its last observed value before the window."""
    idx = levels.index
    t0, t1 = idx.get_loc(pd.Timestamp(start)), idx.get_loc(pd.Timestamp(end))
    logv = np.log(levels["vmt"].to_numpy())
    g0 = logv[t0 - 1] - logv[t0 - 13]
    sim = logv.copy()
    for t in range(t0, t1 + 1):
        sim[t] = sim[t - 12] + g0
    return np.exp(sim[t0:t1 + 1]), np.exp(logv[t0:t1 + 1])


def run_backtests(levels, feat, alpha: float) -> dict:
    out = {}
    for name, (start, end) in SHOCK_WINDOWS.items():
        tr = feat.loc[:pd.Timestamp(start) - pd.offsets.MonthBegin(1)]
        p = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(tr[FEATURES].to_numpy(), tr[TARGET].to_numpy())
        sc, rg = p.named_steps["standardscaler"], p.named_steps["ridge"]
        coef = rg.coef_ / sc.scale_
        intercept = rg.intercept_ - np.sum(rg.coef_ * sc.mean_ / sc.scale_)
        sim, act = closed_loop(levels, feat, start, end, coef, intercept)
        # Closed-loop seasonal naive (zero growth): vmt(t) = vmt(t-12), using its own simulated values,
        # so it never sees observed VMT inside the window either.
        naive, _ = closed_loop(levels, feat, start, end, np.zeros(len(FEATURES)), 0.0)
        persist, _ = closed_loop_persistence(levels, feat, start, end)
        ape = np.abs(sim / act - 1) * 100
        nape = np.abs(naive / act - 1) * 100
        out[name] = {"window": [start, end], "train_rows": int(len(tr)), "months": int(len(act)),
                     "engine_mape_pct": float(ape.mean()), "engine_max_ape_pct": float(ape.max()),
                     "seasonal_naive_mape_pct": float(nape.mean()),
                     "persistence_mape_pct": float((np.abs(persist / act - 1) * 100).mean()),
                     "engine_beats_naive": bool(ape.mean() < nape.mean())}
        out[name]["engine_best"] = bool(out[name]["engine_mape_pct"] < min(out[name]["seasonal_naive_mape_pct"],
                                                                            out[name]["persistence_mape_pct"]))
    return out
