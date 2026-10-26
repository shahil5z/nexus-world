import numpy as np


def regression_metrics(y, yhat) -> dict:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    err = yhat - y
    mse = float(np.mean(err ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return {"mae": float(np.mean(np.abs(err))), "mse": mse, "rmse": float(np.sqrt(mse)),
            "r2": float(1 - np.sum(err ** 2) / ss_tot) if ss_tot > 0 else float("nan"), "n": int(len(y))}
