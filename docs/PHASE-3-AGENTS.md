# Phase 3: Agentic Intelligence Layer

Status labels: IMPLEMENTED (code exists and tests pass), MEASURED (number from a real run), PLANNED (not built).

## Principle
Tools compute every number. Agents plan, call tools, critique and explain. The pipeline, not the LLM, decides
that the Reality Guard runs before any simulation, so it cannot be skipped.

## Pipeline (IMPLEMENTED, `nexus/agentic/orchestrator.py`)
1. Input guardrail (length, control chars, prompt-injection patterns, domain scope). Rejected input makes no LLM call.
2. Supervisor agent returns a `ScenarioIntent` (structured output). It may call list_variables, get_world_state,
   get_causal_context and validate_scenario. It cannot run simulations.
3. Schema validation (`Scenario` pydantic model), then domain validation (`validate_scenario` deterministic dry run).
4. `run_reality_guard`. Tier OOD is not simulated unless the user explicitly asked for an exploratory run; then the
   output is labelled EXPLORATORY and the verdict is BLOCK (no recommendation).
5. `run_monte_carlo` (seeded) and `get_model_evaluation`. If Monte Carlo fails, `run_counterfactual` gives a partial result.
6. Evidence sheet: every citable number with id, display string, tool, tool_call_id and run_id.
7. Explanation agent calls the Model Critic (agent-as-tool), which calls `assess_evidence` (deterministic rules).
   Final verdict = max(deterministic, LLM). The LLM can escalate, never downgrade.
8. Output guardrail: every number in the explanation must match an evidence value within tolerance
   (max of 0.5% relative and half the last displayed digit), or a number from the user's own request.
   Banned wording (probability, likelihood, chance, confidence interval, guarantee, causes) unless negated.
   One regeneration with feedback, then a Python template built only from evidence display strings.

## Agents (IMPLEMENTED, `agents_def.py`, openai-agents 0.24.0)
| Agent | Output | Tools | max_turns |
|---|---|---|---|
| Supervisor | ScenarioIntent | list_variables, get_world_state, get_causal_context, validate_scenario | 5 |
| Explanation | Explanation | model_critic (Model Critic as tool), get_causal_context | 4 |
| Model Critic | CriticOutput (OK/CAUTION/BLOCK) | assess_evidence | 3 |

Prompts are versioned files in `nexus/agentic/prompts/v1/` (system, safety, domain_context, output_schema and one per role).
The prompt version and a sha256 fingerprint are stored with every run.

## Tools (IMPLEMENTED, `tools.py`)
get_world_state, list_variables, validate_scenario, run_reality_guard, run_counterfactual, run_monte_carlo,
compare_scenarios, get_model_status, get_model_evaluation, get_causal_context, assess_evidence.
Closed allowlist; pydantic argument models with extra fields forbidden; limits n_paths 50..1000 (compare 50..600),
horizon 1..36, up to 3 scenarios per compare; 14 tool calls per request. Success envelope
`{status, tool, run_id, tool_call_id, data, warnings, limitations, metadata}`; error envelope has `error {code, message}`
and never a stack trace. Results are cached by (tool, validated args) in an LRU of 256; every tool is a deterministic
function of its arguments (Monte Carlo is seeded). LLM output is never cached.

## Deterministic critic rules (`critic_rules.py`)
BLOCK: Reality Guard OOD, invariant failure. CAUTION: tier LOW or MEDIUM, VMT p10..p90 change range includes zero,
horizon over 24 months, test interval coverage under 75% (it is 69.6%, so this is a standing caveat), engine worse
than seasonal naive in any shock backtest (true for 2008), no Monte Carlo evidence.

## Knowledge layer
`knowledge/causal_graph.json` v1.0.0: the simulator's dependency edges typed learned, identity or assumption, with
pointers into the model card. It describes the model wiring, not proven causation.
`knowledge/external_notes.json`: short notes citing the FRED series pages. Labelled external knowledge; never a source of numbers.

## Memory (IMPLEMENTED, `memory.py`)
In-memory sessions (TTL 1 h, max 500). Baseline is immutable. Slots A, B, C. `modify` composes interventions on a slot
(same variable and start month replaces). `compare` runs slots against one shared baseline with one seed.
Limitation: memory and run registry are per process (serverless instances do not share them).

## Policy Arena (IMPLEMENTED, `arena.py`, `POST /agent/policy-arena`)
2..6 candidates. Objectives (all minimized, median % change vs baseline): co2_kt, vmt, fuel_spend,
energy_burden_mean, energy_burden_low_income. Default weights co2_kt 0.5 and energy_burden_low_income 0.5,
documented and returned; user weights are validated (known names, finite, non-negative, positive sum) and normalized.
Score: per-objective min-max normalization across candidates, weighted sum, lower is better, ties by name.
Pareto label over all five objectives. OOD candidates are excluded unless include_exploratory.
The LLM never chooses weights or rankings.

## Run IDs and trace
`NEXUS-YYYY-xxxxxxxx`. `GET /runs/{id}` returns scenario, seed, n_paths, model/data/prompt versions, intent, tool
evidence index, outputs, critic, explanation, grounding claims map (claim -> evidence id -> tool -> tool_call_id -> run_id)
and the runtime trace (agent, action, tool, timestamp, t_ms, duration_ms, status, summary, warnings). No prompts, model
inputs or secrets are traced. SDK trace export is disabled.

## Robustness
Budgets per request: 8 LLM calls, 60k tokens, 14 tool calls, 90 s wall time, per-agent max_turns. Any model error
(rate limit, timeout, budget, max turns, bad output) switches the rest of the request to engine-only:
deterministic regex intent parser and template explanation (mode `engine_only_fallback` or `partial_fallback`).
With no key the whole API works in engine-only mode.

## Configuration
`NEXUS_OPENAI_MODEL` (default gpt-6-luna), `NEXUS_OPENAI_REASONING` (default low), `OPENAI_API_KEY` or
`NEXUS_OPENAI_KEY_FILE` (a file outside the project), `NEXUS_DISABLE_LLM=1`. See `.env.example`.

## Endpoints
POST /agent/analyze, POST /agent/policy-arena, GET /runs/{id}, GET /agent/status (live models.retrieve check, cached 300 s,
returns only the error class name on failure).

## Measured (Windows, gpt-6-luna, reasoning low, n_paths 500, 2026-10-26)
| Query | Status | LLM calls | Tokens in/out | LLM ms | Tool ms | End to end ms |
|---|---|---|---|---|---|---|
| gasoline +20% for 12 months | ok, LOW, CAUTION | 5 | 13,827 / 1,404 | 22,924 | 1,221 (cold guard) | 24,211 |
| gasoline x3 (OOD) | not executed | 1 | 1,589 / 128 | 2,333 | 11 | 2,347 |
| gasoline x3 exploratory | ok, OOD, BLOCK | 5 | 13,807 / 1,824 | 20,374 | 25 | 20,409 |
| follow-up: add +2 pt unemployment | ok (modify), LOW, CAUTION | 6 | 15,999 / 1,537 | 19,288 | 26 | 19,327 |
| prompt injection | rejected | 0 | 0 | 0 | 0 | 0.1 |
All 27 Monte Carlo evidence values per executed run were re-derived from an independent tool call: 0 mismatches.
Engine-only mode (no key): analyze about 15 ms warm.

## Cost (INFERRED from measured tokens and VERIFIED list prices, $0.10 in / $0.50 out per 1M tokens)
About $0.002 per full analysis (13.8k in, 1.4k out), about $0.0002 for an OOD refusal. Drivers: the evidence sheet and
prompts sent to the explainer and critic (input tokens dominate), the critic as a separate agent (2 calls),
regeneration on grounding failure (one extra explainer call).

## PLANNED
UI (Phase 4), persistent run store, shared rate limiting across instances, streaming, deployment.
