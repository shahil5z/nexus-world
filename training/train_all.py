"""Offline training CLI. Usage: python -m training.train_all [--seed 42] [--no-tf]

Writes models/linear_model.json, linear_bootstrap.npz, tf_ensemble.npz (if TF available),
model_card.json. No pickles. Selection uses the validation split only; test is reported once.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone

import numpy as np
import sklearn

from nexus.config import MODELS_DIR, TRAIN_END, VAL_END
from nexus.data.pipeline import FEATURES, TARGET, run_pipeline
from nexus.ml import train_sklearn as sk
from nexus.ml.inference import load_mlp_npz, save_mlp_npz
from nexus.ml.metrics import regression_metrics
from nexus.rng import make_rng

COVID = ("2020-03-01", "2021-12-01")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-tf", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    levels, feat, splits, report = run_pipeline()
    tr, va, te = splits["train"], splits["val"], splits["test"]
    test_ex = te[~((te.index >= COVID[0]) & (te.index <= COVID[1]))]

    ridge = sk.fit_ridge(tr)
    rpred = lambda df: df[FEATURES].to_numpy() @ ridge["coef"] + ridge["intercept"]  # noqa: E731
    hgb, hgb_cv = sk.fit_hgb(tr, a.seed)
    bc, bi = sk.block_bootstrap_ridge(tr, ridge["alpha"], make_rng(a.seed))

    def preds(df):
        p = sk.naive_predictions(df)
        p["ridge"] = rpred(df)
        p["hist_gradient_boosting"] = hgb.predict(df[FEATURES].to_numpy())
        return p

    metrics = {s: sk.evaluate(preds(df), df[TARGET].to_numpy())
               for s, df in {"val": va, "test": te, "test_excl_covid": test_ex}.items()}

    # 80% interval coverage of Ridge + out-of-fold residual quantiles (an empirical check).
    lo, hi = np.percentile(ridge["residuals"], [10, 90])
    coverage = {s: float(np.mean((df[TARGET] >= rpred(df) + lo) & (df[TARGET] <= rpred(df) + hi)))
                for s, df in {"val": va, "test": te, "test_excl_covid": test_ex}.items()}

    (MODELS_DIR / "linear_model.json").write_text(json.dumps({
        "type": "ridge", "features": FEATURES, "target": TARGET, "alpha": ridge["alpha"],
        "coef": ridge["coef"].tolist(), "intercept": ridge["intercept"], "train_end": TRAIN_END}, indent=2))
    np.savez(MODELS_DIR / "linear_bootstrap.npz", coef=bc, intercept=bi, residuals=ridge["residuals"])

    tf_info = {"attempted": not a.no_tf, "selected": False}
    if not a.no_tf:
        try:
            import tensorflow as tf
            from nexus.ml.tf_model import train_ensemble
            Xtr = tr[FEATURES].to_numpy()
            mean, scale, members, hist, first_tf = train_ensemble(Xtr, tr[TARGET].to_numpy() - rpred(tr), seed=a.seed)
            path = MODELS_DIR / "tf_ensemble.npz"
            save_mlp_npz(path, mean, scale, members)
            ens = load_mlp_npz(path)
            parity = float(np.max(np.abs(ens.predict_members(Xtr)[0] - first_tf)))
            tfm = {}
            for s, df in {"val": va, "test": te, "test_excl_covid": test_ex}.items():
                y = df[TARGET].to_numpy()
                tfm[s] = regression_metrics(y, rpred(df) + ens.predict_members(df[FEATURES].to_numpy()).mean(axis=0))
                metrics[s]["ridge_plus_tf_ensemble"] = tfm[s]
            best_other_val = min(v["mae"] for k, v in metrics["val"].items() if k != "ridge_plus_tf_ensemble")
            selected = tfm["val"]["mae"] < best_other_val
            tf_info = {"attempted": True, "selected": bool(selected), "tensorflow_version": tf.__version__,
                       "members": len(members), "hidden": [16, 16], "loss": "huber", "early_stopping_patience": 30,
                       "training_history": hist, "numpy_parity_max_abs_diff": parity,
                       "selection_rule": "selected only if val MAE < best of ridge, HGB and naive baselines",
                       "val_mae": tfm["val"]["mae"], "best_other_val_mae": best_other_val}
            if not selected:
                tf_info["note"] = "Not used in the simulation loop; Ridge-only transition. Comparison kept."
        except ImportError:
            tf_info = {"attempted": False, "selected": False, "note": "tensorflow not installed"}

    card = {
        "model_version": f"1.0.0+{report.data_hash}", "trained_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": a.seed, "data_version": report.data_hash, "pipeline": report.__dict__,
        "splits": {"train_end": TRAIN_END, "val_end": VAL_END, "rows": report.split_rows},
        "target": "g = log VMT(t) - log VMT(t-12)", "features": FEATURES,
        "ridge": {"alpha": ridge["alpha"], "timeseries_cv_mae": ridge["cv_mae"],
                  "coef": dict(zip(FEATURES, ridge["coef"].tolist())), "intercept": ridge["intercept"],
                  "bootstrap_draws": int(len(bc)), "bootstrap_block": 24, "oof_residuals": int(len(ridge["residuals"])),
                  "interval80_coverage": coverage},
        "hist_gradient_boosting": {"timeseries_cv_mae": hgb_cv, "role": "benchmark only"},
        "metrics": metrics, "tensorflow": tf_info,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "sklearn": sklearn.__version__},
        "train_seconds": round(time.perf_counter() - t0, 2),
    }
    (MODELS_DIR / "model_card.json").write_text(json.dumps(card, indent=2, default=str))
    print(json.dumps({"val": {k: round(v["mae"], 5) for k, v in metrics["val"].items()},
                      "test": {k: round(v["mae"], 5) for k, v in metrics["test"].items()},
                      "test_excl_covid": {k: round(v["mae"], 5) for k, v in metrics["test_excl_covid"].items()},
                      "tf_selected": tf_info.get("selected"), "seconds": card["train_seconds"]}, indent=1))


if __name__ == "__main__":
    main()
