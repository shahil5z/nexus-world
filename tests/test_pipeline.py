import json

import numpy as np
import pandas as pd
import pytest

from nexus.config import RAW_DIR, TRAIN_END, VAL_END
from nexus.data import pipeline as pl


def test_manifest_hashes_match():
    assert len(pl.verify_manifest()) == 16


def test_tampered_file_detected(tmp_path):
    import shutil
    for f in RAW_DIR.iterdir():
        shutil.copy(f, tmp_path / f.name)
    m = json.loads((tmp_path / "manifest.json").read_text())
    p = tmp_path / m["files"][0]["file"] if "files" in m else None
    target = p or next(tmp_path.glob("UNRATE.csv"))
    target.write_text(target.read_text() + "2099-01-01,5.0\n")
    with pytest.raises(pl.DataValidationError):
        pl.verify_manifest(tmp_path)


def test_splits_are_temporal_and_disjoint(pipeline):
    _, feat, splits, report = pipeline
    tr, va, te = splits["train"], splits["val"], splits["test"]
    assert tr.index.max() <= pd.Timestamp(TRAIN_END) < va.index.min()
    assert va.index.max() <= pd.Timestamp(VAL_END) < te.index.min()
    assert len(tr) + len(va) + len(te) == len(feat)


def test_no_leakage_features_use_only_past(pipeline):
    levels, feat, _, _ = pipeline
    # Perturb the future and confirm earlier features are unchanged.
    cut = pd.Timestamp("2010-01-01")
    lv2 = levels.copy()
    lv2.loc[lv2.index > cut, ["vmt", "real_gasoline_price", "real_electricity_price", "real_income", "unemployment"]] *= 1.5
    f2 = pl.make_features(lv2)
    a, b = feat.loc[:cut], f2.loc[:cut]
    pd.testing.assert_frame_equal(a, b)


def test_g_lag1_is_previous_target(pipeline):
    _, feat, _, _ = pipeline
    s = feat["g"].shift(1)
    ok = s.notna()
    contiguous = feat.index.to_series().diff().dt.days.between(28, 31)
    m = ok & contiguous
    assert np.allclose(feat.loc[m, "g_lag1"], s[m])


def test_gaps_recorded_not_interpolated(pipeline):
    levels, feat, _, report = pipeline
    assert "2025-10-01" in report.gap_months
    assert levels.loc["2025-10-01"].isna().any()
    assert pd.Timestamp("2025-10-01") not in feat.index
