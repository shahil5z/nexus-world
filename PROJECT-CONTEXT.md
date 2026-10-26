# Project Context

## Project
Name: NEXUS // WORLD
Purpose: Synthetic World Intelligence Engine. Tagline: "Simulate tomorrow before you build it."
Product vision: A domain-bounded system for counterfactual simulation and decision experimentation. Computational models produce every number; LLM agents plan, critique and explain, never produce numbers.
Current phase: Phase 5: Production deployment (complete)
Status: Live at https://nexus-world-sim.vercel.app (VERIFIED). Repo: https://github.com/shahil5z/nexus-world (public). Vercel project nexus-world, Git-connected, Services layout.

## Stack (pinned, VERIFIED installed on Windows, Python 3.13.15)
- Runtime: numpy 2.5.4, pandas 3.1.0, scikit-learn 1.9.1, fastapi 0.162.0, uvicorn 0.54.0, pydantic 2.14.1, openai-agents 0.24.0, openai 3.37.0, python-dotenv 1.2.4
- Dev: pytest 9.1.1, httpx 0.28.1. Training only: tensorflow-cpu 2.21.0
- OpenAI model: gpt-6-luna (default, env NEXUS_OPENAI_MODEL), reasoning effort low
- Frontend: next 16.4.3, react 19.3.1, typescript 5.9.3, vitest 5.0.5, @playwright/test 1.64.1`n- Hosting: GitHub (shahil5z/nexus-world), Vercel Services (Beta), Python 3.13 on Vercel

## Important Structure
- `nexus/` engine (Phase 2) and `nexus/services.py` (shared cached engine, guard, backtests)
- `nexus/agentic/`: config, secrets, schemas, tools, evidence, critic_rules, grounding, guardrails, intent_fallback, template, memory, runs, arena, trace, prompts (+ prompts/v1/*.md), agents_def, orchestrator, api; knowledge/{causal_graph,external_notes}.json
- `training/agent_live_run.py` live runs, writes `reports/phase3_live.json`
- Docs: docs/PHASE-1-DISCOVERY.md, PHASE-2-IMPLEMENTATION.md, PHASE-3-AGENTS.md, DATA-AND-MODEL.md, README.md

## Domain
US national, monthly: gasoline, electricity, real income, unemployment -> vehicle miles traveled, fuel, CO2, fuel spend, household energy burden.

## Architecture
Modular monolith. Hybrid simulator (Ridge transition + identities + household agents + Monte Carlo + Reality Guard). Agent layer: input guardrail -> Supervisor (ScenarioIntent) -> schema and domain validation -> Reality Guard -> Monte Carlo -> Explanation agent with Model Critic as tool -> grounding check -> run record.

## Data / Simulation / ML
Unchanged from Phase 2: data hash 3a305740276a45a6, Ridge alpha 30, TF ensemble not selected.

## Agents
Household-type agents in the simulation. LLM agents: Supervisor, Model Critic, Explanation (IMPLEMENTED).

## OpenAI
IMPLEMENTED. Key loaded in-process from OPENAI_API_KEY or NEXUS_OPENAI_KEY_FILE; never logged or returned. Engine-only fallback on no key or any model error.

## Validation
Phase 2 validation plus: deterministic critic rules, numeric grounding of explanations against tool evidence, independent re-derivation of evidence in live runs (0 mismatches).

## Security
Phase 2 controls plus: injection and scope guardrail before any LLM call, closed tool allowlist with typed args and limits, no code execution, budgets on LLM calls, tokens, tool calls and wall time, no prompts or secrets in traces.

## Deployment
See docs/DEPLOYMENT.md. Phase 3 note: Agent deps add about 30 MB to the Python bundle (MEASURED on Windows site-packages: openai 15.2 MB, agents 10.7 MB, mcp 2.4 MB, griffe 1.3 MB). Measured analyze end to end about 20-24 s, under the 300 s Hobby limit.

## Constraints
- No TensorFlow in the runtime bundle. Only edit files inside the project folder.
- Never print, log or commit the key. No em dash characters in project files. forblog.md is never committed.

## Important Decisions
- Phase 2 decisions unchanged.
- gpt-6-luna chosen as the most cost-efficient current model (VERIFIED on OpenAI models and pricing pages 2026-10-26).
- The pipeline, not the LLM, runs the Reality Guard and simulations, so the guard cannot be skipped.
- Critic verdict is max(deterministic rules, LLM). LLM can escalate, never downgrade.
- Policy Arena ranking and weights are Python-only; default weights co2_kt 0.5, energy_burden_low_income 0.5.

## Phase 3 Acceptance Criteria
- [x] Agents SDK, agents-as-tools, versioned prompts, structured outputs
- [x] Allowlisted typed tools with envelopes and limits
- [x] Pipeline with validation, Reality Guard, OOD handling
- [x] Grounding guardrail with evidence mapping and fallback
- [x] Session memory, Policy Arena, run ids, runtime trace
- [x] Tests (115 pass on Windows, no key), live runs measured
- [ ] Shahil review before Phase 4

## Verification
Verified on Windows: 115 tests (no key), live runs with gpt-6-luna, /agent/status live check. Not verified: deployment, cold start on Vercel, shared state across instances, UI.

## Phase 4 Summary
- Next.js console in frontend/: landing, /console, /run/[id]. Real backend data only; DATA UNAVAILABLE when missing.
- Backend: vercel_app mounts API at /api; streaming analyze; suggestions and causal-graph endpoints; GET and POST rate limits split.
- vercel.json: Services web (frontend/, nextjs) and api (nexus.api.vercel_app:app). Services is Beta.
- Run store is in-memory per instance; UI degrades with an explicit not-available message.

## Phase 4 Acceptance Criteria
- [x] Landing, console, run view, Policy Arena, compare, trace
- [x] Accessibility: keyboard, focus, labels, reduced motion, chart text tables
- [x] SEO and OG metadata, favicon from logo.png (undistorted)
- [x] 121 pytest, tsc, eslint, vitest 7, next build, Playwright 3 passed with live key
- [ ] Shahil review before Phase 5 (deployment)
## Phase 5 Summary
- Audit: npm audit 0 vulnerabilities (prod deps), pip-audit no known vulnerabilities, no secrets or forblog.md/.env/.venv/node_modules in git history.
- README rewritten short; detail in docs/. Legacy api/index.py removed.
- GitHub repo created and pushed; Vercel project imported from it; every change deployed by git push.
- Env vars on Vercel: OPENAI_API_KEY (sensitive), NEXUS_OPENAI_MODEL, NEXT_PUBLIC_SITE_URL.
- Production fixes from evidence: /_next/image 404 under Services (images unoptimized), /api security headers, Python pinned to 3.13.

## Phase 5 Verification (MEASURED on production)
- /, /console, /run/[id], /api/health, /api/agent/status: 200. Live check ok with gpt-6-luna.
- Playwright against production with live key: 3 passed, 1 skipped; engine run 842 ms, AI analysis 17.8 s in UI.
- One of three live UI runs returned PARTIAL AI FALLBACK (labelled honestly); rerun passed.
- No key patterns in HTML, JS chunks or API responses.
- NOT VERIFIED: true cold start (first request after deploy took 0.38 s, possibly pre-warmed), behaviour under concurrent load, run-store persistence across instances.
