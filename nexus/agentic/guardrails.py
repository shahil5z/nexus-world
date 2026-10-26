"""Input guardrail. Runs before any LLM call; rejected input never reaches a model."""
from __future__ import annotations

import re
import unicodedata

from nexus.agentic.config import MAX_QUESTION_CHARS

INJECTION = [r"ignore (all |any |the )?(previous|prior|above) (instructions|prompts?)", r"\bsystem prompt\b",
             r"\bdeveloper (message|mode)\b", r"\bjailbreak\b", r"\byou are now\b", r"\bact as (an? )?(unrestricted|dan)\b",
             r"\b(print|reveal|show|leak)\b.{0,30}\b(api key|secret|password|token|instructions|prompt)\b",
             r"\b(execute|run|eval)\b.{0,20}\b(python|code|shell|command|script)\b", r"\bimport os\b|\bsubprocess\b|__import__",
             r"</?(system|assistant|tool)>", r"\bOPENAI_API_KEY\b"]
INJ = re.compile("|".join(INJECTION), re.I)
DOMAIN = re.compile(r"\b(gas\w*|petrol|fuel|electric\w*|energy|income|wage\w*|unemploy\w*|jobless|vmt|miles?|driv\w*|"
                    r"travel|emission\w*|co2|carbon|burden|household\w*|scenario\w*|simulat\w*|model|forecast|"
                    r"backtest\w*|accura\w*|price\w*|compare|slot|baseline|policy|tax|what if|happens)\b", re.I)


def check_input(text: str) -> tuple[bool, str | None, str]:
    """Returns (ok, reason_code, cleaned_text)."""
    if not isinstance(text, str):
        return False, "malformed", ""
    t = unicodedata.normalize("NFKC", text)
    t = "".join(ch for ch in t if ch in "\n\t" or unicodedata.category(ch)[0] != "C").strip()
    if not t:
        return False, "malformed", t
    if len(t) > MAX_QUESTION_CHARS:
        return False, "too_long", t
    if INJ.search(t):
        return False, "prompt_injection", t
    if not DOMAIN.search(t):
        return False, "out_of_scope", t
    return True, None, t
