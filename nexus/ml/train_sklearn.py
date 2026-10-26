"""scikit-learn models: naive baselines, Ridge (selected for simulation), HistGradientBoosting benchmark."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nexus.data.pipeline import FEATURES, TARGET
from nexus.ml.metrics import regression_metrics

CV = TimeSeriesSplit(n_splits=5)  # expanding window, respects time order


def naive_predictions(df):
    return {"seasonal_naive_zero_growth": np.zeros(len(df)), "persistence_g_lag1": df["g_lag1"].to_numpy()}


def fit_ridge(train):
    X, y = train[FEATURES].to_numpy(), train[TARGET].to_numpy()
    gs = GridSearchCV(make_pipeline(StandardScaler(), Ridge()), {"ridge__alpha": [0.01, 0.1, 1, 3, 10, 30, 100]},
                      cv=CV, scoring="neg_mean_absolute_error")
    gs.fit(X, y)
    pipe = gs.best_estimator_
    sc, rg = pipe.named_steps["standardscaler"], pipe.named_steps["ridge"]
    coef = rg.coef_ / sc.scale_
    intercept = float(rg.intercept_ - np.sum(rg.coef_ * sc.mean_ / sc.scale_))
    # Out-of-fold residuals from expanding-window folds (strictly forward in time); used to scale noise.
    residuals = []
    for tr, te in CV.split(X):
        m = make_pipeline(StandardScaler(), Ridge(alpha=gs.best_params_["ridge__alpha"])).fit(X[tr], y[tr])
        residuals.append(y[te] - m.predict(X[te]))
    residuals = np.concatenate(residuals)
    return {"alpha": float(gs.best_params_["ridge__alpha"]), "cv_mae": float(-gs.best_score_),
            "coef": coef, "intercept": intercept, "residuals": residuals}


def block_bootstrap_ridge(train, alpha, rng, n_boot=200, block=24):
    X, y = train[FEATURES].to_numpy(), train[TARGET].to_numpy()
    n = len(X)
    coefs, inters = [], []
    for _ in range(n_boot):
        starts = rng.integers(0, n - block, size=int(np.ceil(n / block)))
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        p = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(X[idx], y[idx])
        sc, rg = p.named_steps["standardscaler"], p.named_steps["ridge"]
        coefs.append(rg.coef_ / sc.scale_)
        inters.append(rg.intercept_ - np.sum(rg.coef_ * sc.mean_ / sc.scale_))
    return np.array(coefs), np.array(inters)


def fit_hgb(train, seed):
    X, y = train[FEATURES].to_numpy(), train[TARGET].to_numpy()
    model = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=20,
                                          random_state=seed)
    cv_scores = []
    for tr, te in CV.split(X):
        m = HistGradientBoostingRegressor(**model.get_params()).fit(X[tr], y[tr])
        cv_scores.append(regression_metrics(y[te], m.predict(X[te]))["mae"])
    model.fit(X, y)
    return model, float(np.mean(cv_scores))


def evaluate(name_to_pred: dict, y) -> dict:
    return {k: regression_metrics(y, v) for k, v in name_to_pred.items()}
