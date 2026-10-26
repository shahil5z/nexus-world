# NEXUS // WORLD: Data, Models, Validation (Phase 2, MEASURED on the box, Python 3.13.5)

## Data (IMPLEMENTED)
Six keyless FRED CSV series, snapshotted in `data/raw/` (about 80 KB) with sha256 in `manifest.json`. Data hash `3a305740276a45a6`.

| Variable | FRED id | Publisher |
|---|---|---|
| gasoline_price | APU00007471A | BLS |
| electricity_price | APU000072610 | BLS |
| cpi | CPIAUCSL | BLS |
| real_income | DSPIC96 | BEA |
| unemployment | UNRATE | BLS |
| vmt | TRFVOLUSM227NFWA | FHWA |

Pipeline: verify hashes; check columns, dates, duplicates, ordering, month starts, numeric, positivity, unemployment bounds; drop and count FRED "." values; join on a contiguous monthly index (gaps kept as NaN: 1985-09, 2025-10); deflate prices with CPI rebased to 2012-12; build features; drop rows touching a gap.

Merged window 1978-11..2026-08, 552 model rows. Splits (fixed, temporal): train 1980-05..2012-12 (390), val 2013-01..2017-12 (60), test 2018-01..2026-08 (102). A test perturbs all data after a date and asserts earlier features do not change (no look-ahead).

Target `g` = YoY log VMT growth. Features: `dlp`, `dlp_lag6` (real gasoline YoY log change, and lagged 6 months), `dle` (real electricity), `dly` (real income), `du` (unemployment YoY change, points), `g_lag1`.

## Models (MAE of g; lower is better)

| Model | Val | Test | Test excl. 2020-03..2021-12 |
|---|---|---|---|
| Seasonal naive (g = 0) | 0.01727 | 0.04332 | 0.01606 |
| Persistence (g = g_lag1) | **0.00792** | 0.03182 | 0.01448 |
| Ridge (alpha 30, TimeSeriesSplit CV) | 0.00888 | **0.03015** | **0.01412** |
| HistGradientBoosting (benchmark) | 0.01058 | 0.04091 | 0.01428 |
| Ridge + TF residual ensemble | 0.01020 | 0.03095 | 0.01498 |

RMSE and R2 are in `models/model_card.json`. Honest reading: on validation, persistence beats Ridge. Ridge beats every baseline on test. Ridge is used for simulation because it is the only candidate that responds to interventions; a persistence model cannot represent a counterfactual. Gains over persistence are small.

Ridge coefficients (raw scale): dlp -0.0181, dlp_lag6 -0.0129, dle -0.0082, dly 0.131, du -0.0029, g_lag1 0.428. Implied short-run gasoline elasticity of VMT is about -0.03, long-run about -0.054 (via g_lag1). Parameter uncertainty: 200 block-bootstrap refits (block 24). Noise: 325 out-of-fold residuals from expanding-window folds. Empirical 80% interval coverage of Ridge plus residual quantiles: val 0.93, test 0.70, test excluding COVID 0.84.

## TensorFlow (IMPLEMENTED, NOT SELECTED)
5-member MLP ensemble (16-16 ReLU, L2 1e-3, Huber, Adam 1e-3, batch 32), seeds 42..46, op determinism on, early stopping on the last 15% of train (patience 30, max 500 epochs). Members ran 417 to 500 epochs, so early stopping rarely triggered before the epoch cap. Exported to `models/tf_ensemble.npz` with NumPy inference; parity with Keras max abs diff 1.2e-8. Rule: used only if val MAE beats every other model. Result: val 0.01020 (box, Linux) / 0.01022 (Windows; TF is not bit-identical across platforms even with op determinism, OBSERVED) vs best 0.00792, so it is NOT used in the simulation loop. The comparison is kept and served by `/model/evaluate`. `tf_ensemble.npz` remains so the structural-uncertainty path stays tested.

## Backtests (rolling origin, VMT level MAPE %, 24 months, observed drivers, recursive)

| Window | Ridge | Seasonal naive | Persistence | Ridge best? |
|---|---|---|---|---|
| 2008 oil spike (2007-07..2009-06) | 4.03 | 1.90 | 2.60 | no |
| 2014-2016 collapse | 2.10 | 3.28 | 1.58 | no |
| 2022 spike (2021-07..2023-06) | 3.59 | 5.73 | 11.24 | yes |

Ridge wins 1 of 3 shock windows. The cause of the 2008 miss was not analyzed (NOT VERIFIED).

## Reality Guard probes (24-month deterministic run)
baseline HIGH; gasoline x1.3 LOW (price changes outside the 1980-2012 range); x2 OOD; x5 OOD.

## Uncertainty decomposition (gasoline x1.3 for 12 months, 500 paths, 24 months, VMT, seed 42)
Spread p5..p95 of the horizon-mean scenario-vs-baseline delta (million miles/month): all sources 1757; without parameters 71; without drivers 1736; without noise 1769; without structural 1757. Parameter uncertainty dominates the intervention effect. Driver paths and noise dominate the level spread (all sources 12700; without drivers 10849; without noise 10557). Structural (TF) contributes 0 because TF is not selected. Removing noise can widen the delta spread slightly because the response depends nonlinearly on path state (OBSERVED, not analyzed further).

## Household agents (ASSUMPTIONS, not estimated)
3 income x 3 location types with assumed relative income, miles, kWh and elasticity multipliers (`nexus/simulation/agents.py`). Allocation preserves national VMT exactly. All VMT is attributed to households (overstates fuel burden, since VMT includes commercial traffic). 131M households, 860 kWh/month, electricity elasticity -0.10, 22 mpg fleet.

## Performance (MEASURED, Windows 11, Intel64 Family 6 Model 183, Python 3.13.15, median of reps)
| Operation | Median ms | p95 ms |
|---|---|---|
| Engine init (load data + models) | 26.5 | n/a |
| One step, 1000 paths | 0.031 | 0.036 |
| Deterministic 24-month baseline + scenario | 2.23 | 2.49 |
| Monte Carlo 500 paths x 24 months, 2 scenarios | 11.1 | 12.3 |
| Monte Carlo 2000 x 36, 2 scenarios (max single run) | 57.9 | 59.1 |
| Ridge inference, 1000 rows | 0.003 | 0.003 |
| TF ensemble NumPy inference, 1000 rows | 0.255 | 0.33 |
| API /simulation/monte-carlo 500x24 (in-process TestClient) | 28.9 | 30.9 |
| API /simulation/run (in-process) | 13.1 | 14.1 |

In-process numbers exclude network and serverless cold start (NOT MEASURED). Full numbers: `models/benchmark.json`.
