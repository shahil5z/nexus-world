"""Evidence sheet: every number an agent may cite, with display form and provenance (tool, tool_call_id, run_id)."""
from __future__ import annotations

METRIC_LABEL = {"vmt": ("vehicle miles traveled", "million miles/month", 0),
                "co2_kt": ("CO2 emissions", "thousand t/month", 0),
                "fuel_spend": ("motor fuel spending", "million USD/month", 0),
                "fuel_gallons": ("fuel use", "million gallons/month", 0),
                "energy_burden_mean": ("mean household energy burden", "% of income", 2),
                "energy_burden_low_income": ("low-income household energy burden", "% of income", 2)}
SHEET_METRICS = ("vmt", "co2_kt", "fuel_spend", "energy_burden_mean", "energy_burden_low_income")


def _fmt(v: float, dec: int) -> str:
    return f"{v:,.{dec}f}"


class SheetBuilder:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.items: list[dict] = []

    def add(self, label, value, unit, dec, env, path):
        eid = f"E{len(self.items) + 1}"
        v = round(float(value), dec)
        self.items.append({"id": eid, "label": label, "value": v, "display": (f"{_fmt(v, dec)}%" if unit == "%" else f"{_fmt(v, dec)} {unit}".strip()),
                           "unit": unit, "tool": env["tool"], "tool_call_id": env["tool_call_id"],
                           "run_id": self.run_id, "path": path})
        return eid


def _scale(metric, v):
    return 100 * v if metric.startswith("energy_burden") else v


def add_monte_carlo(sb: SheetBuilder, env: dict, scen: str, prefix: str = ""):
    s = env["data"]["summary"]
    for m in SHEET_METRICS:
        label, unit, dec = METRIC_LABEL[m]
        b, c = s["baseline"][m], s[scen][m]
        p = f"{prefix}{scen}: " if prefix else ""
        sb.add(f"{p}baseline {label}, median of horizon mean", _scale(m, b["level"]["median"]), unit, dec, env, f"summary.baseline.{m}.level.median")
        sb.add(f"{p}scenario {label}, median of horizon mean", _scale(m, c["level"]["median"]), unit, dec, env, f"summary.{scen}.{m}.level.median")
        sb.add(f"{p}{label} change vs baseline, median", c["pct_delta"]["median"], "%", 2, env, f"summary.{scen}.{m}.pct_delta.median")
        sb.add(f"{p}{label} change vs baseline, p10 of simulated paths", c["pct_delta"]["p10"], "%", 2, env, f"summary.{scen}.{m}.pct_delta.p10")
        sb.add(f"{p}{label} change vs baseline, p90 of simulated paths", c["pct_delta"]["p90"], "%", 2, env, f"summary.{scen}.{m}.pct_delta.p90")
        if m.startswith("energy_burden"):
            sb.add(f"{p}{label} change vs baseline, median", 100 * c["delta"]["median"], "percentage points", 2, env, f"summary.{scen}.{m}.delta.median")
    sb.add(f"{prefix}number of simulated paths", env["data"]["n_paths"], "", 0, env, "n_paths")


def add_guard(sb, env, prefix=""):
    d = env["data"]
    sb.add(f"{prefix}Reality Guard max Mahalanobis distance", d["max_mahalanobis"], "", 2, env, "max_mahalanobis")
    sb.add(f"{prefix}training-data Mahalanobis p99", d["train_mahalanobis_p99"], "", 2, env, "train_mahalanobis_p99")
    for f in d["out_of_range_features"]:
        sb.add(f"{prefix}{f['feature']} max induced value (YoY log change)", f["max_seen"], "", 3, env, f"oor.{f['feature']}.max_seen")
        sb.add(f"{prefix}{f['feature']} training max", f["train_max"], "", 3, env, f"oor.{f['feature']}.train_max")


def add_evaluation(sb, env):
    d = env["data"]
    sb.add("80% interval coverage on test 2018-2026", 100 * d["interval80_coverage"]["test"], "%", 1, env, "interval80_coverage.test")
    sb.add("80% interval coverage on test excluding COVID", 100 * d["interval80_coverage"]["test_excl_covid"], "%", 1, env, "interval80_coverage.test_excl_covid")
    for k, v in d["backtests"].items():
        sb.add(f"backtest {k} engine error (MAPE)", v["engine_mape_pct"], "%", 2, env, f"backtests.{k}.engine_mape_pct")
        sb.add(f"backtest {k} seasonal naive error (MAPE)", v["seasonal_naive_mape_pct"], "%", 2, env, f"backtests.{k}.seasonal_naive_mape_pct")
