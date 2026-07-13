"""Sequential Hopeit workflow coordinating the main and expert agents."""

import json
from typing import Any

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject
from pydantic_ai import Agent
from pydantic_ai.models import Model

from hopeit_agents.agent_model import SETTINGS_KEY, AgentModelSettings, build_agent_model
from hopeit_agents.example_agents.agents.expert_agent import create_expert_agent
from hopeit_agents.example_agents.models import (
    AgentRequest,
    AgentResponse,
    AgentUsage,
    ExpertAgentResults,
    agent_usage,
    combine_usage,
)
from hopeit_agents.example_agents.settings import (
    AgentRunSettings,
    load_instructions,
    usage_limits,
)
from hopeit_agents.example_agents.tools import ExpertAgentDeps

MAIN_SETTINGS_KEY = "main_agent"
EXPERT_SETTINGS_KEY = "expert_agent"

__steps__ = ["prepare_agents", "plan_expression", "solve_expression", "build_response"]

__api__ = event_api(
    summary="Solve a natural-language integer addition task through agent delegation",
    payload=(AgentRequest, "Natural-language agent task"),
    responses={200: (AgentResponse, "Main-agent answer and canonical history")},
)


@dataobject
@dataclass
class ExpressionPlan:
    """Typed output passed from the main agent to the expert agent."""

    expression: str


@dataobject
@dataclass
class PreparedAgents:
    """Serializable configuration for the main-agent planning step."""

    request: AgentRequest
    model_settings: AgentModelSettings
    main_settings: AgentRunSettings
    expert_settings: AgentRunSettings
    main_instructions: str
    expert_instructions: str


@dataobject
@dataclass
class ExpertAgentTask:
    """Typed hand-off from the main agent step to the expert agent step."""

    expression: str
    conversation_id: str
    metadata: dict[str, Any]
    main_history_json: str
    main_usage: AgentUsage
    model_settings: AgentModelSettings
    expert_settings: AgentRunSettings
    expert_instructions: str


@dataobject
@dataclass
class MainAgentExecution:
    """Serializable result passed to the final response step."""

    expression: str
    conversation_id: str
    results: ExpertAgentResults
    history_json: str
    usage: AgentUsage


def create_main_agent(model: Model, instructions: str) -> Agent[None, ExpressionPlan]:
    """Create the main agent that produces a typed expert-agent task."""
    return Agent(
        model,
        name="main_agent",
        output_type=ExpressionPlan,
        instructions=instructions,
    )


async def prepare_agents(payload: AgentRequest, context: EventContext) -> PreparedAgents:
    """Resolve both agents' settings before executing the workflow."""
    main_settings = context.settings(key=MAIN_SETTINGS_KEY, datatype=AgentRunSettings)
    expert_settings = context.settings(key=EXPERT_SETTINGS_KEY, datatype=AgentRunSettings)
    return PreparedAgents(
        request=payload,
        model_settings=context.settings(key=SETTINGS_KEY, datatype=AgentModelSettings),
        main_settings=main_settings,
        expert_settings=expert_settings,
        main_instructions=load_instructions(main_settings),
        expert_instructions=load_instructions(expert_settings),
    )


async def plan_expression(
    payload: PreparedAgents,
    context: EventContext,
) -> ExpertAgentTask:
    """Run the main agent and pass its typed expression to the expert step."""
    agent = create_main_agent(
        build_agent_model(payload.model_settings),
        payload.main_instructions,
    )
    result = await agent.run(
        payload.request.user_message,
        usage_limits=usage_limits(payload.main_settings),
        conversation_id=payload.request.conversation_id,
        metadata=payload.request.metadata,
    )
    return ExpertAgentTask(
        expression=result.output.expression,
        conversation_id=result.conversation_id,
        metadata=payload.request.metadata,
        main_history_json=result.all_messages_json().decode("utf-8"),
        main_usage=agent_usage(result.usage),
        model_settings=payload.model_settings,
        expert_settings=payload.expert_settings,
        expert_instructions=payload.expert_instructions,
    )


async def solve_expression(
    payload: ExpertAgentTask,
    context: EventContext,
) -> MainAgentExecution:
    """Run the expert agent as the next explicit Hopeit workflow step."""
    agent = create_expert_agent(
        build_agent_model(payload.model_settings),
        payload.expert_instructions,
    )
    result = await agent.run(
        payload.expression,
        deps=ExpertAgentDeps(),
        usage_limits=usage_limits(payload.expert_settings),
        conversation_id=payload.conversation_id,
        metadata=payload.metadata,
    )
    history = [
        *json.loads(payload.main_history_json),
        *json.loads(result.all_messages_json()),
    ]
    return MainAgentExecution(
        expression=payload.expression,
        conversation_id=result.conversation_id,
        results=result.output,
        history_json=json.dumps(history),
        usage=combine_usage(payload.main_usage, agent_usage(result.usage)),
    )


async def build_response(
    payload: MainAgentExecution,
    context: EventContext,
) -> AgentResponse:
    """Render the typed expert result as the public main-agent response."""
    values = ", ".join(f"{item.expr} = {item.value}" for item in payload.results.expr_values)
    return AgentResponse(
        conversation_id=payload.conversation_id,
        output=f"Expression `{payload.expression}` evaluated to: {values}",
        history_json=payload.history_json,
        usage=payload.usage,
    )
