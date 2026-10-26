"""Simulation invariants. Violations raise; values are never silently clamped."""
import numpy as np


class InvariantViolation(RuntimeError):
    def __init__(self, name: str, detail: str):
        super().__init__(f"{name}: {detail}")
        self.name, self.detail = name, detail


def check_trajectories(traj: dict[str, np.ndarray]) -> list[str]:
    checked = []
    for k, v in traj.items():
        if not np.all(np.isfinite(v)):
            raise InvariantViolation("finite_values", f"{k} contains NaN or inf")
        checked.append(f"finite:{k}")
    for k in ("vmt", "fuel_gallons", "co2_kt", "fuel_spend", "gasoline_price", "electricity_price"):
        if k in traj and np.any(traj[k] <= 0):
            raise InvariantViolation("strictly_positive", f"{k} has non-positive values")
        checked.append(f"positive:{k}")
    for k in ("energy_burden_mean", "energy_burden_low_income"):
        if k in traj and np.any((traj[k] < 0) | (traj[k] > 1)):
            raise InvariantViolation("share_bounds", f"{k} outside [0,1]")
        checked.append(f"share:{k}")
    if "unemployment" in traj and np.any((traj["unemployment"] < 0) | (traj["unemployment"] > 100)):
        raise InvariantViolation("percent_bounds", "unemployment outside [0,100]")
    return checked


def check_identities(traj: dict[str, np.ndarray], mpg: float, co2_factor: float) -> list[str]:
    if not np.allclose(traj["fuel_gallons"], traj["vmt"] / mpg, rtol=1e-12):
        raise InvariantViolation("fuel_identity", "fuel_gallons != vmt / mpg")
    if not np.allclose(traj["co2_kt"], traj["fuel_gallons"] * co2_factor, rtol=1e-12):
        raise InvariantViolation("co2_identity", "co2 != fuel * factor")
    if not np.allclose(traj["fuel_spend"], traj["fuel_gallons"] * traj["gasoline_price"], rtol=1e-12):
        raise InvariantViolation("spend_identity", "fuel_spend != gallons * price")
    return ["fuel_identity", "co2_identity", "spend_identity"]
