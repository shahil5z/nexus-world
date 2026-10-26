"""Deterministic intent parser used when no LLM is available (engine-only mode). Conservative by design."""
from __future__ import annotations

import re

from nexus.agentic.schemas import IntentIntervention, ScenarioIntent

VAR_WORDS = {"gasoline_price": r"gas(?:oline)?|petrol|fuel price",
             "electricity_price": r"electric(?:ity)?|power price|kwh",
             "real_income": r"income|wages?|earnings",
             "unemployment": r"unemployment|jobless"}
UP = r"ris\w*|increas\w*|up|jump\w*|go(?:es)? up|spike\w*|higher|doubl\w*|tripl\w*|grow\w*|surg\w*"
DOWN = r"fall\w*|drop\w*|decreas\w*|down|declin\w*|lower|cut\w*|halv\w*|shrink\w*"
MODEL_Q = re.compile(r"\b(how accurate|accuracy|backtest|model (?:status|version|evaluation|card)|how good is the model|error)\b", re.I)


def _months(text, word):
    m = re.search(rf"(\d{{1,2}})\s*-?\s*(?:months?|mo)\b(?:\s+{word})?", text, re.I)
    return int(m.group(1)) if m else None


def parse(question: str) -> ScenarioIntent:
    q = question.lower()
    ivs, plan = [], ["deterministic fallback parser (no LLM)"]
    for var, pat in VAR_WORDS.items():
        if not re.search(rf"\b(?:{pat})", q):
            continue
        seg = re.search(rf"(?:{pat})[^.;]*", q).group(0)
        sign = -1 if re.search(rf"\b(?:{DOWN})\b", seg) else 1
        if re.search(r"\bdoubl", seg):
            val = 2.0
        elif re.search(r"\btripl", seg):
            val = 3.0
        elif re.search(r"\bhalv", seg):
            val = 0.5
        else:
            m = re.search(r"(\d+(?:\.\d+)?)\s*(%|percent|pct|points?|pp|x\b)", seg)
            if not m:
                continue
            n, unit = float(m.group(1)), m.group(2)
            if var == "unemployment":
                val = sign * n
            elif unit.startswith("x"):
                val = n
            else:
                val = 1 + sign * n / 100
        op = "add" if var == "unemployment" else "multiply"
        ivs.append(IntentIntervention(variable=var, operation=op, value=round(val, 6), start_month=0,
                                      duration_months=min(36, _months(seg, "") or 12)))
    if not ivs:
        if MODEL_Q.search(q):
            return _intent("explain_model", [], plan)
        return _intent("clarify", [], plan, clar="Which driver (gasoline price, electricity price, real income or unemployment) should change, by how much, and for how long?")
    dur = max(i.duration_months for i in ivs)
    h = _months(q, "horizon") if "horizon" in q else None
    expl = bool(re.search(r"\b(exploratory|stress test|stress-test|extreme)\b", q))
    return _intent("simulate", ivs, plan, horizon=min(36, max(h or 24, dur)), expl=expl)


def _intent(action, ivs, plan, clar=None, horizon=None, expl=False):
    return ScenarioIntent(in_scope=action != "reject", action=action, scenario_name=None, interventions=ivs,
                          target_slot=None, base_slot=None, compare_slots=[], horizon_months=horizon,
                          user_requested_exploratory=expl, clarification_question=clar, rejection_reason=None, plan=plan)
