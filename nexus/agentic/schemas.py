"""Structured-output and request schemas for the agent layer."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nexus.agentic.config import MAX_QUESTION_CHARS

Driver = Literal["gasoline_price", "electricity_price", "real_income", "unemployment"]
Slot = Literal["A", "B", "C"]


class IntentIntervention(BaseModel):
    variable: Driver
    operation: Literal["multiply", "add"]
    value: float
    start_month: int
    duration_months: int


class ScenarioIntent(BaseModel):
    """Supervisor structured output. All fields required (nullable where not applicable)."""
    in_scope: bool
    action: Literal["simulate", "modify", "compare", "explain_model", "clarify", "reject"]
    scenario_name: str | None
    interventions: list[IntentIntervention]
    target_slot: Slot | None
    base_slot: Slot | None
    compare_slots: list[Slot]
    horizon_months: int | None
    user_requested_exploratory: bool
    clarification_question: str | None
    rejection_reason: str | None
    plan: list[str]


class CriticOutput(BaseModel):
    verdict: Literal["OK", "CAUTION", "BLOCK"]
    reasons: list[str]
    evidence_ids: list[str]


class Explanation(BaseModel):
    executive_result: str
    key_outcomes: list[str]
    scenario: str
    baseline: str
    counterfactual: str
    uncertainty: str
    key_modeled_drivers: str
    critique: str
    assumptions: list[str]
    limitations: list[str]
    recommendation: str | None
    evidence_ids_used: list[str]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9\-]{8,64}$")
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    n_paths: int = Field(default=500, ge=50, le=1000)
    use_llm: bool = True
