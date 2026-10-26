"""Performance measurements: python -m training.benchmark -> models/benchmark.json"""
import json
import platform
import statistics
import time

import numpy as np
from fastapi.testclient import TestClient

from nexus.config import MODELS_DIR
from nexus.data.pipeline import FEATURES
from nexus.domain.scenario import Intervention, Scenario
from nexus.ml.inference import load_models
from nexus.simulation.engine import HIST, SimulationEngine


def timeit(fn, reps):
    fn()
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); fn(); ts.append((time.perf_counter() - t) * 1000)
    return {"median_ms": round(statistics.median(ts), 3), "p95_ms": round(float(np.percentile(ts, 95)), 3), "reps": reps}


def main():
    out = {"python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor()}
    t = time.perf_counter(); e = SimulationEngine(); out["engine_init_ms"] = round((time.perf_counter() - t) * 1000, 1)
    s = Scenario(name="gas30", interventions=(Intervention(variable="gasoline_price", operation="multiply", value=1.3),))
    inp = e.sample_inputs(1000, 24, 1)
    logd = np.concatenate([np.broadcast_to(e._log_hist, (1000, HIST, 4)), e.baseline_drivers(inp)], axis=1)
    logv = np.concatenate([np.broadcast_to(e._log_vmt_hist, (1000, HIST)), np.zeros((1000, 24))], axis=1)
    c, i = e._coefs(inp)
    out["step_1000_paths"] = timeit(lambda: e.step(HIST, logd, logv, c, i, inp), 200)
    out["deterministic_trajectory_24m"] = timeit(lambda: e.run_deterministic(s, 24), 30)
    out["monte_carlo_500x24_2_scenarios"] = timeit(lambda: e.run_scenarios([s], 500, 24, 42), 10)
    out["monte_carlo_2000x36_2_scenarios"] = timeit(lambda: e.run_scenarios([s], 2000, 36, 42), 5)
    m = load_models()
    X = np.random.default_rng(0).normal(size=(1000, len(FEATURES)))
    out["ridge_inference_1000"] = timeit(lambda: m.linear.predict(X), 500)
    if m.mlp is not None:
        out["tf_ensemble_numpy_inference_1000"] = timeit(lambda: m.mlp.predict_members(X), 200)
    cl = TestClient(__import__("nexus.api.app", fromlist=["app"]).app)
    import nexus.api.app as appmod
    body = {"scenario": s.model_dump(mode="json"), "horizon_months": 24, "n_paths": 500}
    def api():
        appmod._hits.clear(); assert cl.post("/simulation/monte-carlo", json=body).status_code == 200
    def api_run():
        appmod._hits.clear(); assert cl.post("/simulation/run", json={"scenario": body["scenario"]}).status_code == 200
    out["api_monte_carlo_500x24_inprocess"] = timeit(api, 10)
    out["api_run_deterministic_inprocess"] = timeit(api_run, 20)
    (MODELS_DIR / "benchmark.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
