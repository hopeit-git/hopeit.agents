"""Expert agent event that orchestrates a tool-enabled conversation."""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects.payload import Payload

from hopeit_agents.agent_toolkit.app.steps.agent_loop import (
    AgentLoopConfig,
    AgentLoopPayload,
    AgentLoopResult,
    agent_with_tools_loop,
)
from hopeit_agents.agent_toolkit.mcp.agent_tools import resolve_tool_prompt
from hopeit_agents.agent_toolkit.settings import AgentSettings
from hopeit_agents.example_agents.models import (
    ExpertAgentRequest,
    ExpertAgentResponse,
    ExpertAgentResults,
)
from hopeit_agents.mcp_client.models import MCPClientConfig
from hopeit_agents.mcp_server.tools.api import _datatype_schema, event_tool_api
from hopeit_agents.model_client.conversation import build_conversation
from hopeit_agents.model_client.models import (
    CompletionConfig,
    Role,
)

logger, extra = app_extra_logger()

__steps__ = ["init_conversation", agent_with_tools_loop.__name__, "result"]

__api__ = event_api(
    summary="example-agents: expert agent",
    payload=(ExpertAgentRequest, "Agent task request"),
    responses={200: (ExpertAgentResponse, "Aggregated agent response")},
)

__mcp__ = event_tool_api(
    summary="example-agents: expert agent",
    payload=(ExpertAgentRequest, "Agent task description"),
    response=(ExpertAgentResponse, "Aggregated agent response"),
)


async def init_conversation(payload: ExpertAgentRequest, context: EventContext) -> AgentLoopPayload:
    """Prepare the expert agent conversation and tool configuration."""
    agent_settings = context.settings(key="expert_agent_llm", datatype=AgentSettings)
    mcp_settings = context.settings(key="mcp_client_example_tools", datatype=MCPClientConfig)
    tool_prompt, tools = await resolve_tool_prompt(
        mcp_settings,
        context,
        agent_id="latest",
        enable_tools=agent_settings.enable_tools,
        template=agent_settings.tool_prompt_template,
        include_schemas=agent_settings.include_tool_schemas_in_prompt,
    )
    completion_config = CompletionConfig(available_tools=tools)
    result_schema = _datatype_schema("", ExpertAgentResults)
    conversation = build_conversation(
        None,
        user_message=payload.user_message,
        system_prompt=agent_settings.system_prompt.replace(
            "{expert-agent-results-schema}",
            "```" + Payload.to_json(result_schema, indent=2) + "```",
        ),
        tool_prompt=tool_prompt,
    )
    return AgentLoopPayload(
        conversation=conversation,
        completion_config=completion_config,
        loop_config=AgentLoopConfig(max_iterations=10),
        agent_settings=agent_settings,
        mcp_settings=mcp_settings,
    )


async def result(payload: AgentLoopResult, context: EventContext) -> ExpertAgentResponse:
    """Convert the last loop message into an expert agent response payload."""
    try:
        last_message = payload.conversation.messages[-1]

        response = ExpertAgentResponse(
            conversation_id=payload.conversation.conversation_id,
            results=Payload.from_json(last_message.content or "", datatype=ExpertAgentResults)
            if last_message.role == Role.ASSISTANT
            else None,
            tool_calls=payload.tool_call_log,
            error=str(last_message.content or "") if last_message.role == Role.SYSTEM else None,
        )

    except Exception as e:
        response = ExpertAgentResponse(
            conversation_id=payload.conversation.conversation_id,
            results=None,
            error=str(e),
            assistant_message=last_message,
            tool_calls=payload.tool_call_log,
        )

    return response
