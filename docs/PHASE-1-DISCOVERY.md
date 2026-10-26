# NEXUS // WORLD: Phase 1 Discovery Report

Date: 2026-10-26 (Asia/Calcutta). Phase: 1 of 5 (Discovery, product definition, architecture feasibility). No implementation performed.

Evidence labels: VERIFIED, OBSERVED, MEASURED, INFERRED, PLANNED, NOT VERIFIED, UNKNOWN.

## 1. Environment discovery

| Item | Finding | Label |
| --- | --- | --- |
| Project folder | `C:\Users\Shahil\Downloads\PROJECT\Synthetic World Intelligence Engine` | VERIFIED |
| Contents before Phase 1 | `logo.png` (1,583,494 bytes, 1254x1254 px), `Thumbs.db` (40,448 bytes, Windows thumbnail cache, auto-generated) | VERIFIED |
| Hidden files | None besides the above (recursive `Get-ChildItem -Force`) | VERIFIED |
| Git | Not a git repository (`git status`: fatal: not a git repository); no branches | VERIFIED |
| README, manifests, lockfiles, Python/Node config, tests, scripts, CI, deployment config, env files, .gitignore, agent instruction files | None present | VERIFIED |
| Frameworks in use | None | VERIFIED |
| Existing user changes | Only logo.png placed by Shahil; preserved untouched | VERIFIED |
| OpenAI key file | `My Sources\env` exists (164 bytes); contents not read | VERIFIED (existence only) |
| Rulebook | 00 to 12 rule files, AGENTS.md, CLAUDE.md, GEMINI.md, README.md, RULEBOOK-MANIFEST.txt, templates, `.gitignore.template` | VERIFIED |

Rulebook files read for this phase: 00-ORCHESTRATOR, 01-PROJECT-DISCOVERY, 02-ARCHITECTURE, 12-BLOG-CONTENT, AGENTS.md, both templates, .gitignore.template. Remaining files (03 to 11) are relevant to Phases 2 to 5 and were not loaded in full, per the rulebook's context-budget rule.

Logo placement: keep `logo.png` at the root for now. In Phase 3 it will be referenced (moved only with Shahil's approval) into `apps/web/public/`. Not duplicated or transformed.

## 2. Product definition

NEXUS // WORLD is a domain-bounded counterfactual simulation engine. A user states an intervention in natural language ("What happens if gasoline prices rise 30%?"). The system:

1. Interprets it into a typed, validated `ScenarioSpec` (LLM, structured output).
2. Checks it against the calibrated envelope (Reality Guard, deterministic).
3. Builds baseline and counterfactual world states from versioned data snapshots.
4. Runs seeded Monte Carlo simulation over a monthly horizon (Python).
5. Computes distributions, deltas vs baseline, sensitivity and pathway attribution (Python).
6. Critiques results against validation metrics (Critic agent, tool-backed).
7. Explains results with every number quoted from tool output (Explanation agent, output guardrail).

Responsibility split (non-negotiable): LLM = interpretation, orchestration, critique, explanation. Python simulation/ML = all numbers.

Honest framing: outputs are "simulated outcomes", "model-based projections" and "uncertainty ranges", never predictions of the future.

### Differentiation (live sites fetched 2026-10-26, VERIFIED)

| Project | What it is (observed) | Core question |
| --- | --- | --- |
| Market Intelligence Lab | Data science case study on online-retail transactions: sales KPIs, revenue by category, order-value bands (GBP) | What happened in sales? |
| Autonomous BI Analyst | Question -> validated analysis plan; SQL and Python compute numbers on 2009 to 2011 retail data; LLM explains | What does the existing data say? |
| NEXUS // WORLD | Counterfactual simulation of a dynamic system with interventions, agents and uncertainty | What could happen if we change X, and how sure is the model? |

NEXUS shares one principle with ABI Analyst (code computes, LLM explains) but is different in kind: forward simulation of interventions, time evolution, stochastic futures, learned dynamics, OOD detection. It must not use retail data or a BI query interface.

## 3. Domain evaluation

Scores 1 (weak) to 5 (strong). INFERRED from source availability and domain knowledge.

| Domain | Data | Measurable vars | Counterfactual value | ML/TF fit | Monte Carlo | Agents | Validation | Scope | Demo | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Synthetic city economy | 2 | 3 | 4 | 3 | 4 | 5 | 1 | 2 | 5 | 29 |
| Energy + transport | 5 | 5 | 5 | 4 | 5 | 4 | 5 | 4 | 5 | 42 |
| Labor market + automation | 4 | 4 | 5 | 3 | 4 | 4 | 2 | 3 | 4 | 33 |
| Consumer economy | 4 | 4 | 3 | 4 | 4 | 3 | 3 | 3 | 3 | 31 |
| Supply chain | 2 | 3 | 4 | 3 | 5 | 4 | 2 | 3 | 4 | 30 |
| Climate / energy policy | 4 | 4 | 5 | 3 | 4 | 3 | 2 | 2 | 4 | 31 |
| Hybrid socio-economic | 3 | 4 | 5 | 3 | 4 | 5 | 1 | 1 | 5 | 31 |

Key reasons:
- Labor + automation: "AI replaces 20% of jobs" has no historical analogue, so it cannot be backtested; it is OOD by construction.
- Synthetic city / hybrid: data is synthetic, so validation would be circular.
- Supply chain: firm-level data is mostly proprietary.
- Climate policy: horizons of decades, impossible to validate in a prototype.

### Selected: US Energy + Transportation system

Scope: US national (optionally Census-region) monthly system linking gasoline, diesel and electricity prices to vehicle miles traveled, fuel consumption, EV share of new sales, household energy burden, transport CPI and CO2.

Why:
- Deep, free, official monthly time series back to 1970s to 1990s (VERIFIED: FRED VMT from 1970, GASREGW from 1990-08).
- Real natural experiments for backtesting: 2008 oil spike, 2014 to 2016 collapse, 2020 shock, 2022 spike (historical events, INFERRED usable as holdout windows).
- Interventions are concrete and numeric (price +X%, carbon fee, EV subsidy, transit fare change, efficiency standard).
- Short-run and long-run price elasticities give known reference ranges from literature for sanity checks (specific values to be sourced in Phase 2, NOT VERIFIED here).
- Natural agents: household archetypes (income, commute distance, vehicle type, urban/rural).
- Visual: flows of energy, travel and emissions over a timeline map well onto a mission-control UI.
- Labor/automation can be a later extension, explicitly flagged OOD.

### Data sources (existence VERIFIED via web 2026-10-26)

| Source | Content | URL |
| --- | --- | --- |
| EIA Open Data API v2 + bulk files | Petroleum retail prices (gasoline, diesel), electricity retail price/sales by sector and state, SEDS, STEO, AEO | https://www.eia.gov/opendata/ |
| FRED GASREGW | US regular gasoline price, weekly, 1990 to present | https://fred.stlouisfed.org/series/GASREGW |
| FRED TRFVOLUSM227NFWA | Vehicle miles traveled, monthly, 1970 to present (source FHWA) | https://fred.stlouisfed.org/series/TRFVOLUSM227NFWA |
| BLS CPI databases | CPI all items and components (motor fuel, electricity, transportation) | https://www.bls.gov/cpi/data.htm |

Candidate, NOT VERIFIED in Phase 1: FHWA NHTS (household travel microdata), Census ACS (income, commute), Argonne/AFDC EV sales, EIA CO2 coefficients. To verify in Phase 2.

Data policy: EIA API requires a free registered key (VERIFIED from page). Data will be snapshotted offline to versioned CSV/Parquet with a manifest (source URL, retrieval date, hash). No live data API calls in a user request.

## 4. Simulation strategy (PLANNED)

Hybrid, not a pure learned world model. A pure neural transition model is not defensible: about 400 to 650 monthly national observations with strong autocorrelation is far too little data, and it would not respect accounting identities.

State vector S_t (monthly): prices (gasoline, diesel, electricity), VMT, fuel consumption, EV stock share, household energy burden by archetype, transport CPI, CO2.

Transition S_{t+1} = F(S_t, A_t, exogenous_t, noise):
- Explicit rules: identities (fuel use = VMT / fleet efficiency; CO2 = fuel x emission factor; spending = price x quantity), fleet turnover, bounded shares.
- Learned components: price response of VMT and fuel demand (short and long run), EV adoption response, seasonality.
- Agents: N synthetic household archetypes (target 20 to 50 weighted types, not millions) with response functions; aggregated with weights to national totals.
- Monte Carlo: sample parameter uncertainty (bootstrap/posterior of elasticities), residual noise (empirical residuals), exogenous paths; seeded via `numpy.random.Generator`.
- Baseline vs counterfactual use common random numbers so the delta is not noise-dominated.
- Scenario comparison: up to K interventions on the same seeds.
- Horizon: up to 36 months default (scope bound).

## 5. Machine learning (PLANNED)

scikit-learn:
- Ridge/ElasticNet log-log regressions for elasticities (interpretable baseline).
- HistGradientBoosting as nonlinear benchmark.
- KMeans/GaussianMixture to derive household archetypes (if microdata available).
- IsolationForest + Mahalanobis distance for Reality Guard.
- TimeSeriesSplit cross-validation, model comparison tables.
SciPy: distributions, bootstrap CIs, KS tests for residual checks, optimisation for calibration.
SHAP: optional, only if the gradient boosting or TF model is kept; otherwise coefficients and simulation-based attribution suffice.

## 6. TensorFlow role (PLANNED, conditionally justified)

Role: a small deep ensemble (5 MLPs, Keras) learning the residual monthly transition of demand variables, Delta y_{t+1} = f(S_t, A_t, lags, month) on top of the rule-based core. Ensemble spread gives epistemic uncertainty, which feeds confidence tiers. Trained offline on CPU.

Justification test: kept only if it beats the sklearn baselines on rolling-origin holdout (MAE and interval coverage). If it does not, it is documented as a negative result and removed from the runtime path. This is the honest condition for using TensorFlow.

Deployment: weights exported to NumPy (`.npz`) and run with a pure NumPy forward pass in the API. ONNX Runtime is the fallback if layers become complex. TensorFlow is not installed in the Vercel function.

## 7. Agent architecture (PLANNED)

Smallest effective set (3 agents, manager pattern via OpenAI Agents SDK "agents as tools"):

| Agent | Job | Tools |
| --- | --- | --- |
| Supervisor | Parse request into `ScenarioSpec` (structured output), call tools, assemble result | `profile_world`, `check_reality_guard`, `run_monte_carlo`, `compare_scenarios`, `retrieve_domain_knowledge` |
| Model Critic | Check result against validation metrics, OOD status, invariant reports | `evaluate_model`, `detect_distribution_shift`, `inspect_model`, `calculate_uncertainty` |
| Explanation | Grounded narrative and recommendations; only quotes tool numbers | `generate_report` (fills a typed template) |

Rejected as separate agents: Research, Data, Policy, Simulation agents. Their work is deterministic tool code; wrapping it in extra LLM calls adds latency and cost without evidence value.

A deterministic non-LLM path (form controls -> ScenarioSpec -> tools) must work without OpenAI, so the simulation is testable and the app still functions if the API fails.

## 8. OpenAI integration (PLANNED)

- OpenAI Agents SDK (Python, `pip install openai-agents`, VERIFIED from docs) using the Responses API by default.
- Structured outputs (Pydantic) for ScenarioSpec and Report.
- Function tools with Pydantic validation (VERIFIED SDK feature).
- Input guardrail: off-domain / injection classifier; output guardrail: every number in the narrative must match a tool output value (numeric grounding check).
- Tracing: SDK built-in tracing for dev; no user data in traces in production unless disabled/redacted.
- Sessions/memory: not needed for MVP (single-shot runs). Revisit later.
- Only structured summaries (quantiles, deltas, flags) sent to the model, never raw datasets.
- Model names and pricing: UNKNOWN, choose in Phase 2.

## 9. Knowledge layer decision

GraphRAG: REJECTED. The domain's knowledge is a small, known causal structure (about 15 to 30 nodes), not a large document corpus. GraphRAG and a vector DB would add infra with no measurable benefit.

Selected instead: a static, versioned causal graph (`knowledge/causal_graph.json`) with nodes (variables), edges (sign, lag, source citation, model component). Uses: variable selection for an intervention, pathway explanation ("gasoline price -> VMT -> fuel use -> CO2"), UI graph view. Plus a small set of curated markdown notes with citations for `retrieve_domain_knowledge` (keyword lookup).

## 10. Validation, uncertainty, Reality Guard (PLANNED)

Validation:
- Backtesting: fit on data before each shock window, simulate the observed price path, compare simulated vs actual VMT/fuel use (2008, 2014 to 2016, 2022).
- Rolling-origin holdout with TimeSeriesSplit; metrics MAE, MAPE, CRPS.
- Baselines: seasonal naive and random walk; model must beat them to be reported as useful.
- Calibration: empirical coverage of 50/80/95% intervals on holdout.
- Sensitivity: one-at-a-time and Sobol-style (if affordable) on elasticities.
- Ablation: rules-only vs rules+sklearn vs rules+TF.
- Invariants (property tests): zero intervention gives delta distribution centred on 0; higher price never increases fuel demand in expectation; shares in [0,1]; energy and spending identities hold; no negative quantities.
- Reproducibility: same seed + same data hash + same model version gives byte-identical summary.

Uncertainty: report median and 5/25/75/95 quantiles from Monte Carlo; decompose into parameter (bootstrap), structural (ensemble spread), and stochastic (residual) by running variants with each source switched off.

Confidence tiers (measurable criteria, thresholds to be calibrated in Phase 2):

| Tier | Criteria (all required) |
| --- | --- |
| HIGH | Intervention within the central 90% of the historical range; Mahalanobis distance below in-sample 90th percentile; backtest MAPE for the target below threshold; 80% interval coverage within +/-10 points of nominal; horizon <= 12 months |
| MEDIUM | Within observed min-max; distance below 99th percentile; coverage within +/-20 points; horizon <= 24 months |
| LOW | Within 1.5x observed range or weak validation metrics or horizon > 24 months |
| OUT-OF-DISTRIBUTION | Outside 1.5x observed range on any driver, or distance above max in-sample, or IsolationForest flags anomaly, or unsupported variable |

Reality Guard: deterministic module run before simulation. Compares the ScenarioSpec's driver values (e.g. implied gasoline price, rate of change) with the training envelope (per-variable min/max/quantiles, joint Mahalanobis on standardized state, IsolationForest score). Output: tier, distance values, the specific violated bounds, and a fixed text. Example: +300% gasoline price implies a price far above the observed maximum since 1990, so the result is labelled OUT-OF-DISTRIBUTION and shown as exploratory. OOD runs still execute (with a cap) but cannot be shown with HIGH/MEDIUM styling.

## 11. Proposed directory tree (PLANNED)

```
/
  apps/web/                 Next.js + TypeScript UI
  api/ or backend entry     FastAPI app entrypoint for Vercel Python
  nexus/                    Python package (modular monolith)
    domain/                 ScenarioSpec, WorldState (Pydantic)
    data/                   loaders for snapshot files, manifest checks
    simulation/             rules, agents, monte_carlo, scenarios
    ml/                     sklearn models, numpy inference for TF weights
    guard/                  reality guard, confidence tiers
    validation/             backtests, metrics, invariants
    agents/                 Agents SDK definitions, tools, guardrails
    api/                    FastAPI routers, rate limiting, errors
  training/                 offline scripts (TF, sklearn), not deployed
  data/snapshots/           versioned CSV/Parquet + manifest.json
  models/                   exported artifacts (.npz, .joblib) + model cards
  knowledge/                causal_graph.json, notes/
  tests/                    unit, property, regression
  docs/
  PROJECT-CONTEXT.md, README.md, .gitignore
```

Exact Vercel layout (Services vs `/api` folder vs single FastAPI entrypoint) to be confirmed in Phase 2 against Vercel docs.

## 12. High-level architecture (PLANNED)

Layers (one repo, two deployables at most: web and Python API):

1. Presentation: Next.js mission-control UI, no secrets, calls API.
2. API / orchestration: FastAPI; validation, rate limits, run budget, streaming progress.
3. Agent system: Supervisor, Critic, Explanation (Agents SDK). Optional per request.
4. Simulation engine: rules + agents + Monte Carlo, pure Python/NumPy.
5. ML: sklearn models (joblib) and NumPy TF-ensemble inference.
6. Data / knowledge: snapshot files, causal graph, notes.
7. Validation / observability: precomputed validation reports, run logs (no PII), agent traces in dev.

Main data flows:
- Offline: sources -> snapshot -> features -> train/validate -> export artifacts + validation report -> commit.
- Online (AI path): question -> Supervisor (ScenarioSpec) -> Reality Guard -> Monte Carlo (baseline + counterfactual) -> stats -> Critic -> Explanation (grounding check) -> UI.
- Online (manual path): UI controls -> ScenarioSpec -> same tools -> UI (no LLM).

## 13. Technology decision matrix

| Technology | Purpose | Why needed | Alternative | Decision | Risk |
| --- | --- | --- | --- | --- | --- |
| Python | Simulation, ML, API | Ecosystem for science/ML | Julia, TS | Selected | Cold start with heavy deps |
| FastAPI | HTTP API | Typed, Pydantic-native, Vercel preset (VERIFIED docs) | Flask | Selected | Low |
| Pandas | Data prep | Time-series wrangling | Polars | Selected (offline + light runtime) | Bundle size |
| NumPy | Simulation core, inference | Vectorised Monte Carlo | JAX | Selected | Low |
| SciPy | Stats, bootstrap, tests | Distributions, optimisation | statsmodels | Selected | Size; may limit to offline |
| scikit-learn | Baselines, guard, clustering | Interpretable defensible models | statsmodels | Selected | Version pin for joblib artifacts |
| TensorFlow | Learned residual transition ensemble | Nonlinear dynamics + epistemic uncertainty | PyTorch, sklearn MLP | Selected offline only, conditional on beating baselines | May not beat baselines; size |
| SHAP | Feature attribution | Explainability of nonlinear models | Coefficients, permutation importance | Optional, offline only | Adds little if linear models win |
| OpenAI API | Interpretation, explanation | NL -> typed spec, narratives | Rules-only UI | Selected | Cost, latency, availability |
| OpenAI Agents SDK | Orchestration, guardrails, tracing | Managed loop and tools (VERIFIED features) | Raw Responses API | Selected | API churn; pin version |
| Next.js | Frontend | Vercel-native, SSR | Vite SPA | Selected | Low |
| TypeScript | Frontend language | Type safety for spec schemas | JS | Selected | Low |
| Three.js | 3D viewport | Possible visual world view | SVG/Canvas 2D | Deferred to Phase 3 | Performance, a11y, gimmick risk |
| Recharts | Charts, fan charts | Distribution and timeline views | visx, D3 | Selected | Custom fan charts need work |
| GraphRAG / KG | Knowledge | Pathway explanation | Static JSON causal graph | GraphRAG rejected; static graph selected | Low |
| Vector DB | Retrieval | Not needed (tiny corpus) | Keyword lookup | Rejected | None |
| Database | Persistence | Not needed for MVP (stateless runs) | Neon Postgres later for saved scenarios | Rejected for MVP | Shareable runs need it later |
| Vercel | Hosting | Required target | Render, Fly | Selected (Phase 5) | Duration, size limits |
| GitHub | Source | Required, git-connected deploy | GitLab | Selected (Phase 5 push) | Secret leakage, mitigated by .gitignore |

## 14. Deployment feasibility (Vercel docs fetched 2026-10-26)

VERIFIED from https://vercel.com/docs/functions/limitations:
- Max duration: Hobby 300 s (default and max); Pro/Enterprise 300 s default, 800 s max, 1800 s beta.
- Memory: Hobby 2 GB / 1 vCPU; Pro/Enterprise up to 4 GB / 2 vCPU.
- Bundle size: 250 MB uncompressed, 500 MB for Python; large functions up to 5 GB (beta).
- Request/response body: 4.5 MB.

VERIFIED from https://vercel.com/docs/functions/runtimes/python:
- Python 3.12 (default), 3.13, 3.14; FastAPI detected via `pyproject.toml`/`requirements.txt`; entrypoints `app.py`, `index.py`, `main.py` etc. or `tool.vercel.entrypoint`; streaming supported; no tree-shaking; `excludeFiles` supported; "Services" for Python backend + frontend in one project.

TensorFlow: `tensorflow-cpu` 2.21.0 is current on PyPI (VERIFIED). Installed size not measured; INFERRED that TF plus its dependencies would consume most or all of the 500 MB budget and slow cold starts. Decision: never ship TF at runtime; export weights.

Realistic architecture: Next.js frontend + one FastAPI Python function with NumPy, scikit-learn, minimal SciPy, openai-agents. Per-request budget: Monte Carlo of about 1,000 paths x 36 months x ~50 archetypes in NumPy is INFERRED to run in seconds; NOT MEASURED, to be benchmarked in Phase 2. Agent path adds several LLM round trips (latency UNKNOWN). Cold start: NOT MEASURED.
Hard caps: max paths, horizon, scenarios per request, so worst case stays far below 300 s.

Deployment rule: GitHub first, then Vercel git-connected deploy, Phase 5 only.

## 15. Decisions needing Shahil's confirmation

1. Domain: US national Energy + Transportation (vs UK/EU with ONS/Eurostat data).
2. Geography granularity: national only for MVP, or Census regions.
3. Vercel plan: Hobby (300 s, 2 GB) or Pro. Architecture assumes Hobby.
4. TensorFlow kept conditionally (removed if it loses to baselines): acceptable?
5. OpenAI model choice and per-request cost ceiling.
6. Allow user CSV uploads? Recommended: no for MVP.
7. Public live demo with rate limiting and an LLM spend cap, or demo-key gate.
8. Three.js viewport in scope or 2D only.

## 16. Security threat assessment

| Threat | Mitigation (PLANNED) |
| --- | --- |
| API key exposure | `OPENAI_API_KEY` server-side env only (Vercel env vars); never in Next.js client bundle; `.env*` gitignored; local key file never committed or read by code paths that log |
| Prompt injection | LLM output only reaches typed tools via Pydantic schemas with bounds; no free-form tool args; input guardrail; retrieved notes are curated static files |
| Uploaded data | No uploads in MVP; if later: CSV only, size cap below 4.5 MB, schema validation, no pickle/joblib from users |
| Arbitrary code execution | No eval/exec, no dynamic imports, no user-provided formulas; model artifacts only from repo |
| Resource exhaustion | Caps on paths, horizon, scenarios; timeouts; request size limits |
| API/LLM abuse | Per-IP rate limiting (method to verify: Vercel Firewall or in-app), daily LLM spend cap, manual path works without LLM |
| Privacy | No accounts, no PII, aggregate public data; logs store scenario params and hashes only |
| Logging | No keys or full prompts in production logs; tracing redacted or off in prod |

## 17. UI/UX direction (PLANNED, Phase 3)

2050 scientific mission control, not SaaS: dark instrument-panel aesthetic, monospace telemetry, the NEXUS logo as identity. Panels: World State, Simulation Viewport (flow diagram of energy -> travel -> emissions), Timeline with fan charts, Counterfactual Controls, Policy Arena (scenario comparison), AI Command Console, Agent Activity trace, Reality Guard status lamp (HIGH/MEDIUM/LOW/OOD), Model Health (validation metrics), Evidence/trace drawer. Uncertainty shown as bands, never single lines. Accessibility (contrast, keyboard) per rulebook 09.

## 18. Key risks

1. Learned components may not beat simple baselines (mitigation: report honestly, keep rules + sklearn).
2. Monthly national data limits what can be learned; elasticity confounding (income, recessions).
3. Household archetype data (NHTS/ACS) access NOT VERIFIED.
4. Python bundle size and cold start with sklearn + SciPy (NOT MEASURED).
5. LLM latency/cost for the agent path; spend abuse on public demo.
6. Over-claiming in UI copy; mitigated by honesty glossary and tiers.
7. Agents SDK API changes; pin versions.

## 19. Phase 2 plan (not started)

1. Confirm open decisions (section 15).
2. Initialise repo locally (git init), pin Python and dependency versions after checking current releases.
3. Verify and snapshot data sources (EIA key needed, FRED, BLS, NHTS/ACS); write data manifest.
4. Define Pydantic schemas: ScenarioSpec, WorldState, SimulationResult.
5. Implement rule-based core + baseline elasticity models + Monte Carlo with seeds.
6. Implement invariants and backtest harness before any TF work.
7. Train sklearn baselines, then TF ensemble offline; compare; export weights.
8. Implement Reality Guard and calibrate tier thresholds.
9. Benchmark runtime and measure bundle size locally.
10. Update PROJECT-CONTEXT.md and forblog.md with measured evidence.
