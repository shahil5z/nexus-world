"""Agent definitions (openai-agents SDK, agents-as-tools pattern)."""
from __future__ import annotations

import json
import os

from agents import Agent, ModelSettings

from nexus.agentic import prompts
from nexus.agentic.config import BUDGET, model_name
from nexus.agentic.schemas import CriticOutput, Explanation, ScenarioIntent
from nexus.agentic.tools import sdk_tools
from nexus.agentic.trace import ContextHooks

SUPERVISOR_TOOLS = ["list_variables", "get_world_state", "get_causal_context", "validate_scenario"]


def _settings(max_tokens: int) -> ModelSettings:
    kw = {"max_tokens": max_tokens, "parallel_tool_calls": False}
    eff = os.environ.get("NEXUS_OPENAI_REASONING", "low").strip()
    if eff and eff != "none":
        from openai.types.shared import Reasoning
        kw["reasoning"] = Reasoning(effort=eff)
    return ModelSettings(**kw)


def build(model=None) -> dict[str, Agent]:
    m = model or model_name()
    critic = Agent(name="ModelCritic", instructions=prompts.instructions("critic"), model=m,
                   tools=sdk_tools(["assess_evidence"]), output_type=CriticOutput,
                   model_settings=_settings(BUDGET.critic_max_output_tokens * 4))

    async def keep_critic(result) -> str:
        ctx = result.context_wrapper.context
        ctx.critic_called = True
        ctx.critic_output = result.final_output
        return json.dumps(result.final_output.model_dump())

    critic_tool = critic.as_tool("model_critic", "Skeptical review of the evidence; returns verdict OK, CAUTION or BLOCK.",
                                 custom_output_extractor=keep_critic, max_turns=BUDGET.critic_max_turns,
                                 hooks=ContextHooks())
    explainer = Agent(name="Explanation", instructions=prompts.instructions("explainer"), model=m,
                      tools=[critic_tool] + sdk_tools(["get_causal_context"]), output_type=Explanation,
                      model_settings=_settings(BUDGET.explainer_max_output_tokens * 4))
    supervisor = Agent(name="Supervisor", instructions=prompts.instructions("supervisor"), model=m,
                       tools=sdk_tools(SUPERVISOR_TOOLS), output_type=ScenarioIntent,
                       model_settings=_settings(BUDGET.supervisor_max_output_tokens * 4))
    return {"supervisor": supervisor, "critic": critic, "explainer": explainer}
