"""Main agent that delegates expression solving to the expert agent in process."""

from dataclasses import dataclass
from typing import Any

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.models import Model
from pydantic_ai.run import AgentRunResult

from hopeit_agents.agent_model import SETTINGS_KEY, AgentModelSettings, build_agent_model
from hopeit_agents.example_agents.agents.expert_agent import run_expert_agent
from hopeit_agents.example_agents.models import (
    AgentRequest,
    AgentResponse,
    ExpertAgentResults,
    agent_usage,
)
from hopeit_agents.example_agents.settings import (
    AgentRunSettings,
    load_instructions,
    usage_limits,
)
from hopeit_agents.example_agents.tools import ExpertAgentDeps

MAIN_SETTINGS_KEY = "main_agent"
EXPERT_SETTINGS_KEY = "expert_agent"

__steps__ = ["run"]

__api__ = event_api(
    summary="Solve a natural-language integer addition task through agent delegation",
    payload=(AgentRequest, "Natural-language agent task"),
    responses={200: (AgentResponse, "Main-agent answer and canonical history")},
)


@dataclass(frozen=True)
class MainAgentDeps:
    """Dependencies required by the main agent's delegation tool."""

    expert_model: Model
    expert_instructions: str
    expert_deps: ExpertAgentDeps


async def solve_expression(
    ctx: RunContext[MainAgentDeps],
    expression: str,
) -> ExpertAgentResults:
    """Delegate an integer sum expression to the expert agent."""
    result = await run_expert_agent(
        expression,
        model=ctx.deps.expert_model,
        instructions=ctx.deps.expert_instructions,
        deps=ctx.deps.expert_deps,
        limits=ctx.usage_limits,
        usage=ctx.usage,
        conversation_id=ctx.conversation_id,
    )
    return result.output


def create_main_agent(model: Model, instructions: str) -> Agent[MainAgentDeps, str]:
    """Create the main agent with one explicit agent-delegation tool."""
    return Agent(
        model,
        name="main_agent",
        deps_type=MainAgentDeps,
        instructions=instructions,
        tools=[solve_expression],
    )


async def run_main_agent(
    user_message: str,
    *,
    main_model: Model,
    expert_model: Model,
    main_instructions: str,
    expert_instructions: str,
    expert_deps: ExpertAgentDeps | None = None,
    limits: UsageLimits | None = None,
    conversation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentRunResult[str]:
    """Run the main agent and its in-process expert delegation."""
    agent = create_main_agent(main_model, main_instructions)
    return await agent.run(
        user_message,
        deps=MainAgentDeps(
            expert_model=expert_model,
            expert_instructions=expert_instructions,
            expert_deps=expert_deps or ExpertAgentDeps(),
        ),
        usage_limits=limits,
        conversation_id=conversation_id,
        metadata=metadata,
    )


async def run(payload: AgentRequest, context: EventContext) -> AgentResponse:
    """Expose the main agent as a Hopeit HTTP event."""
    model_settings = context.settings(key=SETTINGS_KEY, datatype=AgentModelSettings)
    main_settings = context.settings(key=MAIN_SETTINGS_KEY, datatype=AgentRunSettings)
    expert_settings = context.settings(key=EXPERT_SETTINGS_KEY, datatype=AgentRunSettings)
    result = await run_main_agent(
        payload.user_message,
        main_model=build_agent_model(model_settings),
        expert_model=build_agent_model(model_settings),
        main_instructions=load_instructions(main_settings),
        expert_instructions=load_instructions(expert_settings),
        limits=usage_limits(main_settings),
        conversation_id=payload.conversation_id,
        metadata=payload.metadata,
    )
    return AgentResponse(
        conversation_id=result.conversation_id,
        output=result.output,
        history_json=result.all_messages_json().decode("utf-8"),
        usage=agent_usage(result.usage),
    )
