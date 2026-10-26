<p align="center">
  <img src="logo.png" alt="NEXUS // WORLD logo" width="180">
</p>

<h1 align="center">NEXUS // WORLD</h1>
<p align="center"><b>Synthetic World Intelligence Engine</b><br>Simulate tomorrow before you build it.</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.13-blue">
  <img alt="FastAPI" src="https://img.shields.io/badge/API-FastAPI-009688">
  <img alt="scikit-learn" src="https://img.shields.io/badge/ML-scikit--learn-f7931e">
  <img alt="TensorFlow" src="https://img.shields.io/badge/offline-TensorFlow-ff6f00">
  <img alt="Status" src="https://img.shields.io/badge/phase-4%20frontend-lightgrey">
</p>

A hybrid simulator of US monthly energy and mobility: what happens to miles driven, fuel use, CO2 and household energy burden if gasoline, electricity, income or unemployment change? A learned transition model fitted on public FRED data, combined with accounting identities, household-type agents, Monte Carlo percentile ranges and a Reality Guard that flags extrapolation.

- Engine, API and tests: see `docs/PHASE-2-IMPLEMENTATION.md`
- Data, metrics, backtests and limitations: see `docs/DATA-AND-MODEL.md`
- Frontend console (IMPLEMENTED, Next.js, not deployed): see `docs/PHASE-4-FRONTEND.md`.
- Agent layer (IMPLEMENTED: Supervisor, Model Critic, Explanation, Policy Arena, grounding; PLANNED: deployment): see `docs/PHASE-3-AGENTS.md`. Copy `.env.example` to `.env` for a key; without one the API runs engine-only.

Quick start (Windows):
```
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
.venv\Scripts\uvicorn nexus.api.app:app --port 8000
```
Outputs are simulations under stated assumptions, not forecasts or advice.
