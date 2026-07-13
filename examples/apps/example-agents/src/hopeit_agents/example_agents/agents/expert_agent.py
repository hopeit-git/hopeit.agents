"""Structured expert agent with application-local random and addition tools."""

from typing import Any

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.models import Model
from pydantic_ai.run import AgentRunResult
from pydantic_ai.usage import RunUsage

from hopeit_agents.agent_model import SETTINGS_KEY, AgentModelSettings, build_agent_model
from hopeit_agents.example_agents.models import (
    AgentRequest,
    ExpertAgentResponse,
    ExpertAgentResults,
    agent_usage,
)
from hopeit_agents.example_agents.settings import (
    AgentRunSettings,
    load_instructions,
    usage_limits,
)
from hopeit_agents.example_agents.tools import (
    ExpertAgentDeps,
    generate_random,
    sum_two_numbers,
)

EXPERT_SETTINGS_KEY = "expert_agent"

__steps__ = ["run"]

__api__ = event_api(
    summary="Solve integer sum expressions with generated values and typed tools",
    payload=(AgentRequest, "Expression-solving task"),
    responses={200: (ExpertAgentResponse, "Structured expression results")},
)


def create_expert_agent(
    model: Model,
    instructions: str,
) -> Agent[ExpertAgentDeps, ExpertAgentResults]:
    """Create the expert agent independently of its configured model provider."""
    return Agent(
        model,
        name="expert_agent",
        deps_type=ExpertAgentDeps,
        output_type=ExpertAgentResults,
        instructions=instructions,
        tools=[generate_random, sum_two_numbers],
    )


async def run_expert_agent(
    user_message: str,
    *,
    model: Model,
    instructions: str,
    deps: ExpertAgentDeps | None = None,
    limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    conversation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentRunResult[ExpertAgentResults]:
    """Run the reusable expert-agent component."""
    agent = create_expert_agent(model, instructions)
    return await agent.run(
        user_message,
        deps=deps or ExpertAgentDeps(),
        usage_limits=limits,
        usage=usage,
        conversation_id=conversation_id,
        metadata=metadata,
    )


async def run(payload: AgentRequest, context: EventContext) -> ExpertAgentResponse:
    """Expose the expert runner as a standalone Hopeit HTTP event."""
    model_settings = context.settings(key=SETTINGS_KEY, datatype=AgentModelSettings)
    run_settings = context.settings(key=EXPERT_SETTINGS_KEY, datatype=AgentRunSettings)
    result = await run_expert_agent(
        payload.user_message,
        model=build_agent_model(model_settings),
        instructions=load_instructions(run_settings),
        limits=usage_limits(run_settings),
        conversation_id=payload.conversation_id,
        metadata=payload.metadata,
    )
    return ExpertAgentResponse(
        conversation_id=result.conversation_id,
        results=result.output,
        history_json=result.all_messages_json().decode("utf-8"),
        usage=agent_usage(result.usage),
    )
