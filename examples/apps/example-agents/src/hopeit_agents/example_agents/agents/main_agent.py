"""Sequential Hopeit workflow coordinating the main and expert agents."""

import json
from typing import Any, cast

from hopeit.app.api import event_api
from hopeit.app.client import app_call
from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject
from pydantic_ai import Agent, AgentRetries
from pydantic_ai.models import Model

from hopeit_agents.agent_model import SETTINGS_KEY, AgentModelSettings, build_agent_model
from hopeit_agents.example_agents.models import (
    AgentRequest,
    AgentResponse,
    AgentUsage,
    ExpertAgentResponse,
    ExpertAgentResults,
    agent_usage,
    combine_usage,
)
from hopeit_agents.example_agents.settings import (
    AgentRunSettings,
    agent_retries,
    load_instructions,
    usage_limits,
)

MAIN_SETTINGS_KEY = "main_agent"
EXPERT_AGENT_CONNECTION = "expert-agent"
EXPERT_AGENT_EVENT = "agents.expert_agent"

__steps__ = ["prepare_agent", "plan_expression", "call_expert_agent", "build_response"]

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
class PreparedMainAgent:
    """Serializable configuration for the main-agent planning step."""

    request: AgentRequest
    model_settings: AgentModelSettings
    main_settings: AgentRunSettings
    main_instructions: str


@dataobject
@dataclass
class ExpertAgentTask:
    """Typed hand-off from the main agent step to the expert agent step."""

    expression: str
    conversation_id: str
    metadata: dict[str, Any]
    main_history_json: str
    main_usage: AgentUsage


@dataobject
@dataclass
class MainAgentExecution:
    """Serializable result passed to the final response step."""

    expression: str
    conversation_id: str
    results: ExpertAgentResults
    history_json: str
    usage: AgentUsage


def create_main_agent(
    model: Model,
    instructions: str,
    *,
    retries: AgentRetries | None = None,
) -> Agent[None, ExpressionPlan]:
    """Create the main agent that produces a typed expert-agent task."""
    return Agent(
        model,
        name="main_agent",
        output_type=ExpressionPlan,
        instructions=instructions,
        retries=retries,
    )


async def prepare_agent(payload: AgentRequest, context: EventContext) -> PreparedMainAgent:
    """Resolve the main agent's settings before executing its workflow."""
    main_settings = context.settings(key=MAIN_SETTINGS_KEY, datatype=AgentRunSettings)
    return PreparedMainAgent(
        request=payload,
        model_settings=context.settings(key=SETTINGS_KEY, datatype=AgentModelSettings),
        main_settings=main_settings,
        main_instructions=load_instructions(main_settings),
    )


async def plan_expression(
    payload: PreparedMainAgent,
    context: EventContext,
) -> ExpertAgentTask:
    """Run the main agent and pass its typed expression to the expert step."""
    agent = create_main_agent(
        build_agent_model(payload.model_settings),
        payload.main_instructions,
        retries=agent_retries(payload.main_settings),
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
    )


async def call_expert_agent(
    payload: ExpertAgentTask,
    context: EventContext,
) -> MainAgentExecution:
    """Invoke the independently addressable expert-agent Hopeit event."""
    result = cast(
        ExpertAgentResponse,
        await app_call(
            EXPERT_AGENT_CONNECTION,
            event=EXPERT_AGENT_EVENT,
            datatype=ExpertAgentResponse,
            payload=AgentRequest(
                user_message=payload.expression,
                conversation_id=payload.conversation_id,
                metadata=payload.metadata,
            ),
            context=context,
        ),
    )
    history = [
        *json.loads(payload.main_history_json),
        *json.loads(result.history_json),
    ]
    return MainAgentExecution(
        expression=payload.expression,
        conversation_id=result.conversation_id,
        results=result.results,
        history_json=json.dumps(history),
        usage=combine_usage(payload.main_usage, result.usage),
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
