# Project Context

## Project
Name: NEXUS // WORLD
Purpose: Synthetic World Intelligence Engine. Tagline: "Simulate tomorrow before you build it."
Product vision: A domain-bounded system for counterfactual simulation and decision experimentation. Computational models (Python simulation + ML) produce every number; the LLM (Phase 3) interprets and explains, never produces numbers.
Current phase: Phase 2: Engineering foundation (complete, awaiting review)
Status: Data pipeline, world state, engine, counterfactuals, Monte Carlo, ML, validation, Reality Guard and FastAPI backend IMPLEMENTED and run locally. No UI, no LLM, no deployment, no remote repository.

## Stack (pinned in requirements*.txt, VERIFIED installed on Windows, Python 3.13.15)
- Runtime: numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, fastapi 0.162.0, uvicorn 0.54.0, pydantic 2.14.1
- Dev: pytest 9.1.1, httpx 0.28.1
- Training only: tensorflow-cpu 2.21.0 (never imported at runtime)
- PLANNED: Next.js + TypeScript 2D UI, OpenAI (model choice deferred to Phase 3), GitHub, Vercel

## Important Structure
- `nexus/` package: config, rng, data/pipeline, domain/{state,scenario}, simulation/{engine,agents,montecarlo}, ml/{train_sklearn,tf_model,inference,metrics}, guard/reality, validation/{invariants,backtest}, api/{app,schemas}
- `training/`: snapshot_data, train_all, validate, benchmark (CLIs)
- `data/raw/` FRED snapshots + manifest.json; `models/` JSON/NPZ artifacts, model_card, validation_report, benchmark
- `tests/` pytest suite + `fixtures/regression.json`; `api/index.py` Vercel entrypoint (not deployed)
- Docs: docs/PHASE-1-DISCOVERY.md, docs/PHASE-2-IMPLEMENTATION.md, docs/DATA-AND-MODEL.md, README.md
- Local git repository (no remote)

## Domain
US national, monthly: gasoline, electricity, real income, unemployment -> vehicle miles traveled, fuel, CO2, fuel spend, household energy burden.

## Architecture
Modular monolith. Hybrid simulator: learned transition (Ridge on YoY log VMT growth) + accounting identities + 9 household-type agents + Monte Carlo with common random numbers. TF ensemble trained offline, exported to NPZ, NumPy inference; not selected (did not beat baselines on validation).

## Data
Six keyless FRED CSVs (BLS, BEA, FHWA), sha256 manifest, data hash 3a305740276a45a6, window 1978-11..2026-08. Splits: train ..2012-12, val 2013..2017, test 2018-01..2026-08.

## Simulation
initialize / sample_inputs (all randomness, seeded PCG64) / apply_intervention (copy) / step (deterministic) / run / collect (identities, agents, invariants). Same seed gives identical output (tested).

## ML
Ridge (alpha 30, TimeSeriesSplit CV) used for simulation. Test MAE 0.03015 vs persistence 0.03182 and seasonal naive 0.04332; on validation persistence wins (0.00792 vs 0.00888). HGB benchmark only. TF ensemble: val 0.0102, not selected.

## Agents
Household-type agents in the simulation (assumption-based parameters). LLM agents: PLANNED (Phase 3).

## OpenAI
NOT IMPLEMENTED. Engine runs with no LLM. Key file exists at My Sources\env (contents never read).

## Validation
Invariants (fail, never clamp), identity checks, rolling-origin backtests on 3 shock windows (engine best in 1 of 3), interval coverage, uncertainty decomposition, regression fixture.

## Security
Strict Pydantic schemas (extra fields forbidden), work caps, 64 KB body cap, 30 req/min/IP in-memory limit, structured errors without stack traces, JSON logs without bodies or secrets, no uploads, no training endpoint, no pickles.

## Deployment
NOT IMPLEMENTED. Vercel limits verified in Phase 1 (Hobby 300 s, 2 GB, 500 MB Python bundle, 4.5 MB body).

## Constraints
- No TensorFlow in the runtime bundle.
- Only edit files inside the project folder. Never read or print the key file.
- No em dash characters in project files. forblog.md is never committed.

## Important Decisions
- US national monthly domain; Vercel Hobby; 2D UI; no uploads; public demo with caps (Shahil, Phase 2 brief).
- TF kept only if it beats sklearn baselines on holdout: it did not; comparison kept.
- Ridge chosen over persistence because only a driver-responsive model can represent counterfactuals.
- Pandemic months 2020-03..2021-06 excluded from the driver bootstrap pool (ASSUMPTION).

## Phase 2 Acceptance Criteria
- [x] Reproducible pipeline with manifest, validation, temporal splits, leakage test
- [x] Typed world state and variable registry
- [x] Engine, counterfactuals, Monte Carlo, uncertainty output, decomposition
- [x] sklearn models vs naive baselines; TF ensemble trained, evaluated, exported, decision recorded
- [x] Invariants, backtests, Reality Guard
- [x] FastAPI endpoints with limits, safe errors, structured logs
- [x] Tests run (52 passed on Windows and box), performance measured
- [ ] Shahil review before Phase 3

## Verification
Verified on Windows (Python 3.13.15): training, validation, 52 tests, benchmarks. Not verified: deployment, cold start, bundle size, serverless rate limiting, frontend, LLM.
