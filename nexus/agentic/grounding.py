"""Output guardrail: every number in an explanation must match evidence (or the user's own request)."""
from __future__ import annotations

import re

NUM = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?")
PCT_LABEL = re.compile(r"\bp(?:5|10|25|50|75|90|95)\b", re.I)
NEGATION = re.compile(r"\b(not|no|never|nor|neither|rather than|instead of)\b", re.I)
EVID_ID = re.compile(r"\bE\d+\b")
BANNED = re.compile(r"\b(probabilit\w*|likelihood|likely|chance[s]?|confidence interval[s]?|guarantee\w*|will cause|causes|caused)\b", re.I)


def numbers_in(text: str) -> list[tuple[str, float]]:
    text = PCT_LABEL.sub(" ", EVID_ID.sub(" ", text))
    text = re.sub(r"\b(19|20)\d{2}-\d{2}(-\d{2})?\b", " ", text)  # ISO months/dates
    return [(m.group(0), float(m.group(0).replace(",", "").replace("+", ""))) for m in NUM.finditer(text)]


def _decimals(tok: str) -> int:
    return len(tok.split(".")[1]) if "." in tok else 0


def matches(tok: str, x: float, v: float) -> bool:
    half = 0.5 * 10 ** (-_decimals(tok))
    for cand in (v, abs(v)):
        if abs(abs(x) - abs(cand)) <= max(half, 0.005 * abs(cand)) and (abs(cand) > 0 or x == 0):
            return True
    return False


def check(fields: dict[str, str], sheet: list[dict], allowed_extra: list[float]) -> dict:
    claims, bad, lang = [], [], []
    for fname, text in fields.items():
        if not text:
            continue
        for m in BANNED.finditer(text):
            if NEGATION.search(text[max(0, m.start() - 30):m.start()]):
                continue  # e.g. "not probabilities or confidence intervals"
            lang.append({"field": fname, "phrase": m.group(0)})
        for tok, x in numbers_in(text):
            hit = next((it for it in sheet if matches(tok, x, it["value"])), None)
            if hit:
                claims.append({"field": fname, "text": tok, "evidence_id": hit["id"], "tool": hit["tool"],
                               "tool_call_id": hit["tool_call_id"], "run_id": hit["run_id"], "value": hit["value"]})
            elif any(abs(x - a) < 1e-9 for a in allowed_extra) or (float(x).is_integer() and 1978 <= x <= 2026):
                claims.append({"field": fname, "text": tok, "evidence_id": None, "source": "user_request_or_date"})
            else:
                bad.append({"field": fname, "text": tok})
    return {"ok": not bad and not lang, "claims": claims, "ungrounded_numbers": bad, "language_violations": lang}


def explanation_fields(exp) -> dict[str, str]:
    d = exp.model_dump()
    out = {}
    for k, v in d.items():
        if k == "evidence_ids_used":
            continue
        if isinstance(v, list):
            for i, s in enumerate(v):
                out[f"{k}[{i}]"] = s
        else:
            out[k] = v or ""
    return out
