# Phase 4: Recruiter-facing frontend

Status: IMPLEMENTED and verified locally on Windows (2026-10-26). Not deployed.

## What it is
A Next.js 16.4.3 + React 19.3.1 + TypeScript 5.9.3 app in `frontend/`, styled as a restrained dark mission-control console (design tokens in `app/globals.css`, IBM Plex Sans and Mono, thin borders, subtle grid). Every number on screen comes from the FastAPI backend. Missing values render as DATA UNAVAILABLE; there are no mocks or fake progress.

## Routes
- `/` landing: tagline, LAUNCH SIMULATION, causal graph drawn from `/knowledge/causal-graph`, how it works, architecture, model evidence from `/model/evaluate`, tech stack (TensorFlow evaluated, not selected), limitations, demo notice.
- `/console`: system status, NL command with suggestions (`/agent/suggestions`), scenario builder (debounced `/simulation/validate`, run via `/simulation/monte-carlo`), Reality Guard tiers with reasons, stage indicators fed only by streamed trace events (`/agent/analyze/stream`, NDJSON), metric cards (baseline vs counterfactual, P10/P50/P90 percentile spread), fan chart (hover, arrow keys, metric switch, text table), analysis, evidence, critic, trace with real timestamps, compare baseline + A/B/C (`/scenario/compare`), local run history, Policy Arena (weights editable, ranking and Pareto from `/agent/policy-arena`). Engine-only fallback is labelled ENGINE-ONLY.
- `/run/[id]`: replays a stored run from `/runs/{id}`; shows "not available" when the instance no longer has it.

## Backend changes in Phase 4
- `nexus/api/vercel_app.py` mounts the core app at `/api`.
- Streaming analyze endpoint, suggestions, causal-graph endpoint, P5..P95 bands.
- Real trace events `critic_rules` and `template_explanation` so engine-only runs show critique and explanation stages.
- Rate limit split: POST 30/min, GET 120/min per IP. `x-real-ip` trusted only when `VERCEL` is set.

## Known limitation: run store
Run records live in process memory. On serverless, `/run/{id}` works only while the same instance is warm. The browser keeps the last 25 run summaries in localStorage (`nexus.runs.v1`) and the run view degrades to an explicit "not available on this instance" message. A shared store is PLANNED.

## Verification (MEASURED, Windows, 2026-10-26)
- pytest: 121 passed (engine-only).
- Frontend: tsc 0 errors, eslint 0 errors, vitest 7 passed, `next build` OK.
- Playwright (desktop 1440x900 + Pixel 7): 3 passed, 1 skipped (mobile spec under desktop project), with live key, mode AI AGENTS / GPT-6-LUNA. No console errors; responses scanned for secret patterns.
- Latency: engine Monte Carlo run in UI 65 ms; full live agent analyze in UI 17.7 s; causal graph GET 28 ms.
- Client JS: 653 KB total across `.next/static/chunks` (uncompressed, all routes).
- Python bundle: site-packages about 343 MB unzipped, app code about 0.85 MB; no TensorFlow in `requirements.txt`. The 500 MB Vercel Python limit is NOT VERIFIED.
- Screenshots: `reports/screenshots/` (desktop and mobile).

## Run locally
```
.venv\Scripts\python -m uvicorn nexus.api.vercel_app:app --port 8000
cd frontend
$env:NEXUS_BACKEND_URL="http://127.0.0.1:8000"; npm run build; npm start
```
`NEXUS_BACKEND_URL` must be set at build time and start time (Next rewrites).
