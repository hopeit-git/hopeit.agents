"""Main agent event that coordinates the tool-enabled agent loop."""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.agent_toolkit.app.steps.agent_loop import (
    AgentLoopConfig,
    AgentLoopPayload,
    AgentLoopResult,
    agent_with_tools_loop,
)
from hopeit_agents.agent_toolkit.mcp.agent_tools import resolve_tool_prompt
from hopeit_agents.agent_toolkit.settings import AgentSettings
from hopeit_agents.example_agents.models import AgentRequest, AgentResponse
from hopeit_agents.mcp_client.models import MCPClientConfig
from hopeit_agents.model_client.conversation import build_conversation
from hopeit_agents.model_client.models import CompletionConfig

logger, extra = app_extra_logger()


__steps__ = ["init_conversation", agent_with_tools_loop.__name__, "result"]


__api__ = event_api(
    summary="example-agents: main agent",
    payload=(AgentRequest, "Agent task description"),
    responses={200: (AgentResponse, "Aggregated agent response")},
)


async def init_conversation(payload: AgentRequest, context: EventContext) -> AgentLoopPayload:
    """Build the initial conversation and tool prompt for the main agent."""
    agent_settings = context.settings(key="main_agent_llm", datatype=AgentSettings)
    mcp_settings = context.settings(key="sub_agents_mcp_client", datatype=MCPClientConfig)
    tool_prompt, tools = await resolve_tool_prompt(
        mcp_settings,
        context,
        agent_id="latest",
        enable_tools=agent_settings.enable_tools,
        template=agent_settings.tool_prompt_template,
        include_schemas=agent_settings.include_tool_schemas_in_prompt,
    )
    completion_config = CompletionConfig(available_tools=tools)
    conversation = build_conversation(
        None,
        user_message=payload.user_message,
        system_prompt=agent_settings.system_prompt,
        tool_prompt=tool_prompt,
    )
    return AgentLoopPayload(
        conversation=conversation,
        completion_config=completion_config,
        loop_config=AgentLoopConfig(max_iterations=3),
        agent_settings=agent_settings,
        mcp_settings=mcp_settings,
    )


async def result(payload: AgentLoopResult, context: EventContext) -> AgentResponse:
    """Wrap the final loop message and tool call log into a response object."""
    last_message = payload.conversation.messages[-1]
    response = AgentResponse(
        conversation=payload.conversation,
        assistant_message=last_message,
        tool_calls=payload.tool_call_log,
    )
    return response
