"""Sequential Hopeit workflow for the structured expert agent."""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject
from pydantic_ai import Agent, AgentRetries
from pydantic_ai.models import Model

from hopeit_agents.agent_model import SETTINGS_KEY, AgentModelSettings, build_agent_model
from hopeit_agents.example_agents.models import (
    AgentRequest,
    AgentUsage,
    ExpertAgentResponse,
    ExpertAgentResults,
    agent_usage,
)
from hopeit_agents.example_agents.settings import (
    AgentRunSettings,
    agent_retries,
    load_instructions,
    usage_limits,
)
from hopeit_agents.example_agents.tools import (
    ExpertAgentDeps,
    generate_random,
    sum_two_numbers,
)

EXPERT_SETTINGS_KEY = "expert_agent"

__steps__ = ["prepare_agent", "execute_agent", "build_response"]

__api__ = event_api(
    summary="Solve integer sum expressions with generated values and typed tools",
    payload=(AgentRequest, "Expression-solving task"),
    responses={200: (ExpertAgentResponse, "Structured expression results")},
)


@dataobject
@dataclass
class PreparedExpertAgent:
    """Serializable input for the expert execution step."""

    request: AgentRequest
    model_settings: AgentModelSettings
    run_settings: AgentRunSettings
    instructions: str


@dataobject
@dataclass
class ExpertAgentExecution:
    """Serializable output from the expert execution step."""

    conversation_id: str
    results: ExpertAgentResults
    history_json: str
    usage: AgentUsage


def create_expert_agent(
    model: Model,
    instructions: str,
    *,
    retries: AgentRetries | None = None,
) -> Agent[ExpertAgentDeps, ExpertAgentResults]:
    """Create the expert agent independently of its configured model provider."""
    return Agent(
        model,
        name="expert_agent",
        deps_type=ExpertAgentDeps,
        output_type=ExpertAgentResults,
        instructions=instructions,
        tools=[generate_random, sum_two_numbers],
        retries=retries,
    )


async def prepare_agent(payload: AgentRequest, context: EventContext) -> PreparedExpertAgent:
    """Resolve settings and instructions for the expert run."""
    run_settings = context.settings(key=EXPERT_SETTINGS_KEY, datatype=AgentRunSettings)
    return PreparedExpertAgent(
        request=payload,
        model_settings=context.settings(key=SETTINGS_KEY, datatype=AgentModelSettings),
        run_settings=run_settings,
        instructions=load_instructions(run_settings),
    )


async def execute_agent(
    payload: PreparedExpertAgent,
    context: EventContext,
) -> ExpertAgentExecution:
    """Run the expert agent and project its native result for the next step."""
    agent = create_expert_agent(
        build_agent_model(payload.model_settings),
        payload.instructions,
        retries=agent_retries(payload.run_settings),
    )
    result = await agent.run(
        payload.request.user_message,
        deps=ExpertAgentDeps(),
        usage_limits=usage_limits(payload.run_settings),
        conversation_id=payload.request.conversation_id,
        metadata=payload.request.metadata,
    )
    return ExpertAgentExecution(
        conversation_id=result.conversation_id,
        results=result.output,
        history_json=result.all_messages_json().decode("utf-8"),
        usage=agent_usage(result.usage),
    )


async def build_response(
    payload: ExpertAgentExecution,
    context: EventContext,
) -> ExpertAgentResponse:
    """Convert the execution payload into the public Hopeit response."""
    return ExpertAgentResponse(
        conversation_id=payload.conversation_id,
        results=payload.results,
        history_json=payload.history_json,
        usage=payload.usage,
    )
