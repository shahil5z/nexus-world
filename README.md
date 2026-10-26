<p align="center">
  <img src="logo.png" alt="NEXUS // WORLD logo" width="160">
</p>

<h1 align="center">NEXUS // WORLD</h1>
<p align="center"><i>Simulate tomorrow before you build it.</i></p>

<p align="center">
  <a href="LIVE_URL"><img alt="Live demo" src="https://img.shields.io/badge/live-demo-2ea44f?style=flat-square"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.162-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="scikit-learn" src="https://img.shields.io/badge/scikit--learn-1.9-F7931E?style=flat-square&logo=scikitlearn&logoColor=white">
  <img alt="OpenAI Agents" src="https://img.shields.io/badge/OpenAI%20Agents-SDK-412991?style=flat-square&logo=openai&logoColor=white">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=nextdotjs&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5.9-3178C6?style=flat-square&logo=typescript&logoColor=white">
  <img alt="Vercel" src="https://img.shields.io/badge/Deployed%20on-Vercel-000000?style=flat-square&logo=vercel&logoColor=white">
</p>

A counterfactual simulator for US energy and mobility. Ask what happens to miles driven, fuel spend, CO2 and household energy burden if gasoline, electricity, income or jobs change, and get modeled percentile ranges instead of single guesses.

**How it works:** question → Reality Guard → Monte Carlo engine (Ridge transition model + accounting identities) → AI agents critique and explain, grounded only in computed numbers.

<p align="center">
  <img src="reports/screenshots/desktop-landing.png" alt="NEXUS // WORLD landing page" width="820">
</p>

## Quick start

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt   # Windows: .venv\Scripts\pip
.venv/bin/uvicorn nexus.api.vercel_app:app --port 8000
cd frontend && npm ci
NEXUS_BACKEND_URL=http://127.0.0.1:8000 npm run build && NEXUS_BACKEND_URL=http://127.0.0.1:8000 npm start
```

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` for AI mode. Without a key the app runs engine-only.

## Docs

- [Data and model](docs/DATA-AND-MODEL.md)
- [Engine and API](docs/PHASE-2-IMPLEMENTATION.md)
- [Agent layer](docs/PHASE-3-AGENTS.md)
- [Frontend](docs/PHASE-4-FRONTEND.md)
- [Deployment](docs/DEPLOYMENT.md)

<sub>Outputs are simulations under stated assumptions, not forecasts or advice.</sub>
