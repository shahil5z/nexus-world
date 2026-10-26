"""Grounded fallback explanation built in Python from evidence display strings only."""
from __future__ import annotations

from nexus.agentic.schemas import Explanation


def _find(sheet, label_part, prefix=""):
    for it in sheet:
        if it["label"].startswith(prefix) and label_part in it["label"]:
            return it
    return None


def describe(scen: dict) -> str:
    parts = []
    for i in scen["interventions"]:
        v = i["variable"].replace("_", " ")
        if i["operation"] == "multiply":
            pct = (i["value"] - 1) * 100
            parts.append(f"{v} {'+' if pct >= 0 else ''}{pct:g}% from month {i['start_month']} for {i['duration_months']} months")
        else:
            parts.append(f"{v} {'+' if i['value'] >= 0 else ''}{i['value']:g} points from month {i['start_month']} for {i['duration_months']} months")
    return "; ".join(parts) or "no interventions"


def simulation(sheet, scen, tier, verdict, reasons, horizon, exploratory, prefix="") -> Explanation:
    def g(part):
        it = _find(sheet, part, prefix)
        return (it["display"], it["id"]) if it else ("not available", None)
    ids = []
    def use(part):
        d, i = g(part)
        if i:
            ids.append(i)
        return f"{d} [{i}]" if i else d
    outcomes = []
    for lab in ("vehicle miles traveled", "CO2 emissions", "motor fuel spending", "low-income household energy burden"):
        outcomes.append(f"{lab}: median change {use(lab + ' change vs baseline, median')}, "
                        f"p10 {use(lab + ' change vs baseline, p10')} to p90 {use(lab + ' change vs baseline, p90')} of simulated paths")
    tag = "EXPLORATORY (outside training data): " if exploratory else ""
    exe = (f"{tag}In this simulation, {describe(scen)} changes simulated vehicle miles traveled by a median "
           f"{use('vehicle miles traveled change vs baseline, median')} versus the baseline over the horizon. "
           f"Reality Guard tier {tier}; critic verdict {verdict}.")
    crit = "; ".join(r["reason"] if isinstance(r, dict) else str(r) for r in reasons) or "no issues flagged by deterministic checks"
    return Explanation(
        executive_result=exe, key_outcomes=outcomes, scenario=describe(scen),
        baseline=f"Drivers held at their last observed values; simulated VMT median {use('baseline vehicle miles traveled')}.",
        counterfactual=f"Scenario VMT median {use('scenario vehicle miles traveled')}; CO2 median {use('scenario CO2 emissions')}.",
        uncertainty=(f"Ranges are p10 to p90 of {use('number of simulated paths')} simulated paths (driver block bootstrap plus "
                     "residual bootstrap). They are spreads of simulated outcomes, not probabilities or confidence intervals. "
                     f"Historical 80% interval coverage on the test period was {use('80% interval coverage on test 2018')}."),
        key_modeled_drivers="In the model, VMT growth responds to fuel price changes (current and six-month lag), electricity price, real income and unemployment changes, and its own recent growth. These are modeled associations, not proven causal effects.",
        critique=f"Verdict {verdict}: {crit}.",
        assumptions=["Drivers not intervened on follow block-bootstrapped historical paths around their last value.",
                     "Household responses scale with the aggregate response; no new behavior is learned."],
        limitations=["Simulation, not a forecast.", "Linear transition model; large shocks are extrapolation.",
                     "Energy burden uses a simplified household cost model."],
        recommendation=None, evidence_ids_used=ids)


def message(kind: str, text: str) -> Explanation:
    return Explanation(executive_result=text, key_outcomes=[], scenario="not executed", baseline="unchanged",
                       counterfactual="not executed", uncertainty="not applicable", key_modeled_drivers="not applicable",
                       critique=kind, assumptions=[], limitations=[], recommendation=None, evidence_ids_used=[])
