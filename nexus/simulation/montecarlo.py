"""Monte Carlo summaries. Ranges are empirical percentile ranges of simulated paths, NOT confidence intervals."""
from __future__ import annotations

import numpy as np

PCTS = (5, 10, 25, 50, 75, 90, 95)
SUMMARY_METRICS = ("vmt", "fuel_gallons", "co2_kt", "fuel_spend", "energy_burden_mean", "energy_burden_low_income")


def summarize(x: np.ndarray) -> dict:
    x = np.asarray(x, float).ravel()
    q = np.percentile(x, PCTS)
    out = {"mean": float(x.mean()), "median": float(np.median(x)), "std": float(x.std(ddof=1)) if len(x) > 1 else 0.0,
           "min": float(x.min()), "max": float(x.max()), "n": int(len(x))}
    out.update({f"p{p}": float(v) for p, v in zip(PCTS, q)})
    return out


def uncertainty(x: np.ndarray, lower=5, upper=95) -> dict:
    """Standard uncertainty output: central estimate, lower/upper percentile, spread, n."""
    x = np.asarray(x, float).ravel()
    lo, mid, hi = np.percentile(x, [lower, 50, upper])
    return {"central": float(mid), "lower": float(lo), "upper": float(hi), "spread": float(hi - lo),
            "lower_pct": lower, "upper_pct": upper, "n": int(len(x)), "kind": "percentile_range"}


def band_series(traj: np.ndarray) -> dict:
    q = np.percentile(traj, [5, 25, 50, 75, 95], axis=0)
    return {"p5": q[0].tolist(), "p25": q[1].tolist(), "median": q[2].tolist(), "p75": q[3].tolist(), "p95": q[4].tolist()}


def horizon_mean(traj: np.ndarray) -> np.ndarray:
    return traj.mean(axis=1)


def compare(results: dict, metrics=SUMMARY_METRICS) -> dict:
    """Per scenario: level summary over the horizon mean, and paired deltas vs baseline (common random numbers)."""
    base = results["baseline"].trajectories
    out = {}
    for name, r in results.items():
        entry = {}
        for m in metrics:
            lvl = horizon_mean(r.trajectories[m])
            e = {"level": summarize(lvl), "level_uncertainty": uncertainty(lvl)}
            if name != "baseline":
                b = horizon_mean(base[m])
                delta = lvl - b
                e["delta"] = summarize(delta)
                e["delta_uncertainty"] = uncertainty(delta)
                e["pct_delta"] = summarize(100.0 * delta / b)
            entry[m] = e
        out[name] = entry
    return out


def decompose(engine, scenario, n_paths, horizon, seed, metric="vmt") -> dict:
    """Spread of the scenario-vs-baseline delta with all sources on, and with each source switched off."""
    from nexus.simulation.engine import SOURCES

    def spread(sources):
        res = engine.run_scenarios([scenario], n_paths, horizon, seed, tuple(sources))
        d = horizon_mean(res[scenario.name].trajectories[metric]) - horizon_mean(res["baseline"].trajectories[metric])
        lvl = horizon_mean(res[scenario.name].trajectories[metric])
        return float(np.percentile(d, 95) - np.percentile(d, 5)), float(np.percentile(lvl, 95) - np.percentile(lvl, 5))

    full_d, full_l = spread(SOURCES)
    out = {"metric": metric, "all_sources": {"delta_spread_p5_p95": full_d, "level_spread_p5_p95": full_l}, "without": {}}
    for s in SOURCES:
        d, l = spread([x for x in SOURCES if x != s])
        out["without"][s] = {"delta_spread_p5_p95": d, "level_spread_p5_p95": l}
    return out
