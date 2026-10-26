"""Reality Guard: how far a scenario pushes the model outside the data it learned from.

Checks the model inputs a scenario actually induces (deterministic path) against the training
distribution: per-feature range, Mahalanobis distance, and an IsolationForest. Output is a
reliability tier, never a claim that the result is correct.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest

from nexus.data.pipeline import FEATURES

TIERS = ("HIGH", "MEDIUM", "LOW", "OOD")
EXTEND = 1.5  # LOW tier allows the training min/max range widened by 50% of its width on each side


@dataclass
class RealityGuard:
    lo1: np.ndarray
    hi99: np.ndarray
    mn: np.ndarray
    mx: np.ndarray
    mean: np.ndarray
    icov: np.ndarray
    d95: float
    d99: float
    iforest: IsolationForest

    @classmethod
    def fit(cls, train_X: np.ndarray, seed: int = 42) -> "RealityGuard":
        mean = train_X.mean(axis=0)
        cov = np.cov(train_X, rowvar=False)
        icov = np.linalg.pinv(cov)
        d = cls._maha(train_X, mean, icov)
        iforest = IsolationForest(n_estimators=200, contamination=0.02, random_state=seed).fit(train_X)
        return cls(np.percentile(train_X, 1, axis=0), np.percentile(train_X, 99, axis=0), train_X.min(axis=0),
                   train_X.max(axis=0), mean, icov, float(np.percentile(d, 95)), float(np.percentile(d, 99)), iforest)

    @staticmethod
    def _maha(X, mean, icov):
        Z = X - mean
        return np.sqrt(np.einsum("ij,jk,ik->i", Z, icov, Z))

    def assess(self, X: np.ndarray) -> dict:
        """X: [N, F] induced feature rows (e.g. all months of a deterministic scenario path)."""
        width = self.mx - self.mn
        ext_lo, ext_hi = self.mn - (EXTEND - 1) * width, self.mx + (EXTEND - 1) * width
        d = self._maha(X, self.mean, self.icov)
        iso = self.iforest.predict(X)  # -1 anomaly
        row_tier = np.full(len(X), 0)
        inner = np.all((X >= self.lo1) & (X <= self.hi99), axis=1)
        in_range = np.all((X >= self.mn) & (X <= self.mx), axis=1)
        in_ext = np.all((X >= ext_lo) & (X <= ext_hi), axis=1)
        row_tier[~(inner & (d <= self.d95) & (iso == 1))] = 1
        row_tier[~(in_range & (d <= self.d99))] = 2
        row_tier[~in_ext] = 3
        worst = int(row_tier.max())
        flags = []
        for j, f in enumerate(FEATURES):
            if np.any(X[:, j] < self.mn[j]) or np.any(X[:, j] > self.mx[j]):
                flags.append({"feature": f, "min_seen": float(X[:, j].min()), "max_seen": float(X[:, j].max()),
                              "train_min": float(self.mn[j]), "train_max": float(self.mx[j])})
        return {"tier": TIERS[worst], "months_by_tier": {t: int(np.sum(row_tier == i)) for i, t in enumerate(TIERS)},
                "max_mahalanobis": float(d.max()), "train_mahalanobis_p95": self.d95, "train_mahalanobis_p99": self.d99,
                "isolation_forest_anomalies": int(np.sum(iso == -1)), "out_of_range_features": flags,
                "meaning": "reliability tier of the model for these inputs; not a guarantee of correctness"}
