import os
from dataclasses import dataclass

DEFAULT_MODEL = "gpt-6-luna"  # verified on developers.openai.com/api/docs/models (2026-10-26); override via env


@dataclass(frozen=True)
class AgentBudget:
    max_llm_calls: int = 8            # per request, all agents together
    max_tool_calls: int = 14          # per request
    max_total_tokens: int = 60_000    # per request (input + output)
    wall_time_s: float = 90.0         # per request, well under Vercel Hobby 300 s
    supervisor_max_turns: int = 5
    critic_max_turns: int = 3
    explainer_max_turns: int = 4
    supervisor_max_output_tokens: int = 1200
    critic_max_output_tokens: int = 600
    explainer_max_output_tokens: int = 1800


def model_name() -> str:
    return os.environ.get("NEXUS_OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


BUDGET = AgentBudget()
MAX_QUESTION_CHARS = 2000
DEFAULT_N_PATHS = 500
