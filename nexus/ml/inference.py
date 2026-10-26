"""Runtime inference with NumPy only (no TensorFlow, no pickle). Loads JSON/NPZ artifacts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from nexus.config import MODELS_DIR


class ModelUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class LinearModel:
    features: tuple[str, ...]
    coef: np.ndarray          # raw-scale coefficients, shape [F]
    intercept: float
    boot_coef: np.ndarray     # [B, F]
    boot_intercept: np.ndarray  # [B]
    residuals: np.ndarray     # out-of-fold residuals for noise sampling

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.coef + self.intercept


@dataclass(frozen=True)
class MLPEnsemble:
    mean: np.ndarray
    scale: np.ndarray
    layers: tuple  # per member: tuple of (W, b)

    @property
    def n_members(self) -> int:
        return len(self.layers)

    def predict_members(self, X: np.ndarray) -> np.ndarray:
        """Returns [M, N] residual predictions. ReLU hidden layers, linear output."""
        Z0 = (X - self.mean) / self.scale
        out = []
        for member in self.layers:
            Z = Z0
            for k, (W, b) in enumerate(member):
                Z = Z @ W + b
                if k < len(member) - 1:
                    Z = np.maximum(Z, 0.0)
            out.append(Z[:, 0])
        return np.stack(out)


def save_mlp_npz(path, mean, scale, members) -> None:
    arrays = {"mean": mean, "scale": scale, "n_members": np.array(len(members))}
    for i, layers in enumerate(members):
        arrays[f"m{i}_n_layers"] = np.array(len(layers))
        for k, (W, b) in enumerate(layers):
            arrays[f"m{i}_W{k}"] = W
            arrays[f"m{i}_b{k}"] = b
    np.savez(path, **arrays)


def load_mlp_npz(path) -> MLPEnsemble:
    d = np.load(path, allow_pickle=False)
    members = []
    for i in range(int(d["n_members"])):
        n = int(d[f"m{i}_n_layers"])
        members.append(tuple((d[f"m{i}_W{k}"], d[f"m{i}_b{k}"]) for k in range(n)))
    return MLPEnsemble(mean=d["mean"], scale=d["scale"], layers=tuple(members))


@dataclass(frozen=True)
class ModelBundle:
    linear: LinearModel
    mlp: MLPEnsemble | None
    card: dict

    @property
    def tf_selected(self) -> bool:
        return bool(self.card.get("tensorflow", {}).get("selected")) and self.mlp is not None


@lru_cache(maxsize=1)
def load_models(models_dir: str = str(MODELS_DIR)) -> ModelBundle:
    from pathlib import Path
    p = Path(models_dir)
    try:
        lin = json.loads((p / "linear_model.json").read_text())
        boot = np.load(p / "linear_bootstrap.npz", allow_pickle=False)
        card = json.loads((p / "model_card.json").read_text())
    except (OSError, ValueError) as e:
        raise ModelUnavailableError("model artifacts missing; run python -m training.train_all") from e
    linear = LinearModel(tuple(lin["features"]), np.array(lin["coef"]), float(lin["intercept"]),
                         boot["coef"], boot["intercept"], boot["residuals"])
    mlp = load_mlp_npz(p / "tf_ensemble.npz") if (p / "tf_ensemble.npz").exists() else None
    return ModelBundle(linear, mlp, card)
