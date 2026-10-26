# NEXUS // WORLD: Phase 2 Implementation

Status legend: IMPLEMENTED (code exists and was run), PLANNED (later phase), NOT IMPLEMENTED (deliberately out of scope).

## Layout

| Path | Role | Status |
|---|---|---|
| `training/snapshot_data.py` | Downloads keyless FRED CSVs into `data/raw/` and writes `manifest.json` (URL, UTC retrieval time, sha256, bytes) | IMPLEMENTED |
| `nexus/data/pipeline.py` | raw -> validation -> cleaning -> features -> temporal splits | IMPLEMENTED |
| `nexus/domain/state.py` | Variable registry (name, type, unit, description, range, source, update) and Pydantic `WorldState` | IMPLEMENTED |
| `nexus/domain/scenario.py` | Strict `Intervention` / `Scenario` schemas | IMPLEMENTED |
| `nexus/rng.py` | Central seeded RNG (PCG64) | IMPLEMENTED |
| `nexus/simulation/engine.py` | initialize, sample_inputs (all randomness), apply_intervention, step, run, collect | IMPLEMENTED |
| `nexus/simulation/agents.py` | 9 vectorized household types | IMPLEMENTED |
| `nexus/simulation/montecarlo.py` | Statistics, percentile ranges, paired deltas, uncertainty decomposition | IMPLEMENTED |
| `nexus/ml/` | sklearn training, TF ensemble training, NumPy inference | IMPLEMENTED |
| `nexus/guard/reality.py` | Reality Guard | IMPLEMENTED |
| `nexus/validation/` | Invariants, shock-window backtests | IMPLEMENTED |
| `nexus/api/` | FastAPI backend | IMPLEMENTED |
| `training/train_all.py`, `training/validate.py`, `training/benchmark.py` | Offline CLIs | IMPLEMENTED |
| Frontend (2D UI), LLM narration, deployment | | PLANNED (Phase 3+) |
| File uploads, training endpoint | | NOT IMPLEMENTED (by decision) |

## Reproduce

```
python -m venv .venv
.venv\Scripts\pip install -r requirements-train.txt
.venv\Scripts\python -m training.train_all      # writes models/*
.venv\Scripts\python -m training.validate       # writes models/validation_report.json
.venv\Scripts\python -m pytest
.venv\Scripts\python -m training.benchmark      # writes models/benchmark.json
.venv\Scripts\uvicorn nexus.api.app:app --port 8000
```
`training/snapshot_data.py` re-downloads data; doing so changes the data hash and requires retraining and regenerating `tests/fixtures/regression.json` (`python -m tests.make_fixtures`).

## Engine contract

1. `initialize()` builds a 24-month state buffer ending at the last common month. Single missing months in the buffer only are linearly interpolated and listed in `WorldState.imputed_months`. Training data is never interpolated.
2. `sample_inputs(n_paths, horizon, seed, sources)` draws every random quantity in a fixed order from one generator: driver shocks (12-month block bootstrap of historical monthly log changes, pandemic months 2020-03..2021-06 excluded, ASSUMPTION), transition noise (out-of-fold Ridge residuals), a bootstrap coefficient draw per path, an ensemble member per path. Switching a source off zeroes it without shifting the others.
3. `baseline_drivers` builds the baseline driver path and marks it read-only. `apply_intervention` returns a modified copy. All scenarios in a request share the same inputs (common random numbers).
4. `step` is deterministic: features from the buffer, g = linear(x) [+ TF residual if selected] + noise, log VMT(t) = log VMT(t-12) + g.
5. `collect` applies identities (fuel = VMT / 22 mpg ASSUMPTION, CO2 = fuel x 8.887 kg/gal, spend = fuel x price), household agents, and invariants. Violations raise; nothing is clamped.

CPI is held at its last observed value during simulation, so nominal and real price changes coincide.

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness, data as-of month, `llm_required: false` |
| `POST /simulation/validate` | Schema validation, deterministic dry run, invariants, Reality Guard tier |
| `POST /simulation/run` | Deterministic baseline vs scenario trajectories |
| `POST /simulation/monte-carlo` | Statistics, percentile bands (not confidence intervals), optional uncertainty decomposition (`decompose: true`) |
| `POST /scenario/compare` | Baseline plus up to 3 scenarios (4 total) under common random numbers |
| `GET /model/status` | Versions, transition model in use, limits, variable registry |
| `GET /model/evaluate` | Stored metrics, backtests, guard probes |

Limits: horizon 1..36 months, 10..2000 paths, up to 4 scenarios including baseline, 4 interventions each, total work n_paths x horizon x runs <= 100,000 path-months, 64 KB body, 30 requests per minute per IP (in-memory, per instance, so not a global limit on serverless). Errors are JSON `{error: {code, message, run_id}}` without stack traces. One JSON log line per request: run id, method, path, status, duration, seed, engine/data/model version. No request bodies or secrets are logged.
