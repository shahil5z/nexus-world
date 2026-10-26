"""Deterministic critic verdict. The LLM critic may escalate it but never downgrade it."""
from __future__ import annotations

SEVERITY = {"OK": 0, "CAUTION": 1, "BLOCK": 2}


def deterministic_verdict(evidence: dict) -> dict:
    envs = [e for e in evidence.values() if e.get("status") == "ok"]
    reasons, verdict = [], "OK"

    def bump(level, why):
        nonlocal verdict
        reasons.append({"level": level, "reason": why})
        if SEVERITY[level] > SEVERITY[verdict]:
            verdict = level

    guards = [e for e in envs if e["tool"] == "run_reality_guard"]
    sims = [e for e in envs if e["tool"] in ("run_monte_carlo", "compare_scenarios")]
    evals = [e for e in envs if e["tool"] == "get_model_evaluation"]
    if any(e.get("status") == "error" and e.get("error", {}).get("code") == "invariant_violation" for e in evidence.values()):
        bump("BLOCK", "a simulation invariant failed")
    if not sims:
        bump("CAUTION", "no Monte Carlo evidence: uncertainty not quantified")
    for g in guards:
        t = g["data"]["tier"]
        if t == "OOD":
            bump("BLOCK", "Reality Guard tier OOD: the scenario is outside the data the model learned from (exploratory only)")
        elif t in ("LOW", "MEDIUM"):
            bump("CAUTION", f"Reality Guard tier {t}: partial extrapolation beyond training data")
    for s in sims:
        for name, entry in s["data"]["summary"].items():
            if name == "baseline":
                continue
            d = entry["vmt"]["pct_delta"]
            if d["p10"] < 0 < d["p90"]:
                bump("CAUTION", f"{name}: VMT change p10..p90 range includes zero (direction not robust across paths)")
        if s["data"].get("horizon_months", 24) > 24:
            bump("CAUTION", "horizon beyond 24 months exceeds the backtested window length")
    for e in evals:
        cov = e["data"]["interval80_coverage"]["test"]
        if cov < 0.75:
            bump("CAUTION", "historical 80% intervals under-covered test outcomes, so ranges may be too narrow")
        if any(v["engine_mape_pct"] > v["seasonal_naive_mape_pct"] for v in e["data"]["backtests"].values()):
            bump("CAUTION", "engine error exceeded the seasonal naive baseline in at least one historical shock backtest")
    return {"verdict": verdict, "reasons": reasons}


def combine(det: str, llm: str | None) -> str:
    if llm is None:
        return det
    return llm if SEVERITY.get(llm, 0) > SEVERITY[det] else det
