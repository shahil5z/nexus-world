"""Request pipeline: NL -> intent -> schema validation -> domain validation -> Reality Guard -> simulation
-> critique -> grounded explanation. Numbers come only from tools; the LLM never computes them."""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone

from pydantic import ValidationError

from nexus.agentic import evidence as ev
from nexus.agentic import grounding, intent_fallback, runs, template
from nexus.agentic.config import BUDGET, model_name
from nexus.agentic.critic_rules import combine, deterministic_verdict
from nexus.agentic.guardrails import check_input
from nexus.agentic.memory import SESSIONS, SessionStore
from nexus.agentic.prompts import prompt_fingerprint
from nexus.agentic.schemas import CriticOutput, Explanation, ScenarioIntent
from nexus.agentic.secrets import ensure_openai_key
from nexus.agentic.tools import AgentContext, call_tool
from nexus.agentic.trace import Tracer, TraceHooks
from nexus.domain.scenario import Scenario

_AGENTS = None


def get_agents(model=None):
    global _AGENTS
    if model is not None:
        from nexus.agentic.agents_def import build
        return build(model)
    if _AGENTS is None:
        from nexus.agentic.agents_def import build
        _AGENTS = build()
    return _AGENTS


def llm_available() -> bool:
    return os.environ.get("NEXUS_DISABLE_LLM") != "1" and ensure_openai_key()


class Pipeline:
    def __init__(self, req, agents=None, force_llm: bool | None = None):
        self.req = req
        self.run_id = runs.new_run_id()
        self.tr = Tracer()
        self.ctx = AgentContext(run_id=self.run_id, tracer=self.tr, budget=BUDGET)
        self.hooks = TraceHooks(self.tr, BUDGET)
        self.ctx.hooks = self.hooks
        self.use_llm = (force_llm if force_llm is not None else (req.use_llm and llm_available()))
        self.agents = agents if agents is not None else (get_agents() if self.use_llm else None)
        self.mode = "agentic" if self.use_llm else "engine_only_fallback"
        self.warnings: list[str] = []
        self.deadline = time.perf_counter() + BUDGET.wall_time_s

    def remaining(self) -> float:
        return max(1.0, self.deadline - time.perf_counter())

    async def _run_agent(self, agent, inp: str, max_turns: int):
        from agents import RunConfig, Runner
        cfg = RunConfig(tracing_disabled=True, trace_include_sensitive_data=False)
        return await asyncio.wait_for(Runner.run(agent, inp, context=self.ctx, max_turns=max_turns, hooks=self.hooks,
                                                 run_config=cfg), timeout=self.remaining())

    def _llm_failed(self, stage: str, e: BaseException):
        name = type(e).__name__
        self.tr.add(stage, "llm_error", "error", summary=name)
        self.warnings.append(f"{stage} LLM step failed ({name}); deterministic fallback used")
        self.mode = "engine_only_fallback" if stage == "Supervisor" else "partial_fallback"
        self.use_llm = False  # no further model calls in this request after a model failure

    # ---------------- stages ----------------
    async def intent(self, question: str, session: dict) -> ScenarioIntent:
        if self.use_llm:
            payload = json.dumps({"user_message": question, "session_state": SessionStore.public(session)})
            try:
                res = await self._run_agent(self.agents["supervisor"], payload, BUDGET.supervisor_max_turns)
                it = res.final_output
                if isinstance(it, ScenarioIntent):
                    return it
                raise TypeError("supervisor returned no ScenarioIntent")
            except Exception as e:  # noqa: BLE001
                self._llm_failed("Supervisor", e)
        with self.tr.step("IntentFallback", "parse_intent") as s:
            it = intent_fallback.parse(question)
            s.summary = it.action
        return it

    async def critic(self) -> CriticOutput | None:
        if not self.use_llm:
            return None
        try:
            res = await self._run_agent(self.agents["critic"], "Review the evidence for this run.", BUDGET.critic_max_turns)
            self.ctx.critic_called = True
            self.ctx.critic_output = res.final_output
            return res.final_output
        except Exception as e:  # noqa: BLE001
            self._llm_failed("ModelCritic", e)
            return None

    async def explain(self, brief: dict, allowed: list[float], fallback: Explanation, verdict_fn) -> tuple[Explanation, dict, str]:
        sheet = self.ctx.sheet
        if self.use_llm:
            feedback = None
            for attempt in (1, 2):
                inp = json.dumps({**brief, **({"grounding_feedback": feedback} if feedback else {})}, default=str)
                try:
                    res = await self._run_agent(self.agents["explainer"], inp, BUDGET.explainer_max_turns)
                except Exception as e:  # noqa: BLE001
                    self._llm_failed("Explanation", e)
                    break
                if not self.ctx.critic_called:
                    self.tr.add("pipeline", "critic_not_called", "warning", summary="explainer skipped model_critic; called directly")
                    self.warnings.append("Explanation agent did not call the critic; the pipeline called it directly")
                    await self.critic()
                exp = res.final_output
                verdict = verdict_fn()
                if verdict == "BLOCK":
                    exp.recommendation = None
                g = grounding.check(grounding.explanation_fields(exp), sheet, allowed)
                self.tr.add("pipeline", "grounding_check", "ok" if g["ok"] else "failed",
                            summary=f"attempt {attempt}: {len(g['ungrounded_numbers'])} ungrounded, {len(g['language_violations'])} wording")
                if g["ok"]:
                    return exp, g, "llm"
                feedback = {"ungrounded_numbers": [b["text"] for b in g["ungrounded_numbers"]],
                            "banned_wording": [b["phrase"] for b in g["language_violations"]],
                            "instruction": "Use only display values from evidence_sheet and the user's own numbers; fix wording."}
            self.warnings.append("LLM explanation failed grounding or errored; grounded template used")
        self.tr.add("pipeline", "template_explanation", "ok", summary="deterministic grounded template")
        g = grounding.check(grounding.explanation_fields(fallback), sheet, allowed)
        self.tr.add("pipeline", "grounding_check", "ok" if g["ok"] else "failed", summary="template explanation")
        return fallback, g, "template"


def _allowed_numbers(question: str, scen: dict | None, extra=()) -> list[float]:
    vals = [x for _, x in grounding.numbers_in(question)] + [0, 1, 6, 10, 80, 90, 5, 95, 12, 24, 36, *extra]
    for i in (scen or {}).get("interventions", []):
        v = i["value"]
        vals += [v, abs(v), i["start_month"], i["duration_months"], i["start_month"] + i["duration_months"]]
        if i["operation"] == "multiply":
            p = round((v - 1) * 100, 6)
            vals += [p, abs(p), round(v * 100, 6)]
    return vals


def _scenario_from(intent: ScenarioIntent, session: dict) -> tuple[dict, str]:
    new = [i.model_dump() for i in intent.interventions]
    if intent.action == "modify":
        base = session["slots"].get(intent.base_slot or "")
        if not base:
            raise ValueError(f"slot {intent.base_slot} is empty; nothing to modify")
        ivs = SessionStore.compose(base["scenario"]["interventions"], new)
        slot = intent.target_slot or intent.base_slot
        name = intent.scenario_name or f"{base['scenario']['name']} modified"
    else:
        ivs, slot = new, intent.target_slot or SessionStore.free_slot(session)
        name = intent.scenario_name or "scenario " + slot
    safe = "".join(c for c in name if c.isalnum() or c in " _-.+%")[:60].strip() or f"scenario {slot}"
    if safe.lower() == "baseline":
        safe = f"scenario {slot}"
    return {"name": safe, "interventions": ivs}, slot


async def analyze(req, agents=None, force_llm=None, listener=None) -> dict:
    p = Pipeline(req, agents, force_llm)
    p.tr.listener = listener
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sid, session = SESSIONS.get_or_create(req.session_id)
    rec = {"run_id": p.run_id, "kind": "analyze", "created_utc": started, "session_id": sid, "seed": req.seed,
           "n_paths": req.n_paths, "question_chars": len(req.question)}

    def finish(status, explanation: Explanation | None, **kw):
        if explanation is not None:  # house style: no em dashes in generated text
            explanation = Explanation.model_validate_json(explanation.model_dump_json().replace("\u2014", ", "))
        stats = p.tr.stats()
        from nexus.services import get_engine
        rec.update({"status": status, "mode": p.mode, "model": model_name() if p.use_llm else None,
                    "versions": {**get_engine().version_info(), **prompt_fingerprint()},
                    "explanation": explanation.model_dump() if explanation else None, "warnings": p.warnings,
                    "session": SessionStore.public(session), "trace": p.tr.events, "metrics": stats,
                    "tool_evidence": {k: {kk: v.get(kk) for kk in ("status", "tool", "tool_call_id", "warnings", "error")}
                                      for k, v in p.ctx.evidence.items()}, **kw})
        session["history"].append({"run_id": p.run_id, "status": status})
        runs.save(rec)
        return rec

    ok, reason, q = check_input(req.question)
    p.tr.add("InputGuardrail", "check_input", "ok" if ok else "rejected", summary=reason or "passed")
    if not ok:
        return finish("rejected", template.message("input_guardrail", {
            "prompt_injection": "Request rejected: it contains instructions aimed at the system rather than a scenario question.",
            "out_of_scope": "Request rejected: outside the scope of this simulator (US driving, fuel, emissions and household energy burden).",
            "too_long": "Request rejected: the question is too long.", "malformed": "Request rejected: malformed input."}[reason]),
            rejection={"stage": "input_guardrail", "reason": reason})

    intent = await p.intent(q, session)
    rec["intent"] = intent.model_dump()
    if intent.action == "reject" or not intent.in_scope:
        return finish("rejected", template.message("supervisor", f"Request not executed: {intent.rejection_reason or 'out of scope'}."),
                      rejection={"stage": "supervisor", "reason": intent.rejection_reason})
    if intent.action == "clarify":
        return finish("needs_clarification", template.message("clarify", intent.clarification_question or "Please specify the scenario."))
    if intent.action == "explain_model":
        a = call_tool("get_model_status", {}, p.ctx)
        b = call_tool("get_model_evaluation", {}, p.ctx)
        sb = ev.SheetBuilder(p.run_id)
        if b["status"] == "ok":
            ev.add_evaluation(sb, b)
        p.ctx.sheet = sb.items
        lines = [f"{it['label']}: {it['display']} [{it['id']}]" for it in sb.items]
        exp = template.message("model_evaluation", "Model evaluation evidence (holdout and historical shock backtests).")
        exp.key_outcomes, exp.evidence_ids_used = lines, [it["id"] for it in sb.items]
        exp.limitations = ["Ridge model on aggregate monthly data; 80% intervals under-covered on the 2018-2026 test period."]
        g = grounding.check(grounding.explanation_fields(exp), sb.items, _allowed_numbers(q, None))
        return finish("ok", exp, evidence_sheet=sb.items, grounding=g, model_status=a.get("data"))

    if intent.action == "compare":
        slots = [s for s in intent.compare_slots if s in session["slots"]]
        if len(slots) < 1:
            return finish("needs_clarification", template.message("clarify", "There are no saved scenarios in those slots to compare yet."))
        scens = [session["slots"][s]["scenario"] for s in slots]
        horizon = intent.horizon_months or max(session["slots"][s]["horizon_months"] for s in slots)
        guards = [call_tool("run_reality_guard", {"scenario": s, "horizon_months": horizon}, p.ctx) for s in scens]
        ood = [s["name"] for s, g in zip(scens, guards) if g["status"] == "ok" and g["data"]["tier"] == "OOD"]
        if ood and not intent.user_requested_exploratory:
            return finish("not_executed", template.message("reality_guard", f"Comparison not run: {', '.join(ood)} is outside the training data (Reality Guard OOD). Ask for an exploratory comparison to run it anyway."))
        cmp = call_tool("compare_scenarios", {"scenarios": scens, "horizon_months": horizon, "n_paths": min(req.n_paths, 600), "seed": req.seed}, p.ctx)
        if cmp["status"] != "ok":
            return finish("error", template.message("tool_failure", f"Comparison failed: {cmp['error']['code']}."))
        sb = ev.SheetBuilder(p.run_id)
        for s in scens:
            ev.add_monte_carlo(sb, cmp, s["name"], prefix="compare ")
        p.ctx.sheet = sb.items
        det = deterministic_verdict(p.ctx.evidence)
        exp = template.message("comparison", f"Comparison of {', '.join(slots)} against the shared baseline (same seed and paths).")
        exp.key_outcomes = [f"{it['label']}: {it['display']} [{it['id']}]" for it in sb.items if "change vs baseline, median" in it["label"]]
        exp.evidence_ids_used = [it["id"] for it in sb.items]
        exp.critique = f"Verdict {det['verdict']}: " + "; ".join(r["reason"] for r in det["reasons"])
        g = grounding.check(grounding.explanation_fields(exp), sb.items, _allowed_numbers(q, None))
        return finish("ok", exp, evidence_sheet=sb.items, grounding=g, critic={"verdict": det["verdict"], "deterministic": det})

    # simulate / modify
    try:
        scen_raw, slot = _scenario_from(intent, session)
        scen = Scenario.model_validate(scen_raw)  # schema validation
    except (ValidationError, ValueError) as e:
        msg = "; ".join(x["msg"] for x in e.errors()[:3]) if isinstance(e, ValidationError) else str(e)
        p.tr.add("pipeline", "schema_validation", "rejected", summary=msg)
        return finish("invalid", template.message("schema_validation", f"Scenario not executed: {msg}."), rejection={"stage": "schema_validation", "reason": msg})
    if not scen.interventions:
        return finish("needs_clarification", template.message("clarify", "No intervention was found. Which driver should change, by how much and for how long?"))
    sj = scen.model_dump(mode="json")
    horizon = intent.horizon_months or 24
    horizon = min(36, max(horizon, max(i.start_month + i.duration_months for i in scen.interventions)))
    rec["scenario"], rec["horizon_months"], rec["slot"] = sj, horizon, slot
    v = call_tool("validate_scenario", {"scenario": sj, "horizon_months": horizon}, p.ctx)
    if v["status"] != "ok":
        return finish("invalid", template.message("domain_validation", f"Scenario not executed: {v['error']['message']}."), rejection={"stage": "domain_validation", "reason": v["error"]})
    g = call_tool("run_reality_guard", {"scenario": sj, "horizon_months": horizon}, p.ctx)
    tier = g["data"]["tier"] if g["status"] == "ok" else "UNKNOWN"
    exploratory = tier == "OOD"
    sb = ev.SheetBuilder(p.run_id)
    if g["status"] == "ok":
        ev.add_guard(sb, g)
    if tier == "OOD" and not intent.user_requested_exploratory:
        p.ctx.sheet = sb.items
        exp = template.message("reality_guard", "Scenario not executed: the Reality Guard rated it OOD (inputs outside the data the model learned from). Results would be pure extrapolation. Ask for an exploratory run to simulate it anyway, labelled as exploratory.")
        exp.scenario = template.describe(sj)
        exp.key_outcomes = [f"{it['label']}: {it['display']} [{it['id']}]" for it in sb.items]
        exp.evidence_ids_used = [it["id"] for it in sb.items]
        gr = grounding.check(grounding.explanation_fields(exp), sb.items, _allowed_numbers(q, sj))
        return finish("not_executed", exp, guard=g.get("data"), evidence_sheet=sb.items, grounding=gr,
                      rejection={"stage": "reality_guard", "reason": "OOD without exploratory label"})
    m = call_tool("run_monte_carlo", {"scenario": sj, "horizon_months": horizon, "n_paths": req.n_paths, "seed": req.seed}, p.ctx)
    e = call_tool("get_model_evaluation", {}, p.ctx)
    if m["status"] != "ok":
        p.warnings.append(f"Monte Carlo failed ({m['error']['code']}); deterministic counterfactual only")
        c = call_tool("run_counterfactual", {"scenario": sj, "horizon_months": horizon}, p.ctx)
        if c["status"] != "ok":
            return finish("error", template.message("tool_failure", "Simulation tools failed; no result."))
        for met, d in c["data"]["metrics"].items():
            sb.add(f"{met} change vs baseline, deterministic", d["pct_delta"], "%", 2, c, f"metrics.{met}.pct_delta")
        p.ctx.sheet = sb.items
        det = deterministic_verdict(p.ctx.evidence)
        exp = template.message("partial", "Partial result: deterministic counterfactual only (no uncertainty range).")
        exp.key_outcomes = [f"{it['label']}: {it['display']} [{it['id']}]" for it in sb.items]
        gr = grounding.check(grounding.explanation_fields(exp), sb.items, _allowed_numbers(q, sj))
        return finish("partial", exp, evidence_sheet=sb.items, grounding=gr, critic={"verdict": det["verdict"], "deterministic": det})
    ev.add_monte_carlo(sb, m, scen.name)
    if e["status"] == "ok":
        ev.add_evaluation(sb, e)
    else:
        p.warnings.append("model evaluation unavailable; critique uses guard and Monte Carlo only")
    p.ctx.sheet = sb.items
    det = deterministic_verdict(p.ctx.evidence)
    p.ctx.deterministic = det
    p.tr.add("pipeline", "critic_rules", "ok", summary=f"deterministic verdict {det['verdict']} ({len(det['reasons'])} reasons)")

    def verdict_now():
        llm = p.ctx.critic_output.verdict if isinstance(p.ctx.critic_output, CriticOutput) else None
        return combine(det["verdict"], llm)

    brief = {"question": q, "scenario": sj, "scenario_description": template.describe(sj), "horizon_months": horizon,
             "reality_guard_tier": tier, "exploratory": exploratory, "deterministic_critic": det,
             "evidence_sheet": [{k: it[k] for k in ("id", "label", "display")} for it in sb.items]}
    fb = template.simulation(sb.items, sj, tier, det["verdict"], det["reasons"], horizon, exploratory)
    exp, gr, source = await p.explain(brief, _allowed_numbers(q, sj, [horizon, req.n_paths]), fb, verdict_now)
    final_v = verdict_now()
    if source == "template":
        exp.critique = f"Verdict {final_v}: " + "; ".join(r["reason"] for r in det["reasons"])
        gr = grounding.check(grounding.explanation_fields(exp), sb.items, _allowed_numbers(q, sj, [horizon, req.n_paths]))
    if final_v == "BLOCK":
        exp.recommendation = None
    if exploratory and not exp.executive_result.upper().startswith("EXPLORATORY"):
        exp.executive_result = "EXPLORATORY (outside training data): " + exp.executive_result
    SessionStore.put(session, slot, sj, horizon, p.run_id)
    co = p.ctx.critic_output
    return finish("ok", exp, slot=slot, exploratory=exploratory, guard=g.get("data"), evidence_sheet=sb.items, grounding=gr,
                  explanation_source=source,
                  critic={"verdict": final_v, "deterministic": det, "llm": co.model_dump() if isinstance(co, CriticOutput) else None},
                  outputs={"tool_call_id": m["tool_call_id"], "summary": m["data"]["summary"]})


async def policy_arena(areq) -> dict:
    from nexus.agentic.arena import OBJECTIVES, normalize, rank
    run_id = runs.new_run_id()
    tr = Tracer()
    ctx = AgentContext(run_id=run_id, tracer=tr, budget=BUDGET)
    from dataclasses import replace
    ctx.budget = replace(BUDGET, max_tool_calls=4 * len(areq.candidates) + 4)
    weights, wsrc = normalize(areq.weights)
    cands = [c.model_dump(mode="json") for c in areq.candidates]
    tiers, excluded = {}, []
    for c in cands:
        g = call_tool("run_reality_guard", {"scenario": c, "horizon_months": areq.horizon_months}, ctx)
        tiers[c["name"]] = g["data"]["tier"] if g["status"] == "ok" else "UNKNOWN"
        if tiers[c["name"]] == "OOD" and not areq.include_exploratory:
            excluded.append(c["name"])
    kept = [c for c in cands if c["name"] not in excluded]
    summary = {}
    for i in range(0, len(kept), 3):
        r = call_tool("compare_scenarios", {"scenarios": kept[i:i + 3], "horizon_months": areq.horizon_months,
                                            "n_paths": areq.n_paths, "seed": areq.seed}, ctx)
        if r["status"] != "ok":
            raise RuntimeError(r["error"]["code"])
        summary.update(r["data"]["summary"])
    medians = {c["name"]: {o: summary[c["name"]][o]["pct_delta"]["median"] for o in OBJECTIVES} for c in kept}
    ranking = rank(medians, weights) if len(medians) >= 1 else []
    for row in ranking:
        n = row["candidate"]
        row["tier"] = tiers[n]
        row["exploratory"] = tiers[n] == "OOD"
        row["median_pct_delta"] = {o: round(v, 4) for o, v in medians[n].items()}
        row["p10_p90_pct_delta"] = {o: [round(summary[n][o]["pct_delta"]["p10"], 4), round(summary[n][o]["pct_delta"]["p90"], 4)] for o in OBJECTIVES}
    from nexus.services import get_engine
    rec = {"run_id": run_id, "kind": "policy_arena", "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "status": "ok", "seed": areq.seed, "n_paths": areq.n_paths, "horizon_months": areq.horizon_months,
           "candidates": cands, "weights": {"normalized": weights, "source": wsrc,
                                            "default": "co2_kt 0.5, energy_burden_low_income 0.5"},
           "scoring": "min-max normalize each weighted objective's median % change across candidates, weighted sum; lower is better; ties by name",
           "pareto_objectives": list(OBJECTIVES), "ranking": ranking, "excluded_ood": excluded,
           "versions": get_engine().version_info(), "trace": tr.events, "metrics": tr.stats(),
           "note": "Ranking is computed in Python; it is a comparison of simulated outcomes under these weights, not a policy endorsement."}
    runs.save(rec)
    return rec
