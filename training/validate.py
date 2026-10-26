"""Offline validation CLI: python -m training.validate -> models/validation_report.json"""
import json

from nexus.config import MODELS_DIR
from nexus.data.pipeline import FEATURES, run_pipeline
from nexus.domain.scenario import Intervention, Scenario
from nexus.guard.reality import RealityGuard
from nexus.simulation.engine import SimulationEngine
from nexus.simulation import montecarlo as mc
from nexus.validation.backtest import run_backtests


def main():
    levels, feat, splits, report = run_pipeline()
    card = json.loads((MODELS_DIR / "model_card.json").read_text())
    e = SimulationEngine(levels, data_version=report.data_hash)
    g = RealityGuard.fit(splits["train"][FEATURES].to_numpy(), seed=42)
    probes = {"baseline": Scenario(name="baseline"),
              "gas_x1.3": Scenario(name="gas_x1.3", interventions=(Intervention(variable="gasoline_price", operation="multiply", value=1.3),)),
              "gas_x2": Scenario(name="gas_x2", interventions=(Intervention(variable="gasoline_price", operation="multiply", value=2.0),)),
              "gas_x5": Scenario(name="gas_x5", interventions=(Intervention(variable="gasoline_price", operation="multiply", value=5.0),))}
    guard = {}
    for k, s in probes.items():
        r = e.run_deterministic(s, 24)[s.name]
        guard[k] = {key: v for key, v in g.assess(r.features.reshape(-1, len(FEATURES))).items() if key in ("tier", "months_by_tier", "max_mahalanobis", "out_of_range_features")}
    s = probes["gas_x1.3"]
    out = {"data_version": report.data_hash, "backtests": run_backtests(levels, feat, card["ridge"]["alpha"]),
           "reality_guard_probes": guard,
           "uncertainty_decomposition_gas_x1.3": mc.decompose(e, s, 500, 24, 42)}
    (MODELS_DIR / "validation_report.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"backtests": {k: {m: round(v[m], 2) for m in ("engine_mape_pct", "seasonal_naive_mape_pct", "persistence_mape_pct")}
                                    for k, v in out["backtests"].items()}, "guard": {k: v["tier"] for k, v in guard.items()}, "decomposition": out["uncertainty_decomposition_gas_x1.3"]}, indent=1))


if __name__ == "__main__":
    main()
