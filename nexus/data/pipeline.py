"""Reproducible data pipeline: raw -> validation -> cleaning -> transforms -> features -> splits.

Every transform is documented in docs/DATA-AND-MODEL.md. No interpolation, no random splits.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from nexus.config import PIPELINE_VERSION, RAW_DIR, TRAIN_END, VAL_END

SERIES = {
    "gasoline_price": {"id": "APU00007471A", "unit": "USD/gallon", "publisher": "BLS via FRED"},
    "electricity_price": {"id": "APU000072610", "unit": "USD/kWh", "publisher": "BLS via FRED"},
    "cpi": {"id": "CPIAUCSL", "unit": "index 1982-84=100", "publisher": "BLS via FRED"},
    "real_income": {"id": "DSPIC96", "unit": "billions chained 2017 USD, SAAR", "publisher": "BEA via FRED"},
    "unemployment": {"id": "UNRATE", "unit": "percent", "publisher": "BLS via FRED"},
    "vmt": {"id": "TRFVOLUSM227NFWA", "unit": "million vehicle miles", "publisher": "FHWA via FRED"},
}
POSITIVE = {"gasoline_price", "electricity_price", "cpi", "real_income", "vmt"}
REAL_BASE_DATE = "2012-12-01"  # CPI rebasing month for real prices (inside train period)

EXOG_FEATURES = ["dlp", "dlp_lag6", "dle", "dly", "du"]
FEATURES = EXOG_FEATURES + ["g_lag1"]
TARGET = "g"


class DataValidationError(ValueError):
    """Raised when raw data fails schema or integrity checks. Never silently repaired."""


@dataclass
class PipelineReport:
    version: str = PIPELINE_VERSION
    data_hash: str = ""
    rows_raw: dict = field(default_factory=dict)
    missing_dropped: dict = field(default_factory=dict)
    merged_range: tuple = ("", "")
    model_rows: int = 0
    split_rows: dict = field(default_factory=dict)
    gap_months: list = field(default_factory=list)


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(raw_dir=RAW_DIR) -> str:
    manifest = json.loads((raw_dir / "manifest.json").read_text())
    h = hashlib.sha256()
    for e in manifest["files"]:
        actual = _sha256(raw_dir / e["file"])
        if actual != e["sha256"]:
            raise DataValidationError(f"hash mismatch for {e['file']}")
        h.update(actual.encode())
    return h.hexdigest()[:16]


def load_series(name: str, raw_dir=RAW_DIR) -> tuple[pd.Series, int]:
    """Validate and clean one FRED CSV. Returns (monthly series, rows dropped as missing)."""
    sid = SERIES[name]["id"]
    df = pd.read_csv(raw_dir / f"{sid}.csv", dtype=str)
    if list(df.columns) != ["observation_date", sid]:
        raise DataValidationError(f"{sid}: unexpected columns {list(df.columns)}")
    dates = pd.to_datetime(df["observation_date"], format="%Y-%m-%d", errors="coerce")
    if dates.isna().any():
        raise DataValidationError(f"{sid}: unparseable dates")
    if dates.duplicated().any():
        raise DataValidationError(f"{sid}: duplicate dates")
    if not dates.is_monotonic_increasing:
        raise DataValidationError(f"{sid}: dates not sorted")
    if (dates.dt.day != 1).any():
        raise DataValidationError(f"{sid}: not month-start dates")
    values = pd.to_numeric(df[sid].replace({".": None, "": None}), errors="coerce")
    bad_text = df[sid].notna() & ~df[sid].isin([".", ""]) & values.isna()
    if bad_text.any():
        raise DataValidationError(f"{sid}: non-numeric values")
    s = pd.Series(values.to_numpy(), index=dates, name=name)
    missing = int(s.isna().sum())
    s = s.dropna()  # FRED marks missing as "."; dropped and counted, never interpolated
    if name in POSITIVE and (s <= 0).any():
        raise DataValidationError(f"{sid}: non-positive values")
    if name == "unemployment" and ((s < 0) | (s > 100)).any():
        raise DataValidationError(f"{sid}: unemployment outside [0,100]")
    return s, missing


def build_levels(raw_dir=RAW_DIR, report: PipelineReport | None = None) -> pd.DataFrame:
    report = report or PipelineReport()
    cols = {}
    for name in SERIES:
        s, missing = load_series(name, raw_dir)
        cols[name] = s
        report.rows_raw[name] = int(len(s) + missing)
        report.missing_dropped[name] = missing
    df = pd.concat(cols, axis=1, join="outer", sort=True).sort_index()
    # Common coverage window: from the latest series start to the earliest series end.
    start = max(s.index[0] for s in cols.values())
    end = min(s.index[-1] for s in cols.values())
    full = pd.date_range(start, end, freq="MS")
    # Reindex to a contiguous monthly index. Missing months stay NaN (never interpolated
    # for training); any feature that touches a missing month becomes NaN and is dropped.
    df = df.reindex(full)
    report.gap_months = [str(d.date()) for d in df.index[df.isna().any(axis=1)]]
    base_cpi = df.loc[REAL_BASE_DATE, "cpi"]
    df["real_gasoline_price"] = df["gasoline_price"] / df["cpi"] * base_cpi
    df["real_electricity_price"] = df["electricity_price"] / df["cpi"] * base_cpi
    report.merged_range = (str(df.index[0].date()), str(df.index[-1].date()))
    return df


def make_features(levels: pd.DataFrame) -> pd.DataFrame:
    """Features at month t use only information at or before t (and VMT up to t-1)."""
    lv = np.log(levels[["vmt", "real_gasoline_price", "real_electricity_price", "real_income"]])
    f = pd.DataFrame(index=levels.index)
    f["g"] = lv["vmt"] - lv["vmt"].shift(12)                       # target: YoY log VMT growth
    f["dlp"] = lv["real_gasoline_price"] - lv["real_gasoline_price"].shift(12)
    f["dlp_lag6"] = f["dlp"].shift(6)
    f["dle"] = lv["real_electricity_price"] - lv["real_electricity_price"].shift(12)
    f["dly"] = lv["real_income"] - lv["real_income"].shift(12)
    f["du"] = levels["unemployment"] - levels["unemployment"].shift(12)
    f["g_lag1"] = f["g"].shift(1)
    return f.dropna()


def temporal_split(feat: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "train": feat.loc[:TRAIN_END],
        "val": feat.loc[pd.Timestamp(TRAIN_END) + pd.offsets.MonthBegin(1):VAL_END],
        "test": feat.loc[pd.Timestamp(VAL_END) + pd.offsets.MonthBegin(1):],
    }


def run_pipeline(raw_dir=RAW_DIR):
    report = PipelineReport()
    report.data_hash = verify_manifest(raw_dir)
    levels = build_levels(raw_dir, report)
    feat = make_features(levels)
    splits = temporal_split(feat)
    report.model_rows = len(feat)
    report.split_rows = {k: [len(v), str(v.index[0].date()), str(v.index[-1].date())] for k, v in splits.items()}
    return levels, feat, splits, report
