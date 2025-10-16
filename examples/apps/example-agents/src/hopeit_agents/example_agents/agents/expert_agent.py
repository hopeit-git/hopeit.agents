"""Agent that can receive expressions with numbers and variables, creates random numbers
for the variables and solve sums
"""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects.payload import Payload

from hopeit_agents.agent_toolkit.agents.agent_config import create_agent_config
from hopeit_agents.agent_toolkit.agents.prompts import render_prompt
from hopeit_agents.agent_toolkit.app.steps.agent_loop import (
    AgentLoopConfig,
    AgentLoopPayload,
    AgentLoopResult,
    agent_with_tools_loop,
)
from hopeit_agents.agent_toolkit.mcp.agent_tools import (
    resolve_tools,
    tool_descriptions,
)
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
    summary="example-agents: expert agent that can generate random number an solve sums",
    payload=(ExpertAgentRequest, "Agent task request"),
    responses={200: (ExpertAgentResponse, "Aggregated agent response")},
)

__mcp__ = event_tool_api(
    payload=(ExpertAgentRequest, "Agent task description"),
    response=(ExpertAgentResponse, "Aggregated agent response"),
)


async def init_conversation(payload: ExpertAgentRequest, context: EventContext) -> AgentLoopPayload:
    """Prepare the expert agent conversation and tool configuration."""
    agent_settings = context.settings(key="expert_agent_llm", datatype=AgentSettings)
    mcp_settings = context.settings(key="mcp_client_example_tools", datatype=MCPClientConfig)

    with open(agent_settings.system_prompt_template) as f:
        system_prompt_template = f.read()
    with open(agent_settings.tool_prompt_template) as f:
        tool_prompt_template = f.read()

    agent_config = create_agent_config(
        name=agent_settings.agent_name,
        prompt_template=system_prompt_template,
        variables={},
        enable_tools=True,
        tools=agent_settings.allowed_tools,
        tool_prompt_template=tool_prompt_template,
    )
    tools = await resolve_tools(
        mcp_settings,
        context,
        agent_id=agent_config.key,
        allowed_tools=agent_config.tools,
    )
    completion_config = CompletionConfig(available_tools=tools)
    result_schema = _datatype_schema("", ExpertAgentResults)
    conversation = build_conversation(
        None,
        message=payload.user_message,
        system_prompt=render_prompt(
            agent_config,
            {
                "expert_agent_result_schema": Payload.to_json(result_schema),
                "tool_descriptions": tool_descriptions(
                    tools, include_schemas=agent_settings.include_tool_schemas_in_prompt
                ),
            },
            include_tools=agent_config.enable_tools,
        ),
    )
    return AgentLoopPayload(
        conversation=conversation,
        user_context={},
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
